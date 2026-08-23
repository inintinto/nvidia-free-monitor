import re
from typing import Optional

from .catalog_manager import CatalogManager
from .schema import ModelDetail, ResolveResult


def normalize_text(text: str) -> str:
    """Normalize string by lowercasing, replacing punctuation/symbols/underscores with spaces, and trimming."""
    if not text:
        return ""
    # Replace non-alphanumeric characters (including hyphens, underscores, slashes) with space
    cleaned = re.sub(r"[^\w\s]|_", " ", text.lower())
    return " ".join(cleaned.split())


class ModelResolver:
    """Unified search and resolver engine for Model Catalog."""

    def __init__(self, catalog_manager: Optional[CatalogManager] = None):
        self.catalog_manager = catalog_manager or CatalogManager()

    def resolve(
        self,
        query: str,
        provider: Optional[str] = None,
        capability: Optional[str] = None,
        active_only: bool = False,
    ) -> ResolveResult:
        """Resolve a user query into exact match, multiple candidates, or empty result."""
        raw_query = (query or "").strip()
        norm_query = normalize_text(raw_query)

        # 1. Fetch candidate model pool based on optional provider/capability filters
        candidates = self.catalog_manager.list_models(
            provider_id=provider,
            capability=capability,
            active_only=active_only,
        )

        # Handle empty query with filter applied (e.g. list all in provider/capability)
        if not raw_query:
            if candidates:
                return ResolveResult(
                    query=raw_query,
                    match_type="MULTIPLE",
                    matched_models=candidates,
                    total_matches=len(candidates),
                    filter_provider=provider,
                    filter_capability=capability,
                )
            return ResolveResult(
                query=raw_query,
                match_type="EMPTY",
                matched_models=[],
                total_matches=0,
                filter_provider=provider,
                filter_capability=capability,
            )

        # 2. Score each candidate
        scored_results: list[tuple[int, ModelDetail]] = []
        q_tokens = norm_query.split()

        for model in candidates:
            score = self._calculate_match_score(raw_query, norm_query, q_tokens, model)
            if score > 0:
                scored_results.append((score, model))

        # 3. Sort by score descending, then by display name ascending
        scored_results.sort(key=lambda item: (-item[0], item[1].display_name.lower()))

        if not scored_results:
            return ResolveResult(
                query=raw_query,
                match_type="EMPTY",
                matched_models=[],
                total_matches=0,
                filter_provider=provider,
                filter_capability=capability,
            )

        top_score = scored_results[0][0]
        matched_models = [item[1] for item in scored_results]

        # 4. Determine Match Type
        # Exact match if top score is 100 (exact model_id) or 90 (exact alias/display name) with single top match
        top_tier = [item for item in scored_results if item[0] == top_score]

        if top_score == 100 or (top_score >= 85 and len(top_tier) == 1):
            return ResolveResult(
                query=raw_query,
                match_type="EXACT",
                matched_models=[matched_models[0]],
                total_matches=1,
                filter_provider=provider,
                filter_capability=capability,
            )

        # If multiple candidates matched
        if len(matched_models) == 1:
            return ResolveResult(
                query=raw_query,
                match_type="EXACT",
                matched_models=matched_models,
                total_matches=1,
                filter_provider=provider,
                filter_capability=capability,
            )

        return ResolveResult(
            query=raw_query,
            match_type="MULTIPLE",
            matched_models=matched_models,
            total_matches=len(matched_models),
            filter_provider=provider,
            filter_capability=capability,
        )

    def _calculate_match_score(
        self,
        raw_query: str,
        norm_query: str,
        q_tokens: list[str],
        model: ModelDetail,
    ) -> int:
        """Calculate relevance score (0-100) for a given model."""
        raw_q_lower = raw_query.lower()
        model_id_lower = model.model_id.lower()

        # Rank 1: Exact Model ID Match (Score 100)
        if raw_q_lower == model_id_lower:
            return 100

        # Rank 2: Exact Display Name or Exact Alias Match (Score 90)
        norm_display = normalize_text(model.display_name)
        if norm_query == norm_display:
            return 90

        for alias in model.aliases:
            if norm_query == normalize_text(alias):
                return 90

        # Rank 3: Slug Match (Score 75)
        slug = model.model_id.split("/")[-1] if "/" in model.model_id else model.model_id
        if raw_q_lower == slug.lower() or norm_query == normalize_text(slug):
            return 75

        # Rank 4: Token All-Match (Score 60)
        # Check if all query tokens appear in model searchable representation
        search_blob = " ".join(
            filter(
                None,
                [
                    model.model_id,
                    model.display_name,
                    " ".join(model.aliases),
                    model.model_family or "",
                    model.provider,
                    model.architecture or "",
                ],
            )
        )
        norm_blob = normalize_text(search_blob)
        blob_tokens = set(norm_blob.split())

        if q_tokens and all(token in blob_tokens or any(token in bt for bt in blob_tokens) for token in q_tokens):
            return 60

        # Rank 5: Partial Substring Match in Display Name or Model ID (Score 40)
        if norm_query and (norm_query in norm_display or norm_query in normalize_text(model.model_id)):
            return 40

        # Rank 6: Single Token Match (Score 20, only when query itself is a single token)
        if len(q_tokens) == 1 and any(q_tokens[0] in bt for bt in blob_tokens):
            return 20

        return 0
