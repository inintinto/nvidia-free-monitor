import type {
  TelegramApiResponse,
  TelegramBotCommand,
  TelegramBotCommandScope,
  TelegramInlineKeyboardMarkup,
} from "./types.ts";

export function escapeHtml(text: string): string {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export class TelegramBotClient {
  private token: string;
  private baseUrl: string;

  constructor(token: string) {
    if (!token) {
      throw new Error("TELEGRAM_BOT_TOKEN is required.");
    }
    this.token = token;
    this.baseUrl = `https://api.telegram.org/bot${token}`;
  }

  private async callApi<T>(
    method: string,
    payload: Record<string, unknown>
  ): Promise<TelegramApiResponse<T>> {
    const url = `${this.baseUrl}/${method}`;
    let response: Response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch (err) {
      // Never log token in error message
      throw new Error(`Telegram API network error during ${method}: ${(err as Error).message}`);
    }

    let data: TelegramApiResponse<T>;
    try {
      data = (await response.json()) as TelegramApiResponse<T>;
    } catch (err) {
      throw new Error(`Failed to parse Telegram API JSON for ${method} (status: ${response.status})`);
    }

    if (!response.ok || !data.ok) {
      const desc = data.description || "Unknown Telegram error";
      const code = data.error_code || response.status;
      throw new Error(`Telegram API error (${code}) on ${method}: ${desc}`);
    }

    return data;
  }

  async sendMessage(
    chatId: number | string,
    text: string,
    options?: {
      parse_mode?: "HTML" | "MarkdownV2" | "Markdown";
      reply_markup?: TelegramInlineKeyboardMarkup;
      disable_web_page_preview?: boolean;
    }
  ): Promise<TelegramApiResponse> {
    return this.callApi("sendMessage", {
      chat_id: chatId,
      text,
      parse_mode: options?.parse_mode ?? "HTML",
      reply_markup: options?.reply_markup,
      disable_web_page_preview: options?.disable_web_page_preview ?? true,
    });
  }

  async editMessageText(
    chatId: number | string,
    messageId: number,
    text: string,
    options?: {
      parse_mode?: "HTML" | "MarkdownV2" | "Markdown";
      reply_markup?: TelegramInlineKeyboardMarkup;
      disable_web_page_preview?: boolean;
    }
  ): Promise<TelegramApiResponse> {
    return this.callApi("editMessageText", {
      chat_id: chatId,
      message_id: messageId,
      text,
      parse_mode: options?.parse_mode ?? "HTML",
      reply_markup: options?.reply_markup,
      disable_web_page_preview: options?.disable_web_page_preview ?? true,
    });
  }

  async answerCallbackQuery(
    callbackQueryId: string,
    options?: {
      text?: string;
      show_alert?: boolean;
    }
  ): Promise<TelegramApiResponse> {
    return this.callApi("answerCallbackQuery", {
      callback_query_id: callbackQueryId,
      text: options?.text,
      show_alert: options?.show_alert ?? false,
    });
  }

  async setMyCommands(
    commands: TelegramBotCommand[],
    options?: {
      scope?: TelegramBotCommandScope;
      language_code?: string;
    }
  ): Promise<TelegramApiResponse> {
    const payload: Record<string, unknown> = { commands };
    if (options?.scope) {
      payload.scope = options.scope;
    }
    if (options?.language_code) {
      payload.language_code = options.language_code;
    }
    return this.callApi("setMyCommands", payload);
  }
}
