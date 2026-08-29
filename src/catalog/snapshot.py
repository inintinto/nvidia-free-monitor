"""
Raw Snapshot Layer for NVIDIA Build Evidence Preservation (S1-C)
Provides atomic writing, SHA-256 integrity verification, and safe offline reading.
"""

import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

DEFAULT_SNAPSHOTS_DIR = Path("data") / "sources" / "nvidia_build" / "snapshots"
NVIDIA_BUILD_BASE = "https://build.nvidia.com"


class SnapshotError(Exception):
    """Base exception for snapshot operations."""
    pass


class SnapshotCorruptedError(SnapshotError):
    """Raised when snapshot files are missing or SHA-256 checksum mismatches."""
    pass


class InvalidModelIdError(SnapshotError):
    """Raised when a model_id contains unsafe path traversal or invalid characters."""
    pass


class InvalidSourceUrlError(SnapshotError):
    """Raised when source_url does not match the official NVIDIA Build endpoint."""
    pass


def sanitize_model_id(model_id: str) -> str:
    """
    Sanitize and validate model_id to prevent path traversal and invalid filesystem characters.
    e.g. 'meta/llama-3.1-405b-instruct' -> 'meta__llama-3.1-405b-instruct'
    """
    if not model_id or not isinstance(model_id, str):
        raise InvalidModelIdError("model_id must be a non-empty string")

    clean_id = model_id.strip()

    # Block path traversal attempts
    if ".." in clean_id or clean_id.startswith("/") or clean_id.startswith("\\"):
        raise InvalidModelIdError(f"Path traversal detected in model_id: {model_id}")

    # Check for invalid characters in model identifiers
    # Valid model IDs usually follow: provider/model-name or simple-model-name
    # Allowed characters: alphanumeric, dashes, underscores, dots, and a single slash
    if not re.match(r'^[a-zA-Z0-9_\.\-]+(/[a-zA-Z0-9_\.\-]+)?$', clean_id):
        raise InvalidModelIdError(f"Invalid characters in model_id: {model_id}")

    # Replace slash with double underscore for safe directory naming
    safe_name = clean_id.replace("/", "__")
    return safe_name


def validate_source_url(model_id: str, source_url: str) -> None:
    """Ensure source_url is strictly the official NVIDIA Build endpoint for the model."""
    clean_id = model_id.strip()
    expected_url = f"{NVIDIA_BUILD_BASE}/{clean_id}"
    normalized_url = source_url.rstrip("/")
    if normalized_url != expected_url:
        raise InvalidSourceUrlError(
            f"Invalid source_url: {source_url}. Expected: {expected_url}"
        )


def _atomic_write_text(target_path: Path, content: str) -> None:
    """Write text content atomically using a temporary file and atomic rename."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.parent / f".tmp_{uuid.uuid4().hex}_{target_path.name}"
    
    try:
        with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        # Atomic rename
        os.replace(temp_path, target_path)
    except Exception as err:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise err


def save_snapshot(
    model_id: str,
    raw_html: str,
    fetched_at: Optional[str] = None,
    source_url: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> dict[str, Any]:
    """
    Save a raw HTML snapshot and its companion JSON metadata atomically.
    Does NOT modify model_catalog.json.
    """
    if raw_html is None or not isinstance(raw_html, str):
        raise ValueError("raw_html must be a string")

    safe_dir_name = sanitize_model_id(model_id)
    
    if not source_url:
        source_url = f"{NVIDIA_BUILD_BASE}/{model_id.strip()}"
    validate_source_url(model_id, source_url)

    if not fetched_at:
        fetched_at = datetime.now(timezone.utc).isoformat()

    # Calculate SHA-256 of raw UTF-8 content
    html_bytes = raw_html.encode("utf-8")
    content_sha256 = hashlib.sha256(html_bytes).hexdigest()
    content_length = len(html_bytes)

    # Format timestamp for filenames (e.g., 20260826T095000Z)
    try:
        dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        time_tag = dt.strftime("%Y%m%dT%H%M%SZ")
    except Exception:
        time_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    root_dir = Path(base_dir) if base_dir else DEFAULT_SNAPSHOTS_DIR
    model_snapshot_dir = root_dir / safe_dir_name

    html_file = model_snapshot_dir / f"{time_tag}.html"
    meta_file = model_snapshot_dir / f"{time_tag}.json"

    meta_payload = {
        "model_id": model_id.strip(),
        "source_url": source_url,
        "fetched_at": fetched_at,
        "sha256": content_sha256,
        "content_length": content_length,
        "format_version": "1.0",
    }

    # Atomic write HTML, then atomic write Metadata JSON
    _atomic_write_text(html_file, raw_html)
    _atomic_write_text(meta_file, json.dumps(meta_payload, indent=2, ensure_ascii=False) + "\n")

    return {
        "model_id": model_id.strip(),
        "html_path": str(html_file),
        "meta_path": str(meta_file),
        "sha256": content_sha256,
        "content_length": content_length,
        "fetched_at": fetched_at,
    }


def load_snapshot(
    model_id: str,
    timestamp_tag: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> dict[str, Any]:
    """
    Load a raw snapshot and its metadata, strictly verifying SHA-256 integrity.
    If timestamp_tag is None, loads the latest available snapshot for the model.
    """
    safe_dir_name = sanitize_model_id(model_id)
    root_dir = Path(base_dir) if base_dir else DEFAULT_SNAPSHOTS_DIR
    model_snapshot_dir = root_dir / safe_dir_name

    if not model_snapshot_dir.exists() or not model_snapshot_dir.is_dir():
        raise FileNotFoundError(f"No snapshots directory found for model: {model_id}")

    if timestamp_tag:
        target_tag = timestamp_tag
    else:
        # Find latest snapshot by checking json files
        json_files = sorted(model_snapshot_dir.glob("*.json"), reverse=True)
        if not json_files:
            html_files = list(model_snapshot_dir.glob("*.html"))
            if html_files:
                raise SnapshotCorruptedError(f"Orphan snapshot HTML found without metadata in: {model_snapshot_dir}")
            raise FileNotFoundError(f"No snapshot files found for model: {model_id}")
        target_tag = json_files[0].stem

    html_file = model_snapshot_dir / f"{target_tag}.html"
    meta_file = model_snapshot_dir / f"{target_tag}.json"

    if not meta_file.exists():
        raise SnapshotCorruptedError(f"Missing snapshot metadata file: {meta_file}")
    if not html_file.exists():
        raise SnapshotCorruptedError(f"Missing snapshot HTML file: {html_file}")

    with open(meta_file, "r", encoding="utf-8") as f:
        try:
            meta_data = json.load(f)
        except Exception as err:
            raise SnapshotCorruptedError(f"Corrupted metadata JSON in {meta_file}: {err}")

    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Integrity verification
    actual_sha256 = hashlib.sha256(html_content.encode("utf-8")).hexdigest()
    expected_sha256 = meta_data.get("sha256")

    if actual_sha256 != expected_sha256:
        raise SnapshotCorruptedError(
            f"Checksum mismatch for snapshot {target_tag}! "
            f"Expected: {expected_sha256}, Actual: {actual_sha256}"
        )

    return {
        "metadata": meta_data,
        "raw_html": html_content,
        "html_path": str(html_file),
        "meta_path": str(meta_file),
        "timestamp_tag": target_tag,
    }


def list_snapshots(
    model_id: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> list[dict[str, Any]]:
    """List available snapshots ordered by timestamp descending."""
    root_dir = Path(base_dir) if base_dir else DEFAULT_SNAPSHOTS_DIR
    if not root_dir.exists():
        return []

    snapshots = []
    if model_id:
        safe_dirs = [root_dir / sanitize_model_id(model_id)]
    else:
        safe_dirs = [d for d in root_dir.iterdir() if d.is_dir()]

    for s_dir in safe_dirs:
        if not s_dir.exists():
            continue
        for meta_file in sorted(s_dir.glob("*.json"), reverse=True):
            tag = meta_file.stem
            html_file = s_dir / f"{tag}.html"
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                snapshots.append({
                    "model_id": meta.get("model_id"),
                    "tag": tag,
                    "fetched_at": meta.get("fetched_at"),
                    "sha256": meta.get("sha256"),
                    "has_html": html_file.exists(),
                    "meta_path": str(meta_file),
                })
            except Exception:
                continue

    return snapshots
