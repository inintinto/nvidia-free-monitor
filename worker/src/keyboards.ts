import {
  formatModelButtonText,
  getCapabilityIcon,
  getProviderIcon,
  getProviderShortName,
} from "./branding.ts";
import type {
  ModelDetail,
  ProviderSummary,
  TelegramInlineKeyboardButton,
  TelegramInlineKeyboardMarkup,
} from "./types.ts";

export const getProviderEmoji = getProviderIcon;
export const getCapabilityEmoji = getCapabilityIcon;

// -------------------------------------------------------------
// Level 1: Provider Menu Keyboard
// -------------------------------------------------------------
export function buildProviderKeyboard(providers: ProviderSummary[]): TelegramInlineKeyboardMarkup {
  const rows: TelegramInlineKeyboardButton[][] = [];
  let currentRow: TelegramInlineKeyboardButton[] = [];

  for (const prov of providers) {
    const icon = getProviderIcon(prov.provider_id);
    const shortName = getProviderShortName(prov.provider_id);
    const btn: TelegramInlineKeyboardButton = {
      text: `${icon} ${shortName} · ${prov.model_count}`,
      callback_data: `c:p:${prov.provider_id}`,
    };

    currentRow.push(btn);
    if (currentRow.length === 2) {
      rows.push(currentRow);
      currentRow = [];
    }
  }

  if (currentRow.length > 0) {
    rows.push(currentRow);
  }

  // All Models entry
  rows.push([
    {
      text: "🌐 全部模型",
      callback_data: "c:p:all",
    },
  ]);

  return { inline_keyboard: rows };
}

// -------------------------------------------------------------
// Level 2: Capability Menu Keyboard
// -------------------------------------------------------------
export function buildCapabilityKeyboard(
  providerId: string,
  capabilities: string[]
): TelegramInlineKeyboardMarkup {
  const rows: TelegramInlineKeyboardButton[][] = [];
  let currentRow: TelegramInlineKeyboardButton[] = [];

  for (const cap of capabilities) {
    const icon = getCapabilityIcon(cap);
    const btn: TelegramInlineKeyboardButton = {
      text: `${icon} ${cap}`,
      callback_data: `c:c:${providerId}:${cap.toLowerCase()}`,
    };

    currentRow.push(btn);
    if (currentRow.length === 2) {
      rows.push(currentRow);
      currentRow = [];
    }
  }

  if (currentRow.length > 0) {
    rows.push(currentRow);
  }

  // All capabilities under this provider
  rows.push([
    {
      text: "📋 全部能力 (All Capabilities)",
      callback_data: `c:c:${providerId}:all`,
    },
  ]);

  // Back button
  rows.push([
    {
      text: "🔙 返回提供商 (Back to Providers)",
      callback_data: "c:r",
    },
  ]);

  return { inline_keyboard: rows };
}

// -------------------------------------------------------------
// Level 3: Model List Keyboard
// -------------------------------------------------------------
export function buildModelListKeyboard(
  providerId: string,
  capability: string,
  models: ModelDetail[],
  page = 0,
  pageSize = 8
): TelegramInlineKeyboardMarkup {
  const rows: TelegramInlineKeyboardButton[][] = [];

  const start = page * pageSize;
  const pageModels = models.slice(start, start + pageSize);

  for (const model of pageModels) {
    const text = formatModelButtonText(model);
    rows.push([
      {
        text,
        callback_data: `c:d:${model.short_index}`,
      },
    ]);
  }

  // Pagination navigation if needed
  const navRow: TelegramInlineKeyboardButton[] = [];
  if (page > 0) {
    navRow.push({
      text: "⬅️ 上一页",
      callback_data: `c:l:${providerId}:${capability}:${page - 1}`,
    });
  }
  if (start + pageSize < models.length) {
    navRow.push({
      text: "下一页 ➡️",
      callback_data: `c:l:${providerId}:${capability}:${page + 1}`,
    });
  }
  if (navRow.length > 0) {
    rows.push(navRow);
  }

  // Back button to capabilities
  rows.push([
    {
      text: "🔙 返回能力筛选 (Back to Capabilities)",
      callback_data: `c:p:${providerId}`,
    },
  ]);

  return { inline_keyboard: rows };
}

// -------------------------------------------------------------
// Level 4: Model Detail Keyboard
// -------------------------------------------------------------
export function buildModelDetailKeyboard(
  model: ModelDetail,
  backProviderId?: string,
  backCapability?: string
): TelegramInlineKeyboardMarkup {
  const rows: TelegramInlineKeyboardButton[][] = [];

  // Official portal links row
  const linkRow: TelegramInlineKeyboardButton[] = [];
  if (model.links?.nvidia || model.source_urls?.nvidia_nim) {
    linkRow.push({
      text: "🌐 NVIDIA NIM",
      url: model.links?.nvidia || model.source_urls.nvidia_nim,
    });
  }
  if (model.links?.official || model.source_urls?.official_site) {
    linkRow.push({
      text: "🏠 官方网站",
      url: model.links?.official || model.source_urls.official_site,
    });
  }
  if (linkRow.length > 0) {
    rows.push(linkRow);
  }

  // Back button routing
  const pId = backProviderId || model.provider_id;
  const cap = backCapability || "all";
  rows.push([
    {
      text: "🔙 返回模型列表 (Back to Model List)",
      callback_data: `c:c:${pId}:${cap}`,
    },
    {
      text: "🏠 目录首页 (Catalog Home)",
      callback_data: "c:r",
    },
  ]);

  return { inline_keyboard: rows };
}

// -------------------------------------------------------------
// Multiple Match Disambiguation Keyboard
// -------------------------------------------------------------
export function buildMultipleResultsKeyboard(models: ModelDetail[]): TelegramInlineKeyboardMarkup {
  const rows: TelegramInlineKeyboardButton[][] = [];

  for (const model of models.slice(0, 8)) {
    const text = formatModelButtonText(model);
    rows.push([
      {
        text,
        callback_data: `c:d:${model.short_index}`,
      },
    ]);
  }

  rows.push([
    {
      text: "🌐 浏览全部目录 (/models)",
      callback_data: "c:r",
    },
  ]);

  return { inline_keyboard: rows };
}

export const buildMultipleMatchKeyboard = buildMultipleResultsKeyboard;
