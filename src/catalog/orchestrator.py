"""
Official Metadata Ingestion Orchestrator (Phase S1-E)
Coordinates fetching NVIDIA Build pages, saving raw snapshots, parsing Ground Truth,
performing Safe Catalog Merge, and safely writing data/model_catalog.json atomically.
"""

import argparse
import copy
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union

from src.catalog.build_parser import fetch_build_html, parse_build_metadata
from src.catalog.lifecycle_parser import parse_official_lifecycle
from src.catalog.merge import merge_catalog, merge_model
from src.catalog.snapshot import save_snapshot

DEFAULT_CATALOG_PATH = Path("data") / "model_catalog.json"
DEFAULT_API_MODELS_PATH = Path("data") / "nvidia_api_models.json"
DEFAULT_SNAPSHOTS_DIR = Path("data") / "sources" / "nvidia_build" / "snapshots"


class OrchestratorSafetyError(Exception):
    """Raised when a safety fuse prevents catalog modification."""
    pass


def load_json_file(file_path: Path) -> dict[str, Any]:
    """Safely load a JSON file, returning an empty dict if not found."""
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_catalog_hash(catalog_dict: dict[str, Any]) -> str:
    """
    Calculate deterministic SHA-256 hash of catalog models,
    ignoring root updated_at and internal last_verified timestamps to detect true semantic changes.
    """
    clean_models = copy.deepcopy(catalog_dict.get("models", {}))
    for mid, entry in clean_models.items():
        if isinstance(entry, dict) and "source_metadata" in entry and isinstance(entry["source_metadata"], dict):
            entry["source_metadata"].pop("last_verified", None)

    normalized = {
        "version": catalog_dict.get("version", "3.1"),
        "models": clean_models,
    }
    dumped = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def atomic_write_catalog(target_path: Path, catalog_data: dict[str, Any]) -> None:
    """Atomically write catalog JSON data to disk using temporary file and fsync."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.parent / f".tmp_catalog_{uuid.uuid4().hex}_{target_path.name}"
    try:
        with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(catalog_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, target_path)
    except Exception as err:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise err


def validate_catalog_schema(catalog_data: dict[str, Any]) -> None:
    """Validate that the merged catalog satisfies structural integrity constraints."""
    if not isinstance(catalog_data, dict):
        raise OrchestratorSafetyError("Catalog root must be a JSON dictionary.")
    if "models" not in catalog_data or not isinstance(catalog_data["models"], dict):
        raise OrchestratorSafetyError("Catalog must contain a 'models' dictionary.")
    
    models = catalog_data["models"]
    for mid, entry in models.items():
        if not isinstance(entry, dict):
            raise OrchestratorSafetyError(f"Model entry for '{mid}' must be a dictionary.")
        if entry.get("model_id") != mid:
            raise OrchestratorSafetyError(f"Model ID mismatch: key '{mid}' != entry '{entry.get('model_id')}'.")
        if not entry.get("display_name"):
            raise OrchestratorSafetyError(f"Model entry '{mid}' is missing 'display_name'.")


def discover_target_models(
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    api_models_path: Path = DEFAULT_API_MODELS_PATH,
    filter_models: Optional[list[str]] = None,
) -> list[str]:
    """Discover all target model IDs from existing catalog and monitor baseline."""
    if filter_models:
        return [m.strip() for m in filter_models if m.strip()]

    target_set = set()

    # 1. Existing catalog models
    catalog = load_json_file(catalog_path)
    if "models" in catalog and isinstance(catalog["models"], dict):
        target_set.update(catalog["models"].keys())

    # 2. API models baseline (from V2 monitor)
    api_data = load_json_file(api_models_path)
    if "data" in api_data and isinstance(api_data["data"], list):
        for item in api_data["data"]:
            mid = item.get("id")
            if mid:
                target_set.add(mid)

    return sorted(list(target_set))


def run_official_metadata_sync(
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    api_models_path: Path = DEFAULT_API_MODELS_PATH,
    snapshots_dir: Path = DEFAULT_SNAPSHOTS_DIR,
    filter_models: Optional[list[str]] = None,
    dry_run: bool = False,
    lifecycle_only: bool = False,
    fetch_func: Callable[[str], Optional[str]] = fetch_build_html,
) -> dict[str, Any]:
    """
    Execute full official metadata synchronization pipeline.
    
    Returns:
        Summary report dict.
    """
    start_time = datetime.now(timezone.utc).isoformat()
    catalog_path = Path(catalog_path)
    api_models_path = Path(api_models_path)
    snapshots_dir = Path(snapshots_dir)

    # 1. Load current catalog
    existing_catalog = load_json_file(catalog_path)
    if not existing_catalog:
        existing_catalog = {"version": "3.1", "updated_at": start_time, "models": {}}
    
    old_hash = calculate_catalog_hash(existing_catalog)
    existing_count = len(existing_catalog.get("models", {}))

    # 2. Discover models
    target_models = discover_target_models(
        catalog_path=catalog_path,
        api_models_path=api_models_path,
        filter_models=filter_models,
    )

    total_discovered = len(target_models)
    fetched_count = 0
    parsed_count = 0
    failed_models = []
    incoming_parsed_models = []

    print(f"[INFO] Starting Official Metadata Sync: {total_discovered} target models (dry_run={dry_run})")

    # 3. Ingestion & Snapshot Pipeline
    for mid in target_models:
        html_content = fetch_func(mid)
        if not html_content:
            failed_models.append({"model_id": mid, "reason": "fetch_failed_or_404"})
            continue
        fetched_count += 1

        # Save snapshot evidence (even in dry-run, saving evidence is safe and useful)
        try:
            save_snapshot(
                model_id=mid,
                raw_html=html_content,
                base_dir=snapshots_dir,
            )
        except Exception as snap_err:
            print(f"[WARN] Failed to save snapshot for {mid}: {snap_err}", file=sys.stderr)

        # Parse Ground Truth metadata & lifecycle
        try:
            parsed_meta = parse_build_metadata(mid, html_content)
            parsed_lc = parse_official_lifecycle(mid, html_content)

            if parsed_meta:
                if parsed_lc and any(v is not None for v in parsed_lc.values() if v not in ["NVIDIA Build", "low", "medium", "high"]):
                    parsed_meta["lifecycle"] = parsed_lc
                    if "source_metadata" in parsed_meta:
                        fs = parsed_meta["source_metadata"].setdefault("field_sources", {})
                        for lk in ["availability", "official_deprecation_date", "official_retirement_date", "replacement_model_id"]:
                            if parsed_lc.get(lk):
                                fs[f"lifecycle.{lk}"] = "NVIDIA Build"

                if lifecycle_only:
                    # Strip other fields, only carry lifecycle and identity
                    parsed_meta = {
                        "model_id": mid,
                        "lifecycle": parsed_lc,
                        "source_metadata": {
                            "field_sources": {
                                f"lifecycle.{lk}": "NVIDIA Build"
                                for lk in ["availability", "official_deprecation_date", "official_retirement_date", "replacement_model_id"]
                                if parsed_lc.get(lk)
                            },
                            "last_verified": datetime.now(timezone.utc).isoformat(),
                        }
                    }

                incoming_parsed_models.append(parsed_meta)
                parsed_count += 1
            else:
                failed_models.append({"model_id": mid, "reason": "parse_returned_none"})
        except Exception as parse_err:
            failed_models.append({"model_id": mid, "reason": f"parser_exception: {parse_err}"})

    # 4. Safety Fuse Evaluations
    failure_rate = len(failed_models) / total_discovered if total_discovered > 0 else 0.0

    # Fuse 1: High failure rate protection (>50% failure on batches larger than 5)
    if total_discovered > 5 and failure_rate > 0.50:
        raise OrchestratorSafetyError(
            f"Safety Fuse Triggered: Build failure rate is {failure_rate:.1%} (>50% threshold). "
            f"Aborting catalog update to prevent systemic corruption."
        )

    # If zero models were parsed, safely return summary without modifying catalog
    if parsed_count == 0:
        print("[INFO] Zero models successfully parsed. Skipping catalog merge and write.")
        return {
            "run_at": start_time,
            "dry_run": dry_run,
            "lifecycle_only": lifecycle_only,
            "catalog_path": str(catalog_path),
            "discovered": total_discovered,
            "fetched": fetched_count,
            "parsed": 0,
            "merged": 0,
            "new": 0,
            "unchanged": total_discovered,
            "failed": len(failed_models),
            "catalog_changed": False,
            "failed_models": failed_models,
        }

    # 5. Safe Catalog Merge
    new_catalog, merge_summary = merge_catalog(existing_catalog, incoming_parsed_models)

    # Fuse 2: Catalog shrink protection
    new_count = len(new_catalog.get("models", {}))
    if new_count < existing_count:
        raise OrchestratorSafetyError(
            f"Safety Fuse Triggered: Merged catalog size ({new_count}) is smaller than original ({existing_count})."
        )

    # Fuse 3: Schema validation
    validate_catalog_schema(new_catalog)

    # Fuse 4: Mass Deprecation Spike Fuse (>20% deprecated/removed on batches > 5)
    deprecated_or_removed_count = 0
    replacement_count = 0
    for mid, m in new_catalog.get("models", {}).items():
        avail = m.get("lifecycle", {}).get("availability")
        if avail in ["deprecated", "removed"]:
            deprecated_or_removed_count += 1
        if m.get("lifecycle", {}).get("replacement_model_id"):
            replacement_count += 1

    if total_discovered > 5 and (deprecated_or_removed_count / new_count) > 0.20:
        raise OrchestratorSafetyError(
            f"Safety Fuse Triggered: Mass deprecation spike detected ({deprecated_or_removed_count}/{new_count} models deprecated/removed > 20%). "
            f"Aborting catalog update to prevent erroneous mass deprecation."
        )

    # Fuse 5: Replacement Explosion Fuse (>30% replacements on batches > 5)
    if total_discovered > 5 and (replacement_count / new_count) > 0.30:
        raise OrchestratorSafetyError(
            f"Safety Fuse Triggered: Replacement explosion detected ({replacement_count}/{new_count} models with replacements > 30%). "
            f"Aborting catalog update to protect catalog integrity."
        )

    # 6. Change Detection & Atomic Write
    new_hash = calculate_catalog_hash(new_catalog)
    catalog_has_changed = (old_hash != new_hash) and merge_summary.get("changed", False)

    if catalog_has_changed and not dry_run:
        print(f"[INFO] Writing updated catalog to {catalog_path} (created={merge_summary['total_created']}, updated={merge_summary['total_updated']})")
        atomic_write_catalog(catalog_path, new_catalog)
    elif catalog_has_changed and dry_run:
        print(f"[DRY-RUN] Catalog changes detected but skipped disk write (created={merge_summary['total_created']}, updated={merge_summary['total_updated']})")
    else:
        print("[INFO] Catalog is completely up-to-date. No changes to write.")

    # 7. Construct Summary Report
    summary_report = {
        "run_at": start_time,
        "dry_run": dry_run,
        "lifecycle_only": lifecycle_only,
        "catalog_path": str(catalog_path),
        "discovered": total_discovered,
        "fetched": fetched_count,
        "parsed": parsed_count,
        "merged": merge_summary.get("total_updated", 0),
        "new": merge_summary.get("total_created", 0),
        "unchanged": merge_summary.get("total_preserved", 0),
        "failed": len(failed_models),
        "catalog_changed": catalog_has_changed,
        "failed_models": failed_models,
    }

    return summary_report


def main():
    parser = argparse.ArgumentParser(description="NVIDIA Build Official Metadata & Lifecycle Sync Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Execute sync pipeline without modifying data/model_catalog.json")
    parser.add_argument("--lifecycle-only", action="store_true", help="Only sync official lifecycle metadata")
    parser.add_argument("--models", type=str, default=None, help="Comma-separated list of specific model IDs to sync")
    parser.add_argument("--catalog-path", type=str, default=str(DEFAULT_CATALOG_PATH), help="Path to model_catalog.json")
    parser.add_argument("--api-models-path", type=str, default=str(DEFAULT_API_MODELS_PATH), help="Path to nvidia_api_models.json")
    parser.add_argument("--snapshots-dir", type=str, default=str(DEFAULT_SNAPSHOTS_DIR), help="Path to snapshots directory")

    args = parser.parse_args()

    filter_list = [m.strip() for m in args.models.split(",")] if args.models else None

    try:
        summary = run_official_metadata_sync(
            catalog_path=Path(args.catalog_path),
            api_models_path=Path(args.api_models_path),
            snapshots_dir=Path(args.snapshots_dir),
            filter_models=filter_list,
            dry_run=args.dry_run,
            lifecycle_only=args.lifecycle_only,
        )
        print("\n=== Sync Summary Report ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    except Exception as err:
        print(f"[FATAL] Orchestrator execution failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
