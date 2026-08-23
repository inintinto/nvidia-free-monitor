export interface Env {
  TELEGRAM_BOT_TOKEN?: string;
  TELEGRAM_WEBHOOK_SECRET_TOKEN?: string;
  INIT_COMMAND_SECRET?: string;
  GITHUB_REPO?: string;
  GITHUB_BRANCH?: string;
}

export interface TelegramUser {
  id: number;
  is_bot: boolean;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

export interface TelegramChat {
  id: number;
  type: "private" | "group" | "supergroup" | "channel";
  title?: string;
  username?: string;
  first_name?: string;
  last_name?: string;
}

export interface TelegramMessage {
  message_id: number;
  from?: TelegramUser;
  chat: TelegramChat;
  date: number;
  text?: string;
}

export interface TelegramInlineKeyboardButton {
  text: string;
  callback_data?: string;
  url?: string;
}

export interface TelegramInlineKeyboardMarkup {
  inline_keyboard: TelegramInlineKeyboardButton[][];
}

export interface TelegramCallbackQuery {
  id: string;
  from: TelegramUser;
  message?: TelegramMessage;
  data?: string;
}

export interface TelegramUpdate {
  update_id: number;
  message?: TelegramMessage;
  callback_query?: TelegramCallbackQuery;
}

export interface TelegramBotCommand {
  command: string;
  description: string;
}

export interface TelegramBotCommandScope {
  type: "default" | "all_private_chats" | "all_group_chats" | "all_chat_administrators";
}

export interface TelegramApiResponse<T = unknown> {
  ok: boolean;
  result?: T;
  description?: string;
  error_code?: number;
}

// -------------------------------------------------------------
// Model Metadata & Catalog Types
// -------------------------------------------------------------

export interface UsageStats {
  api_calls_24h: string | null;
  api_calls_daily: string | null;
  api_calls_7d: string | null;
  api_calls_30d: string | null;
  usage_updated_at: string | null;
  usage_source: string | null;
}

export interface OfficialLifecycle {
  official_status: string;
  official_deprecation_date: string | null;
  sunset_date: string | null;
  deprecation_source_url: string | null;
  deprecation_notes: string | null;
}

export interface LifecycleRecord {
  model_id: string;
  first_seen: string | null;
  free_since: string | null;
  last_seen: string | null;
  removed_at: string | null;
  is_currently_active: boolean;
  official_lifecycle: OfficialLifecycle;
}

export interface ModelDetail {
  short_index: number;
  model_id: string;
  display_name: string;
  aliases: string[];
  platform: string;
  provider: string;
  provider_id: string;
  model_family: string | null;
  architecture: string | null;
  parameter_count: string | null;
  context_length: string | null;
  capabilities: string[];
  free_endpoint: boolean;
  source_urls: Record<string, string>;
  usage: UsageStats;
  lifecycle: LifecycleRecord;
}

export interface ResolveResult {
  query: string;
  match_type: "EXACT" | "MULTIPLE" | "EMPTY";
  matched_models: ModelDetail[];
  total_matches: number;
  filter_provider?: string;
  filter_capability?: string;
}

export interface ProviderSummary {
  provider_id: string;
  display_name: string;
  model_count: number;
}
