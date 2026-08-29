"""
Safe Catalog Merge Engine (Phase S1-D)
Pure, non-mutating merger adhering to strict Ground Truth preservation rules.
Guarantees official new data updates while zero-erasing existing trusted data.
"""

import copy
from datetime import datetime, timezone
from typing import Any, Optional, Union

INVALID_VALUES = {None, "", "unknown", "Unknown", "null", "None"}
TRUST_PRECEDENCE = {
    "official": 3,
    "NVIDIA Build": 3,
    "official_aggregate": 2,
    "observed": 1,
    "local_heuristic": 0,
    "unknown": -1,
}


def _is_valid_value(val: Any) -> bool:
    """Check if a value is meaningful and non-empty."""
    if val in INVALID_VALUES:
        return False
    if isinstance(val, (list, dict, set)) and len(val) == 0:
        return False
    return True


def _get_trust_score(source: Optional[str]) -> int:
    """Get numeric rank of data source trust."""
    if not source:
        return -1
    return TRUST_PRECEDENCE.get(source, 1)


def merge_model(
    existing: Optional[dict[str, Any]],
    incoming: Optional[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Merge a single incoming model metadata dict into an existing catalog entry.
    Pure function: Does NOT mutate input dictionaries.
    
    Returns:
        (merged_model_dict, diff_report_dict)
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Case 1: If incoming is None or empty, preserve existing completely
    if not incoming or not isinstance(incoming, dict):
        if existing:
            return copy.deepcopy(existing), {
                "changed": False,
                "created": False,
                "updated_fields": [],
                "preserved_fields": list(existing.keys()),
                "field_diffs": {},
            }
        return {}, {
            "changed": False,
            "created": False,
            "updated_fields": [],
            "preserved_fields": [],
            "field_diffs": {},
        }

    # Case 2: If existing is None or empty, create a clean minimal entry from incoming
    if not existing or not isinstance(existing, dict):
        new_entry = copy.deepcopy(incoming)
        # Ensure standard structure exists
        model_id = incoming.get("model_id", "unknown/unknown")
        parts = model_id.split("/")
        provider_id = parts[0] if len(parts) > 1 else "nvidia"
        slug = parts[-1]

        if "slug" not in new_entry:
            new_entry["slug"] = slug
        if "aliases" not in new_entry:
            new_entry["aliases"] = []
        if "provider" not in new_entry:
            new_entry["provider"] = {"id": provider_id, "name": provider_id.replace("-", " ").title()}
        if "classification" not in new_entry:
            new_entry["classification"] = {"family": None, "tier": "standard", "model_type": "chat", "speed": "standard"}
        if "architecture" not in new_entry:
            new_entry["architecture"] = {"type": None, "total_parameters": None, "active_parameters": None, "parameter_status": "unknown"}
        if "context" not in new_entry:
            new_entry["context"] = {"length": None, "max_output": None, "status": "unknown"}
        if "capabilities" not in new_entry:
            new_entry["capabilities"] = ["Chat"]
        if "release" not in new_entry:
            new_entry["release"] = {"first_seen": now_iso, "release_date": None, "status": "official"}
        if "lifecycle" not in new_entry:
            new_entry["lifecycle"] = {"availability": "active", "removed_at": None, "official_deprecation_date": None, "deprecation_source_url": None}
        if "endpoint" not in new_entry:
            new_entry["endpoint"] = {"available": True, "api_calls_24h": None, "api_calls_daily": None, "api_calls_7d": None, "api_calls_30d": None}
        if "links" not in new_entry:
            new_entry["links"] = {"nvidia": f"https://build.nvidia.com/{model_id}", "official": None, "documentation": None, "model_card": None}
        if "source_metadata" not in new_entry:
            new_entry["source_metadata"] = {"field_sources": {}, "confidence": "high", "last_verified": now_iso}

        return new_entry, {
            "changed": True,
            "created": True,
            "updated_fields": ["*"],
            "preserved_fields": [],
            "field_diffs": {"*": {"old": None, "new": model_id, "source": "creation"}},
        }

    # Case 3: Merge existing and incoming
    merged = copy.deepcopy(existing)
    updated_fields = []
    preserved_fields = []
    field_diffs = {}

    incoming_sources = incoming.get("source_metadata", {}).get("field_sources", {})
    existing_sources = merged.get("source_metadata", {}).get("field_sources", {})

    # Helper function to merge simple field with source precedence and null protection
    def _merge_scalar_field(
        field_path: str,
        curr_val: Any,
        new_val: Any,
        source_key: Optional[str] = None,
    ) -> tuple[Any, bool]:
        if not _is_valid_value(new_val):
            # incoming has no valid value -> preserve existing
            preserved_fields.append(field_path)
            return curr_val, False

        # If existing value is invalid/null, accept new value directly
        if not _is_valid_value(curr_val):
            updated_fields.append(field_path)
            src = incoming_sources.get(source_key or field_path, "NVIDIA Build")
            field_diffs[field_path] = {"old": curr_val, "new": new_val, "source": src}
            return new_val, True

        # Both values exist: check trust precedence
        curr_source = existing_sources.get(source_key or field_path, "official")
        new_source = incoming_sources.get(source_key or field_path, "NVIDIA Build")

        curr_rank = _get_trust_score(curr_source)
        new_rank = _get_trust_score(new_source)

        if new_rank >= curr_rank:
            if curr_val != new_val:
                updated_fields.append(field_path)
                field_diffs[field_path] = {"old": curr_val, "new": new_val, "source": new_source}
                return new_val, True
            else:
                preserved_fields.append(field_path)
                return curr_val, False
        else:
            # Current value has higher trust -> preserve
            preserved_fields.append(field_path)
            return curr_val, False

    # 1. Identity & Display Name
    if "display_name" in incoming:
        new_name, ch = _merge_scalar_field("display_name", merged.get("display_name"), incoming.get("display_name"))
        merged["display_name"] = new_name

    # 2. Aliases & Capabilities (Set union preserving order)
    if "aliases" in incoming and isinstance(incoming["aliases"], list):
        merged_aliases = list(dict.fromkeys(merged.get("aliases", []) + incoming["aliases"]))
        if merged_aliases != merged.get("aliases", []):
            updated_fields.append("aliases")
            field_diffs["aliases"] = {"old": merged.get("aliases", []), "new": merged_aliases, "source": "merge"}
            merged["aliases"] = merged_aliases

    if "capabilities" in incoming and isinstance(incoming["capabilities"], list):
        in_caps = incoming["capabilities"]
        curr_caps = merged.get("capabilities", [])
        incoming_caps_source = incoming_sources.get("capabilities", "NVIDIA Build")
        incoming_model_type = incoming.get("classification", {}).get("model_type")

        # If incoming is official and explicitly non-vision (chat/coding/embedding), purge spurious legacy Vision
        if (
            incoming_caps_source == "NVIDIA Build"
            and "Vision" not in in_caps
            and incoming_model_type in ["chat", "coding", "embedding"]
        ):
            filtered_curr = [c for c in curr_caps if c != "Vision"]
            merged_caps = list(dict.fromkeys(filtered_curr + in_caps))
        else:
            merged_caps = list(dict.fromkeys(curr_caps + in_caps))

        if merged_caps != curr_caps:
            updated_fields.append("capabilities")
            field_diffs["capabilities"] = {"old": curr_caps, "new": merged_caps, "source": incoming_caps_source}
            merged["capabilities"] = merged_caps

    # 3. Architecture
    if "architecture" in incoming and isinstance(incoming["architecture"], dict):
        merged_arch = merged.setdefault("architecture", {})
        in_arch = incoming["architecture"]

        for k in ["type", "total_parameters", "active_parameters"]:
            if k in in_arch:
                val, ch = _merge_scalar_field(
                    f"architecture.{k}",
                    merged_arch.get(k),
                    in_arch.get(k),
                    source_key=f"architecture.{k}",
                )
                merged_arch[k] = val

        # Parameter status
        if in_arch.get("parameter_status") == "official" and _is_valid_value(merged_arch.get("total_parameters")):
            merged_arch["parameter_status"] = "official"

    # 4. Context
    if "context" in incoming and isinstance(incoming["context"], dict):
        merged_ctx = merged.setdefault("context", {})
        in_ctx = incoming["context"]

        for k in ["length", "max_output"]:
            if k in in_ctx:
                val, ch = _merge_scalar_field(
                    f"context.{k}",
                    merged_ctx.get(k),
                    in_ctx.get(k),
                    source_key=f"context.{k}",
                )
                merged_ctx[k] = val

        if in_ctx.get("status") == "official" and _is_valid_value(merged_ctx.get("length")):
            merged_ctx["status"] = "official"

    # 5. Classification
    if "classification" in incoming and isinstance(incoming["classification"], dict):
        merged_cls = merged.setdefault("classification", {})
        in_cls = incoming["classification"]

        for k in ["family", "tier", "model_type", "speed"]:
            if k in in_cls:
                val, ch = _merge_scalar_field(
                    f"classification.{k}",
                    merged_cls.get(k),
                    in_cls.get(k),
                    source_key=f"classification.{k}",
                )
                merged_cls[k] = val

    # 6. Links
    if "links" in incoming and isinstance(incoming["links"], dict):
        merged_links = merged.setdefault("links", {})
        in_links = incoming["links"]

        for k in ["nvidia", "official", "documentation", "model_card"]:
            if k in in_links:
                val, ch = _merge_scalar_field(
                    f"links.{k}",
                    merged_links.get(k),
                    in_links.get(k),
                    source_key=f"links.{k}",
                )
                merged_links[k] = val

    # 7. Lifecycle State Machine & Official Metadata Merge
    if "lifecycle" in incoming and isinstance(incoming["lifecycle"], dict):
        merged_lc = merged.setdefault("lifecycle", {})
        in_lc = incoming["lifecycle"]

        # 7.1 Availability state machine with monotonic progression
        curr_avail = merged_lc.get("availability")
        new_avail = in_lc.get("availability")
        
        severity_map = {
            "unknown": 0,
            "active": 1,
            "retiring": 2,
            "deprecated": 3,
            "removed": 4,
        }

        if _is_valid_value(new_avail) and str(new_avail).lower() in severity_map:
            new_avail_norm = str(new_avail).lower()
            curr_avail_norm = str(curr_avail).lower() if curr_avail else "unknown"

            curr_rank = _get_trust_score(existing_sources.get("lifecycle.availability", "observed"))
            new_rank = _get_trust_score(incoming_sources.get("lifecycle.availability", "NVIDIA Build"))

            curr_sev = severity_map.get(curr_avail_norm, 0)
            new_sev = severity_map.get(new_avail_norm, 0)

            should_update_avail = False
            if not _is_valid_value(curr_avail):
                should_update_avail = True
            elif new_rank > curr_rank:
                # Higher trust source (e.g. NVIDIA Build vs observed) can update
                should_update_avail = True
            elif new_rank == curr_rank:
                # Same trust rank: allow progression forward (severity increase) or confirmation
                if new_sev >= curr_sev:
                    should_update_avail = True
                else:
                    # Block downgrade (e.g. deprecated -> active) unless higher trust
                    preserved_fields.append("lifecycle.availability")

            if should_update_avail and curr_avail != new_avail_norm:
                updated_fields.append("lifecycle.availability")
                src = incoming_sources.get("lifecycle.availability", "NVIDIA Build")
                field_diffs["lifecycle.availability"] = {"old": curr_avail, "new": new_avail_norm, "source": src}
                merged_lc["availability"] = new_avail_norm
            elif not should_update_avail:
                preserved_fields.append("lifecycle.availability")

        # 7.2 Explicit dates, replacement model, and notes
        for lc_key in [
            "official_deprecation_date",
            "official_retirement_date",
            "replacement_model_id",
            "deprecation_source_url",
            "deprecation_notes",
        ]:
            if lc_key in in_lc:
                val, ch = _merge_scalar_field(
                    f"lifecycle.{lc_key}",
                    merged_lc.get(lc_key),
                    in_lc.get(lc_key),
                    source_key=f"lifecycle.{lc_key}",
                )
                merged_lc[lc_key] = val

    # 7. Source Metadata Merge
    merged_sources = merged.setdefault("source_metadata", {}).setdefault("field_sources", {})
    for f in updated_fields:
        if f in incoming_sources:
            merged_sources[f] = incoming_sources[f]
        elif any(f.startswith(p) for p in ["architecture", "context", "display_name", "links"]):
            merged_sources[f] = "NVIDIA Build"

    merged["source_metadata"]["last_verified"] = now_iso
    merged["source_metadata"]["confidence"] = "high" if len(merged_sources) >= 3 else "medium"

    return merged, {
        "changed": len(updated_fields) > 0,
        "created": False,
        "updated_fields": updated_fields,
        "preserved_fields": preserved_fields,
        "field_diffs": field_diffs,
    }


def merge_catalog(
    existing_catalog: dict[str, Any],
    incoming_models: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Merge a list of incoming model dictionaries into a complete catalog.
    Pure function: Does NOT mutate existing_catalog.
    
    Returns:
        (new_catalog_dict, summary_diff_dict)
    """
    new_catalog = copy.deepcopy(existing_catalog)
    models_map = new_catalog.setdefault("models", {})
    now_iso = datetime.now(timezone.utc).isoformat()

    total_updated = 0
    total_created = 0
    total_preserved = 0
    model_reports = {}

    for incoming in incoming_models:
        if not isinstance(incoming, dict):
            continue
        model_id = incoming.get("model_id")
        if not model_id:
            continue

        existing_entry = models_map.get(model_id)
        merged_entry, diff = merge_model(existing_entry, incoming)

        models_map[model_id] = merged_entry
        model_reports[model_id] = diff

        if diff["created"]:
            total_created += 1
        elif diff["changed"]:
            total_updated += 1
        else:
            total_preserved += 1

    new_catalog["updated_at"] = now_iso

    summary = {
        "changed": (total_created > 0 or total_updated > 0),
        "total_incoming": len(incoming_models),
        "total_created": total_created,
        "total_updated": total_updated,
        "total_preserved": total_preserved,
        "model_diffs": model_reports,
    }

    return new_catalog, summary
