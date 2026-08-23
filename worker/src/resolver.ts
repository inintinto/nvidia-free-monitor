import { CatalogStore } from "./catalog.ts";
import type { ModelDetail, ResolveResult } from "./types.ts";

export function normalizeText(text: string): string {
  if (!text) return "";
  // Replace non-alphanumeric characters, underscores, hyphens, slashes with space
  const cleaned = text.toLowerCase().replace(/[^\w\s]|_/g, " ");
  return cleaned.trim().replace(/\s+/g, " ");
}

export class ModelResolver {
  private store: CatalogStore;

  constructor(store: CatalogStore) {
    this.store = store;
  }

  resolve(
    query: string,
    provider?: string,
    capability?: string
  ): ResolveResult {
    const rawQuery = (query || "").trim();
    const normQuery = normalizeText(rawQuery);

    const candidates = this.store.listModels(provider, capability);

    if (!rawQuery) {
      if (candidates.length > 0) {
        return {
          query: rawQuery,
          match_type: "MULTIPLE",
          matched_models: candidates,
          total_matches: candidates.length,
          filter_provider: provider,
          filter_capability: capability,
        };
      }
      return {
        query: rawQuery,
        match_type: "EMPTY",
        matched_models: [],
        total_matches: 0,
        filter_provider: provider,
        filter_capability: capability,
      };
    }

    const scored: Array<{ score: number; model: ModelDetail }> = [];
    const qTokens = normQuery.split(" ").filter(Boolean);

    for (const model of candidates) {
      const score = this.calculateMatchScore(rawQuery, normQuery, qTokens, model);
      if (score > 0) {
        scored.push({ score, model });
      }
    }

    // Sort by score descending, then display name ascending
    scored.sort((a, b) => b.score - a.score || a.model.display_name.localeCompare(b.model.display_name));

    if (scored.length === 0) {
      return {
        query: rawQuery,
        match_type: "EMPTY",
        matched_models: [],
        total_matches: 0,
        filter_provider: provider,
        filter_capability: capability,
      };
    }

    const topScore = scored[0].score;
    const topTier = scored.filter((item) => item.score === topScore);
    const matchedModels = scored.map((item) => item.model);

    // Exact match: score 100 (exact ID) or score >= 85 with single highest winner
    if (topScore === 100 || (topScore >= 85 && topTier.length === 1)) {
      return {
        query: rawQuery,
        match_type: "EXACT",
        matched_models: [matchedModels[0]],
        total_matches: 1,
        filter_provider: provider,
        filter_capability: capability,
      };
    }

    if (matchedModels.length === 1) {
      return {
        query: rawQuery,
        match_type: "EXACT",
        matched_models: matchedModels,
        total_matches: 1,
        filter_provider: provider,
        filter_capability: capability,
      };
    }

    return {
      query: rawQuery,
      match_type: "MULTIPLE",
      matched_models: matchedModels,
      total_matches: matchedModels.length,
      filter_provider: provider,
      filter_capability: capability,
    };
  }

  private calculateMatchScore(
    rawQuery: string,
    normQuery: string,
    qTokens: string[],
    model: ModelDetail
  ): number {
    const rawQLower = rawQuery.toLowerCase();
    const modelIdLower = model.model_id.toLowerCase();

    // Rank 1: Exact Model ID Match (Score 100)
    if (rawQLower === modelIdLower) {
      return 100;
    }

    // Rank 2: Exact Display Name or Exact Alias Match (Score 90)
    const normDisplay = normalizeText(model.display_name);
    if (normQuery === normDisplay) {
      return 90;
    }

    for (const alias of model.aliases) {
      if (normQuery === normalizeText(alias)) {
        return 90;
      }
    }

    // Rank 3: Slug / Suffix Match (Score 75)
    const slug = model.model_id.includes("/") ? model.model_id.split("/").slice(1).join("/") : model.model_id;
    if (rawQLower === slug.toLowerCase() || normQuery === normalizeText(slug)) {
      return 75;
    }

    // Rank 4: Token All-Match (Score 60)
    const searchBlob = [
      model.model_id,
      model.display_name,
      ...model.aliases,
      model.model_family || "",
      model.provider,
      model.architecture || "",
    ]
      .filter(Boolean)
      .join(" ");
    const normBlob = normalizeText(searchBlob);
    const blobTokens = new Set(normBlob.split(" ").filter(Boolean));

    if (qTokens.length > 0) {
      const allTokensFound = qTokens.every(
        (token) => blobTokens.has(token) || Array.from(blobTokens).some((bt) => bt.includes(token))
      );
      if (allTokensFound) {
        return 60;
      }
    }

    // Rank 5: Partial Substring Match (Score 40)
    if (normQuery && (normDisplay.includes(normQuery) || normalizeText(model.model_id).includes(normQuery))) {
      return 40;
    }

    // Rank 6: Single Token Match (Score 20, only when the query itself is a single token)
    if (qTokens.length === 1 && (blobTokens.has(qTokens[0]) || Array.from(blobTokens).some((bt) => bt.includes(qTokens[0])))) {
      return 20;
    }

    return 0;
  }
}
