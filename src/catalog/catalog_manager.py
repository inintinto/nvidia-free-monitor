import json
from pathlib import Path
from typing import Any, Optional

from .schema import LifecycleRecord, ModelDetail


class CatalogManager:
    """Manages loading and merging of Model Catalog, Lifecycle, and API Baseline."""

    def __init__(
        self,
        catalog_path: Optional[Path] = None,
        lifecycle_path: Optional[Path] = None,
        baseline_path: Optional[Path] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.catalog_path = catalog_path or (base_dir / "data" / "model_catalog.json")
        self.lifecycle_path = lifecycle_path or (base_dir / "data" / "lifecycle.json")
        self.baseline_path = baseline_path or (base_dir / "data" / "nvidia_api_models.json")

        self._catalog_raw: dict[str, Any] = {}
        self._lifecycle_raw: dict[str, Any] = {}
        self._baseline_models: list[dict[str, Any]] = []
        self._models_cache: dict[str, ModelDetail] = {}

        self.reload()

    def reload(self) -> None:
        """Reload all data files and rebuild the in-memory ModelDetail registry."""
        self._load_baseline()
        self._load_catalog()
        self._load_lifecycle()
        self._rebuild_cache()

    def _load_baseline(self) -> None:
        """Load raw API models list from baseline JSON if present."""
        if not self.baseline_path.exists():
            self._baseline_models = []
            return
        try:
            content = self.baseline_path.read_text(encoding="utf-8")
            data = json.loads(content)
            self._baseline_models = data.get("models", [])
        except Exception:
            self._baseline_models = []

    def _load_catalog(self) -> None:
        """Load curated rich catalog JSON if present."""
        if not self.catalog_path.exists():
            self._catalog_raw = {}
            return
        try:
            content = self.catalog_path.read_text(encoding="utf-8")
            data = json.loads(content)
            self._catalog_raw = data.get("models", {})
        except Exception:
            self._catalog_raw = {}

    def _load_lifecycle(self) -> None:
        """Load lifecycle history JSON if present."""
        if not self.lifecycle_path.exists():
            self._lifecycle_raw = {}
            return
        try:
            content = self.lifecycle_path.read_text(encoding="utf-8")
            data = json.loads(content)
            self._lifecycle_raw = data.get("history", {})
        except Exception:
            self._lifecycle_raw = {}

    def _rebuild_cache(self) -> None:
        """Merge all sources into a unified ModelDetail dictionary keyed by model_id."""
        self._models_cache.clear()

        # 1. Collect all known model IDs across baseline, catalog, and lifecycle
        all_ids: set[str] = set()
        for m in self._baseline_models:
            if isinstance(m, dict) and "id" in m:
                all_ids.add(m["id"])
        all_ids.update(self._catalog_raw.keys())
        all_ids.update(self._lifecycle_raw.keys())

        # 2. Build ModelDetail for each model ID with graceful fallbacks
        for model_id in sorted(all_ids):
            cat_data = self._catalog_raw.get(model_id)
            life_data = self._lifecycle_raw.get(model_id)
            model_detail = ModelDetail.from_dict(
                model_id=model_id,
                catalog_data=cat_data,
                lifecycle_data=life_data,
            )
            self._models_cache[model_id] = model_detail

    def get_model(self, model_id: str) -> Optional[ModelDetail]:
        """Fetch model by exact model_id, returning None if not found."""
        return self._models_cache.get(model_id)

    def list_models(
        self,
        provider_id: Optional[str] = None,
        capability: Optional[str] = None,
        active_only: bool = False,
    ) -> list[ModelDetail]:
        """List models filtered by provider, capability, and active state."""
        results: list[ModelDetail] = []
        for model in self._models_cache.values():
            if active_only and not model.lifecycle.is_currently_active:
                continue

            if provider_id:
                norm_p = provider_id.lower().replace(" ", "").replace("-", "")
                m_p = model.provider_id.lower().replace(" ", "").replace("-", "")
                m_p_name = model.provider.lower().replace(" ", "").replace("-", "")
                if norm_p not in (m_p, m_p_name):
                    continue

            if capability and capability.lower() != "all":
                cap_lower = capability.lower()
                model_caps_lower = [c.lower() for c in model.capabilities]
                if cap_lower not in model_caps_lower:
                    continue

            results.append(model)

        results.sort(key=lambda m: (m.provider.lower(), m.display_name.lower()))
        return results

    def get_all_providers(self, active_only: bool = False) -> list[dict[str, Any]]:
        """Get summary list of all providers with model counts."""
        prov_map: dict[str, dict[str, Any]] = {}
        for model in self._models_cache.values():
            if active_only and not model.lifecycle.is_currently_active:
                continue
            pid = model.provider_id
            if pid not in prov_map:
                prov_map[pid] = {
                    "provider_id": pid,
                    "display_name": model.provider,
                    "model_count": 0,
                }
            prov_map[pid]["model_count"] += 1

        providers = list(prov_map.values())
        providers.sort(key=lambda x: (-x["model_count"], x["display_name"]))
        return providers

    def get_all_capabilities(self) -> list[str]:
        """Get distinct list of all capabilities across all models."""
        caps: set[str] = set()
        for model in self._models_cache.values():
            caps.update(model.capabilities)
        order = ["Chat", "Reasoning", "Coding", "Vision", "Audio", "Video", "Embedding", "Agentic"]
        sorted_caps = [c for c in order if c in caps]
        other_caps = sorted([c for c in caps if c not in order])
        return sorted_caps + other_caps
