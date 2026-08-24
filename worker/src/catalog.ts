import { getProviderDisplayName, inferTierFromModelId } from "./branding.ts";
import type {
  LifecycleRecord,
  ModelDetail,
  OfficialLifecycle,
  ProviderSummary,
  UsageStats,
} from "./types.ts";

export class CatalogStore {
  private modelsMap: Map<string, ModelDetail> = new Map();
  private indexMap: Map<number, ModelDetail> = new Map();
  private modelToShortIndex: Map<string, number> = new Map();

  constructor(
    catalogRaw?: { models?: Record<string, Record<string, unknown>> },
    lifecycleRaw?: { history?: Record<string, Record<string, unknown>> },
    baselineRaw?: { models?: Array<{ id: string; owned_by?: string }> }
  ) {
    this.rebuild(catalogRaw, lifecycleRaw, baselineRaw);
  }

  rebuild(
    catalogRaw?: { models?: Record<string, Record<string, unknown>> },
    lifecycleRaw?: { history?: Record<string, Record<string, unknown>> },
    baselineRaw?: { models?: Array<{ id: string; owned_by?: string }> }
  ): void {
    this.modelsMap.clear();
    this.indexMap.clear();
    this.modelToShortIndex.clear();

    const catalogModels = catalogRaw?.models || {};
    const lifecycleHistory = lifecycleRaw?.history || {};
    const baselineModels = baselineRaw?.models || [];

    // 1. Collect all known Model IDs
    const allIds = new Set<string>();
    for (const m of baselineModels) {
      if (m && typeof m.id === "string") {
        allIds.add(m.id.trim());
      }
    }
    for (const id of Object.keys(catalogModels)) {
      allIds.add(id);
    }
    for (const id of Object.keys(lifecycleHistory)) {
      allIds.add(id);
    }

    const sortedIds = Array.from(allIds).sort();

    // 2. Build ModelDetail with graceful fallback and short integer index
    let index = 0;
    for (const modelId of sortedIds) {
      const cat = catalogModels[modelId] || {};
      const life = lifecycleHistory[modelId] || {};

      const defaultProviderId = modelId.includes("/") ? modelId.split("/")[0] : "nvidia";
      const defaultProviderName = getProviderDisplayName(defaultProviderId);
      const rawName = modelId.includes("/") ? modelId.split("/").slice(1).join("/") : modelId;
      const defaultDisplay = rawName.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

      // Stage 3A Usage Stats
      const epUsage = (cat.endpoint as Record<string, unknown>) || {};
      const catUsage = (cat.usage as Record<string, unknown>) || {};
      const usage: UsageStats = {
        api_calls_24h: (epUsage.api_calls_24h as string) ?? (catUsage.api_calls_24h as string) ?? (cat.api_calls_24h as string) ?? null,
        api_calls_daily: (epUsage.api_calls_daily as string) ?? (catUsage.api_calls_daily as string) ?? (cat.api_calls_daily as string) ?? null,
        api_calls_7d: (epUsage.api_calls_7d as string) ?? (catUsage.api_calls_7d as string) ?? (cat.api_calls_7d as string) ?? null,
        api_calls_30d: (epUsage.api_calls_30d as string) ?? (catUsage.api_calls_30d as string) ?? (cat.api_calls_30d as string) ?? null,
        usage_updated_at: (epUsage.usage_updated_at as string) ?? (catUsage.usage_updated_at as string) ?? (cat.usage_updated_at as string) ?? null,
        usage_source: (epUsage.usage_source as string) ?? (catUsage.usage_source as string) ?? "NVIDIA API Catalog Public Aggregate",
      };

      // Stage 3A Lifecycle Record
      const catLife = (cat.lifecycle as Record<string, unknown>) || {};
      const rawOfficial = (catLife.official_lifecycle as Record<string, unknown>) || {};
      const officialLifecycle: OfficialLifecycle = {
        official_status: (rawOfficial.official_status as any) || (catLife.availability as any) || "none",
        official_deprecation_date: (rawOfficial.official_deprecation_date as string) ?? (catLife.official_deprecation_date as string) ?? null,
        sunset_date: (rawOfficial.sunset_date as string) ?? null,
        deprecation_source_url: (rawOfficial.deprecation_source_url as string) ?? (catLife.deprecation_source_url as string) ?? null,
        deprecation_notes: (rawOfficial.deprecation_notes as string) ?? null,
      };

      const lifecycle: LifecycleRecord = {
        model_id: modelId,
        first_seen: (life.first_seen as string) ?? null,
        free_since: (life.free_since as string) ?? null,
        last_seen: (life.last_seen as string) ?? null,
        removed_at: (life.removed_at as string) ?? (catLife.removed_at as string) ?? null,
        is_currently_active: (life.is_currently_active as boolean) ?? (catLife.availability !== "removed"),
        official_lifecycle: officialLifecycle,
      };

      // Stage 3A Provider Info
      const rawProv = cat.provider;
      const provider_info =
        typeof rawProv === "object" && rawProv !== null
          ? {
              id: (rawProv as Record<string, string>).id || defaultProviderId,
              name: (rawProv as Record<string, string>).name || defaultProviderName,
            }
          : {
              id: (cat.provider_id as string) || defaultProviderId,
              name: (cat.provider as string) || defaultProviderName,
            };

      // Stage 3A Classification with smart heuristics fallback
      const rawClass = (cat.classification as Record<string, unknown>) || {};
      const defaultTier = inferTierFromModelId(modelId);
      const defaultSpeed = modelId.toLowerCase().includes("flash") || modelId.toLowerCase().includes("turbo") ? "fast" : "standard";

      const classification = {
        family: (rawClass.family as string) ?? (cat.model_family as string) ?? null,
        tier: (rawClass.tier as any) || defaultTier,
        model_type: (rawClass.model_type as any) || "chat",
        speed: (rawClass.speed as any) || defaultSpeed,
      };

      // Stage 3A Architecture
      const rawArch = cat.architecture;
      const arch_info =
        typeof rawArch === "object" && rawArch !== null
          ? {
              type: ((rawArch as Record<string, string>).type as string) ?? null,
              total_parameters: ((rawArch as Record<string, string>).total_parameters as string) ?? null,
              active_parameters: ((rawArch as Record<string, string>).active_parameters as string) ?? null,
              parameter_status: ((rawArch as Record<string, string>).parameter_status as any) || "unknown",
            }
          : {
              type: (cat.architecture as string) ?? null,
              total_parameters: (cat.parameter_count as string) ?? null,
              active_parameters: null,
              parameter_status: (cat.parameter_count ? "official" : "unknown") as any,
            };

      // Stage 3A Context Info
      const rawCtx = cat.context;
      const context_info =
        typeof rawCtx === "object" && rawCtx !== null
          ? {
              length: ((rawCtx as Record<string, string>).length as string) ?? null,
              max_output: ((rawCtx as Record<string, string>).max_output as string) ?? null,
              status: ((rawCtx as Record<string, string>).status as any) || "unknown",
            }
          : {
              length: (cat.context_length as string) ?? null,
              max_output: null,
              status: "unknown" as any,
            };

      // Stage 3A Release Info
      const rawRel = (cat.release as Record<string, unknown>) || {};
      const release_info = {
        first_seen: (rawRel.first_seen as string) ?? (life.first_seen as string) ?? null,
        release_date: (rawRel.release_date as string) ?? null,
        status: (rawRel.status as any) || "unknown",
      };

      // Stage 3A Links
      const rawLinks = (cat.links as Record<string, unknown>) || {};
      const oldUrls = (cat.source_urls as Record<string, string>) || {};
      const links = {
        nvidia: (rawLinks.nvidia as string) ?? oldUrls.nvidia_nim ?? `https://build.nvidia.com/${modelId}`,
        official: (rawLinks.official as string) ?? oldUrls.official_site ?? null,
        documentation: (rawLinks.documentation as string) ?? null,
        model_card: (rawLinks.model_card as string) ?? null,
      };

      // Stage 3A Source Metadata
      const rawSrc = (cat.source_metadata as Record<string, unknown>) || {};
      const source_metadata = {
        field_sources: (rawSrc.field_sources as Record<string, string>) || {},
        confidence: (rawSrc.confidence as any) || "unknown",
        last_verified: (rawSrc.last_verified as string) ?? null,
      };

      const source_urls: Record<string, string> = {};
      if (links.nvidia) source_urls.nvidia_nim = links.nvidia;
      if (links.official) source_urls.official_site = links.official;

      // Smart capability inference
      let capabilities = Array.isArray(cat.capabilities) && cat.capabilities.length > 0 ? (cat.capabilities as string[]) : [];
      if (capabilities.length === 0) {
        const norm = modelId.toLowerCase();
        if (norm.includes("embed") || norm.includes("bge") || norm.includes("e5")) {
          capabilities = ["Embedding"];
        } else if (norm.includes("code") || norm.includes("coder") || norm.includes("starcoder")) {
          capabilities = ["Coding", "Chat"];
        } else if (norm.includes("vision") || norm.includes("vl") || norm.includes("fuyu") || norm.includes("deplot") || norm.includes("neva")) {
          capabilities = ["Vision", "Chat"];
        } else if (norm.includes("rerank")) {
          capabilities = ["Rerank"];
        } else if (norm.includes("math") || norm.includes("reasoning") || norm.includes("r1")) {
          capabilities = ["Reasoning", "Chat"];
        } else {
          capabilities = ["Chat"];
        }
      }

      const detail: ModelDetail = {
        short_index: index,
        model_id: modelId,
        display_name: (cat.display_name as string) || defaultDisplay,
        aliases: Array.isArray(cat.aliases) ? (cat.aliases as string[]) : [],
        slug: (cat.slug as string) || (modelId.includes("/") ? modelId.split("/")[1] : modelId),
        platform: (cat.platform as string) || "NVIDIA NIM",

        provider_info,
        classification,
        arch_info,
        context_info,
        release_info,
        links,
        source_metadata,

        capabilities,
        free_endpoint: (cat.free_endpoint as boolean) ?? (epUsage.available as boolean) ?? true,
        usage,
        lifecycle,

        // Backward compatibility getters
        provider: provider_info.name,
        provider_id: provider_info.id,
        model_family: classification.family,
        architecture: arch_info.type,
        parameter_count: arch_info.total_parameters,
        context_length: context_info.length,
        source_urls,
      };

      this.modelsMap.set(modelId, detail);
      this.indexMap.set(index, detail);
      this.modelToShortIndex.set(modelId, index);
      index++;
    }
  }

  getModel(modelId: string): ModelDetail | undefined {
    return this.modelsMap.get(modelId);
  }

  getModelByShortIndex(index: number): ModelDetail | undefined {
    return this.indexMap.get(index);
  }

  getAllModels(): ModelDetail[] {
    return Array.from(this.modelsMap.values());
  }

  listModels(): ModelDetail[] {
    return this.getAllModels();
  }

  getProviders(): ProviderSummary[] {
    const map = new Map<string, { display_name: string; count: number }>();
    for (const model of this.modelsMap.values()) {
      const pid = model.provider_id;
      const displayName = getProviderDisplayName(pid);
      const existing = map.get(pid);
      if (existing) {
        existing.count++;
      } else {
        map.set(pid, { display_name: displayName, count: 1 });
      }
    }

    const result: ProviderSummary[] = [];
    for (const [pid, val] of map.entries()) {
      result.push({
        provider_id: pid,
        display_name: val.display_name,
        model_count: val.count,
      });
    }

    result.sort((a, b) => b.model_count - a.model_count || a.display_name.localeCompare(b.display_name));
    return result;
  }

  getCapabilities(providerId?: string): string[] {
    const caps = new Set<string>();
    for (const model of this.modelsMap.values()) {
      if (providerId && providerId !== "all") {
        const normP = providerId.toLowerCase().replace(/[-_\s]/g, "");
        const mP = model.provider_id.toLowerCase().replace(/[-_\s]/g, "");
        if (normP !== mP) continue;
      }
      for (const cap of model.capabilities) {
        caps.add(cap);
      }
    }
    return Array.from(caps).sort();
  }

  filterModels(providerId?: string, capability?: string): ModelDetail[] {
    return this.getAllModels().filter((m) => {
      if (providerId && providerId !== "all") {
        const normP = providerId.toLowerCase().replace(/[-_\s]/g, "");
        const mP = m.provider_id.toLowerCase().replace(/[-_\s]/g, "");
        if (normP !== mP) return false;
      }
      if (capability && capability !== "all") {
        const normCap = capability.toLowerCase().trim();
        const hasCap = m.capabilities.some((c) => c.toLowerCase().trim() === normCap);
        if (!hasCap) return false;
      }
      return true;
    });
  }
}
