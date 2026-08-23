import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

NVIDIA_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"
OUTPUT_FILE = Path("data/nvidia_api_models.json")


def fetch_models() -> dict:
    request = urllib.request.Request(
        NVIDIA_MODELS_URL,
        headers={
            "User-Agent": "NVIDIA-Free-Endpoint-Monitor/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(
                f"NVIDIA API returned HTTP {response.status}"
            )

        return json.loads(
            response.read().decode("utf-8")
        )


def main() -> None:
    print("==================================")
    print("NVIDIA API Model Collector")
    print("==================================")

    payload = fetch_models()

    raw_models = payload.get("data", [])

    models = []

    for item in raw_models:
        model_id = item.get("id")

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

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": NVIDIA_MODELS_URL,
        "model_count": len(models),
        "models": models,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"NVIDIA API returned: {len(raw_models)} records")
    print(f"Valid model IDs: {len(models)}")
    print(f"Saved: {OUTPUT_FILE}")

    print("")
    print("First 20 models:")

    for model in models[:20]:
        print(f"  - {model['id']}")


if __name__ == "__main__":
    main()
