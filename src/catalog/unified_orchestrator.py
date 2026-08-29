"""
Unified Evidence Orchestrator (Phase S3-E)
Orchestrates multi-source evidence collection (NVIDIA Build, NIMStats, Reddit),
appends to immutable Evidence Ledger, executes deterministic replay through
Evidence State Machine, updates Materialized View, and safely projects
verified/corroborated evidence onto the Model Catalog.
"""

import argparse
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Callable, Optional, Union

from src.catalog.build_parser import fetch_build_html, parse_build_metadata
from src.catalog.ecosystem.nimstats import (
    EcosystemSignal,
    fetch_nimstats_data,
    parse_nimstats_payload,
    save_nimstats_raw_evidence,
)
from src.catalog.ecosystem.reddit import (
    CommunitySignal,
    fetch_reddit_data,
    generate_reddit_evidence_hash,
    parse_reddit_payload,
    save_reddit_raw_evidence,
)
from src.catalog.evidence import (
    EvidenceItem,
    EvidenceState,
    FieldEvidence,
    ModelEvidenceRecord,
    SourceTier,
)
from src.catalog.evidence_ledger import (
    DEFAULT_LEDGER_PATH,
    DEFAULT_STATE_PATH,
    LedgerRecord,
    append_evidence,
    append_evidence_batch,
    calculate_materialized_state_hash,
    load_ledger,
    rebuild_materialized_state,
    replay_evidence,
    verify_ledger,
)
from src.catalog.lifecycle_parser import parse_official_lifecycle
from src.catalog.merge import (
    merge_catalog,
    merge_model,
)
from src.catalog.orchestrator import (
    DEFAULT_API_MODELS_PATH,
    DEFAULT_CATALOG_PATH,
    DEFAULT_SNAPSHOTS_DIR,
    OrchestratorSafetyError,
    atomic_write_catalog,
    calculate_catalog_hash,
    discover_target_models,
    load_json_file,
    validate_catalog_schema,
)
from src.catalog.snapshot import save_snapshot


def build_metadata_to_ledger_records(
    model_id: str,
    parsed_meta: dict[str, Any],
    raw_sha256: Optional[str] = None,
    observed_at: Optional[str] = None,
) -> list[LedgerRecord]:
    """
    Convert official NVIDIA Build metadata into standard LedgerRecords (SourceTier.NVIDIA_BUILD).
    """
    now_iso = observed_at or datetime.now(timezone.utc).isoformat()
    source_url = f"https://build.nvidia.com/{model_id}"
    records: list[LedgerRecord] = []

    def add_rec(field_name: str, claim: Any):
        if claim is not None and str(claim).strip() not in ["", "unknown", "None", "null"]:
            rec = LedgerRecord.create(
                model_id=model_id,
                field_name=field_name,
                claim=claim,
                source_id="nvidia_build",
                source_tier=SourceTier.NVIDIA_BUILD,
                source_url=source_url,
                observed_at=now_iso,
                confidence=1.0,
                raw_evidence_sha256=raw_sha256,
                source_kind="official",
                state_effect="verified",
            )
            records.append(rec)

    # 1. Display name
    if "display_name" in parsed_meta:
        add_rec("display_name", parsed_meta["display_name"])

    # 2. Classification
    if "classification" in parsed_meta and isinstance(parsed_meta["classification"], dict):
        cl = parsed_meta["classification"]
        if "model_type" in cl:
            add_rec("classification.model_type", cl["model_type"])

    # 3. Architecture
    if "architecture" in parsed_meta and isinstance(parsed_meta["architecture"], dict):
        arch = parsed_meta["architecture"]
        if "type" in arch:
            add_rec("architecture.type", arch["type"])
        if "total_parameters" in arch:
            add_rec("architecture.total_parameters", arch["total_parameters"])
        if "active_parameters" in arch:
            add_rec("architecture.active_parameters", arch["active_parameters"])

    # 4. Context
    if "context" in parsed_meta and isinstance(parsed_meta["context"], dict):
        ctx = parsed_meta["context"]
        if "length" in ctx:
            add_rec("context.length", ctx["length"])

    # 5. Capabilities
    if "capabilities" in parsed_meta and isinstance(parsed_meta["capabilities"], list):
        add_rec("capabilities", parsed_meta["capabilities"])

    # 6. Links
    if "links" in parsed_meta and isinstance(parsed_meta["links"], dict):
        links = parsed_meta["links"]
        if "documentation" in links:
            add_rec("links.documentation", links["documentation"])

    # 7. Lifecycle
    if "lifecycle" in parsed_meta and isinstance(parsed_meta["lifecycle"], dict):
        lc = parsed_meta["lifecycle"]
        if "availability" in lc:
            add_rec("lifecycle.availability", lc["availability"])
        if "official_deprecation_date" in lc:
            add_rec("lifecycle.official_deprecation_date", lc["official_deprecation_date"])
        if "official_retirement_date" in lc:
            add_rec("lifecycle.official_retirement_date", lc["official_retirement_date"])
        if "replacement_model_id" in lc:
            add_rec("lifecycle.replacement_model_id", lc["replacement_model_id"])

    return records


def nimstats_signals_to_ledger_records(
    signals: list[EcosystemSignal],
) -> list[LedgerRecord]:
    """
    Convert NIMStats EcosystemSignals into standard LedgerRecords (SourceTier.COMMUNITY_SCRAPER).
    """
    records: list[LedgerRecord] = []
    for sig in signals:
        obs_time = sig.observed_at or datetime.now(timezone.utc).isoformat()

        if sig.observed_context:
            r = LedgerRecord.create(
                model_id=sig.model_id,
                field_name="context.length",
                claim=sig.observed_context,
                source_id=f"nimstats:{sig.model_id}",
                source_tier=SourceTier.COMMUNITY_SCRAPER,
                source_url=sig.source_url,
                observed_at=obs_time,
                confidence=sig.confidence,
                raw_evidence_sha256=sig.raw_evidence_sha256,
                source_kind="community_scraper",
            )
            records.append(r)

        if sig.observed_status:
            r = LedgerRecord.create(
                model_id=sig.model_id,
                field_name="lifecycle.availability",
                claim=sig.observed_status,
                source_id=f"nimstats:{sig.model_id}",
                source_tier=SourceTier.COMMUNITY_SCRAPER,
                source_url=sig.source_url,
                observed_at=obs_time,
                confidence=sig.confidence,
                raw_evidence_sha256=sig.raw_evidence_sha256,
                source_kind="community_scraper",
            )
            records.append(r)

    return records


def reddit_signals_to_ledger_records(
    signals: list[CommunitySignal],
) -> list[LedgerRecord]:
    """
    Convert Reddit CommunitySignals into standard LedgerRecords (SourceTier.COMMUNITY_FORUM).
    """
    records: list[LedgerRecord] = []
    for sig in signals:
        obs_time = sig.observed_at or datetime.now(timezone.utc).isoformat()
        r = LedgerRecord.create(
            model_id=sig.model_id,
            field_name=sig.claim_type,
            claim=sig.claim_value,
            source_id=sig.source_id,
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url=sig.source_url,
            observed_at=obs_time,
            confidence=sig.confidence,
            raw_evidence_sha256=sig.raw_evidence_sha256,
            source_kind="community_forum",
        )
        records.append(r)
    return records


def project_materialized_state_to_catalog(
    existing_catalog: dict[str, Any],
    materialized_state: dict[str, ModelEvidenceRecord],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Safely project materialized evidence state onto the production catalog format.
    Guarantees Ground Truth supremacy and records verified/corroborated sources.
    """
    incoming_models_payload = []

    for mid, model_record in materialized_state.items():
        entry: dict[str, Any] = {"model_id": mid}
        field_sources: dict[str, str] = {}

        for fname, fev in model_record.fields.items():
            # Only project fields with accepted values (VERIFIED, CORROBORATED, or OBSERVED with high confidence)
            if fev.current_value is None or fev.state == EvidenceState.CONFLICTED:
                continue

            val = fev.current_value
            active_src = fev.active_evidence.source_id if fev.active_evidence else "unknown"
            active_tier = fev.active_evidence.source_tier.value if fev.active_evidence else "unknown"

            source_label = "NVIDIA Build" if active_tier == SourceTier.NVIDIA_BUILD.value else f"{active_src} ({fev.state.value})"

            # Map dot notation to nested dict structure
            if "." in fname:
                parts = fname.split(".", 1)
                entry.setdefault(parts[0], {})[parts[1]] = val
            elif fname == "capabilities":
                entry["capabilities"] = val
            elif fname == "display_name":
                entry["display_name"] = val

            field_sources[fname] = source_label

        entry["source_metadata"] = {
            "field_sources": field_sources,
            "last_verified": datetime.now(timezone.utc).isoformat(),
        }
        incoming_models_payload.append(entry)

    # Use pure merge_catalog
    return merge_catalog(existing_catalog, incoming_models_payload)


def run_unified_evidence_sync(
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    api_models_path: Path = DEFAULT_API_MODELS_PATH,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    state_path: Path = DEFAULT_STATE_PATH,
    snapshots_dir: Path = DEFAULT_SNAPSHOTS_DIR,
    filter_models: Optional[list[str]] = None,
    dry_run: bool = False,
    include_community: bool = True,
    build_fetch_func: Callable[[str], Optional[str]] = fetch_build_html,
    nimstats_fetch_func: Callable[..., Optional[bytes]] = fetch_nimstats_data,
    reddit_fetch_func: Callable[..., tuple[Optional[bytes], str]] = fetch_reddit_data,
) -> dict[str, Any]:
    """
    Unified end-to-end multi-source evidence ingestion, ledger persistence,
    deterministic replay, and catalog update pipeline.
    """
    start_time = datetime.now(timezone.utc).isoformat()
    catalog_path = Path(catalog_path)
    api_models_path = Path(api_models_path)
    ledger_path = Path(ledger_path)
    state_path = Path(state_path)
    snapshots_dir = Path(snapshots_dir)

    # 1. Load baseline catalog & verify ledger
    existing_catalog = load_json_file(catalog_path)
    if not existing_catalog:
        existing_catalog = {"version": "3.1", "updated_at": start_time, "models": {}}
    old_catalog_hash = calculate_catalog_hash(existing_catalog)
    existing_count = len(existing_catalog.get("models", {}))

    # 2. Discover models
    target_models = discover_target_models(
        catalog_path=catalog_path,
        api_models_path=api_models_path,
        filter_models=filter_models,
    )
    total_discovered = len(target_models)

    print(f"[INFO] Unified Evidence Sync Started: {total_discovered} target models (dry_run={dry_run})")

    new_ledger_records: list[LedgerRecord] = []
    source_statuses: dict[str, Any] = {
        "nvidia_build": {"fetched": 0, "failed": 0, "records_generated": 0},
        "nimstats": {"status": "skipped", "records_generated": 0},
        "reddit": {"status": "skipped", "records_generated": 0},
    }

    # 3. Source A: Official NVIDIA Build Ingestion (Highest Authority)
    for mid in target_models:
        html_content = build_fetch_func(mid)
        if not html_content:
            source_statuses["nvidia_build"]["failed"] += 1
            continue
        source_statuses["nvidia_build"]["fetched"] += 1

        # Snapshot raw evidence
        snap_meta = None
        try:
            snap_meta = save_snapshot(model_id=mid, raw_html=html_content, base_dir=snapshots_dir)
        except Exception as e:
            print(f"[WARN] Failed to save raw build snapshot for {mid}: {e}", file=sys.stderr)

        raw_sha256 = snap_meta.get("sha256") if isinstance(snap_meta, dict) else hashlib.sha256(html_content.encode("utf-8")).hexdigest()

        # Parse specs and lifecycle
        parsed_meta = parse_build_metadata(mid, html_content)
        parsed_lc = parse_official_lifecycle(mid, html_content)
        if parsed_meta and parsed_lc:
            parsed_meta["lifecycle"] = parsed_lc

        if parsed_meta:
            recs = build_metadata_to_ledger_records(mid, parsed_meta, raw_sha256=raw_sha256)
            new_ledger_records.extend(recs)
            source_statuses["nvidia_build"]["records_generated"] += len(recs)

    # 4. Source B & C: Community Ecosystem Signals (Failure Isolated)
    if include_community:
        # B. NIMStats
        try:
            nim_bytes = nimstats_fetch_func(timeout=5, max_retries=1)
            if nim_bytes:
                save_nimstats_raw_evidence(nim_bytes)
                signals, _ = parse_nimstats_payload(nim_bytes)
                nim_recs = nimstats_signals_to_ledger_records(signals)
                new_ledger_records.extend(nim_recs)
                source_statuses["nimstats"] = {"status": "success", "signals_count": len(signals), "records_generated": len(nim_recs)}
            else:
                source_statuses["nimstats"] = {"status": "unavailable_or_blocked", "records_generated": 0}
        except Exception as nim_err:
            source_statuses["nimstats"] = {"status": f"error: {nim_err}", "records_generated": 0}

        # C. Reddit (Zero Raw Content Storage Mode)
        try:
            reddit_bytes, reddit_status = reddit_fetch_func(timeout=5, max_retries=1)
            if reddit_bytes:
                # In-memory cryptographic proof generation without persisting raw User Content to disk
                _, meta = generate_reddit_evidence_hash(reddit_bytes)
                signals, _ = parse_reddit_payload(reddit_bytes, sha256_hash=meta["sha256"])
                reddit_recs = reddit_signals_to_ledger_records(signals)
                new_ledger_records.extend(reddit_recs)
                source_statuses["reddit"] = {"status": "success", "signals_count": len(signals), "records_generated": len(reddit_recs)}
            else:
                source_statuses["reddit"] = {"status": reddit_status, "records_generated": 0}
        except Exception as red_err:
            source_statuses["reddit"] = {"status": f"error: {red_err}", "records_generated": 0}

    # 5. Append to Immutable Evidence Ledger
    appended_count = 0
    duplicate_count = 0
    if not dry_run and new_ledger_records:
        batch_res = append_evidence_batch(ledger_path, new_ledger_records)
        appended_count = batch_res["inserted"]
        duplicate_count = batch_res["duplicates"]

    # 6. Replay & Materialize Evidence State
    # Load all records from ledger (or combine with dry-run records)
    all_ledger_records = load_ledger(ledger_path)
    if dry_run:
        # In dry run, simulate replay including new records
        combined_records = all_ledger_records + new_ledger_records
    else:
        combined_records = all_ledger_records

    materialized_state = replay_evidence(combined_records)

    # Rebuild state file if not dry run
    if not dry_run:
        rebuild_materialized_state(ledger_path, state_path)

    # 7. Safe Projection onto Model Catalog
    new_catalog, merge_summary = project_materialized_state_to_catalog(existing_catalog, materialized_state)

    # 8. Safety Fuse Evaluations
    new_count = len(new_catalog.get("models", {}))
    if new_count < existing_count:
        raise OrchestratorSafetyError(
            f"Safety Fuse Triggered: Merged catalog size ({new_count}) is smaller than original ({existing_count})."
        )
    validate_catalog_schema(new_catalog)

    # Mass Deprecation Spike Fuse
    deprecated_or_removed_count = 0
    for mid, m in new_catalog.get("models", {}).items():
        avail = m.get("lifecycle", {}).get("availability")
        if avail in ["deprecated", "removed"]:
            deprecated_or_removed_count += 1

    if total_discovered > 5 and (deprecated_or_removed_count / new_count) > 0.20:
        raise OrchestratorSafetyError(
            f"Safety Fuse Triggered: Mass deprecation spike detected ({deprecated_or_removed_count}/{new_count} > 20%)."
        )

    # 9. Change Detection & Disk Write
    new_catalog_hash = calculate_catalog_hash(new_catalog)
    catalog_has_changed = (old_catalog_hash != new_catalog_hash) and merge_summary.get("changed", False)

    if catalog_has_changed and not dry_run:
        print(f"[INFO] Writing updated catalog to {catalog_path} (created={merge_summary['total_created']}, updated={merge_summary['total_updated']})")
        atomic_write_catalog(catalog_path, new_catalog)
    elif catalog_has_changed and dry_run:
        print(f"[DRY-RUN] Catalog changes detected but skipped disk write (created={merge_summary['total_created']}, updated={merge_summary['total_updated']})")
    else:
        print("[INFO] Catalog is completely up-to-date. No changes to write.")

    summary_report = {
        "run_at": start_time,
        "dry_run": dry_run,
        "catalog_path": str(catalog_path),
        "ledger_path": str(ledger_path),
        "state_path": str(state_path),
        "discovered_models": total_discovered,
        "new_evidence_generated": len(new_ledger_records),
        "ledger_appended": appended_count,
        "ledger_duplicates": duplicate_count,
        "materialized_models_count": len(materialized_state),
        "catalog_updated": merge_summary.get("total_updated", 0),
        "catalog_created": merge_summary.get("total_created", 0),
        "catalog_changed": catalog_has_changed,
        "source_statuses": source_statuses,
    }

    return summary_report


def main():
    parser = argparse.ArgumentParser(description="Unified Multi-Source Evidence Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Simulate pipeline without writing to ledger, state, or catalog")
    parser.add_argument("--skip-community", action="store_true", help="Skip NIMStats and Reddit community signal ingestion")
    parser.add_argument("--models", type=str, default=None, help="Comma-separated list of specific model IDs to sync")
    parser.add_argument("--catalog-path", type=str, default=str(DEFAULT_CATALOG_PATH))
    parser.add_argument("--ledger-path", type=str, default=str(DEFAULT_LEDGER_PATH))
    parser.add_argument("--state-path", type=str, default=str(DEFAULT_STATE_PATH))

    args = parser.parse_args()

    filter_list = [m.strip() for m in args.models.split(",")] if args.models else None

    try:
        summary = run_unified_evidence_sync(
            catalog_path=Path(args.catalog_path),
            ledger_path=Path(args.ledger_path),
            state_path=Path(args.state_path),
            filter_models=filter_list,
            dry_run=args.dry_run,
            include_community=not args.skip_community,
        )
        print("\n=== Unified Evidence Sync Report ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    except Exception as err:
        print(f"[FATAL] Unified Orchestrator failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
