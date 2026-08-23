# NVIDIA Free Endpoint Monitor (v2)

Automated monitor for NVIDIA Free API endpoints (`https://integrate.api.nvidia.com/v1/models`). Tracks new, removed, and active models, detects catalog changes, and maintains a version-controlled baseline snapshot.

## Features

- **Scheduled & On-Demand Runs**: Executes every 30 minutes via GitHub Actions (`cron`) with manual dispatch support (`workflow_dispatch`).
- **Baseline Comparison & Change Detection**: Compares incoming API data against `data/nvidia_api_models.json` to detect added or removed models.
- **Safety Guards**:
  - `MIN_VALID_MODEL_COUNT = 50`: Prevents updating baseline when response has insufficient models.
  - `MAX_DROP_RATIO = 0.5`: Guards against upstream API outages or partial responses by halting if >50% models drop in a single run.
- **Noise-Free Persistence**: Commits and updates baseline snapshot only when actual model changes are detected (`No model changes detected` runs produce 0 commits).
- **GitHub Step Summary**: Produces structured Markdown reports directly on workflow execution pages.
- **Concurrency Control**: Ensures sequential execution to prevent baseline race conditions.

## Data Artifacts

- **Baseline Snapshot**: `data/nvidia_api_models.json` (committed to repository on change)
- **Workflow Artifact**: `nvidia-api-model-snapshot` (retained for 14 days per run)
