import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ================= Configuration =================
NVIDIA_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"
BASE_DIR = Path(__file__).resolve().parent.parent
BASELINE_FILE = BASE_DIR / "data" / "nvidia_api_models.json"

# Safety Guards
MIN_VALID_MODEL_COUNT = 50
MAX_DROP_RATIO = 0.5
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30


def fetch_models() -> dict:
    """Fetch model list from NVIDIA API with retry and safety checks."""
    request = urllib.request.Request(
        NVIDIA_MODELS_URL,
        headers={
            "User-Agent": "NVIDIA-Free-Endpoint-Monitor/2.0",
            "Accept": "application/json",
        },
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise RuntimeError(f"NVIDIA API returned HTTP status {response.status}")

                content = response.read().decode("utf-8")
                try:
                    payload = json.loads(content)
                except json.JSONDecodeError as err:
                    raise RuntimeError(f"Failed to parse JSON response: {err}") from err

                if not isinstance(payload, dict) or "data" not in payload:
                    raise RuntimeError("Invalid API response format: missing 'data' field")

                return payload
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as err:
            last_error = err
            print(f"[WARN] Attempt {attempt}/{MAX_RETRIES} failed: {err}")
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)

    raise RuntimeError(f"All {MAX_RETRIES} attempts to fetch NVIDIA models failed: {last_error}")


def extract_models(payload: dict) -> list[dict]:
    """Extract, filter, and sort valid model items."""
    raw_models = payload.get("data", [])
    if not isinstance(raw_models, list):
        raise RuntimeError("Invalid 'data' field type in API response: expected list")

    models = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")

        if not isinstance(model_id, str):
            continue

        model_id = model_id.strip()

        if not model_id:
            continue

        models.append(
            {
                "id": model_id,
                "owned_by": item.get("owned_by"),
                "created": item.get("created"),
            }
        )

    models.sort(key=lambda x: x["id"])
    return models


def load_baseline() -> dict | None:
    """Load previous baseline snapshot if it exists."""
    if not BASELINE_FILE.exists():
        return None

    try:
        content = BASELINE_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, dict) and "models" in data:
            return data
    except Exception as err:
        print(f"[WARN] Failed to read existing baseline file ({BASELINE_FILE}): {err}")

    return None


def compare_models(baseline_data: dict | None, current_models: list[dict]) -> dict:
    """Compare current models against baseline and enforce safety thresholds."""
    current_count = len(current_models)

    # 1. Minimum valid count threshold
    if current_count < MIN_VALID_MODEL_COUNT:
        raise RuntimeError(
            f"Safety Guard Triggered: Fetched {current_count} models, "
            f"which is below the minimum threshold of {MIN_VALID_MODEL_COUNT}. "
            "Refusing to update baseline."
        )

    current_id_set = {m["id"] for m in current_models}

    # Initial run (No baseline)
    if baseline_data is None:
        return {
            "is_initial": True,
            "has_changes": True,
            "previous_count": 0,
            "current_count": current_count,
            "added": sorted(list(current_id_set)),
            "removed": [],
            "previous_checked_at": None,
        }

    old_models = baseline_data.get("models", [])
    old_id_set = {m["id"] for m in old_models if isinstance(m, dict) and "id" in m}
    old_count = len(old_id_set)

    added = sorted(list(current_id_set - old_id_set))
    removed = sorted(list(old_id_set - current_id_set))

    # 2. Maximum drop ratio safety threshold
    if old_count > 0 and (len(removed) / old_count) > MAX_DROP_RATIO:
        drop_ratio = len(removed) / old_count
        raise RuntimeError(
            f"Safety Guard Triggered: {len(removed)}/{old_count} ({drop_ratio:.1%}) models removed, "
            f"exceeding the maximum allowed drop ratio of {MAX_DROP_RATIO:.0%}. "
            "Possible upstream API outage or partial response. Refusing to update baseline."
        )

    has_changes = len(added) > 0 or len(removed) > 0

    return {
        "is_initial": False,
        "has_changes": has_changes,
        "previous_count": old_count,
        "current_count": current_count,
        "added": added,
        "removed": removed,
        "previous_checked_at": baseline_data.get("checked_at"),
    }


def save_baseline(current_models: list[dict], now_iso: str) -> None:
    """Save the updated snapshot to baseline file."""
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "checked_at": now_iso,
        "source": NVIDIA_MODELS_URL,
        "model_count": len(current_models),
        "models": current_models,
    }
    BASELINE_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[INFO] Baseline updated and saved to: {BASELINE_FILE}")


def write_github_step_summary(diff_result: dict, now_iso: str) -> None:
    """Write formatted markdown report to GITHUB_STEP_SUMMARY if available."""
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    is_initial = diff_result["is_initial"]
    has_changes = diff_result["has_changes"]
    cur_cnt = diff_result["current_count"]
    prev_cnt = diff_result["previous_count"]
    added = diff_result["added"]
    removed = diff_result["removed"]

    lines = []
    lines.append("## 🤖 NVIDIA Free Endpoint Monitor v2 Report\n")

    if is_initial:
        status_badge = "🚀 **Initial Baseline Created**"
    elif has_changes:
        status_badge = f"🟡 **Changes Detected** (+{len(added)} / -{len(removed)})"
    else:
        status_badge = "🟢 **No Model Changes Detected**"

    lines.append(f"**Run Status**: {status_badge}\n")
    lines.append(f"- **Checked At (UTC)**: `{now_iso}`")
    lines.append(f"- **Current Models**: `{cur_cnt}`")
    if not is_initial:
        lines.append(f"- **Previous Models**: `{prev_cnt}`")
        lines.append(f"- **Net Delta**: `{cur_cnt - prev_cnt:+d}`")
    lines.append("")

    if is_initial:
        lines.append(f"> Initialized baseline with **{cur_cnt}** models.")
    elif not has_changes:
        lines.append("> ✅ All models match the current baseline. No changes detected.")
    else:
        if added:
            lines.append(f"### 🟢 Added Models ({len(added)})")
            for model_id in added:
                lines.append(f"- `{model_id}`")
            lines.append("")
        if removed:
            lines.append(f"### 🔴 Removed Models ({len(removed)})")
            for model_id in removed:
                lines.append(f"- `{model_id}`")
            lines.append("")

    try:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as err:
        print(f"[WARN] Failed to write to GITHUB_STEP_SUMMARY: {err}")


def print_console_report(diff_result: dict, now_iso: str) -> None:
    """Print readable report to stdout."""
    is_initial = diff_result["is_initial"]
    has_changes = diff_result["has_changes"]
    cur_cnt = diff_result["current_count"]
    prev_cnt = diff_result["previous_count"]
    added = diff_result["added"]
    removed = diff_result["removed"]

    print("==================================")
    print("NVIDIA Free Endpoint Monitor v2")
    print("==================================")
    print(f"Timestamp (UTC) : {now_iso}")
    print(f"Current Models  : {cur_cnt}")

    if is_initial:
        print("[INITIAL BASELINE CREATED]")
        print(f"Initialized baseline snapshot with {cur_cnt} models.")
        print("==================================")
        return

    print(f"Previous Models : {prev_cnt}")
    print(f"Net Delta       : {cur_cnt - prev_cnt:+d}")
    print("----------------------------------")
    print("Diff Summary:")
    print(f"  + Added   : {len(added)}")
    print(f"  - Removed : {len(removed)}")
    print("----------------------------------")

    if not has_changes:
        print("No model changes detected.")
    else:
        if added:
            print(f"[+] Added Models ({len(added)}):")
            for m in added:
                print(f"    + {m}")
        if removed:
            print(f"[-] Removed Models ({len(removed)}):")
            for m in removed:
                print(f"    - {m}")

    print("==================================")


def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Fetch & Validate
    payload = fetch_models()
    models = extract_models(payload)

    # 2. Compare with Baseline
    baseline_data = load_baseline()
    diff_result = compare_models(baseline_data, models)

    # 3. Print & Report
    print_console_report(diff_result, now_iso)
    write_github_step_summary(diff_result, now_iso)

    # 4. Save baseline ONLY if initial or changes detected
    if diff_result["is_initial"] or diff_result["has_changes"]:
        save_baseline(models, now_iso)
    else:
        print("[INFO] No changes detected. Baseline file untouched.")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"\n[ERROR] Monitor execution failed: {err}", file=sys.stderr)
        sys.exit(1)
