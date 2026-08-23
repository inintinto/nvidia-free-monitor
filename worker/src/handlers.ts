import { CatalogStore } from "./catalog.ts";
import {
  formatCapabilityMenuHtml,
  formatModelDetailHtml,
  formatModelListMenuHtml,
  formatProviderMenuHtml,
} from "./formatters.ts";
import {
  buildCapabilityKeyboard,
  buildModelDetailKeyboard,
  buildModelListKeyboard,
  buildMultipleResultsKeyboard,
  buildProviderKeyboard,
} from "./keyboards.ts";
import { ModelResolver } from "./resolver.ts";
import { escapeHtml, TelegramBotClient } from "./telegram.ts";
import type { TelegramCallbackQuery, TelegramMessage } from "./types.ts";

export class BotCommandHandler {
  private botClient: TelegramBotClient;
  private store: CatalogStore;
  private resolver: ModelResolver;

  constructor(botClient: TelegramBotClient, store?: CatalogStore) {
    this.botClient = botClient;
    this.store = store || new CatalogStore();
    this.resolver = new ModelResolver(this.store);
  }

  setStore(store: CatalogStore): void {
    this.store = store;
    this.resolver = new ModelResolver(store);
  }

  async handleMessage(message: TelegramMessage): Promise<void> {
    const text = message.text?.trim() || "";
    const chatId = message.chat.id;

    if (!text) {
      return;
    }

    if (text.startsWith("/start")) {
      await this.handleStart(chatId);
      return;
    }

    if (text.startsWith("/help")) {
      await this.handleHelp(chatId);
      return;
    }

    if (text.startsWith("/models")) {
      await this.handleModels(chatId);
      return;
    }

    if (text.startsWith("/model")) {
      const query = text.replace(/^\/model(@\w+)?/i, "").trim();
      await this.handleModelQuery(chatId, query);
      return;
    }

    // Default unknown command or text response
    if (text.startsWith("/")) {
      await this.botClient.sendMessage(
        chatId,
        "❓ 未知指令。\n\n请使用：\n• /models - 浏览免费模型目录\n• /model &lt;模型名&gt; - 查询指定模型\n• /help - 查看使用帮助"
      );
    }
  }

  async handleCallbackQuery(query: TelegramCallbackQuery): Promise<void> {
    const data = query.data || "";
    const chatId = query.message?.chat.id;
    const messageId = query.message?.message_id;

    // Promptly answer callback query
    await this.botClient.answerCallbackQuery(query.id);

    if (!chatId || !messageId) {
      return;
    }

    const parts = data.split(":");
    const prefix = parts[0];
    const action = parts[1];

    if (prefix !== "c") {
      return;
    }

    // 1. Level 1: Root Provider Menu (`c:r`)
    if (action === "r") {
      const providers = this.store.getProviders();
      const text = formatProviderMenuHtml(providers, this.store.getAllModels().length);
      const keyboard = buildProviderKeyboard(providers);
      await this.botClient.editMessageText(chatId, messageId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    // 2. Level 2: Capability Menu (`c:p:<provider_id>`)
    if (action === "p") {
      const providerId = parts[2] || "all";
      const capabilities = this.store.getCapabilities(providerId);
      const models = this.store.listModels(providerId);
      const providerName = providerId === "all" ? "All Models" : (models[0]?.provider || providerId);

      const text = formatCapabilityMenuHtml(providerName, models.length);
      const keyboard = buildCapabilityKeyboard(providerId, capabilities);
      await this.botClient.editMessageText(chatId, messageId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    // 3. Level 3: Model List (`c:c:<provider_id>:<capability>` or `c:l:<provider_id>:<cap>:<page>`)
    if (action === "c" || action === "l") {
      const providerId = parts[2] || "all";
      const capability = parts[3] || "all";
      const page = action === "l" ? parseInt(parts[4] || "0", 10) : 0;

      const models = this.store.listModels(providerId, capability);
      const providerName = providerId === "all" ? "All Providers" : (models[0]?.provider || providerId);

      const text = formatModelListMenuHtml(providerName, capability, models.length);
      const keyboard = buildModelListKeyboard(providerId, capability, models, page);
      await this.botClient.editMessageText(chatId, messageId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    // 4. Level 4: Model Detail (`c:d:<short_index>`)
    if (action === "d") {
      const shortIndex = parseInt(parts[2], 10);
      const model = this.store.getModelByShortIndex(shortIndex);

      if (!model) {
        await this.botClient.sendMessage(chatId, "❌ 未找到对应模型详情，可能数据已被更新。");
        return;
      }

      const text = formatModelDetailHtml(model);
      const keyboard = buildModelDetailKeyboard(model);
      await this.botClient.editMessageText(chatId, messageId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
    }
  }

  private async handleStart(chatId: number): Promise<void> {
    const welcomeMsg = [
      "🤖 <b>NVIDIA Free Endpoint Monitor</b>",
      "全球免费模型实时监控与多维目录系统\n",
      "您可以通过以下指令探索 NVIDIA NIM 免费模型目录：\n",
      "📚 <b>/models</b> — 浏览所有提供商与能力分类目录",
      "🔍 <b>/model &lt;名称/ID&gt;</b> — 快速精确/模糊查询模型详情",
      "❓ <b>/help</b> — 查看完整使用指南与指令帮助\n",
      "<i>💡 点击输入框左侧菜单或输入 '/' 即可快速选择指令。</i>",
    ].join("\n");

    const keyboard = {
      inline_keyboard: [
        [
          {
            text: "📚 浏览免费模型目录 (/models)",
            callback_data: "c:r",
          },
        ],
      ],
    };

    await this.botClient.sendMessage(chatId, welcomeMsg, {
      parse_mode: "HTML",
      reply_markup: keyboard,
    });
  }

  private async handleHelp(chatId: number): Promise<void> {
    const helpMsg = [
      "📖 <b>NVIDIA Free Endpoint Monitor 使用指南</b>\n",
      "<b>核心指令：</b>",
      "• <b>/models</b>",
      "  按 <code>Provider (提供商)</code> → <code>Capability (能力)</code> → <code>Model (模型)</code> 逐级浏览全部可用免费端点。\n",
      "• <b>/model &lt;关键词&gt;</b>",
      "  直接搜索模型，支持 Model ID、别名、缩写与模糊匹配，例如：",
      "  - <code>/model DS V4 Flash 0731</code>",
      "  - <code>/model deepseek-v4-flash-0731</code>",
      "  - <code>/model llama 3.3</code>",
      "  - <code>/model nemotron</code>\n",
      "<b>数据与监控说明：</b>",
      "• 监控流水线每 30 分钟同步一次 NVIDIA 官方 API 目录。",
      "• 全球调用量数据均来自官方公开聚合统计，不统计个人请求量。",
    ].join("\n");

    await this.botClient.sendMessage(chatId, helpMsg, { parse_mode: "HTML" });
  }

  private async handleModels(chatId: number): Promise<void> {
    const providers = this.store.getProviders();
    const text = formatProviderMenuHtml(providers, this.store.getAllModels().length);
    const keyboard = buildProviderKeyboard(providers);

    await this.botClient.sendMessage(chatId, text, {
      parse_mode: "HTML",
      reply_markup: keyboard,
    });
  }

  private async handleModelQuery(chatId: number, query: string): Promise<void> {
    if (!query) {
      await this.botClient.sendMessage(
        chatId,
        "🔍 <b>模型查询格式：</b>\n<code>/model &lt;模型名称或ID&gt;</code>\n\n例如：\n• <code>/model DS V4 Flash 0731</code>\n• <code>/model llama 3.3</code>\n• <code>/model nemotron</code>"
      );
      return;
    }

    const res = this.resolver.resolve(query);

    if (res.match_type === "EXACT" && res.matched_models.length > 0) {
      const model = res.matched_models[0];
      const text = formatModelDetailHtml(model);
      const keyboard = buildModelDetailKeyboard(model);
      await this.botClient.sendMessage(chatId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    if (res.match_type === "MULTIPLE" && res.matched_models.length > 0) {
      const safeQ = escapeHtml(query);
      const text = `🔍 找到 <b>${res.total_matches}</b> 个与 "<code>${safeQ}</code>" 相关的候选模型：\n\n请点击下方按钮查看详情：`;
      const keyboard = buildMultipleResultsKeyboard(res.matched_models);
      await this.botClient.sendMessage(chatId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    // EMPTY
    const safeQ = escapeHtml(query);
    const emptyMsg = [
      `❌ 未找到与 "<code>${safeQ}</code>" 匹配的模型。\n`,
      "💡 建议尝试：",
      "• 发送 <b>/models</b> 浏览全部提供商目录",
      "• 检查拼写或使用更简短的关键词 (例如 <code>llama</code>, <code>deepseek</code>, <code>nemotron</code>)",
    ].join("\n");

    await this.botClient.sendMessage(chatId, emptyMsg, { parse_mode: "HTML" });
  }
}
