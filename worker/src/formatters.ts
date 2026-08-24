import {
  formatSourceLabel,
  getCapabilityBadges,
  getCapabilityIcon,
  getProviderDisplayName,
  getProviderIcon,
  getSpeedBadge,
  getStatusBadge,
  getTierIcon,
} from "./branding.ts";
import { escapeHtml } from "./telegram.ts";
import type { ModelDetail, ProviderSummary } from "./types.ts";

/**
 * Stage 3 Final: Model Detail Card 2.0 (High Density & Readability)
 */
export function formatModelDetailHtml(model: ModelDetail): string {
  const lines: string[] = [];

  // 1. Header (Provider Icon + Tier Icon + Name)
  const pIcon = getProviderIcon(model.provider_id);
  const tIcon = getTierIcon(model.classification?.tier);
  const displayName = escapeHtml(model.display_name);
  const pName = escapeHtml(model.provider || getProviderDisplayName(model.provider_id));
  const family = model.classification?.family || model.model_family;
  const familyText = family ? ` · ${escapeHtml(family)}` : "";

  lines.push(`${pIcon} ${tIcon} <b>${displayName}</b>`);
  lines.push(`<i>${pName}${familyText}</i>\n`);

  // Availability & Speed Subtitle
  let statusKey = "active";
  if (!model.lifecycle?.is_currently_active || model.lifecycle?.removed_at) {
    statusKey = "observed_removed";
  }
  if (model.lifecycle?.official_lifecycle?.official_deprecation_date) {
    statusKey = "deprecated";
  }
  const statusInfo = getStatusBadge(statusKey);
  const speedText = getSpeedBadge(model.classification?.speed);
  lines.push(`${statusInfo.icon} <b>${statusInfo.zh_label}</b> · ${speedText}`);
  lines.push(`━━━━━━━━━━━━━━\n`);

  // 2. 📐 模型规格
  const archType = model.arch_info?.type || model.architecture;
  const totalParams = model.arch_info?.total_parameters || model.parameter_count;
  const activeParams = model.arch_info?.active_parameters;
  const ctxLen = model.context_info?.length || model.context_length;
  const maxOut = model.context_info?.max_output;

  lines.push(`📐 <b>模型规格</b>\n`);
  lines.push(`🏗️ 架构　 <code>${escapeHtml(archType || "官方未公开")}</code>`);
  lines.push(`🧮 参数　 <code>${escapeHtml(totalParams || "官方未公开")}</code>`);
  lines.push(`⚙️ 激活　 <code>${escapeHtml(activeParams || "官方未公开")}</code>`);
  lines.push(`📏 上下文 <code>${escapeHtml(ctxLen || "官方未公开")}</code>`);
  lines.push(`📤 输出　 <code>${escapeHtml(maxOut || "官方未公开")}</code>\n`);

  // 3. 🎯 能力
  lines.push(`🎯 <b>能力</b>\n`);
  lines.push(getCapabilityBadges(model) + "\n");

  // 4. 📅 生命周期
  lines.push(`📅 <b>生命周期</b>\n`);
  lines.push(`${statusInfo.icon} ${statusInfo.zh_label}`);
  const firstSeen = model.lifecycle?.first_seen ? model.lifecycle.first_seen.split("T")[0] : null;
  lines.push(`👀 首次发现　<code>${escapeHtml(firstSeen || "官方未公开")}</code>`);

  if (model.lifecycle?.removed_at) {
    const remDate = model.lifecycle.removed_at.replace("T", " ").replace(/\.\d+/, "").replace("+00:00", " UTC");
    lines.push(`🟡 监控下线　<code>${escapeHtml(remDate)}</code>`);
  }

  const offLife = model.lifecycle?.official_lifecycle;
  if (offLife?.official_deprecation_date) {
    lines.push(`🔴 官方废弃　<code>${escapeHtml(offLife.official_deprecation_date)}</code>`);
    if (offLife.deprecation_source_url) {
      lines.push(`📢 废弃公告　<a href="${escapeHtml(offLife.deprecation_source_url)}">查看公告</a>`);
    }
  } else {
    lines.push(`📢 官方废弃　<code>暂无公告</code>`);
  }
  lines.push("");

  // 5. 📊 NVIDIA 使用统计
  lines.push(`📊 <b>NVIDIA 使用统计</b>\n`);
  lines.push(`24h　<code>${escapeHtml(model.usage?.api_calls_24h || "官方未公开")}</code>`);
  lines.push(`7d　 <code>${escapeHtml(model.usage?.api_calls_7d || "官方未公开")}</code>`);
  lines.push(`30d　<code>${escapeHtml(model.usage?.api_calls_30d || "官方未公开")}</code>`);
  lines.push(`数据范围　<code>NVIDIA 官方公开累计统计</code>\n`);

  // 6. 🔗 官方资源
  const links = model.links || {};
  const oldUrls = model.source_urls || {};
  const nimUrl = links.nvidia || oldUrls.nvidia_nim;
  const offUrl = links.official || oldUrls.official_site;

  const resourceLinks: string[] = [];
  if (nimUrl) {
    resourceLinks.push(`🌐 <a href="${escapeHtml(nimUrl)}">NVIDIA NIM</a>`);
  }
  if (offUrl) {
    resourceLinks.push(`🏠 <a href="${escapeHtml(offUrl)}">模型官方网站</a>`);
  }
  if (links.documentation) {
    resourceLinks.push(`📖 <a href="${escapeHtml(links.documentation)}">技术文档</a>`);
  }
  if (links.model_card) {
    resourceLinks.push(`🧾 <a href="${escapeHtml(links.model_card)}">Model Card</a>`);
  }

  if (resourceLinks.length > 0) {
    lines.push(`🔗 <b>官方资源</b>\n`);
    lines.push(resourceLinks.join("\n"));
  }

  return lines.join("\n");
}

/**
 * Level 1: Provider Home Menu Formatter
 */
export function formatProviderMenuHtml(providers: ProviderSummary[], totalModels: number): string {
  const lines: string[] = [];
  lines.push(`🤖 <b>NVIDIA Free Models</b>`);
  lines.push(`免费 Endpoint 模型目录 · <b>${totalModels}</b> 款\n`);
  lines.push(`👇 <b>选择 AI 厂商</b>`);
  return lines.join("\n");
}

/**
 * Level 2: Capability Menu Formatter
 */
export function formatCapabilityMenuHtml(providerId: string, modelCount: number): string {
  const pIcon = getProviderIcon(providerId);
  const pName = escapeHtml(getProviderDisplayName(providerId));
  const lines: string[] = [];

  if (providerId === "all") {
    lines.push(`🌐 <b>全部模型 (All Models)</b>`);
    lines.push(`当前共包含 <b>${modelCount}</b> 款免费模型。\n`);
  } else {
    lines.push(`${pIcon} <b>${pName}</b>`);
    lines.push(`该厂商下共有 <b>${modelCount}</b> 款免费模型。\n`);
  }
  lines.push(`👇 <b>选择模型能力：</b>`);
  return lines.join("\n");
}

/**
 * Level 3: Model List Menu Formatter
 */
export function formatModelListMenuHtml(
  providerId: string,
  capability: string,
  totalCount: number,
  page: number,
  pageSize: number
): string {
  const pIcon = getProviderIcon(providerId);
  const pName = escapeHtml(getProviderDisplayName(providerId));
  const capIcon = getCapabilityIcon(capability);
  const capLabel = capability === "all" ? "全部能力" : escapeHtml(capability);
  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  const lines: string[] = [];
  lines.push(`${pIcon} <b>${pName}</b> · ${capIcon} <b>${capLabel}</b>`);
  lines.push(`共找到 <b>${totalCount}</b> 款模型 (第 ${page + 1} / ${totalPages} 页)\n`);
  lines.push(`👇 <b>点击下方模型查看详细规格：</b>`);
  return lines.join("\n");
}

/**
 * Empty Search Formatter
 */
export function formatEmptySearchHtml(query: string): string {
  const safeQuery = escapeHtml(query);
  const lines: string[] = [];
  lines.push(`❌ <b>未找到匹配的模型：</b> <code>${safeQuery}</code>\n`);
  lines.push(`💡 <b>您可以尝试：</b>`);
  lines.push(`• 发送 <code>/models</code> 浏览完整厂商目录`);
  lines.push(`• 按品牌搜索：<code>/model deepseek</code> 或 <code>/model llama</code>`);
  lines.push(`• 按系列搜索：<code>/model nemotron</code> 或 <code>/model gemma</code>`);
  lines.push(`• 按能力搜索：<code>/model coding</code> 或 <code>/model reasoning</code>`);
  return lines.join("\n");
}
