import {
  formatSourceLabel,
  getCapabilityBadges,
  getCapabilityIcon,
  getModelTitle,
  getProviderDisplayName,
  getProviderIcon,
  getProviderShortName,
  getSpeedBadge,
  getTierBadge,
  getTierIcon,
  getTierZhLabel,
} from "./branding.ts";
import { escapeHtml } from "./telegram.ts";
import type { ModelDetail, ProviderSummary } from "./types.ts";

/**
 * Stage 3D: Model Detail Card 2.0 HTML Formatter
 * 中文为主，关键技术术语保留英文，结构清晰，高信息密度。
 */
export function formatModelDetailHtml(model: ModelDetail): string {
  const lines: string[] = [];

  // 1. Header & Identity
  const pIcon = getProviderIcon(model.provider_id);
  const displayName = escapeHtml(model.display_name);
  const pName = escapeHtml(model.provider || getProviderDisplayName(model.provider_id));
  const family = model.classification?.family || model.model_family;
  const familyText = family ? ` · ${escapeHtml(family)}` : "";

  lines.push(`━━━━━━━━━━━━━━━━━━━━`);
  lines.push(`${pIcon} <b>${displayName}</b>`);
  lines.push(`<i>${pName}${familyText}</i>\n`);

  // Availability & Capability Subtitle
  let statusEmoji = "🟢";
  let statusZh = "当前可用 (Active)";
  if (!model.lifecycle?.is_currently_active || model.lifecycle?.removed_at) {
    statusEmoji = "🟡";
    statusZh = "监控观测下线 (Observed Removed)";
  }
  if (model.lifecycle?.official_lifecycle?.official_deprecation_date) {
    statusEmoji = "🔴";
    statusZh = "官方已废弃 (Officially Deprecated)";
  }

  const speedText = getSpeedBadge(model.classification?.speed);
  lines.push(`${statusEmoji} <b>${statusZh}</b> · ${speedText}`);
  lines.push(`${getCapabilityBadges(model)}`);
  lines.push(`━━━━━━━━━━━━━━━━━━━━\n`);

  // 2. 📌 基本信息
  lines.push(`📌 <b>基本信息</b>`);
  lines.push(`• <b>模型 ID：</b> <code>${escapeHtml(model.model_id)}</code>`);
  lines.push(`• <b>提供商：</b> ${pIcon} <code>${pName}</code>`);
  if (family) {
    lines.push(`• <b>模型系列：</b> <code>${escapeHtml(family)}</code>`);
  }
  lines.push(`• <b>模型等级：</b> <code>${getTierBadge(model)}</code>`);
  lines.push(`• <b>模型类型：</b> <code>${escapeHtml(model.classification?.model_type || "Chat")}</code>`);
  lines.push(`• <b>速度等级：</b> <code>${speedText}</code>\n`);

  // 3. 🧠 模型架构
  const archType = model.arch_info?.type || model.architecture;
  const totalParams = model.arch_info?.total_parameters || model.parameter_count;
  const activeParams = model.arch_info?.active_parameters;
  const paramStatus = model.arch_info?.parameter_status;

  let paramStatusZh = "官方未公开";
  if (paramStatus === "official" || totalParams) paramStatusZh = "官方公布";
  if (paramStatus === "observed") paramStatusZh = "监控观测";

  lines.push(`🧠 <b>模型架构</b>`);
  lines.push(`• <b>架构类型：</b> <code>${escapeHtml(archType || "官方未公开")}</code>`);
  lines.push(`• <b>总参数量：</b> <code>${escapeHtml(totalParams || "官方未公开")}</code>`);
  lines.push(`• <b>激活参数：</b> <code>${escapeHtml(activeParams || "官方未公开")}</code>`);
  lines.push(`• <b>参数数据状态：</b> <code>${escapeHtml(paramStatusZh)}</code>\n`);

  // 4. 📏 上下文与输出
  const ctxLen = model.context_info?.length || model.context_length;
  const maxOut = model.context_info?.max_output;
  lines.push(`📏 <b>上下文与输出</b>`);
  lines.push(`• <b>上下文窗口：</b> <code>${escapeHtml(ctxLen || "官方未公开")}</code>`);
  lines.push(`• <b>最大输出：</b> <code>${escapeHtml(maxOut || "官方未公开")}</code>\n`);

  // 5. 🎯 能力清单
  lines.push(`🎯 <b>能力清单</b>`);
  const caps = model.capabilities || [];
  if (caps.length > 0) {
    for (const c of caps) {
      lines.push(`• ${getCapabilityIcon(c)} <code>${escapeHtml(c)}</code>`);
    }
  } else {
    lines.push(`• 💬 <code>Chat</code>`);
  }
  lines.push("");

  // 6. 📅 生命周期
  lines.push(`📅 <b>生命周期</b>`);
  const firstSeen = model.lifecycle?.first_seen ? model.lifecycle.first_seen.split("T")[0] : null;
  lines.push(`• <b>首次发现：</b> <code>${escapeHtml(firstSeen || "官方未公开")}</code>`);
  lines.push(`• <b>当前状态：</b> ${statusEmoji} <code>${escapeHtml(statusZh)}</code>`);

  if (model.lifecycle?.removed_at) {
    const remDate = model.lifecycle.removed_at.replace("T", " ").replace(/\.\d+/, "").replace("+00:00", " UTC");
    lines.push(`• <b>监控观测下线：</b> <code>${escapeHtml(remDate)}</code>`);
  }

  const offLife = model.lifecycle?.official_lifecycle;
  if (offLife?.official_deprecation_date) {
    lines.push(`• <b>官方废弃日期：</b> <code>${escapeHtml(offLife.official_deprecation_date)}</code>`);
    if (offLife.deprecation_source_url) {
      lines.push(`• <b>废弃公告：</b> <a href="${escapeHtml(offLife.deprecation_source_url)}">点击查看公告</a>`);
    }
  } else {
    lines.push(`• <b>官方废弃：</b> <code>暂无官方公告</code>`);
  }
  lines.push("");

  // 7. 📊 NVIDIA API 使用情况
  lines.push(`📊 <b>NVIDIA API 使用情况</b>`);
  lines.push(`• <b>近 24 小时：</b> <code>${escapeHtml(model.usage?.api_calls_24h || "官方未公开")}</code>`);
  lines.push(`• <b>近 7 天：</b> <code>${escapeHtml(model.usage?.api_calls_7d || "官方未公开")}</code>`);
  lines.push(`• <b>近 30 天：</b> <code>${escapeHtml(model.usage?.api_calls_30d || "官方未公开")}</code>`);
  lines.push(`• <b>数据说明：</b> <code>NVIDIA 官方公开统计</code>\n`);

  // 8. 🔎 数据来源与核验
  lines.push(`🔎 <b>数据来源</b>`);
  const srcMeta = model.source_metadata?.field_sources || {};
  lines.push(`• <b>架构数据：</b> <code>${formatSourceLabel(srcMeta.architecture || (archType ? "official" : "unknown"))}</code>`);
  lines.push(`• <b>参数数据：</b> <code>${formatSourceLabel(srcMeta.parameters || (totalParams ? "official" : "unknown"))}</code>`);
  lines.push(`• <b>上下文数据：</b> <code>${formatSourceLabel(srcMeta.context || (ctxLen ? "official" : "unknown"))}</code>`);
  const verified = model.source_metadata?.last_verified ? model.source_metadata.last_verified.split("T")[0] : "2026-08-23";
  lines.push(`• <b>最后核验：</b> <code>${escapeHtml(verified)}</code>\n`);

  // 9. 🔗 官方资源链接
  const links = model.links || {};
  const oldUrls = model.source_urls || {};
  const nimUrl = links.nvidia || oldUrls.nvidia_nim;
  const offUrl = links.official || oldUrls.official_site;

  const resourceLinks: string[] = [];
  if (nimUrl) {
    resourceLinks.push(`• <a href="${escapeHtml(nimUrl)}">🌐 NVIDIA NIM 体验主页</a>`);
  }
  if (offUrl) {
    resourceLinks.push(`• <a href="${escapeHtml(offUrl)}">🏠 模型官方网站</a>`);
  }
  if (links.documentation) {
    resourceLinks.push(`• <a href="${escapeHtml(links.documentation)}">📖 官方技术文档</a>`);
  }
  if (links.model_card) {
    resourceLinks.push(`• <a href="${escapeHtml(links.model_card)}">🧾 Official Model Card</a>`);
  }

  if (resourceLinks.length > 0) {
    lines.push(`🔗 <b>官方资源</b>`);
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
  lines.push(`<i>全球免费 Endpoint 目录与规格百科 (共 <b>${totalModels}</b> 款免费模型)</i>\n`);
  lines.push(`👇 <b>请选择模型提供商 (Provider)：</b>`);
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
    lines.push(`🌐 <b>全部模型目录 (All Models)</b>`);
    lines.push(`当前共包含 <b>${modelCount}</b> 个免费模型。\n`);
  } else {
    lines.push(`${pIcon} <b>${pName}</b>`);
    lines.push(`该提供商下共有 <b>${modelCount}</b> 个免费模型。\n`);
  }
  lines.push(`👇 <b>请选择模型能力 (Capability) 进行筛选：</b>`);
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
  lines.push(`👇 <b>点击下方模型查看详细技术规格：</b>`);
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
  lines.push(`• 发送 <code>/models</code> 浏览完整提供商目录`);
  lines.push(`• 按品牌搜索：<code>/model deepseek</code> 或 <code>/model llama</code>`);
  lines.push(`• 按系列搜索：<code>/model nemotron</code> 或 <code>/model gemma</code>`);
  lines.push(`• 按能力搜索：<code>/model coding</code> 或 <code>/model reasoning</code>`);
  return lines.join("\n");
}
