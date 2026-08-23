import type {
  ModelDetail,
  ProviderSummary,
  TelegramInlineKeyboardButton,
  TelegramInlineKeyboardMarkup,
} from "./types.ts";

const PROVIDER_EMOJIS: Record<string, string> = {
  nvidia: "🟢",
  "deepseek-ai": "🔵",
  meta: "🟣",
  google: "🔴",
  zhipuai: "🟠",
  moonshotai: "🟡",
  mistralai: "⚪",
  "01-ai": "🔹",
  baai: "🔸",
};

export function getProviderEmoji(providerId: string): string {
  const norm = providerId.toLowerCase();
  return PROVIDER_EMOJIS[norm] || "▫️";
}

const CAPABILITY_EMOJIS: Record<string, string> = {
  Chat: "💬",
  Reasoning: "🧠",
  Coding: "💻",
  Vision: "👁",
  Audio: "🎵",
  Image: "🖼",
  Video: "🎬",
  Embedding: "📦",
  Agentic: "🤖",
};

export function getCapabilityEmoji(cap: string): string {
  return CAPABILITY_EMOJIS[cap] || "✨";
}

// -------------------------------------------------------------
// Level 1: Provider Menu Keyboard
// -------------------------------------------------------------
export function buildProviderKeyboard(providers: ProviderSummary[]): TelegramInlineKeyboardMarkup {
  const rows: TelegramInlineKeyboardButton[][] = [];
  let currentRow: TelegramInlineKeyboardButton[] = [];

  for (const prov of providers) {
    const emoji = getProviderEmoji(prov.provider_id);
    const btn: TelegramInlineKeyboardButton = {
      text: `${emoji} ${prov.display_name} (${prov.model_count})`,
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
      text: "🌐 All Models (全部模型)",
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
    const emoji = getCapabilityEmoji(cap);
    const btn: TelegramInlineKeyboardButton = {
      text: `${emoji} ${cap}`,
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
      text: "📋 All (全部能力)",
      callback_data: `c:c:${providerId}:all`,
    },
  ]);

  // Back button
  rows.push([
    {
      text: "🔙 Back to Providers (返回提供商)",
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
    rows.push([
      {
        text: `🔹 ${model.display_name}`,
        callback_data: `c:d:${model.short_index}`,
      },
    ]);
  }

  // Pagination navigation if needed
  const navRow: TelegramInlineKeyboardButton[] = [];
  if (page > 0) {
    navRow.push({
      text: "⬅️ Prev",
      callback_data: `c:l:${providerId}:${capability}:${page - 1}`,
    });
  }
  if (start + pageSize < models.length) {
    navRow.push({
      text: "Next ➡️",
      callback_data: `c:l:${providerId}:${capability}:${page + 1}`,
    });
  }
  if (navRow.length > 0) {
    rows.push(navRow);
  }

  // Back button to Capability menu
  rows.push([
    {
      text: "🔙 Back to Capabilities (返回分类)",
      callback_data: `c:p:${providerId}`,
    },
  ]);

  return { inline_keyboard: rows };
}

// -------------------------------------------------------------
// Level 4: Model Detail Keyboard (Back + Official Links)
// -------------------------------------------------------------
export function buildModelDetailKeyboard(
  model: ModelDetail,
  backProviderId?: string,
  backCapability?: string
): TelegramInlineKeyboardMarkup {
  const rows: TelegramInlineKeyboardButton[][] = [];

  // External Portal Links
  const linkRow: TelegramInlineKeyboardButton[] = [];
  const nimUrl = model.source_urls.nvidia_nim || `https://build.nvidia.com/${model.model_id}`;
  linkRow.push({
    text: "🌐 NVIDIA NIM",
    url: nimUrl,
  });

  if (model.source_urls.official_site) {
    linkRow.push({
      text: "🔗 Official Site",
      url: model.source_urls.official_site,
    });
  } else if (model.source_urls.huggingface) {
    linkRow.push({
      text: "🤗 HuggingFace",
      url: model.source_urls.huggingface,
    });
  }

  rows.push(linkRow);

  // Back button
  const pId = backProviderId || model.provider_id;
  const cap = backCapability || "all";
  rows.push([
    {
      text: "🔙 Back to Model List (返回列表)",
      callback_data: `c:c:${pId}:${cap}`,
    },
  ]);

  return { inline_keyboard: rows };
}

// -------------------------------------------------------------
// Multiple Results Selection Keyboard for /model <query>
// -------------------------------------------------------------
export function buildMultipleResultsKeyboard(models: ModelDetail[]): TelegramInlineKeyboardMarkup {
  const rows: TelegramInlineKeyboardButton[][] = [];

  for (const model of models.slice(0, 8)) {
    rows.push([
      {
        text: `🔹 [${model.provider}] ${model.display_name}`,
        callback_data: `c:d:${model.short_index}`,
      },
    ]);
  }

  rows.push([
    {
      text: "📚 Browse All Providers (浏览完整目录)",
      callback_data: "c:r",
    },
  ]);

  return { inline_keyboard: rows };
}
