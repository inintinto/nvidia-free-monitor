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
// Stage 3A Model Metadata & Catalog Types
// -------------------------------------------------------------

export interface ProviderInfo {
  id: string;
  name: string;
}

export interface ClassificationInfo {
  family: string | null;
  tier: "flagship" | "large" | "medium" | "small" | "embedding" | "specialized" | "standard" | "unknown";
  model_type: "chat" | "reasoning" | "coding" | "vision" | "embedding" | "multimodal" | "specialized" | "unknown";
  speed?: "fast" | "standard" | "unknown";
}

export interface ArchitectureInfo {
  type: string | null; // Dense, MoE, Embedding
  total_parameters: string | null;
  active_parameters: string | null;
  parameter_status: "official" | "observed" | "unknown";
}

export interface ContextInfo {
  length: string | null;
  max_output: string | null;
  status: "official" | "observed" | "unknown";
}

export interface ReleaseInfo {
  first_seen: string | null;
  release_date: string | null;
  status: "official" | "observed" | "unknown";
}

export interface LinksInfo {
  nvidia: string | null;
  official: string | null;
  documentation: string | null;
  model_card: string | null;
}

export interface SourceMetadata {
  field_sources: Record<string, string>;
  confidence: "high" | "medium" | "low" | "unknown";
  last_verified: string | null;
}

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
  model_id: string;
  display_name: string;
  aliases: string[];
  slug: string;
  platform: string;

  // Stage 3A Sub-Schemas
  provider_info: ProviderInfo;
  classification: ClassificationInfo;
  arch_info: ArchitectureInfo;
  context_info: ContextInfo;
  release_info: ReleaseInfo;
  links: LinksInfo;
  source_metadata: SourceMetadata;

  capabilities: string[];
  free_endpoint: boolean;
  usage: UsageStats;
  lifecycle: LifecycleRecord;
  short_index: number;

  // Backward compatibility getters / aliases
  provider: string;
  provider_id: string;
  model_family: string | null;
  architecture: string | null;
  parameter_count: string | null;
  context_length: string | null;
  source_urls: Record<string, string>;
}

export interface ProviderSummary {
  provider_id: string;
  display_name: string;
  model_count: number;
}

export interface ResolveResult {
  query: string;
  match_type: "EXACT" | "MULTIPLE" | "EMPTY";
  matched_models: ModelDetail[];
  total_matches: number;
  filter_provider?: string;
  filter_capability?: string;
}
