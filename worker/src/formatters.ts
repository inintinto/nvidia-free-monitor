import { escapeHtml } from "./telegram.ts";
import type { ModelDetail, ProviderSummary } from "./types.ts";

export function formatModelDetailHtml(model: ModelDetail): string {
  const lines: string[] = [];

  // Header & Identity
  const displayName = escapeHtml(model.display_name);
  const family = model.model_family ? `\n<i>${escapeHtml(model.model_family)} Series</i>` : "";
  lines.push(`🤖 <b>${displayName}</b>${family}\n`);

  lines.push(`🏷 <b>Model ID:</b> <code>${escapeHtml(model.model_id)}</code>`);
  lines.push(`🏢 <b>Provider:</b> <code>${escapeHtml(model.provider)}</code>`);
  lines.push(`🌐 <b>Platform:</b> <code>${escapeHtml(model.platform)}</code>`);

  const statusEmoji = model.lifecycle.is_currently_active ? "🟢" : "🔴";
  const statusText = model.lifecycle.is_currently_active ? "Active Free Endpoint" : "Removed / Inactive";
  lines.push(`✨ <b>Status:</b> ${statusEmoji} <code>${statusText}</code>\n`);

  // Specifications
  lines.push("📋 <b>Specifications:</b>");
  lines.push(`• <b>Architecture:</b> <code>${escapeHtml(model.architecture || "Standard")}</code>`);
  if (model.parameter_count) {
    lines.push(`• <b>Parameters:</b> <code>${escapeHtml(model.parameter_count)}</code>`);
  }
  if (model.context_length) {
    lines.push(`• <b>Context Length:</b> <code>${escapeHtml(model.context_length)}</code>`);
  }
  const caps = model.capabilities.map((c) => `<code>${escapeHtml(c)}</code>`).join(", ");
  lines.push(`• <b>Capabilities:</b> ${caps}\n`);

  // Lifecycle
  lines.push("⏱ <b>Lifecycle:</b>");
  if (model.lifecycle.first_seen) {
    lines.push(`• <b>First Seen:</b> <code>${escapeHtml(model.lifecycle.first_seen.split("T")[0])}</code>`);
  }
  if (model.lifecycle.free_since) {
    lines.push(`• <b>Free Since:</b> <code>${escapeHtml(model.lifecycle.free_since.split("T")[0])}</code>`);
  }
  if (model.lifecycle.last_seen) {
    const lastTime = model.lifecycle.last_seen.replace("T", " ").replace(/\.\d+/, "").replace("+00:00", " UTC");
    lines.push(`• <b>Last Active:</b> <code>${escapeHtml(lastTime)}</code>`);
  }
  if (model.lifecycle.removed_at) {
    const remTime = model.lifecycle.removed_at.replace("T", " ").replace(/\.\d+/, "").replace("+00:00", " UTC");
    lines.push(`• <b>Removed At:</b> <code>${escapeHtml(remTime)}</code>`);
  }

  // Official Deprecation
  const offLife = model.lifecycle.official_lifecycle;
  if (offLife.official_deprecation_date) {
    lines.push(`• <b>Official Deprecation Date:</b> <code>${escapeHtml(offLife.official_deprecation_date)}</code>`);
  } else if (offLife.official_status === "active") {
    lines.push(`• <b>Official Lifecycle:</b> <code>Active (No Deprecation Announced)</code>`);
  }
  if (offLife.sunset_date) {
    lines.push(`• <b>Sunset Date:</b> <code>${escapeHtml(offLife.sunset_date)}</code>`);
  }
  lines.push("");

  // Global NVIDIA API Calls
  lines.push("📊 <b>Global NVIDIA API Calls:</b>");
  let hasUsage = false;
  if (model.usage.api_calls_24h) {
    lines.push(`• <b>Last 24 Hours:</b> <code>${escapeHtml(model.usage.api_calls_24h)} calls</code>`);
    hasUsage = true;
  }
  if (model.usage.api_calls_daily) {
    lines.push(`• <b>Daily Calls:</b> <code>${escapeHtml(model.usage.api_calls_daily)} calls</code>`);
    hasUsage = true;
  }
  if (model.usage.api_calls_7d) {
    lines.push(`• <b>Last 7 Days:</b> <code>${escapeHtml(model.usage.api_calls_7d)} calls</code>`);
    hasUsage = true;
  }
  if (model.usage.api_calls_30d) {
    lines.push(`• <b>Last 30 Days:</b> <code>${escapeHtml(model.usage.api_calls_30d)} calls</code>`);
    hasUsage = true;
  }

  if (!hasUsage) {
    lines.push("• <i>Data not published by NVIDIA</i>");
  } else {
    lines.push(`• <i>Source: ${escapeHtml(model.usage.usage_source || "NVIDIA API Catalog Public Aggregate")}</i>`);
  }

  return lines.join("\n");
}

export function formatProviderMenuHtml(providers: ProviderSummary[], totalCount: number): string {
  return [
    "🤖 <b>NVIDIA Free Endpoint Monitor</b>",
    `全球免费模型目录 (共计 <b>${totalCount}</b> 个可用模型)\n`,
    "请选择模型提供商 (Provider) 进行浏览：",
  ].join("\n");
}

export function formatCapabilityMenuHtml(providerName: string, count: number): string {
  return [
    `🏢 <b>${escapeHtml(providerName)}</b>`,
    `该提供商下共有 <b>${count}</b> 个免费模型。\n`,
    "请选择能力标签 (Capability) 进行筛选：",
  ].join("\n");
}

export function formatModelListMenuHtml(providerName: string, capability: string, count: number): string {
  return [
    `🏢 <b>${escapeHtml(providerName)}</b> › <code>${escapeHtml(capability)}</code>`,
    `找到 <b>${count}</b> 个符合条件的模型：\n`,
    "点击下方模型名称查看完整规格与参数：",
  ].join("\n");
}
