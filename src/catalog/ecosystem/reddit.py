"""
Reddit / Community Ecosystem Signal Integration (Phase S3-C)
Provides Reddit community signal extraction, Evidence State Machine adapter,
SHA-256 raw evidence storage, and compliant OAuth-based connectivity handling.
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
import urllib.parse
import urllib.request

from src.catalog.evidence import EvidenceItem, SourceTier

DEFAULT_REDDIT_SOURCES_DIR = Path("data") / "sources" / "reddit"
DEFAULT_REDDIT_USER_AGENT = "script:NvidiaFreeMonitor:3.0 (by /u/nvidia-free-monitor)"


@dataclass(frozen=True)
class CommunitySignal:
    """Standardized community forum discussion signal."""
    model_id: str
    claim_type: str                     # "context.length", "lifecycle.availability", "performance_tps", "replacement_model_id"
    claim_value: Any                    # e.g. "128k", "deprecated", "meta/llama-3.3-70b-instruct"
    source_id: str                      # e.g. "reddit:r/LocalLLaMA:post_1a2b3c"
    source_url: str                     # e.g. "https://reddit.com/r/LocalLLaMA/comments/1a2b3c"
    subreddit: str                      # e.g. "LocalLLaMA"
    post_id: str                        # e.g. "1a2b3c"
    author: Optional[str] = None
    observed_at: str = ""
    confidence: float = 0.60            # Community forum baseline confidence (0.60)
    raw_evidence_sha256: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommunitySignal":
        return cls(
            model_id=data.get("model_id", "unknown"),
            claim_type=data.get("claim_type", "unknown"),
            claim_value=data.get("claim_value"),
            source_id=data.get("source_id", "unknown"),
            source_url=data.get("source_url", ""),
            subreddit=data.get("subreddit", "unknown"),
            post_id=data.get("post_id", "unknown"),
            author=data.get("author"),
            observed_at=data.get("observed_at", ""),
            confidence=float(data.get("confidence", 0.60)),
            raw_evidence_sha256=data.get("raw_evidence_sha256"),
        )


def compute_sha256(data: bytes) -> str:
    """Calculate SHA-256 hex digest for byte content."""
    return hashlib.sha256(data).hexdigest()


def generate_reddit_evidence_hash(
    raw_bytes: bytes,
    source_url: str = "https://reddit.com",
    now: Optional[datetime] = None,
) -> tuple[str, dict[str, Any]]:
    """
    Zero Raw Storage metadata generator (Production Mode).
    Calculates SHA-256 cryptographic proof in-memory without persisting any
    raw Reddit User Content (titles, body text, or author identities) to disk.
    """
    now_dt = now or datetime.now(timezone.utc)
    sha256_hash = compute_sha256(raw_bytes)

    meta_info = {
        "source": "Reddit",
        "source_url": source_url,
        "observed_at": now_dt.isoformat(),
        "byte_size": len(raw_bytes),
        "sha256": sha256_hash,
        "storage_mode": "in_memory_zero_storage",
    }
    return sha256_hash, meta_info


def save_reddit_raw_evidence(
    raw_bytes: bytes,
    base_dir: Path = DEFAULT_REDDIT_SOURCES_DIR,
    source_url: str = "https://reddit.com",
    now: Optional[datetime] = None,
    persist_to_disk: bool = False,
) -> tuple[Optional[Path], str]:
    """
    Generate SHA-256 integrity hash for Reddit raw response.
    By default (persist_to_disk=False), operates strictly in memory (Zero Storage).
    Disk writing is only performed if explicitly requested for offline testing.
    """
    sha256_hash = compute_sha256(raw_bytes)
    if not persist_to_disk:
        return None, sha256_hash

    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    now_dt = now or datetime.now(timezone.utc)
    ts_str = now_dt.strftime("%Y%m%d_%H%M%S")
    short_hash = sha256_hash[:8]

    target_file = base_dir / f"reddit_snapshot_{ts_str}_{short_hash}.json"
    meta_file = base_dir / f"reddit_snapshot_{ts_str}_{short_hash}.meta.json"

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

    meta_info = {
        "source": "Reddit",
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


def parse_reddit_payload(
    raw_data: Union[str, bytes, dict, list],
    source_url_base: str = "https://reddit.com",
    observed_at: Optional[str] = None,
    sha256_hash: Optional[str] = None,
) -> tuple[list[CommunitySignal], list[dict[str, Any]]]:
    """
    Parse Reddit raw listing JSON into CommunitySignals.
    Filters out malformed posts or posts lacking clear model context claims.
    """
    now_iso = observed_at or datetime.now(timezone.utc).isoformat()

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

    # Extract posts from standard Reddit listing schema {"data": {"children": [...]}} or list
    raw_posts = []
    if isinstance(parsed_json, dict):
        if "data" in parsed_json and isinstance(parsed_json["data"], dict) and "children" in parsed_json["data"]:
            for child in parsed_json["data"]["children"]:
                if isinstance(child, dict) and "data" in child and isinstance(child["data"], dict):
                    raw_posts.append(child["data"])
        elif "posts" in parsed_json and isinstance(parsed_json["posts"], list):
            raw_posts = [p for p in parsed_json["posts"] if isinstance(p, dict)]
        elif "model_id" in parsed_json or "id" in parsed_json:
            raw_posts = [parsed_json]
    elif isinstance(parsed_json, list):
        for item in parsed_json:
            if isinstance(item, dict):
                if "data" in item and isinstance(item["data"], dict):
                    raw_posts.append(item["data"])
                else:
                    raw_posts.append(item)

    signals: list[CommunitySignal] = []
    malformed: list[dict[str, Any]] = []

    for idx, p in enumerate(raw_posts):
        post_id = str(p.get("id") or f"post_{idx}").strip()
        subreddit = str(p.get("subreddit") or "LocalLLaMA").strip()
        author = str(p.get("author") or "anonymous").strip()
        title = str(p.get("title") or "").strip()
        selftext = str(p.get("selftext") or "").strip()
        permalink = p.get("permalink") or f"/r/{subreddit}/comments/{post_id}"
        post_url = f"https://reddit.com{permalink}" if permalink.startswith("/") else permalink

        combined_text = f"{title}\n{selftext}"

        # Resolve model_id: from explicit field or regex in post text
        explicit_mid = p.get("model_id") or p.get("model")
        if explicit_mid and isinstance(explicit_mid, str) and "/" in explicit_mid:
            model_id = explicit_mid.strip()
        else:
            # Match vendor/model pattern in title/text
            m_match = re.search(r'\b([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\.\-]+)\b', combined_text)
            if m_match:
                model_id = m_match.group(1).strip()
            else:
                malformed.append({"record_index": idx, "post_id": post_id, "error": "no_vendor_slash_model_found"})
                continue

        # Extract Claims
        claims_found = 0

        # 1. Context length claim: e.g. "8k context", "128k context", "1M context", "32k ctx"
        ctx_match = re.search(r'\b(4k|8k|16k|32k|64k|128k|256k|512k|1M|2M)\s+(?:context|ctx|tokens|length)\b', combined_text, re.IGNORECASE)
        if ctx_match:
            raw_ctx = ctx_match.group(1)
            norm_ctx = "1M" if raw_ctx.upper() == "1M" else raw_ctx.lower()
            signals.append(
                CommunitySignal(
                    model_id=model_id,
                    claim_type="context.length",
                    claim_value=norm_ctx,
                    source_id=f"reddit:r/{subreddit}:{post_id}",
                    source_url=post_url,
                    subreddit=subreddit,
                    post_id=post_id,
                    author=author,
                    observed_at=now_iso,
                    confidence=0.60,
                    raw_evidence_sha256=sha256_hash,
                )
            )
            claims_found += 1

        # 2. Availability / Status claim: "deprecated", "removed", "broken", "offline" vs "working", "active"
        if re.search(r'\b(?:deprecated|discontinued|shutting down|retiring)\b', combined_text, re.IGNORECASE):
            signals.append(
                CommunitySignal(
                    model_id=model_id,
                    claim_type="lifecycle.availability",
                    claim_value="deprecated",
                    source_id=f"reddit:r/{subreddit}:{post_id}",
                    source_url=post_url,
                    subreddit=subreddit,
                    post_id=post_id,
                    author=author,
                    observed_at=now_iso,
                    confidence=0.60,
                    raw_evidence_sha256=sha256_hash,
                )
            )
            claims_found += 1
        elif re.search(r'\b(?:is down|endpoint offline|no longer works|broken)\b', combined_text, re.IGNORECASE):
            signals.append(
                CommunitySignal(
                    model_id=model_id,
                    claim_type="lifecycle.availability",
                    claim_value="removed",
                    source_id=f"reddit:r/{subreddit}:{post_id}",
                    source_url=post_url,
                    subreddit=subreddit,
                    post_id=post_id,
                    author=author,
                    observed_at=now_iso,
                    confidence=0.50,
                    raw_evidence_sha256=sha256_hash,
                )
            )
            claims_found += 1

        # 3. Replacement model claim: e.g. "use meta/llama-3.3-70b-instruct instead"
        rep_match = re.search(r'(?:use|switch to|replaced by|successor is)\s+([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\.\-]+)', combined_text, re.IGNORECASE)
        if rep_match:
            rep_id = rep_match.group(1).strip()
            if rep_id != model_id:
                signals.append(
                    CommunitySignal(
                        model_id=model_id,
                        claim_type="lifecycle.replacement_model_id",
                        claim_value=rep_id,
                        source_id=f"reddit:r/{subreddit}:{post_id}",
                        source_url=post_url,
                        subreddit=subreddit,
                        post_id=post_id,
                        author=author,
                        observed_at=now_iso,
                        confidence=0.55,
                        raw_evidence_sha256=sha256_hash,
                    )
                )
                claims_found += 1

        if claims_found == 0:
            malformed.append({"record_index": idx, "post_id": post_id, "error": "no_actionable_catalog_claims_in_text"})

    return signals, malformed


def reddit_to_evidence_items(
    signal: CommunitySignal,
    now: Optional[datetime] = None,
) -> list[tuple[str, EvidenceItem]]:
    """
    Adapter: convert CommunitySignal into (field_name, EvidenceItem) pairs
    strictly typed as SourceTier.COMMUNITY_FORUM.
    """
    now_dt = now or datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    obs_time = signal.observed_at or now_iso

    ev = EvidenceItem(
        source_id=signal.source_id,
        source_tier=SourceTier.COMMUNITY_FORUM,
        source_url=signal.source_url,
        observed_at=obs_time,
        claim=signal.claim_value,
        confidence=signal.confidence,
        raw_payload_snippet=f"Reddit r/{signal.subreddit} post {signal.post_id} claim: {signal.claim_type}={signal.claim_value}",
    )

    return [(signal.claim_type, ev)]


def fetch_reddit_data(
    subreddit: str = "LocalLLaMA",
    query: str = "NVIDIA NIM",
    timeout: int = 10,
    max_retries: int = 1,
) -> tuple[Optional[bytes], str]:
    """
    Compliant OAuth / standard check for Reddit API.
    If credentials (REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET) are missing,
    gracefully returns (None, 'credentials_not_configured') without violating terms.
    """
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None, "credentials_not_configured"

    # Authenticated OAuth 2.0 flow
    token_url = "https://www.reddit.com/api/v1/access_token"
    auth_header = "Basic " + urllib.parse.quote(f"{client_id}:{client_secret}")
    
    try:
        # Obtain access token
        auth_req = urllib.request.Request(
            token_url,
            data=b"grant_type=client_credentials",
            headers={
                "User-Agent": DEFAULT_REDDIT_USER_AGENT,
                "Authorization": auth_header,
            },
        )
        with urllib.request.urlopen(auth_req, timeout=timeout) as resp:
            if resp.status != 200:
                return None, f"auth_http_{resp.status}"
            auth_data = json.loads(resp.read().decode("utf-8"))
            access_token = auth_data.get("access_token")
            if not access_token:
                return None, "no_access_token_returned"

        # Search endpoint
        search_url = f"https://oauth.reddit.com/r/{subreddit}/search?q={urllib.parse.quote(query)}&restrict_sr=on&sort=new&limit=10"
        search_req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": DEFAULT_REDDIT_USER_AGENT,
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(search_req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read(), "success"
            return None, f"http_{resp.status}"
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as err:
        return None, f"network_error: {err}"
    except Exception as ex:
        return None, f"exception: {ex}"
