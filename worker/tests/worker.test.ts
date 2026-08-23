import assert from "node:assert/strict";
import test, { describe } from "node:test";
import { CatalogStore } from "../src/catalog.ts";
import { formatModelDetailHtml } from "../src/formatters.ts";
import { BotCommandHandler } from "../src/handlers.ts";
import {
  buildCapabilityKeyboard,
  buildModelDetailKeyboard,
  buildModelListKeyboard,
  buildMultipleResultsKeyboard,
  buildProviderKeyboard,
} from "../src/keyboards.ts";
import { CHINESE_BOT_COMMANDS, ENGLISH_BOT_COMMANDS, injectBotCommands } from "../src/menu.ts";
import { ModelResolver, normalizeText } from "../src/resolver.ts";
import { escapeHtml, TelegramBotClient } from "../src/telegram.ts";
import worker from "../src/index.ts";
import type { Env, TelegramApiResponse, TelegramInlineKeyboardMarkup } from "../src/types.ts";

// Mock Telegram Bot Client
class MockTelegramBotClient extends TelegramBotClient {
  public sentMessages: Array<{ chatId: number | string; text: string; markup?: TelegramInlineKeyboardMarkup }> = [];
  public editedMessages: Array<{ chatId: number | string; messageId: number; text: string; markup?: TelegramInlineKeyboardMarkup }> = [];
  public answeredCallbacks: Array<{ id: string }> = [];
  public registeredCommands: Array<{ commands: unknown; scope?: unknown; lang?: string }> = [];

  constructor() {
    super("mock_token_123");
  }

  override async sendMessage(
    chatId: number | string,
    text: string,
    options?: { reply_markup?: TelegramInlineKeyboardMarkup }
  ): Promise<TelegramApiResponse> {
    this.sentMessages.push({ chatId, text, markup: options?.reply_markup });
    return { ok: true, result: {} };
  }

  override async editMessageText(
    chatId: number | string,
    messageId: number,
    text: string,
    options?: { reply_markup?: TelegramInlineKeyboardMarkup }
  ): Promise<TelegramApiResponse> {
    this.editedMessages.push({ chatId, messageId, text, markup: options?.reply_markup });
    return { ok: true, result: {} };
  }

  override async answerCallbackQuery(callbackQueryId: string): Promise<TelegramApiResponse> {
    this.answeredCallbacks.push({ id: callbackQueryId });
    return { ok: true, result: {} };
  }

  override async setMyCommands(
    commands: unknown[],
    options?: { scope?: unknown; language_code?: string }
  ): Promise<TelegramApiResponse> {
    this.registeredCommands.push({
      commands,
      scope: options?.scope,
      lang: options?.language_code,
    });
    return { ok: true, result: {} };
  }
}

// Sample Curated Dataset for Testing
const TEST_CATALOG = {
  models: {
    "deepseek-ai/deepseek-v4-flash-0731": {
      display_name: "DeepSeek V4 Flash 0731",
      aliases: ["ds v4 flash", "deepseek v4 flash", "ds v4 flash 0731", "v4 flash"],
      platform: "NVIDIA NIM",
      provider: "DeepSeek AI",
      provider_id: "deepseek-ai",
      model_family: "DeepSeek-V4",
      architecture: "MoE",
      parameter_count: "Unknown",
      context_length: "128k",
      capabilities: ["Chat", "Reasoning", "Coding"],
      free_endpoint: true,
      source_urls: {
        nvidia_nim: "https://build.nvidia.com/deepseek-ai/deepseek-v4-flash-0731",
        official_site: "https://www.deepseek.com",
      },
      usage: {
        api_calls_30d: "3.2M",
        usage_source: "NVIDIA API Catalog Public Aggregate",
      },
    },
    "deepseek-ai/deepseek-coder-6.7b-instruct": {
      display_name: "DeepSeek Coder 6.7B Instruct",
      aliases: ["ds coder 6.7b", "deepseek coder"],
      platform: "NVIDIA NIM",
      provider: "DeepSeek AI",
      provider_id: "deepseek-ai",
      model_family: "DeepSeek-Coder",
      architecture: "Dense",
      parameter_count: "6.7B",
      context_length: "16k",
      capabilities: ["Coding", "Chat"],
      free_endpoint: true,
      source_urls: {
        nvidia_nim: "https://build.nvidia.com/deepseek-ai/deepseek-coder-6.7b-instruct",
      },
      usage: {
        api_calls_30d: "1.1M",
      },
    },
    "meta/llama-3.3-70b-instruct": {
      display_name: "Llama 3.3 70B Instruct",
      aliases: ["llama 3.3", "llama 3.3 70b"],
      platform: "NVIDIA NIM",
      provider: "Meta",
      provider_id: "meta",
      model_family: "Llama-3.3",
      architecture: "Dense",
      parameter_count: "70B",
      context_length: "128k",
      capabilities: ["Chat", "Reasoning", "Coding"],
      free_endpoint: true,
      source_urls: {
        nvidia_nim: "https://build.nvidia.com/meta/llama-3.3-70b-instruct",
      },
      usage: {
        api_calls_30d: "5.8M",
      },
    },
    "meta/llama-3.1-405b-instruct": {
      display_name: "Llama 3.1 405B Instruct",
      aliases: ["llama 3.1 405b", "llama 405b"],
      platform: "NVIDIA NIM",
      provider: "Meta",
      provider_id: "meta",
      model_family: "Llama-3.1",
      architecture: "Dense",
      parameter_count: "405B",
      context_length: "128k",
      capabilities: ["Chat", "Reasoning", "Coding"],
      free_endpoint: true,
      source_urls: {
        nvidia_nim: "https://build.nvidia.com/meta/llama-3.1-405b-instruct",
      },
      usage: {
        api_calls_30d: "2.4M",
      },
    },
    "nvidia/nemotron-4-340b-instruct": {
      display_name: "Nemotron-4 340B Instruct",
      aliases: ["nemotron", "nemotron 4 340b"],
      platform: "NVIDIA NIM",
      provider: "NVIDIA",
      provider_id: "nvidia",
      model_family: "Nemotron-4",
      architecture: "Dense",
      parameter_count: "340B",
      context_length: "4k",
      capabilities: ["Chat", "Reasoning"],
      free_endpoint: true,
      source_urls: {
        nvidia_nim: "https://build.nvidia.com/nvidia/nemotron-4-340b-instruct",
      },
      usage: {
        api_calls_30d: "1.9M",
      },
    },
  },
};

const TEST_LIFECYCLE = {
  history: {
    "deepseek-ai/deepseek-v4-flash-0731": {
      first_seen: "2026-07-31T08:00:00Z",
      free_since: "2026-07-31T08:00:00Z",
      last_seen: "2026-08-23T10:00:00Z",
      removed_at: null,
      is_currently_active: true,
      official_lifecycle: {
        official_status: "active",
        official_deprecation_date: null,
      },
    },
  },
};

const TEST_BASELINE = {
  models: [
    { id: "deepseek-ai/deepseek-v4-flash-0731", owned_by: "deepseek-ai" },
    { id: "deepseek-ai/deepseek-coder-6.7b-instruct", owned_by: "deepseek-ai" },
    { id: "meta/llama-3.3-70b-instruct", owned_by: "meta" },
    { id: "meta/llama-3.1-405b-instruct", owned_by: "meta" },
    { id: "nvidia/nemotron-4-340b-instruct", owned_by: "nvidia" },
    { id: "unregistered/new-ai-model", owned_by: "unregistered" },
  ],
};

describe("Stage 2B Comprehensive Worker & Bot Tests", () => {
  const store = new CatalogStore(TEST_CATALOG, TEST_LIFECYCLE, TEST_BASELINE);
  const resolver = new ModelResolver(store);

  // 1. /models Provider Menu Test
  test("1. /models Provider Menu Test", async () => {
    const mockClient = new MockTelegramBotClient();
    const handler = new BotCommandHandler(mockClient, store);

    await handler.handleMessage({
      message_id: 1,
      chat: { id: 1001, type: "private" },
      date: 123456,
      text: "/models",
    });

    assert.equal(mockClient.sentMessages.length, 1);
    const msg = mockClient.sentMessages[0];
    assert.match(msg.text, /全球免费模型目录/);
    assert.ok(msg.markup?.inline_keyboard);
    const buttons = msg.markup.inline_keyboard.flat();
    assert.ok(buttons.some((b) => b.callback_data === "c:p:deepseek-ai"));
    assert.ok(buttons.some((b) => b.callback_data === "c:p:all"));
  });

  // 2. Provider -> Capability Test
  test("2. Provider -> Capability Test", async () => {
    const mockClient = new MockTelegramBotClient();
    const handler = new BotCommandHandler(mockClient, store);

    await handler.handleCallbackQuery({
      id: "cb_1",
      from: { id: 1001, is_bot: false, first_name: "User" },
      message: { message_id: 10, chat: { id: 1001, type: "private" }, date: 123456 },
      data: "c:p:deepseek-ai",
    });

    assert.equal(mockClient.editedMessages.length, 1);
    const msg = mockClient.editedMessages[0];
    assert.match(msg.text, /DeepSeek AI/);
    const buttons = msg.markup?.inline_keyboard.flat() || [];
    assert.ok(buttons.some((b) => b.callback_data === "c:c:deepseek-ai:coding"));
    assert.ok(buttons.some((b) => b.callback_data === "c:c:deepseek-ai:chat"));
    assert.ok(buttons.some((b) => b.callback_data === "c:r")); // Back button
  });

  // 3. Capability -> Model Test
  test("3. Capability -> Model Test", async () => {
    const mockClient = new MockTelegramBotClient();
    const handler = new BotCommandHandler(mockClient, store);

    await handler.handleCallbackQuery({
      id: "cb_2",
      from: { id: 1001, is_bot: false, first_name: "User" },
      message: { message_id: 10, chat: { id: 1001, type: "private" }, date: 123456 },
      data: "c:c:deepseek-ai:coding",
    });

    assert.equal(mockClient.editedMessages.length, 1);
    const msg = mockClient.editedMessages[0];
    assert.match(msg.text, /DeepSeek AI/);
    const buttons = msg.markup?.inline_keyboard.flat() || [];
    assert.ok(buttons.some((b) => b.text.includes("DeepSeek V4 Flash 0731")));
    assert.ok(buttons.some((b) => b.text.includes("DeepSeek Coder 6.7B")));
    assert.ok(buttons.some((b) => b.callback_data === "c:p:deepseek-ai")); // Back button
  });

  // 4. Model -> Detail Test
  test("4. Model -> Detail Test", async () => {
    const mockClient = new MockTelegramBotClient();
    const handler = new BotCommandHandler(mockClient, store);

    const model = store.getModel("deepseek-ai/deepseek-v4-flash-0731")!;
    await handler.handleCallbackQuery({
      id: "cb_3",
      from: { id: 1001, is_bot: false, first_name: "User" },
      message: { message_id: 10, chat: { id: 1001, type: "private" }, date: 123456 },
      data: `c:d:${model.short_index}`,
    });

    assert.equal(mockClient.editedMessages.length, 1);
    const msg = mockClient.editedMessages[0];
    assert.match(msg.text, /DeepSeek V4 Flash 0731/);
    assert.match(msg.text, /deepseek-ai\/deepseek-v4-flash-0731/);
    assert.match(msg.text, /Global NVIDIA API Calls/);
    assert.match(msg.text, /3\.2M calls/);

    const buttons = msg.markup?.inline_keyboard.flat() || [];
    assert.ok(buttons.some((b) => b.url?.includes("build.nvidia.com")));
    assert.ok(buttons.some((b) => b.callback_data?.startsWith("c:c:")));
  });

  // 5. Back Navigation Test
  test("5. Back Navigation Test", async () => {
    const mockClient = new MockTelegramBotClient();
    const handler = new BotCommandHandler(mockClient, store);

    // Root Back
    await handler.handleCallbackQuery({
      id: "cb_back",
      from: { id: 1001, is_bot: false, first_name: "User" },
      message: { message_id: 10, chat: { id: 1001, type: "private" }, date: 123456 },
      data: "c:r",
    });
    assert.equal(mockClient.editedMessages.length, 1);
    assert.match(mockClient.editedMessages[0].text, /全球免费模型目录/);
  });

  // 6. /model Exact Test
  test("6. /model Exact Test", async () => {
    const mockClient = new MockTelegramBotClient();
    const handler = new BotCommandHandler(mockClient, store);

    await handler.handleMessage({
      message_id: 6,
      chat: { id: 1001, type: "private" },
      date: 123456,
      text: "/model deepseek-ai/deepseek-v4-flash-0731",
    });

    assert.equal(mockClient.sentMessages.length, 1);
    assert.match(mockClient.sentMessages[0].text, /DeepSeek V4 Flash 0731/);
    assert.match(mockClient.sentMessages[0].text, /128k/);
  });

  // 7. /model Alias Test
  test("7. /model Alias Test", async () => {
    const mockClient = new MockTelegramBotClient();
    const handler = new BotCommandHandler(mockClient, store);

    await handler.handleMessage({
      message_id: 7,
      chat: { id: 1001, type: "private" },
      date: 123456,
      text: "/model DS V4 Flash 0731",
    });

    assert.equal(mockClient.sentMessages.length, 1);
    assert.match(mockClient.sentMessages[0].text, /DeepSeek V4 Flash 0731/);

    // Nemotron alias
    await handler.handleMessage({
      message_id: 8,
      chat: { id: 1001, type: "private" },
      date: 123456,
      text: "/model nemotron",
    });
    assert.equal(mockClient.sentMessages.length, 2);
    assert.match(mockClient.sentMessages[1].text, /Nemotron-4 340B Instruct/);
  });

  // 8. /model Fuzzy Test
  test("8. /model Fuzzy Test", async () => {
    const res = resolver.resolve("deepseek coder");
    assert.equal(res.match_type, "EXACT");
    assert.equal(res.matched_models[0].model_id, "deepseek-ai/deepseek-coder-6.7b-instruct");
  });

  // 9. /model Multiple Test
  test("9. /model Multiple Test", async () => {
    const mockClient = new MockTelegramBotClient();
    const handler = new BotCommandHandler(mockClient, store);

    await handler.handleMessage({
      message_id: 9,
      chat: { id: 1001, type: "private" },
      date: 123456,
      text: "/model llama",
    });

    assert.equal(mockClient.sentMessages.length, 1);
    assert.match(mockClient.sentMessages[0].text, /找到 <b>2<\/b> 个与/);
    const buttons = mockClient.sentMessages[0].markup?.inline_keyboard.flat() || [];
    assert.ok(buttons.some((b) => b.text.includes("Llama 3.3 70B")));
    assert.ok(buttons.some((b) => b.text.includes("Llama 3.1 405B")));
  });

  // 10. /model Empty Test
  test("10. /model Empty Test", async () => {
    const mockClient = new MockTelegramBotClient();
    const handler = new BotCommandHandler(mockClient, store);

    await handler.handleMessage({
      message_id: 10,
      chat: { id: 1001, type: "private" },
      date: 123456,
      text: "/model non-existent-model-xyz",
    });

    assert.equal(mockClient.sentMessages.length, 1);
    assert.match(mockClient.sentMessages[0].text, /未找到与.*匹配的模型/);
  });

  // 11. Callback Data Length Test (Must be <= 64 bytes)
  test("11. Callback Data Length Test", () => {
    const providers = store.getProviders();
    const pKb = buildProviderKeyboard(providers);
    for (const row of pKb.inline_keyboard) {
      for (const btn of row) {
        if (btn.callback_data) {
          assert.ok(
            Buffer.byteLength(btn.callback_data, "utf8") <= 64,
            `Callback data exceeds 64 bytes: ${btn.callback_data}`
          );
        }
      }
    }

    const caps = store.getCapabilities();
    const cKb = buildCapabilityKeyboard("deepseek-ai", caps);
    for (const row of cKb.inline_keyboard) {
      for (const btn of row) {
        if (btn.callback_data) {
          assert.ok(
            Buffer.byteLength(btn.callback_data, "utf8") <= 64,
            `Callback data exceeds 64 bytes: ${btn.callback_data}`
          );
        }
      }
    }

    const models = store.getAllModels();
    const lKb = buildModelListKeyboard("deepseek-ai", "coding", models);
    for (const row of lKb.inline_keyboard) {
      for (const btn of row) {
        if (btn.callback_data) {
          assert.ok(
            Buffer.byteLength(btn.callback_data, "utf8") <= 64,
            `Callback data exceeds 64 bytes: ${btn.callback_data}`
          );
        }
      }
    }
  });

  // 12. HTML Escaping Test
  test("12. HTML Escaping Test", () => {
    const raw = `special/model_<tag>&_"v1.0"-test/'demo'`;
    const escaped = escapeHtml(raw);
    assert.equal(
      escaped,
      `special/model_&lt;tag&gt;&amp;_&quot;v1.0&quot;-test/&#039;demo&#039;`
    );
  });

  // 13. Missing Catalog Graceful Fallback Test
  test("13. Missing Catalog Graceful Fallback Test", () => {
    const unreg = store.getModel("unregistered/new-ai-model");
    assert.ok(unreg);
    assert.equal(unreg.provider, "Unregistered");
    assert.equal(unreg.display_name, "New Ai Model");
    assert.equal(unreg.platform, "NVIDIA NIM");
  });

  // 14. Global API Calls Null Handling Test
  test("14. Global API Calls Null Handling Test", () => {
    const unreg = store.getModel("unregistered/new-ai-model")!;
    const html = formatModelDetailHtml(unreg);
    assert.match(html, /Data not published by NVIDIA/);
  });

  // 15. init-commands Secret Protection Test
  test("15. init-commands Secret Protection Test", async () => {
    const env: Env = {
      INIT_COMMAND_SECRET: "correct_init_secret",
      TELEGRAM_BOT_TOKEN: "mock_token",
    };

    // 1. Missing Secret Header -> 401
    const missingReq = new Request("https://worker.local/telegram/init-commands", { method: "POST" });
    const missingResp = await worker.fetch(missingReq, env);
    assert.equal(missingResp.status, 401);

    // 2. Wrong Secret Header -> 401
    const wrongReq = new Request("https://worker.local/telegram/init-commands", {
      method: "POST",
      headers: { "X-Init-Command-Secret": "wrong_secret" },
    });
    const wrongResp = await worker.fetch(wrongReq, env);
    assert.equal(wrongResp.status, 401);
  });

  // 16. setMyCommands Menu Payload Test
  test("16. setMyCommands Menu Payload Test", () => {
    assert.equal(CHINESE_BOT_COMMANDS.length, 4);
    assert.equal(CHINESE_BOT_COMMANDS[0].command, "start");
    assert.equal(CHINESE_BOT_COMMANDS[1].command, "models");
    assert.equal(CHINESE_BOT_COMMANDS[2].command, "model");
    assert.equal(CHINESE_BOT_COMMANDS[3].command, "help");

    assert.equal(ENGLISH_BOT_COMMANDS.length, 4);
    assert.equal(ENGLISH_BOT_COMMANDS[1].command, "models");
  });
});
