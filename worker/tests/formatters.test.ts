import test from "node:test";
import assert from "node:assert/strict";
import { CatalogStore } from "../src/catalog.ts";
import { BUNDLED_BASELINE, BUNDLED_CATALOG, BUNDLED_LIFECYCLE } from "../src/default_data.ts";
import {
  formatCapabilityMenuHtml,
  formatEmptySearchHtml,
  formatModelDetailHtml,
  formatModelListMenuHtml,
  formatProviderMenuHtml,
} from "../src/formatters.ts";
import { BotCommandHandler } from "../src/handlers.ts";
import type { TelegramBotClient } from "../src/telegram.ts";
import type { ModelDetail } from "../src/types.ts";

test("Stage 3: Model Detail Card 2.0 Visual Hierarchy Tests", async (t) => {
  const store = new CatalogStore(
    BUNDLED_CATALOG as any,
    BUNDLED_LIFECYCLE as any,
    BUNDLED_BASELINE as any
  );

  const dsModel = store.getModel("deepseek-ai/deepseek-v4-flash-0731")!;
  const llama405 = store.getModel("meta/llama-3.1-405b-instruct")!;
  const yiModel = store.getModel("01-ai/yi-large")!;

  await t.test("1. Hero Header Structure with Provider + Tier Badge", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("🐋 👑 <b>DeepSeek V4 Flash 0731</b>"));
    assert.ok(html.includes("<i>DeepSeek AI · DeepSeek-V4</i>"));
    assert.ok(html.includes("🟢 <b>当前可用</b>"));
    assert.ok(html.includes("⚡ 高速"));
  });

  await t.test("2. Model Specifications Module (📐 模型规格)", () => {
    const html = formatModelDetailHtml(llama405);
    assert.ok(html.includes("📐 <b>模型规格</b>"));
    assert.ok(html.includes("🏗️ 架构　 <code>Dense</code>"));
    assert.ok(html.includes("🧮 参数　 <code>405B</code>"));
    assert.ok(html.includes("⚙️ 激活　 <code>405B</code>"));
    assert.ok(html.includes("📏 上下文 <code>128k</code>"));
    assert.ok(html.includes("📤 输出　 <code>官方未公开</code>"));
  });

  await t.test("3. Unknown Parameters & Outputs Handling (DeepSeek & Yi)", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("🧮 参数　 <code>官方未公开</code>"));
    assert.ok(html.includes("⚙️ 激活　 <code>官方未公开</code>"));
    assert.ok(html.includes("📤 输出　 <code>官方未公开</code>"));

    const yiHtml = formatModelDetailHtml(yiModel);
    assert.ok(yiHtml.includes("🧮 参数　 <code>官方未公开</code>"));
  });

  await t.test("4. Model Capabilities Module (🎯 能力)", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("🎯 <b>能力</b>"));
    assert.ok(html.includes("💬 对话"));
    assert.ok(html.includes("🧠 推理"));
    assert.ok(html.includes("💻 编程"));
  });

  await t.test("5. Lifecycle Active State (📅 生命周期)", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("📅 <b>生命周期</b>"));
    assert.ok(html.includes("🟢 当前可用"));
    assert.ok(html.includes("👀 首次发现　<code>2026-07-31</code>"));
  });

  await t.test("6. Lifecycle Observed Removed State", () => {
    const mockModel: ModelDetail = {
      ...dsModel,
      lifecycle: {
        ...dsModel.lifecycle,
        is_currently_active: false,
        removed_at: "2026-08-20T10:00:00+00:00",
      },
    };
    const html = formatModelDetailHtml(mockModel);
    assert.ok(html.includes("🟡 <b>监控观测下线</b>"));
    assert.ok(html.includes("🟡 监控下线　<code>2026-08-20 10:00:00 UTC</code>"));
  });

  await t.test("7. Lifecycle Officially Deprecated State", () => {
    const mockModel: ModelDetail = {
      ...dsModel,
      lifecycle: {
        ...dsModel.lifecycle,
        is_currently_active: false,
        official_lifecycle: {
          official_status: "deprecated",
          official_deprecation_date: "2026-08-15",
          sunset_date: null,
          deprecation_source_url: "https://nvidia.com/deprecated",
          deprecation_notes: null,
        },
      },
    };
    const html = formatModelDetailHtml(mockModel);
    assert.ok(html.includes("🔴 <b>官方已废弃</b>"));
    assert.ok(html.includes("🔴 官方废弃　<code>2026-08-15</code>"));
    assert.ok(html.includes("📢 废弃公告　<a href=\"https://nvidia.com/deprecated\">查看公告</a>"));
  });

  await t.test("8. NVIDIA API Usage Module (📊 NVIDIA 使用统计)", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("📊 <b>NVIDIA 使用统计</b>"));
    assert.ok(html.includes("24h　<code>官方未公开</code>"));
    assert.ok(html.includes("7d　 <code>官方未公开</code>"));
    assert.ok(html.includes("30d　<code>3.2M</code>"));
    assert.ok(html.includes("数据范围　<code>NVIDIA 官方公开累计统计</code>"));
  });

  await t.test("9. HTML Escaping Safety", () => {
    const mockSpecial: ModelDetail = {
      ...dsModel,
      display_name: "Special <Model> & Co 'Test' \"Quoted\"",
    };
    const html = formatModelDetailHtml(mockSpecial);
    assert.ok(html.includes("Special &lt;Model&gt; &amp; Co &#039;Test&#039; &quot;Quoted&quot;"));
  });

  await t.test("10. Official Links Module (🔗 官方资源)", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("🔗 <b>官方资源</b>"));
    assert.ok(html.includes("🌐 <a href=\"https://build.nvidia.com/deepseek-ai/deepseek-v4-flash-0731\">NVIDIA NIM</a>"));
    assert.ok(html.includes("🏠 <a href=\"https://www.deepseek.com\">模型官方网站</a>"));
  });

  await t.test("11. No Raw null or undefined Leakage", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(!html.includes("<code>null</code>"));
    assert.ok(!html.includes("<code>undefined</code>"));
    assert.ok(!html.includes("<b>null</b>"));
  });

  await t.test("12. Provider Menu & Empty Search Formatters", () => {
    const providers = store.getProviders();
    const pMenu = formatProviderMenuHtml(providers, store.getAllModels().length);
    assert.ok(pMenu.includes("NVIDIA Free Models"));
    assert.ok(pMenu.includes("选择 AI 厂商"));

    const empty = formatEmptySearchHtml("xyz-nonexistent");
    assert.ok(empty.includes("未找到匹配的模型"));
    assert.ok(empty.includes("xyz-nonexistent"));
  });

  await t.test("13. Expired Callback Index Graceful Alert Handling", async () => {
    let alertMsg = "";
    let isShowAlert = false;
    const mockBot: Partial<TelegramBotClient> = {
      answerCallbackQuery: async (id: string, options?: any) => {
        alertMsg = options?.text || "";
        isShowAlert = options?.show_alert || false;
        return true as any;
      },
    };

    const handler = new BotCommandHandler(mockBot as TelegramBotClient, store);

    await handler.handleCallbackQuery({
      id: "cb_123",
      from: { id: 1, is_bot: false, first_name: "Test" },
      data: "c:d:999999",
      message: {
        message_id: 100,
        chat: { id: 1, type: "private" },
        date: 12345,
      },
    });

    assert.ok(alertMsg.includes("该菜单已过期或模型目录已更新"));
    assert.equal(isShowAlert, true);
  });
});
