import type { ModelDetail } from "./types.ts";

export interface ProviderBrand {
  id: string;
  name: string;
  short_name: string;
  icon: string;
  official_url: string | null;
  nvidia_url: string | null;
  description: string | null;
}

export const PROVIDER_REGISTRY: Record<string, ProviderBrand> = {
  "deepseek-ai": {
    id: "deepseek-ai",
    name: "DeepSeek AI",
    short_name: "DeepSeek",
    icon: "🐋",
    official_url: "https://www.deepseek.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=deepseek-ai",
    description: "DeepSeek AI 致力于推进高效率推理与代码大模型研发。",
  },
  nvidia: {
    id: "nvidia",
    name: "NVIDIA",
    short_name: "NVIDIA",
    icon: "🟩",
    official_url: "https://www.nvidia.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=nvidia",
    description: "NVIDIA Nemotron 官方系列与 NIM 云微服务。",
  },
  meta: {
    id: "meta",
    name: "Meta",
    short_name: "Meta",
    icon: "♾️",
    official_url: "https://llama.meta.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=meta",
    description: "Meta AI 开源 Llama 全球主流基础大模型家族。",
  },
  google: {
    id: "google",
    name: "Google",
    short_name: "Google",
    icon: "🔵",
    official_url: "https://deepmind.google/technologies/gemma/",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=google",
    description: "Google DeepMind 开源 Gemma 系列高效轻量模型。",
  },
  "01-ai": {
    id: "01-ai",
    name: "01.AI",
    short_name: "01.AI",
    icon: "🟡",
    official_url: "https://www.01.ai",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=01-ai",
    description: "零一万物中英双语 Yi 系列高精度通用大模型。",
  },
  baai: {
    id: "baai",
    name: "BAAI",
    short_name: "BAAI",
    icon: "🧬",
    official_url: "https://www.baai.ac.cn",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=baai",
    description: "北京智源人工智能研究院 BGE 向量与嵌入模型。",
  },
  mistralai: {
    id: "mistralai",
    name: "Mistral AI",
    short_name: "Mistral",
    icon: "🌊",
    official_url: "https://mistral.ai",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=mistralai",
    description: "Mistral AI 欧陆开源与定制化生成式 AI 模型。",
  },
  cohere: {
    id: "cohere",
    name: "Cohere",
    short_name: "Cohere",
    icon: "🟣",
    official_url: "https://cohere.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=cohere",
    description: "Cohere 企业级 Command R 与 Rerank 精排模型。",
  },
  moonshotai: {
    id: "moonshotai",
    name: "Moonshot AI",
    short_name: "Moonshot",
    icon: "🌙",
    official_url: "https://www.moonshot.cn",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=moonshotai",
    description: "月之暗面 Kimi 超长上下文大语言模型。",
  },
  qwen: {
    id: "qwen",
    name: "Qwen",
    short_name: "Qwen",
    icon: "🐉",
    official_url: "https://github.com/QwenLM",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=qwen",
    description: "阿里云通义千问多语言全模态开源大模型系列。",
  },
  microsoft: {
    id: "microsoft",
    name: "Microsoft",
    short_name: "Microsoft",
    icon: "🪟",
    official_url: "https://www.microsoft.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=microsoft",
    description: "微软 Phi 高性能小型语言模型系列。",
  },
  openai: {
    id: "openai",
    name: "OpenAI",
    short_name: "OpenAI",
    icon: "🟢",
    official_url: "https://openai.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=openai",
    description: "OpenAI 领先前沿多模态大模型。",
  },
};

export const DEFAULT_UNKNOWN_PROVIDER: ProviderBrand = {
  id: "unknown",
  name: "Unknown Provider",
  short_name: "Unknown",
  icon: "🌐",
  official_url: null,
  nvidia_url: null,
  description: null,
};

export function getProviderBrand(providerId: string): ProviderBrand {
  if (!providerId) return DEFAULT_UNKNOWN_PROVIDER;
  const key = providerId.toLowerCase().trim();
  if (PROVIDER_REGISTRY[key]) {
    return PROVIDER_REGISTRY[key];
  }
  for (const [id, brand] of Object.entries(PROVIDER_REGISTRY)) {
    if (id.includes(key) || key.includes(id)) {
      return brand;
    }
  }
  const formattedName = providerId.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return {
    id: providerId,
    name: formattedName,
    short_name: formattedName,
    icon: "🌐",
    official_url: null,
    nvidia_url: null,
    description: null,
  };
}

export function getProviderIcon(providerId: string): string {
  return getProviderBrand(providerId).icon;
}

export function getProviderDisplayName(providerId: string): string {
  return getProviderBrand(providerId).name;
}

export function getProviderShortName(providerId: string): string {
  return getProviderBrand(providerId).short_name;
}

// -------------------------------------------------------------
// Tier & Classification Branding
// -------------------------------------------------------------

export const TIER_ICONS: Record<string, { icon: string; label: string; zh_label: string }> = {
  flagship: { icon: "👑", label: "Flagship", zh_label: "旗舰模型" },
  large: { icon: "🏛️", label: "Large", zh_label: "大型模型" },
  balanced: { icon: "⚖️", label: "Balanced", zh_label: "均衡模型" },
  medium: { icon: "⚡", label: "Medium", zh_label: "中型模型" },
  small: { icon: "🔹", label: "Small", zh_label: "轻量模型" },
  fast: { icon: "⚡", label: "Fast", zh_label: "高速模型" },
  embedding: { icon: "🧬", label: "Embedding", zh_label: "向量模型" },
  reasoning: { icon: "🧠", label: "Reasoning", zh_label: "推理模型" },
  coding: { icon: "💻", label: "Coding", zh_label: "代码模型" },
  vision: { icon: "👁️", label: "Vision", zh_label: "视觉模型" },
  specialized: { icon: "🛠️", label: "Specialized", zh_label: "专用模型" },
  standard: { icon: "🔹", label: "Standard", zh_label: "标准模型" },
  unknown: { icon: "📦", label: "Unknown", zh_label: "基础模型" },
};

export function getTierIcon(tier?: string | null): string {
  if (!tier) return "📦";
  const norm = tier.toLowerCase().trim();
  return TIER_ICONS[norm]?.icon || "📦";
}

export function getTierLabel(tier?: string | null): string {
  if (!tier) return "Unknown";
  const norm = tier.toLowerCase().trim();
  return TIER_ICONS[norm]?.label || "Unknown";
}

export function getTierZhLabel(tier?: string | null): string {
  if (!tier) return "基础模型";
  const norm = tier.toLowerCase().trim();
  return TIER_ICONS[norm]?.zh_label || "基础模型";
}

export function getSpeedBadge(speed?: string | null): string {
  if (speed === "fast") return "⚡ 高速";
  if (speed === "standard") return "🔹 标准";
  return "官方未公开";
}

// -------------------------------------------------------------
// Capability Branding
// -------------------------------------------------------------

export const CAPABILITY_ICONS: Record<string, { icon: string; zh_label: string; short_zh: string }> = {
  Chat: { icon: "💬", zh_label: "对话 (Chat)", short_zh: "对话" },
  Reasoning: { icon: "🧠", zh_label: "深度推理 (Reasoning)", short_zh: "推理" },
  Coding: { icon: "💻", zh_label: "代码编程 (Coding)", short_zh: "编程" },
  Vision: { icon: "👁️", zh_label: "视觉理解 (Vision)", short_zh: "视觉" },
  Embedding: { icon: "🧬", zh_label: "向量检索 (Embedding)", short_zh: "向量" },
  Audio: { icon: "🎧", zh_label: "语音处理 (Audio)", short_zh: "语音" },
  Multimodal: { icon: "🎨", zh_label: "多模态 (Multimodal)", short_zh: "多模态" },
  "Tool Calling": { icon: "🔧", zh_label: "工具调用 (Tool Calling)", short_zh: "工具" },
  Rerank: { icon: "📊", zh_label: "重排精排 (Rerank)", short_zh: "重排" },
  Unknown: { icon: "📦", zh_label: "常规能力", short_zh: "常规" },
};

export function getCapabilityIcon(cap: string): string {
  if (!cap) return "📦";
  const key = Object.keys(CAPABILITY_ICONS).find(
    (k) => k.toLowerCase() === cap.toLowerCase().trim()
  );
  return key ? CAPABILITY_ICONS[key].icon : "✨";
}

export function getCapabilityLabel(cap: string): string {
  return `${getCapabilityIcon(cap)} ${cap}`;
}

export function getCapabilityZhLabel(cap: string): string {
  const key = Object.keys(CAPABILITY_ICONS).find(
    (k) => k.toLowerCase() === cap.toLowerCase().trim()
  );
  if (key) {
    return `${CAPABILITY_ICONS[key].icon} ${CAPABILITY_ICONS[key].short_zh}`;
  }
  return `✨ ${cap}`;
}

// -------------------------------------------------------------
// Source & Confidence Helpers
// -------------------------------------------------------------

export function formatSourceLabel(source?: string | null): string {
  if (!source) return "未公开 / 未知";
  const norm = source.toLowerCase().trim();
  if (norm.includes("official")) return "官方公布";
  if (norm.includes("observed")) return "监控观测";
  if (norm.includes("aggregate") || norm.includes("public")) return "NVIDIA 官方公开统计";
  return "未公开 / 未知";
}

// -------------------------------------------------------------
// Model Badge & Display Helpers
// -------------------------------------------------------------

export function getModelBadge(model: ModelDetail): string {
  return getProviderIcon(model.provider_id);
}

export function getModelTitle(model: ModelDetail): string {
  const pIcon = getProviderIcon(model.provider_id);
  return `${pIcon} ${model.display_name}`;
}

export function getTierBadge(model: ModelDetail): string {
  const tier = model.classification?.tier || "unknown";
  const icon = getTierIcon(tier);
  const label = getTierZhLabel(tier);
  return `${icon} ${label}`;
}

export function getCapabilityBadges(model: ModelDetail): string {
  const caps = model.capabilities || [];
  if (caps.length === 0) return "💬 对话";
  return caps.map((c) => getCapabilityZhLabel(c)).join(" · ");
}

export function formatModelButtonText(model: ModelDetail, inProviderView = false): string {
  if (inProviderView) {
    // Inside a specific provider menu: show clean tier icon only
    const tIcon = getTierIcon(model.classification?.tier);
    return `${tIcon} ${model.display_name}`;
  }
  // Global / search view: show provider icon only
  const pIcon = getProviderIcon(model.provider_id);
  return `${pIcon} ${model.display_name}`;
}
