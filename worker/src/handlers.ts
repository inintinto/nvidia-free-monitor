import { CatalogStore } from "./catalog.ts";
import {
  formatCapabilityMenuHtml,
  formatEmptySearchHtml,
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
        "❓ <b>未知指令。</b>\n\n请使用：\n• <code>/models</code> - 📚 浏览免费模型目录\n• <code>/model &lt;关键词&gt;</code> - 🔍 查询指定模型\n• <code>/help</code> - ❓ 查看使用帮助",
        { parse_mode: "HTML" }
      );
    }
  }

  async handleCallbackQuery(query: TelegramCallbackQuery): Promise<void> {
    const data = query.data || "";
    const chatId = query.message?.chat.id;
    const messageId = query.message?.message_id;

    if (!chatId || !messageId) {
      await this.botClient.answerCallbackQuery(query.id);
      return;
    }

    const parts = data.split(":");
    const prefix = parts[0];
    const action = parts[1];

    if (prefix !== "c") {
      await this.botClient.answerCallbackQuery(query.id);
      return;
    }

    // 1. Level 1: Root Provider Menu (`c:r`)
    if (action === "r") {
      await this.botClient.answerCallbackQuery(query.id);
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
      await this.botClient.answerCallbackQuery(query.id);
      const providerId = parts[2] || "all";
      const capabilities = this.store.getCapabilities(providerId);
      const models = this.store.listModels(providerId);

      const text = formatCapabilityMenuHtml(providerId, models.length);
      const keyboard = buildCapabilityKeyboard(providerId, capabilities);
      await this.botClient.editMessageText(chatId, messageId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    // 3. Level 3: Model List (`c:c:<provider_id>:<capability>` or `c:l:<provider_id>:<cap>:<page>`)
    if (action === "c" || action === "l") {
      await this.botClient.answerCallbackQuery(query.id);
      const providerId = parts[2] || "all";
      const capability = parts[3] || "all";
      const page = action === "l" ? parseInt(parts[4] || "0", 10) : 0;
      const pageSize = 8;

      const models = this.store.listModels(providerId, capability);
      const text = formatModelListMenuHtml(providerId, capability, models.length, page, pageSize);
      const keyboard = buildModelListKeyboard(providerId, capability, models, page, pageSize);
      await this.botClient.editMessageText(chatId, messageId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    // 4. Level 4: Model Detail (`c:d:<short_index>`)
    if (action === "d") {
      const shortIndex = parseInt(parts[2], 10);
      const model = isNaN(shortIndex) ? undefined : this.store.getModelByShortIndex(shortIndex);

      if (!model) {
        // Expired or invalid short index: Alert gracefully
        await this.botClient.answerCallbackQuery(query.id, {
          text: "⚠️ 该菜单已过期或模型目录已更新，请重新发送 /models 浏览。",
          show_alert: true,
        });
        return;
      }

      await this.botClient.answerCallbackQuery(query.id);
      const text = formatModelDetailHtml(model);
      const keyboard = buildModelDetailKeyboard(model);
      await this.botClient.editMessageText(chatId, messageId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    // Default fallback acknowledgement
    await this.botClient.answerCallbackQuery(query.id);
  }

  private async handleStart(chatId: number): Promise<void> {
    const totalCount = this.store.getAllModels().length;
    const welcomeMsg = [
      "🤖 <b>NVIDIA Free Endpoint Explorer</b>",
      "<i>全球免费 Endpoint 监控与交互式目录百科</i>\n",
      `当前共索引 <b>${totalCount}</b> 款 NVIDIA 官方可用免费大模型。\n`,
      "✨ <b>主要功能：</b>",
      "• <code>/models</code> - 📚 交互式浏览提供商与能力目录",
      "• <code>/model &lt;名称&gt;</code> - 🔍 快速查询指定模型技术规格",
      "• <code>/help</code> - ❓ 查看系统使用指南\n",
      "💡 <i>提示：点击下方按钮或左下角「菜单」即可随时开启探索！</i>",
    ].join("\n");

    const keyboard = {
      inline_keyboard: [
        [
          { text: "📚 浏览全部模型 (/models)", callback_data: "c:r" },
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
      "📖 <b>使用帮助与操作指南</b>\n",
      "<b>1. 目录浏览 (4 级导航)：</b>",
      "• 发送 <code>/models</code> 打开目录首页",
      "• 依次按 <b>Provider (提供商)</b> → <b>Capability (能力分类)</b> → <b>Model (模型)</b> 查看详情卡片\n",
      "<b>2. 智能搜索查询：</b>",
      "• 精确查询：<code>/model deepseek-v4-flash-0731</code>",
      "• 别名查询：<code>/model DS V4 Flash</code> 或 <code>/model llama 3.3</code>",
      "• 品牌搜索：<code>/model deepseek</code> 或 <code>/model nemotron</code>",
      "• 能力检索：<code>/model coding</code> 或 <code>/model reasoning</code>\n",
      "<b>3. 数据真实性说明：</b>",
      "• 本目录所有参数与上下文均基于官方发布规范与监控观测",
      "• 未公开数据严格标注为「官方未公开」，严禁猜测",
    ].join("\n");

    const keyboard = {
      inline_keyboard: [
        [
          { text: "📚 立即浏览免费模型 (/models)", callback_data: "c:r" },
        ],
      ],
    };

    await this.botClient.sendMessage(chatId, helpMsg, {
      parse_mode: "HTML",
      reply_markup: keyboard,
    });
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
        "🔍 <b>请输入要查询的模型名称或关键词。</b>\n\n例如：\n• <code>/model DS V4 Flash</code>\n• <code>/model llama 3.3</code>\n• <code>/model nemotron</code>",
        { parse_mode: "HTML" }
      );
      return;
    }

    const result = this.resolver.resolve(query);

    if (result.match_type === "EXACT" && result.matched_models.length === 1) {
      const model = result.matched_models[0];
      const text = formatModelDetailHtml(model);
      const keyboard = buildModelDetailKeyboard(model);
      await this.botClient.sendMessage(chatId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    if (result.match_type === "MULTIPLE" && result.matched_models.length > 0) {
      const safeQuery = escapeHtml(query);
      const text = [
        `🔍 <b>找到 ${result.matched_models.length} 个与「${safeQuery}」相关的模型：</b>\n`,
        `👇 <b>请点击选择要查看的模型：</b>`,
      ].join("\n");

      const keyboard = buildMultipleResultsKeyboard(result.matched_models);
      await this.botClient.sendMessage(chatId, text, {
        parse_mode: "HTML",
        reply_markup: keyboard,
      });
      return;
    }

    // EMPTY match
    const emptyText = formatEmptySearchHtml(query);
    await this.botClient.sendMessage(chatId, emptyText, {
      parse_mode: "HTML",
    });
  }
}
