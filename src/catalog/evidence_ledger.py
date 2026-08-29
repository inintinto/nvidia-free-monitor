"""
Evidence Ledger & Unified Evidence Orchestration (Phase S3-D)
Provides immutable event ledger persistence, deterministic replay,
materialized view caching, and strict cryptographic integrity verification.
"""

import argparse
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any, Optional, Union

from src.catalog.evidence import (
    EvidenceItem,
    EvidenceState,
    FieldEvidence,
    ModelEvidenceRecord,
    SourceTier,
    TIER_WEIGHTS,
    add_evidence,
    check_staleness,
)

DEFAULT_LEDGER_PATH = Path("data") / "evidence_ledger.jsonl"
DEFAULT_STATE_PATH = Path("data") / "evidence_state.json"


class LedgerError(Exception):
    """Base exception for evidence ledger operations."""
    pass


class LedgerCorruptedError(LedgerError):
    """Raised when ledger integrity or checksum verification fails."""
    pass


class DuplicateEvidenceError(LedgerError):
    """Raised when duplicate evidence is rejected."""
    pass


def canonical_json_dumps(obj: Any) -> str:
    """Produce deterministic canonical JSON string with sorted keys and no extra whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonicalize_iso_timestamp(ts_str: str) -> str:
    """
    Parse any valid ISO-8601 timestamp and convert to a canonical, deterministic UTC ISO string.
    Supports 'Z', '+00:00', positive/negative offsets (e.g. '+08:00', '-08:00'),
    with or without microseconds.
    
    Output format: 'YYYY-MM-DDTHH:MM:SS.ffffff+00:00' (fixed-length 6-digit microsecond UTC)
    Guaranteeing that lexicographical string comparison is 100% strictly equivalent to physical timeline order.
    
    Raises:
        ValueError: if input is not a valid ISO timestamp or is empty/non-string.
    """
    if not isinstance(ts_str, str) or not ts_str.strip():
        raise ValueError(f"Invalid timestamp: must be non-empty string, got {ts_str!r}")

    raw = ts_str.strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception as e:
        raise ValueError(f"Malformed ISO-8601 timestamp '{ts_str}': {e}") from e

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f") + "+00:00"


def compute_sha256_str(data_str: str) -> str:
    """Compute SHA-256 hex digest of string in UTF-8."""
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def compute_evidence_id(
    model_id: str,
    field_name: str,
    claim: Any,
    source_id: str,
    source_tier: str,
    source_url: str,
    observed_at: str,
    raw_evidence_sha256: Optional[str] = None,
) -> str:
    """
    Calculate deterministic evidence_id based on canonical identity properties.
    """
    core_payload = {
        "claim": claim,
        "field_name": field_name,
        "model_id": model_id,
        "observed_at": observed_at,
        "raw_evidence_sha256": raw_evidence_sha256 or "",
        "source": {
            "source_id": source_id,
            "source_tier": source_tier,
            "source_url": source_url,
        },
    }
    canonical_str = canonical_json_dumps(core_payload)
    return compute_sha256_str(canonical_str)


@dataclass(frozen=True)
class LedgerRecord:
    """An immutable, cryptographically verifiable record in the Evidence Ledger."""
    evidence_id: str
    model_id: str
    field_name: str
    claim: Any
    source: dict[str, Any]
    observed_at: str
    confidence: float = 1.0
    raw_evidence_sha256: Optional[str] = None
    state_effect: Optional[str] = None
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "model_id": self.model_id,
            "field_name": self.field_name,
            "claim": self.claim,
            "source": self.source,
            "observed_at": self.observed_at,
            "confidence": self.confidence,
            "raw_evidence_sha256": self.raw_evidence_sha256,
            "state_effect": self.state_effect,
            "ingested_at": self.ingested_at,
        }

    @classmethod
    def create(
        cls,
        model_id: str,
        field_name: str,
        claim: Any,
        source_id: str,
        source_tier: Union[SourceTier, str],
        source_url: str,
        observed_at: str,
        confidence: float = 1.0,
        raw_evidence_sha256: Optional[str] = None,
        source_kind: Optional[str] = None,
        state_effect: Optional[str] = None,
        ingested_at: Optional[str] = None,
    ) -> "LedgerRecord":
        tier_str = source_tier.value if isinstance(source_tier, SourceTier) else str(source_tier)
        
        kind = source_kind
        if not kind:
            if tier_str in [SourceTier.NVIDIA_BUILD.value, SourceTier.OFFICIAL_AGGREGATE.value]:
                kind = "official"
            elif tier_str == SourceTier.OBSERVED_PROBE.value:
                kind = "observed_probe"
            else:
                kind = "community"

        source_dict = {
            "source_id": source_id,
            "source_tier": tier_str,
            "source_url": source_url,
            "source_kind": kind,
        }

        ev_id = compute_evidence_id(
            model_id=model_id,
            field_name=field_name,
            claim=claim,
            source_id=source_id,
            source_tier=tier_str,
            source_url=source_url,
            observed_at=observed_at,
            raw_evidence_sha256=raw_evidence_sha256,
        )

        return cls(
            evidence_id=ev_id,
            model_id=model_id,
            field_name=field_name,
            claim=claim,
            source=source_dict,
            observed_at=observed_at,
            confidence=confidence,
            raw_evidence_sha256=raw_evidence_sha256,
            state_effect=state_effect,
            ingested_at=ingested_at or datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LedgerRecord":
        return cls(
            evidence_id=data.get("evidence_id", ""),
            model_id=data.get("model_id", ""),
            field_name=data.get("field_name", ""),
            claim=data.get("claim"),
            source=data.get("source", {}),
            observed_at=data.get("observed_at", ""),
            confidence=float(data.get("confidence", 1.0)),
            raw_evidence_sha256=data.get("raw_evidence_sha256"),
            state_effect=data.get("state_effect"),
            ingested_at=data.get("ingested_at", ""),
        )


def validate_ledger_record(rec: LedgerRecord) -> None:
    """
    Strict validation of a single LedgerRecord.
    Raises LedgerCorruptedError if any rule is violated.
    """
    if not rec.evidence_id:
        raise LedgerCorruptedError("Missing required field: evidence_id")
    if not rec.model_id or "/" not in rec.model_id:
        raise LedgerCorruptedError(f"Invalid model_id format (must be vendor/model): '{rec.model_id}'")
    if not rec.field_name:
        raise LedgerCorruptedError("Missing required field: field_name")
    if rec.claim is None or str(rec.claim).strip() == "":
        raise LedgerCorruptedError("claim cannot be empty or null")

    src = rec.source
    if not isinstance(src, dict):
        raise LedgerCorruptedError("source must be a dictionary")
    for sk in ["source_id", "source_tier", "source_url"]:
        if not src.get(sk):
            raise LedgerCorruptedError(f"Missing required source field: '{sk}'")

    tier_val = src.get("source_tier")
    valid_tiers = [t.value for t in SourceTier]
    if tier_val not in valid_tiers:
        raise LedgerCorruptedError(f"Invalid source_tier: '{tier_val}'. Allowed: {valid_tiers}")

    # Validate ISO timestamp
    try:
        canonicalize_iso_timestamp(rec.observed_at)
    except Exception as e:
        raise LedgerCorruptedError(f"Invalid observed_at timestamp '{rec.observed_at}': {e}")

    # Validate raw_evidence_sha256 format if present
    if rec.raw_evidence_sha256:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", rec.raw_evidence_sha256):
            raise LedgerCorruptedError(f"Invalid raw_evidence_sha256 hex format: '{rec.raw_evidence_sha256}'")

    # Validate deterministic evidence_id match
    expected_id = compute_evidence_id(
        model_id=rec.model_id,
        field_name=rec.field_name,
        claim=rec.claim,
        source_id=src["source_id"],
        source_tier=src["source_tier"],
        source_url=src["source_url"],
        observed_at=rec.observed_at,
        raw_evidence_sha256=rec.raw_evidence_sha256,
    )
    if rec.evidence_id != expected_id:
        raise LedgerCorruptedError(
            f"Evidence ID mismatch: recorded '{rec.evidence_id}', computed '{expected_id}'"
        )


from contextlib import contextmanager
import time


@contextmanager
def _ledger_file_lock(ledger_path: Path, timeout: float = 10.0):
    """
    Cross-platform inter-process exclusive file lock for ledger operations.
    Eliminates TOCTOU races between concurrent processes.
    """
    lock_path = ledger_path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)

    if sys.platform == "win32":
        import msvcrt
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                break
            except (BlockingIOError, OSError):
                if time.time() - start_time > timeout:
                    os.close(fd)
                    raise TimeoutError(f"Timed out after {timeout}s waiting for ledger lock '{lock_path}'")
                time.sleep(0.01)
    else:
        import fcntl
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                if time.time() - start_time > timeout:
                    os.close(fd)
                    raise TimeoutError(f"Timed out after {timeout}s waiting for ledger lock '{lock_path}'")
                time.sleep(0.01)

    try:
        yield
    finally:
        try:
            if sys.platform == "win32":
                import msvcrt
                try:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            os.close(fd)
        except Exception:
            pass


def append_evidence_batch(
    ledger_path: Union[str, Path],
    records: list[Union[LedgerRecord, dict[str, Any]]],
    lock_timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """
    Atomic, deduplicated, and concurrency-safe batch append of Evidence Records.
    Acquires an exclusive inter-process file lock, scans existing records once,
    deduplicates incoming records both against the ledger and within the batch,
    and commits all valid new records in a single fsync.
    """
    ledger_path = Path(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        return {"total": 0, "inserted": 0, "duplicates": 0, "inserted_ids": []}

    parsed_records: list[LedgerRecord] = []
    for r in records:
        if isinstance(r, dict):
            rec = LedgerRecord.from_dict(r)
        else:
            rec = r
        validate_ledger_record(rec)
        parsed_records.append(rec)

    with _ledger_file_lock(ledger_path, timeout=lock_timeout_seconds):
        existing_ids = set()
        if ledger_path.exists():
            with open(ledger_path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        eid = data.get("evidence_id")
                        if eid:
                            existing_ids.add(eid)
                    except Exception as err:
                        raise LedgerCorruptedError(f"Malformed JSON on line {line_idx} of ledger: {err}")

        inserted_records: list[LedgerRecord] = []
        duplicate_count = 0
        seen_in_batch: set[str] = set()

        for rec in parsed_records:
            if rec.evidence_id in existing_ids or rec.evidence_id in seen_in_batch:
                duplicate_count += 1
                continue
            seen_in_batch.add(rec.evidence_id)
            inserted_records.append(rec)

        if inserted_records:
            lines_to_append = "".join(
                canonical_json_dumps(r.to_dict()) + "\n" for r in inserted_records
            )
            with open(ledger_path, "a", encoding="utf-8") as f:
                f.write(lines_to_append)
                f.flush()
                os.fsync(f.fileno())

        return {
            "total": len(records),
            "inserted": len(inserted_records),
            "duplicates": duplicate_count,
            "inserted_ids": [r.evidence_id for r in inserted_records],
        }


def append_evidence(
    ledger_path: Union[str, Path],
    record: Union[LedgerRecord, dict[str, Any]],
    lock_timeout_seconds: float = 10.0,
) -> tuple[bool, str]:
    """
    Atomic and deduplicated append of a single Evidence Record to the JSONL ledger.
    Delegates to append_evidence_batch to guarantee inter-process lock protection.
    Returns (inserted: bool, status_message: str).
    """
    res = append_evidence_batch(
        ledger_path,
        [record],
        lock_timeout_seconds=lock_timeout_seconds,
    )
    if res["inserted"] > 0:
        return True, "inserted"
    return False, "already_exists"


def repair_truncated_ledger(ledger_path: Union[str, Path]) -> dict[str, Any]:
    """
    Detects and safely repairs trailing half-line corruption caused by abnormal process crash.
    Strictly verifies that all preceding lines are 100% valid JSON and valid LedgerRecords.
    If the corruption is in an intermediate line, strictly raises LedgerCorruptedError.
    """
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return {"repaired": False, "reason": "file_not_found"}

    with _ledger_file_lock(ledger_path, timeout=10.0):
        with open(ledger_path, "rb") as f:
            content = f.read()

        if not content:
            return {"repaired": False, "reason": "empty_file"}

        text = content.decode("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)

        valid_lines: list[str] = []
        corrupted_trailing: Optional[str] = None

        for idx, line in enumerate(lines, start=1):
            raw_stripped = line.strip()
            if not raw_stripped:
                continue

            try:
                data = json.loads(raw_stripped)
                rec = LedgerRecord.from_dict(data)
                validate_ledger_record(rec)
                valid_lines.append(raw_stripped + "\n")
            except Exception as err:
                if idx == len(lines):
                    # Only last trailing line is allowed to be repaired
                    corrupted_trailing = line
                else:
                    raise LedgerCorruptedError(
                        f"Non-trailing intermediate line {idx} corrupted: {err}. Cannot auto-repair."
                    )

        if corrupted_trailing is not None:
            # Write valid lines to atomic temp file and replace
            tmp_path = ledger_path.with_suffix(f".tmp_repair_{os.getpid()}")
            with open(tmp_path, "w", encoding="utf-8") as tf:
                for vl in valid_lines:
                    tf.write(vl)
                tf.flush()
                os.fsync(tf.fileno())
            os.replace(tmp_path, ledger_path)
            return {
                "repaired": True,
                "valid_records_retained": len(valid_lines),
                "corrupted_line_removed": corrupted_trailing.strip(),
            }

        return {"repaired": False, "valid_records_retained": len(valid_lines), "reason": "no_corruption_detected"}


def load_ledger(ledger_path: Union[str, Path]) -> list[LedgerRecord]:
    """
    Load all records from JSONL ledger.
    Raises LedgerCorruptedError if any line is invalid.
    """
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return []

    records: list[LedgerRecord] = []
    seen_ids: set[str] = set()

    with open(ledger_path, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as jde:
                raise LedgerCorruptedError(f"Syntax error on line {line_idx} of ledger {ledger_path}: {jde}")

            rec = LedgerRecord.from_dict(data)
            validate_ledger_record(rec)

            if rec.evidence_id in seen_ids:
                raise LedgerCorruptedError(f"Duplicate evidence_id '{rec.evidence_id}' found on line {line_idx}")
            seen_ids.add(rec.evidence_id)
            records.append(rec)

    return records


def verify_ledger(ledger_path: Union[str, Path]) -> dict[str, Any]:
    """
    Perform full cryptographic, schema, and structural audit on the ledger.
    Returns audit summary dict or raises LedgerCorruptedError.
    """
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return {"status": "empty_or_nonexistent", "records_count": 0, "verified": True}

    records = load_ledger(ledger_path)
    return {
        "status": "valid",
        "records_count": len(records),
        "verified": True,
        "path": str(ledger_path),
    }


def replay_evidence(
    records: list[Union[LedgerRecord, dict[str, Any]]],
    as_of: Optional[datetime] = None,
) -> dict[str, ModelEvidenceRecord]:
    """
    Deterministic replay engine.
    Applies records chronologically and orders identical timestamps by SourceTier priority.
    Guarantees that any shuffled or permuted set of identical records yields identical materialized state.
    """
    as_of_dt = as_of or datetime.now(timezone.utc)
    parsed_records: list[LedgerRecord] = []

    for r in records:
        if isinstance(r, dict):
            parsed_records.append(LedgerRecord.from_dict(r))
        else:
            parsed_records.append(r)

    # Canonical sorting:
    # 1. Canonical UTC observed_at ISO timestamp (ascending)
    # 2. SourceTier weight (descending)
    # 3. evidence_id (ascending deterministic tie-breaker)
    def sort_key(rec: LedgerRecord):
        tier_str = rec.source.get("source_tier", "unknown")
        try:
            tier_enum = SourceTier(tier_str)
        except ValueError:
            tier_enum = SourceTier.UNKNOWN
        tier_weight = TIER_WEIGHTS.get(tier_enum, 0)
        try:
            canon_ts = canonicalize_iso_timestamp(rec.observed_at)
        except Exception:
            canon_ts = rec.observed_at
        return (canon_ts, -tier_weight, rec.evidence_id)

    sorted_records = sorted(parsed_records, key=sort_key)

    materialized_models: dict[str, ModelEvidenceRecord] = {}

    for rec in sorted_records:
        mid = rec.model_id
        if mid not in materialized_models:
            materialized_models[mid] = ModelEvidenceRecord(model_id=mid)

        model_ledger = materialized_models[mid]

        tier_str = rec.source.get("source_tier", "unknown")
        try:
            tier_enum = SourceTier(tier_str)
        except ValueError:
            tier_enum = SourceTier.UNKNOWN

        ev_item = EvidenceItem(
            source_id=rec.source.get("source_id", "unknown"),
            source_tier=tier_enum,
            source_url=rec.source.get("source_url", ""),
            observed_at=rec.observed_at,
            claim=rec.claim,
            confidence=rec.confidence,
            raw_payload_snippet=None,
        )

        try:
            obs_dt = datetime.fromisoformat(rec.observed_at)
        except Exception:
            obs_dt = as_of_dt

        model_ledger.record_evidence(
            field_name=rec.field_name,
            incoming=ev_item,
            now=obs_dt,
        )

    # Evaluate TTL staleness across all models as of reference time
    for m in materialized_models.values():
        m.evaluate_all_staleness(as_of=as_of_dt)

    return materialized_models


def calculate_materialized_state_hash(state_dict: dict[str, Any]) -> str:
    """Calculate deterministic SHA-256 hash of materialized state dictionary."""
    canonical_str = canonical_json_dumps(state_dict)
    return compute_sha256_str(canonical_str)


def rebuild_materialized_state(
    ledger_path: Union[str, Path] = DEFAULT_LEDGER_PATH,
    state_path: Union[str, Path] = DEFAULT_STATE_PATH,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Rebuild data/evidence_state.json entirely from the immutable JSONL ledger.
    Guarantees idempotent atomic write.
    """
    ledger_path = Path(ledger_path)
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    records = load_ledger(ledger_path)
    materialized = replay_evidence(records, as_of=as_of)

    state_dict = {
        "version": "1.0",
        "rebuilt_at": (as_of or datetime.now(timezone.utc)).isoformat(),
        "total_records_replayed": len(records),
        "models": {mid: m.to_dict() for mid, m in sorted(materialized.items())},
    }

    state_hash = calculate_materialized_state_hash(state_dict["models"])
    state_dict["state_hash"] = state_hash

    # Atomic write
    tmp_file = state_path.parent / f".tmp_state_{os.getpid()}_{time.time_ns()}.json"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, state_path)
    finally:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass

    return state_dict


def get_ledger_stats(
    ledger_path: Union[str, Path] = DEFAULT_LEDGER_PATH,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Calculate comprehensive stats over the Evidence Ledger and its materialized state.
    """
    ledger_path = Path(ledger_path)
    records = load_ledger(ledger_path)
    materialized = replay_evidence(records, as_of=as_of)

    unique_models = set()
    unique_fields = set()
    official_count = 0
    community_count = 0

    for r in records:
        unique_models.add(r.model_id)
        unique_fields.add(r.field_name)
        tier = r.source.get("source_tier", "")
        if tier in [SourceTier.NVIDIA_BUILD.value, SourceTier.OFFICIAL_AGGREGATE.value]:
            official_count += 1
        else:
            community_count += 1

    conflicts_count = 0
    corroborations_count = 0
    stale_count = 0
    verified_count = 0

    for m in materialized.values():
        for f in m.fields.values():
            if f.state == EvidenceState.CONFLICTED:
                conflicts_count += 1
            elif f.state == EvidenceState.CORROBORATED:
                corroborations_count += 1
            elif f.state == EvidenceState.STALE:
                stale_count += 1
            elif f.state == EvidenceState.VERIFIED:
                verified_count += 1

    return {
        "total_evidence": len(records),
        "unique_models": len(unique_models),
        "unique_fields": len(unique_fields),
        "official_evidence": official_count,
        "community_evidence": community_count,
        "verified_fields": verified_count,
        "conflicts": conflicts_count,
        "corroborations": corroborations_count,
        "stale_candidates": stale_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Evidence Ledger & Materialized View Orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: verify
    p_verify = subparsers.add_parser("verify", help="Verify integrity of JSONL ledger")
    p_verify.add_argument("--ledger-path", type=str, default=str(DEFAULT_LEDGER_PATH))

    # Subcommand: rebuild
    p_rebuild = subparsers.add_parser("rebuild", help="Rebuild materialized state from JSONL ledger")
    p_rebuild.add_argument("--ledger-path", type=str, default=str(DEFAULT_LEDGER_PATH))
    p_rebuild.add_argument("--state-path", type=str, default=str(DEFAULT_STATE_PATH))

    # Subcommand: stats
    p_stats = subparsers.add_parser("stats", help="Compute statistics across ledger and materialized view")
    p_stats.add_argument("--ledger-path", type=str, default=str(DEFAULT_LEDGER_PATH))

    # Subcommand: replay
    p_replay = subparsers.add_parser("replay", help="Replay ledger and output materialized state to stdout")
    p_replay.add_argument("--ledger-path", type=str, default=str(DEFAULT_LEDGER_PATH))

    # Subcommand: append
    p_append = subparsers.add_parser("append", help="Append a single evidence record from JSON string")
    p_append.add_argument("--ledger-path", type=str, default=str(DEFAULT_LEDGER_PATH))
    p_append.add_argument("--record-json", type=str, required=True)

    args = parser.parse_args()

    try:
        if args.command == "verify":
            res = verify_ledger(args.ledger_path)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        elif args.command == "rebuild":
            res = rebuild_materialized_state(args.ledger_path, args.state_path)
            print(f"[INFO] Materialized state successfully rebuilt with {res['total_records_replayed']} records.")
            print(f"[INFO] State hash: {res['state_hash']}")
        elif args.command == "stats":
            res = get_ledger_stats(args.ledger_path)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        elif args.command == "replay":
            recs = load_ledger(args.ledger_path)
            mat = replay_evidence(recs)
            out = {mid: m.to_dict() for mid, m in sorted(mat.items())}
            print(json.dumps(out, indent=2, ensure_ascii=False))
        elif args.command == "append":
            raw_rec = json.loads(args.record_json)
            inserted, msg = append_evidence(args.ledger_path, raw_rec)
            print(json.dumps({"inserted": inserted, "message": msg}, indent=2))
    except Exception as err:
        print(f"[FATAL] Ledger operation failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
