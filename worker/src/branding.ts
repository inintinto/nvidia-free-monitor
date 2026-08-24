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
    icon: "🦾",
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
    icon: "🕊️",
    official_url: "https://deepmind.google/technologies/gemma/",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=google",
    description: "Google DeepMind 开源 Gemma 系列高效轻量模型。",
  },
  "01-ai": {
    id: "01-ai",
    name: "01.AI",
    short_name: "01.AI",
    icon: "🐯",
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
    icon: "🌪️",
    official_url: "https://mistral.ai",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=mistralai",
    description: "Mistral AI 欧陆开源与定制化生成式 AI 模型。",
  },
  "nv-mistralai": {
    id: "nv-mistralai",
    name: "Mistral AI (NVIDIA)",
    short_name: "Mistral",
    icon: "🌪️",
    official_url: "https://mistral.ai",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=mistralai",
    description: "NVIDIA 深度优化的 Mistral/Mixtral 模型系列。",
  },
  cohere: {
    id: "cohere",
    name: "Cohere",
    short_name: "Cohere",
    icon: "🪶",
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
    icon: "🌀",
    official_url: "https://openai.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=openai",
    description: "OpenAI 领先前沿多模态大模型。",
  },
  anthropic: {
    id: "anthropic",
    name: "Anthropic",
    short_name: "Anthropic",
    icon: "🧠",
    official_url: "https://www.anthropic.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=anthropic",
    description: "Anthropic Claude 系列安全对齐前沿大模型。",
  },
  xai: {
    id: "xai",
    name: "xAI",
    short_name: "xAI",
    icon: "✖️",
    official_url: "https://x.ai",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=xai",
    description: "xAI Grok 系列前沿推理大模型。",
  },
  bytedance: {
    id: "bytedance",
    name: "ByteDance",
    short_name: "ByteDance",
    icon: "🪩",
    official_url: "https://www.volcengine.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=bytedance",
    description: "字节跳动豆包大模型家族。",
  },
  ibm: {
    id: "ibm",
    name: "IBM",
    short_name: "IBM",
    icon: "💼",
    official_url: "https://www.ibm.com/granite",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=ibm",
    description: "IBM Granite 企业级全栈开源大语言与代码模型系列。",
  },
  writer: {
    id: "writer",
    name: "Writer",
    short_name: "Writer",
    icon: "✍️",
    official_url: "https://writer.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=writer",
    description: "Writer Palmyra 企业级高精度文本与长文本生成模型。",
  },
  adept: {
    id: "adept",
    name: "Adept",
    short_name: "Adept",
    icon: "🎯",
    official_url: "https://www.adept.ai",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=adept",
    description: "Adept Fuyu 多模态屏幕图表理解与交互模型。",
  },
  ai21labs: {
    id: "ai21labs",
    name: "AI21 Labs",
    short_name: "AI21 Labs",
    icon: "🦖",
    official_url: "https://www.ai21.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=ai21labs",
    description: "AI21 Labs Jamba 结合 Mamba 与 Transformer 架构的混合专家模型。",
  },
  aisingapore: {
    id: "aisingapore",
    name: "AI Singapore",
    short_name: "AI Singapore",
    icon: "🦁",
    official_url: "https://aisingapore.org",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=aisingapore",
    description: "新加坡国家人工智能计划 SEA-LION 东南亚多语言大模型。",
  },
  bigcode: {
    id: "bigcode",
    name: "BigCode",
    short_name: "BigCode",
    icon: "⭐",
    official_url: "https://www.bigcode-project.org",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=bigcode",
    description: "BigCode 开源 StarCoder2 代码大语言模型项目。",
  },
  databricks: {
    id: "databricks",
    name: "Databricks",
    short_name: "Databricks",
    icon: "🧱",
    official_url: "https://www.databricks.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=databricks",
    description: "Databricks 开源 DBRX 细粒度 MoE 架构高效率大模型。",
  },
  minimaxai: {
    id: "minimaxai",
    name: "MiniMax",
    short_name: "MiniMax",
    icon: "🐚",
    official_url: "https://www.minimaxi.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=minimaxai",
    description: "MiniMax 名之梦高智能通用大模型与 MoE 系列。",
  },
  poolside: {
    id: "poolside",
    name: "Poolside",
    short_name: "Poolside",
    icon: "🏊",
    official_url: "https://poolside.ai",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=poolside",
    description: "Poolside 专注极致代码开发与软件工程专化模型。",
  },
  snowflake: {
    id: "snowflake",
    name: "Snowflake",
    short_name: "Snowflake",
    icon: "❄️",
    official_url: "https://www.snowflake.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=snowflake",
    description: "Snowflake Arctic 专为企业级 SQL 与向量检索打造的高效模型。",
  },
  "stepfun-ai": {
    id: "stepfun-ai",
    name: "StepFun",
    short_name: "StepFun",
    icon: "🪜",
    official_url: "https://www.stepfun.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=stepfun-ai",
    description: "阶跃星辰 Step 系列超长文本与多模态大模型。",
  },
  thinkingmachines: {
    id: "thinkingmachines",
    name: "Thinking Machines",
    short_name: "Thinking Machines",
    icon: "💡",
    official_url: "https://thinkingmachin.es",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=thinkingmachines",
    description: "Thinking Machines 专注于下一代通用推理与 Agent 架构研究。",
  },
  zyphra: {
    id: "zyphra",
    name: "Zyphra",
    short_name: "Zyphra",
    icon: "⚡",
    official_url: "https://www.zyphra.com",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=zyphra",
    description: "Zyphra Zamba 高性能 Mamba-Transformer 混合架构大模型。",
  },
  upstage: {
    id: "upstage",
    name: "Upstage",
    short_name: "Upstage",
    icon: "☀️",
    official_url: "https://www.upstage.ai",
    nvidia_url: "https://build.nvidia.com/explore/discover?owner=upstage",
    description: "Upstage Solar 创新深度扩展架构大语言模型。",
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
  flagship: { icon: "👑", label: "Flagship", zh_label: "旗舰" },
  large: { icon: "🏛️", label: "Large", zh_label: "大型" },
  balanced: { icon: "⚖️", label: "Balanced", zh_label: "均衡" },
  medium: { icon: "⚙️", label: "Medium", zh_label: "中型" },
  small: { icon: "🪶", label: "Small", zh_label: "轻量" },
  embedding: { icon: "🧬", label: "Embedding", zh_label: "向量" },
  specialized: { icon: "🛠️", label: "Specialized", zh_label: "专用" },
  unknown: { icon: "📦", label: "Unknown", zh_label: "未分类" },
};

export function inferTierFromModelId(modelId: string): string {
  const norm = modelId.toLowerCase();
  if (norm.includes("405b") || norm.includes("340b") || norm.includes("dbrx") || norm.includes("flagship")) {
    return "flagship";
  }
  if (norm.includes("70b") || norm.includes("65b") || norm.includes("large") || norm.includes("34b") || norm.includes("32b")) {
    return "large";
  }
  if (
    norm.includes("27b") ||
    norm.includes("15b") ||
    norm.includes("14b") ||
    norm.includes("13b") ||
    norm.includes("12b") ||
    norm.includes("medium")
  ) {
    return "medium";
  }
  if (
    norm.includes("7b") ||
    norm.includes("8b") ||
    norm.includes("6.7b") ||
    norm.includes("3b") ||
    norm.includes("2b") ||
    norm.includes("1b") ||
    norm.includes("small") ||
    norm.includes("mini") ||
    norm.includes("flash") ||
    norm.includes("nano")
  ) {
    return "small";
  }
  if (norm.includes("embed") || norm.includes("bge") || norm.includes("e5") || norm.includes("clip")) {
    return "embedding";
  }
  if (
    norm.includes("rerank") ||
    norm.includes("vision") ||
    norm.includes("fuyu") ||
    norm.includes("deplot") ||
    norm.includes("coder") ||
    norm.includes("code") ||
    norm.includes("guard") ||
    norm.includes("reward") ||
    norm.includes("safety")
  ) {
    return "specialized";
  }
  return "balanced";
}

export function getTierIcon(tier?: string | null, modelId?: string): string {
  if (tier && tier !== "unknown") {
    const norm = tier.toLowerCase().trim();
    if (TIER_ICONS[norm]) return TIER_ICONS[norm].icon;
  }
  if (modelId) {
    const inferred = inferTierFromModelId(modelId);
    return TIER_ICONS[inferred]?.icon || "⚙️";
  }
  return "📦";
}

export function getTierLabel(tier?: string | null, modelId?: string): string {
  if (tier && tier !== "unknown") {
    const norm = tier.toLowerCase().trim();
    if (TIER_ICONS[norm]) return TIER_ICONS[norm].label;
  }
  if (modelId) {
    const inferred = inferTierFromModelId(modelId);
    return TIER_ICONS[inferred]?.label || "Balanced";
  }
  return "Unknown";
}

export function getTierZhLabel(tier?: string | null, modelId?: string): string {
  if (tier && tier !== "unknown") {
    const norm = tier.toLowerCase().trim();
    if (TIER_ICONS[norm]) return TIER_ICONS[norm].zh_label;
  }
  if (modelId) {
    const inferred = inferTierFromModelId(modelId);
    return TIER_ICONS[inferred]?.zh_label || "均衡";
  }
  return "未分类";
}

// -------------------------------------------------------------
// Speed Branding (Decoupled from Tier)
// -------------------------------------------------------------

export const SPEED_BADGES: Record<string, string> = {
  fast: "⚡ 高速",
  standard: "◽ 标准",
  slow: "🐢 慢速",
  unknown: "◽ 标准",
};

export function getSpeedBadge(speed?: string | null, modelId?: string): string {
  if (speed && speed !== "unknown") {
    const norm = speed.toLowerCase().trim();
    if (SPEED_BADGES[norm]) return SPEED_BADGES[norm];
  }
  if (modelId) {
    const norm = modelId.toLowerCase();
    if (norm.includes("flash") || norm.includes("turbo") || norm.includes("mini") || norm.includes("fast") || norm.includes("embed")) {
      return "⚡ 高速";
    }
  }
  return "◽ 标准";
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
// Status Branding (Status Only)
// -------------------------------------------------------------

export const STATUS_ICONS: Record<string, { icon: string; label: string; zh_label: string }> = {
  active: { icon: "🟢", label: "Active", zh_label: "当前可用" },
  observed_removed: { icon: "🟡", label: "Observed Removed", zh_label: "监控观测下线" },
  deprecated: { icon: "🔴", label: "Officially Deprecated", zh_label: "官方已废弃" },
  unknown: { icon: "⚪", label: "Unknown", zh_label: "状态未知" },
};

export function getStatusBadge(status?: string | null): { icon: string; zh_label: string; text: string } {
  if (!status) return { icon: "⚪", zh_label: "状态未知", text: "⚪ 状态未知" };
  const norm = status.toLowerCase().trim();
  const info = STATUS_ICONS[norm] || STATUS_ICONS.unknown;
  return { icon: info.icon, zh_label: info.zh_label, text: `${info.icon} ${info.zh_label}` };
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
// Unified Model Title & Badge Helpers (Provider + Tier + Name)
// -------------------------------------------------------------

export function getModelBadge(model: ModelDetail): string {
  const pIcon = getProviderIcon(model.provider_id);
  const tIcon = getTierIcon(model.classification?.tier, model.model_id);
  return `${pIcon} ${tIcon}`.trim();
}

export function getModelTitle(model: ModelDetail): string {
  const pIcon = getProviderIcon(model.provider_id);
  const tIcon = getTierIcon(model.classification?.tier, model.model_id);
  return `${pIcon} ${tIcon} ${model.display_name}`;
}

export function getTierBadge(model: ModelDetail): string {
  const tier = model.classification?.tier || inferTierFromModelId(model.model_id);
  const icon = getTierIcon(tier, model.model_id);
  const label = getTierZhLabel(tier, model.model_id);
  return `${icon} ${label}`;
}

export function getCapabilityBadges(model: ModelDetail): string {
  const caps = model.capabilities || [];
  if (caps.length === 0) {
    const norm = model.model_id.toLowerCase();
    if (norm.includes("embed") || norm.includes("bge") || norm.includes("e5")) return "🧬 向量";
    if (norm.includes("code") || norm.includes("coder") || norm.includes("starcoder")) return "💻 编程 · 💬 对话";
    if (norm.includes("vision") || norm.includes("vl") || norm.includes("fuyu") || norm.includes("deplot")) return "👁️ 视觉 · 💬 对话";
    if (norm.includes("rerank")) return "📊 重排";
    return "💬 对话";
  }
  return caps.map((c) => getCapabilityZhLabel(c)).join(" · ");
}

export function formatModelButtonText(model: ModelDetail): string {
  const pIcon = getProviderIcon(model.provider_id);
  const tIcon = getTierIcon(model.classification?.tier, model.model_id);
  return `${pIcon} ${tIcon} ${model.display_name}`;
}
