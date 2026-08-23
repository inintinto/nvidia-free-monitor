import html
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

# Telegram Settings
TELEGRAM_MAX_ITEMS_DISPLAY = 30
TELEGRAM_TIMEOUT_SECONDS = 15


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


def format_model_list_for_telegram(model_list: list[str]) -> str:
    """Format model list into HTML lines with length and count limit protection."""
    if not model_list:
        return "• <i>None</i>"

    lines = []
    display_items = model_list[:TELEGRAM_MAX_ITEMS_DISPLAY]
    for m in display_items:
        lines.append(f"• <code>{html.escape(m)}</code>")

    if len(model_list) > TELEGRAM_MAX_ITEMS_DISPLAY:
        remaining = len(model_list) - TELEGRAM_MAX_ITEMS_DISPLAY
        lines.append(f"<i>... and {remaining} more</i>")

    return "\n".join(lines)


def build_telegram_message(diff_result: dict, now_iso: str) -> str:
    """Construct HTML formatted Telegram notification message."""
    is_initial = diff_result["is_initial"]
    cur_cnt = diff_result["current_count"]
    prev_cnt = diff_result["previous_count"]
    added = diff_result["added"]
    removed = diff_result["removed"]
    delta = cur_cnt - prev_cnt

    # Format timestamp (e.g. 2026-08-23 10:09 UTC)
    time_str = now_iso.replace("T", " ").split(".")[0] + " UTC"

    lines = [
        "🤖 <b>NVIDIA Free Endpoint Monitor</b>\n",
        f"⏱ <b>Checked:</b> <code>{html.escape(time_str)}</code>",
    ]

    if is_initial:
        lines.append(f"📊 <b>Initial Baseline:</b> <code>{cur_cnt}</code> models\n")
        lines.append("🚀 <b>Initialized baseline snapshot.</b>")
    else:
        delta_sign = f"+{delta}" if delta > 0 else f"{delta}"
        lines.append(f"📊 <b>Models:</b> <code>{prev_cnt} → {cur_cnt} ({delta_sign})</code>\n")

        if added:
            lines.append(f"🟢 <b>Added Models ({len(added)}):</b>")
            lines.append(format_model_list_for_telegram(added))
            lines.append("")

        if removed:
            lines.append(f"🔴 <b>Removed Models ({len(removed)}):</b>")
            lines.append(format_model_list_for_telegram(removed))
            lines.append("")

        if not added and not removed:
            lines.append("<i>No model changes detected.</i>")

    gh_repo = os.getenv("GITHUB_REPOSITORY")
    if gh_repo:
        gh_server = os.getenv("GITHUB_SERVER_URL", "https://github.com")
        repo_url = f"{gh_server}/{gh_repo}"
        lines.append(f"\n🔗 <a href=\"{html.escape(repo_url)}\">View Repository</a>")

    return "\n".join(lines).strip()


def send_telegram_notification(diff_result: dict, now_iso: str) -> None:
    """Send Telegram notification safely if credentials exist and changes occurred on existing baseline."""
    # Strictly require existing baseline with detected changes
    if diff_result.get("is_initial") or not diff_result.get("has_changes"):
        return

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[INFO] Telegram credentials not configured, skipping notification.")
        return

    try:
        message_text = build_telegram_message(diff_result, now_iso)
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=TELEGRAM_TIMEOUT_SECONDS) as resp:
            if resp.status == 200:
                print("[INFO] Telegram notification sent successfully.")
            else:
                print(f"[WARN] Telegram API responded with status {resp.status}")
    except Exception as err:
        print(f"[WARN] Failed to send Telegram notification: {err}")


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

    # 4. Save baseline & Send Notification
    if diff_result["is_initial"] or diff_result["has_changes"]:
        save_baseline(models, now_iso)
        if not diff_result["is_initial"] and diff_result["has_changes"]:
            send_telegram_notification(diff_result, now_iso)
    else:
        print("[INFO] No changes detected. Baseline file untouched.")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"\n[ERROR] Monitor execution failed: {err}", file=sys.stderr)
        sys.exit(1)
