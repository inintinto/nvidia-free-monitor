import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MODELS_URL = "https://build.nvidia.com/models"

OUTPUT_FILE = Path("data/nvidia_models.json")


def fetch_models_page() -> str:
    request = urllib.request.Request(
        MODELS_URL,
        headers={
            "User-Agent": "Mozilla/5.0 NVIDIA-Free-Endpoint-Monitor/1.0"
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_models(html: str) -> list[dict]:
    """
    First-stage parser.

    NVIDIA's public models page is a dynamic web application, so this
    intentionally stores the raw page snapshot for now. We will replace
    this parser with the official structured data source after confirming
    its current format.
    """
    models = []

    # Keep a lightweight record of model names visible in the HTML.
    # This is deliberately conservative; it is not yet the final parser.
    pattern = re.compile(
        r'"(?:modelId|model_id|slug|name)"\s*:\s*"([^"]+)"',
        re.IGNORECASE,
    )

    seen = set()

    for match in pattern.finditer(html):
        value = match.group(1).strip()

        if not value or value in seen:
            continue

        seen.add(value)
        models.append({"name": value})

    return models


def main() -> None:
    print("Fetching NVIDIA Models page...")

    html = fetch_models_page()

    print(f"Downloaded: {len(html):,} bytes")

    models = extract_models(html)

    print(f"Candidate model records found: {len(models)}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": MODELS_URL,
        "model_count": len(models),
        "models": models,
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved snapshot: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
