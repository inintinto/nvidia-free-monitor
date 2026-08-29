"""
NIMStats / NVIDIA Ecosystem Signal Integration (Phase S3-B)
Provides collector, parser, raw evidence preservation with SHA-256 integrity,
and Evidence State Machine adapter for community benchmarking signals.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any, Callable, Optional, Union
import urllib.error
import urllib.request

from src.catalog.evidence import EvidenceItem, SourceTier

DEFAULT_NIMSTATS_SOURCES_DIR = Path("data") / "sources" / "nimstats"
DEFAULT_NIMSTATS_URL = "https://nimstats.com/api/top"
DEFAULT_USER_AGENT = "NvidiaFreeEndpointMonitor/3.0 (Ecosystem Observability Collector; +https://github.com/inintinto/nvidia-free-monitor)"


@dataclass(frozen=True)
class EcosystemSignal:
    """Standardized ecosystem benchmark and activity signal."""
    model_id: str
    tokens_per_sec: Optional[float] = None
    ttft_ms: Optional[float] = None
    success_rate: Optional[float] = None
    observed_context: Optional[str] = None
    observed_status: Optional[str] = None
    speed_rank: Optional[int] = None
    observed_at: str = ""
    source_url: str = "https://nimstats.com"
    confidence: float = 0.85
    raw_evidence_sha256: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EcosystemSignal":
        return cls(
            model_id=data.get("model_id", "unknown"),
            tokens_per_sec=float(data["tokens_per_sec"]) if data.get("tokens_per_sec") is not None else None,
            ttft_ms=float(data["ttft_ms"]) if data.get("ttft_ms") is not None else None,
            success_rate=float(data["success_rate"]) if data.get("success_rate") is not None else None,
            observed_context=str(data["observed_context"]) if data.get("observed_context") is not None else None,
            observed_status=str(data["observed_status"]) if data.get("observed_status") is not None else None,
            speed_rank=int(data["speed_rank"]) if data.get("speed_rank") is not None else None,
            observed_at=data.get("observed_at", ""),
            source_url=data.get("source_url", "https://nimstats.com"),
            confidence=float(data.get("confidence", 0.85)),
            raw_evidence_sha256=data.get("raw_evidence_sha256"),
        )


def compute_sha256(data: bytes) -> str:
    """Calculate SHA-256 hex digest for byte content."""
    return hashlib.sha256(data).hexdigest()


def save_nimstats_raw_evidence(
    raw_bytes: bytes,
    base_dir: Path = DEFAULT_NIMSTATS_SOURCES_DIR,
    source_url: str = DEFAULT_NIMSTATS_URL,
    now: Optional[datetime] = None,
) -> tuple[Path, str]:
    """
    Save raw NIMStats payload snapshot atomically and record SHA-256 integrity.
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    now_dt = now or datetime.now(timezone.utc)
    ts_str = now_dt.strftime("%Y%m%d_%H%M%S")
    sha256_hash = compute_sha256(raw_bytes)
    short_hash = sha256_hash[:8]

    target_file = base_dir / f"nimstats_snapshot_{ts_str}_{short_hash}.json"
    meta_file = base_dir / f"nimstats_snapshot_{ts_str}_{short_hash}.meta.json"

    # Atomic write for payload
    tmp_file = base_dir / f".tmp_payload_{os.getpid()}_{time.time_ns()}"
    try:
        with open(tmp_file, "wb") as f:
            f.write(raw_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, target_file)
    finally:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass

    # Write metadata
    meta_info = {
        "source": "NIMStats",
        "source_url": source_url,
        "saved_at": now_dt.isoformat(),
        "byte_size": len(raw_bytes),
        "sha256": sha256_hash,
        "filename": target_file.name,
    }
    tmp_meta = base_dir / f".tmp_meta_{os.getpid()}_{time.time_ns()}"
    try:
        with open(tmp_meta, "w", encoding="utf-8") as f:
            json.dump(meta_info, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_meta, meta_file)
    finally:
        if tmp_meta.exists():
            try:
                tmp_meta.unlink()
            except Exception:
                pass

    return target_file, sha256_hash


def parse_nimstats_payload(
    raw_data: Union[str, bytes, dict, list],
    source_url: str = DEFAULT_NIMSTATS_URL,
    observed_at: Optional[str] = None,
    sha256_hash: Optional[str] = None,
) -> tuple[list[EcosystemSignal], list[dict[str, Any]]]:
    """
    Parse NIMStats raw JSON into EcosystemSignals with schema drift resilience.
    Returns (valid_signals, malformed_records).
    """
    now_iso = observed_at or datetime.now(timezone.utc).isoformat()

    # Parse JSON if input is str or bytes
    if isinstance(raw_data, (str, bytes)):
        if isinstance(raw_data, bytes):
            if not sha256_hash:
                sha256_hash = compute_sha256(raw_data)
            text_data = raw_data.decode("utf-8", errors="replace").strip()
        else:
            if not sha256_hash:
                sha256_hash = compute_sha256(raw_data.encode("utf-8"))
            text_data = raw_data.strip()

        if not text_data:
            return [], []

        try:
            parsed_json = json.loads(text_data)
        except json.JSONDecodeError as err:
            return [], [{"raw": text_data[:200], "error": f"json_decode_error: {err}"}]
    else:
        parsed_json = raw_data

    # Normalize structure: handle list of records or dict with "data"/"models"/"results"
    records: list[dict[str, Any]] = []
    if isinstance(parsed_json, list):
        for item in parsed_json:
            if isinstance(item, dict):
                records.append(item)
    elif isinstance(parsed_json, dict):
        for container_key in ["data", "models", "results", "benchmarks", "items"]:
            if container_key in parsed_json and isinstance(parsed_json[container_key], list):
                records = [x for x in parsed_json[container_key] if isinstance(x, dict)]
                break
        if not records and "model_id" in parsed_json or "model" in parsed_json:
            records = [parsed_json]

    signals: list[EcosystemSignal] = []
    malformed: list[dict[str, Any]] = []

    for idx, r in enumerate(records):
        # 1. Resolve model ID (support schema drift: model_id, model, id, name)
        mid_raw = r.get("model_id") or r.get("model") or r.get("id") or r.get("name")
        if not mid_raw or not isinstance(mid_raw, str) or "/" not in mid_raw:
            malformed.append({"record_index": idx, "raw": r, "error": "missing_or_invalid_vendor_slash_model_id"})
            continue

        model_id = mid_raw.strip()

        # 2. Extract tokens per second (tps, speed, tokens_per_sec)
        tps = None
        for k in ["tokens_per_sec", "tps", "speed", "speed_tps", "throughput"]:
            if k in r and r[k] is not None:
                try:
                    tps = float(r[k])
                    break
                except (ValueError, TypeError):
                    pass

        # 3. Extract latency / TTFT (ttft, latency, latency_ms)
        ttft = None
        for k in ["ttft_ms", "ttft", "latency_ms", "latency"]:
            if k in r and r[k] is not None:
                try:
                    ttft = float(r[k])
                    break
                except (ValueError, TypeError):
                    pass

        # 4. Extract success rate / availability (success_rate, uptime, availability)
        success_rate = None
        for k in ["success_rate", "uptime", "availability", "success"]:
            if k in r and r[k] is not None:
                try:
                    success_rate = float(r[k])
                    if success_rate > 1.0 and success_rate <= 100.0:
                        success_rate = success_rate / 100.0
                    break
                except (ValueError, TypeError):
                    pass

        # 5. Extract observed context length (context, context_length, max_context)
        obs_context = None
        for k in ["observed_context", "context", "context_length", "max_context"]:
            if k in r and r[k] is not None:
                raw_ctx = str(r[k]).strip()
                if raw_ctx:
                    obs_context = raw_ctx
                    break

        # 6. Extract observed status (status, state)
        obs_status = None
        for k in ["observed_status", "status", "state"]:
            if k in r and r[k] is not None:
                raw_st = str(r[k]).strip().lower()
                if raw_st in ["active", "available", "online"]:
                    obs_status = "active"
                elif raw_st in ["deprecated", "retiring", "removed", "offline"]:
                    obs_status = raw_st
                break

        # 7. Speed rank
        rank = None
        for k in ["speed_rank", "rank", "ranking"]:
            if k in r and r[k] is not None:
                try:
                    rank = int(r[k])
                    break
                except (ValueError, TypeError):
                    pass

        sig = EcosystemSignal(
            model_id=model_id,
            tokens_per_sec=tps,
            ttft_ms=ttft,
            success_rate=success_rate,
            observed_context=obs_context,
            observed_status=obs_status,
            speed_rank=rank,
            observed_at=now_iso,
            source_url=source_url,
            confidence=0.85,
            raw_evidence_sha256=sha256_hash,
        )
        signals.append(sig)

    return signals, malformed


def nimstats_to_evidence_items(
    signal: EcosystemSignal,
    now: Optional[datetime] = None,
) -> list[tuple[str, EvidenceItem]]:
    """
    Adapter: convert EcosystemSignal into (field_name, EvidenceItem) pairs
    ready for submission to the Evidence State Machine.
    """
    now_dt = now or datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    obs_time = signal.observed_at or now_iso

    evidence_pairs: list[tuple[str, EvidenceItem]] = []

    # 1. Observed Context Length Evidence
    if signal.observed_context:
        ev_ctx = EvidenceItem(
            source_id=f"nimstats:{signal.model_id}",
            source_tier=SourceTier.COMMUNITY_SCRAPER,
            source_url=signal.source_url,
            observed_at=obs_time,
            claim=signal.observed_context,
            confidence=signal.confidence,
            raw_payload_snippet=f"NIMStats benchmark observed context={signal.observed_context}",
        )
        evidence_pairs.append(("context.length", ev_ctx))

    # 2. Observed Status Evidence
    if signal.observed_status:
        ev_st = EvidenceItem(
            source_id=f"nimstats:{signal.model_id}",
            source_tier=SourceTier.COMMUNITY_SCRAPER,
            source_url=signal.source_url,
            observed_at=obs_time,
            claim=signal.observed_status,
            confidence=signal.confidence,
            raw_payload_snippet=f"NIMStats benchmark observed status={signal.observed_status}",
        )
        evidence_pairs.append(("lifecycle.availability", ev_st))

    return evidence_pairs


def fetch_nimstats_data(
    url: str = DEFAULT_NIMSTATS_URL,
    timeout: int = 10,
    max_retries: int = 2,
) -> Optional[bytes]:
    """
    Safe HTTP fetcher for NIMStats with strict timeouts, User-Agent, and capped retries.
    Returns bytes or None on failure without throwing unhandled exceptions.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        },
    )

    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read()
                print(f"[WARN] NIMStats fetch returned HTTP {resp.status}", file=sys.stderr)
                return None
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as err:
            if attempt < max_retries:
                time.sleep(1.0)
            else:
                print(f"[INFO] NIMStats fetcher unavailable or blocked ({err}). Falling back gracefully.", file=sys.stderr)
                return None
        except Exception as unk_err:
            print(f"[WARN] Unexpected error fetching NIMStats: {unk_err}", file=sys.stderr)
            return None

    return None
