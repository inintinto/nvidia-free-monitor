export interface CatalogData {
  version: string;
  updated_at: string;
  models: Record<string, unknown>;
}

export interface LifecycleData {
  version: string;
  updated_at: string;
  history: Record<string, unknown>;
}

export class GitHubDataLoader {
  private repo: string;
  private branch: string;
  private cache: Map<string, { data: unknown; timestamp: number }> = new Map();
  private cacheTtlMs: number;

  constructor(repo = "inintinto/nvidia-free-monitor", branch = "main", cacheTtlMinutes = 5) {
    this.repo = repo;
    this.branch = branch;
    this.cacheTtlMs = cacheTtlMinutes * 60 * 1000;
  }

  private async fetchRawJson<T>(filePath: string): Promise<T | null> {
    const now = Date.now();
    const cached = this.cache.get(filePath);
    if (cached && now - cached.timestamp < this.cacheTtlMs) {
      return cached.data as T;
    }

    const url = `https://raw.githubusercontent.com/${this.repo}/${this.branch}/${filePath}`;
    try {
      const resp = await fetch(url, {
        headers: {
          "Accept": "application/json",
          "User-Agent": "NVIDIA-Free-Monitor-Worker/3.0",
        },
      });

      if (!resp.ok) {
        return null;
      }

      const json = (await resp.json()) as T;
      this.cache.set(filePath, { data: json, timestamp: now });
      return json;
    } catch {
      return null;
    }
  }

  async getModelCatalog(): Promise<CatalogData | null> {
    return this.fetchRawJson<CatalogData>("data/model_catalog.json");
  }

  async getLifecycle(): Promise<LifecycleData | null> {
    return this.fetchRawJson<LifecycleData>("data/lifecycle.json");
  }

  async getBaseline(): Promise<{ models?: Array<{ id: string; owned_by?: string }> } | null> {
    return this.fetchRawJson<{ models?: Array<{ id: string; owned_by?: string }> }>("data/nvidia_api_models.json");
  }
}
