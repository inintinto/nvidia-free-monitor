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

test("Stage 3D: Model Detail Card 2.0 & Formatter Tests", async (t) => {
  const store = new CatalogStore(
    BUNDLED_CATALOG as any,
    BUNDLED_LIFECYCLE as any,
    BUNDLED_BASELINE as any
  );

  const dsModel = store.getModel("deepseek-ai/deepseek-v4-flash-0731")!;
  const llama405 = store.getModel("meta/llama-3.1-405b-instruct")!;
  const yiModel = store.getModel("01-ai/yi-large")!;

  await t.test("1. Chinese Detail Card Title & Header Structure", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("DeepSeek V4 Flash 0731"));
    assert.ok(html.includes("DeepSeek AI · DeepSeek-V4"));
    assert.ok(html.includes("当前可用"));
  });

  await t.test("2. Provider Branding Icon & Display", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("🐋 <b>DeepSeek V4 Flash 0731</b>"));
    assert.ok(html.includes("• <b>提供商：</b> 🐋 <code>DeepSeek AI</code>"));
  });

  await t.test("3. Tier Badge Formatter", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("👑 旗舰模型"));
  });

  await t.test("4. Capability Badges Formatter", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("💬 对话"));
    assert.ok(html.includes("🧠 推理"));
    assert.ok(html.includes("💻 编程"));
  });

  await t.test("5. Parameters Known Official (Llama 405B)", () => {
    const html = formatModelDetailHtml(llama405);
    assert.ok(html.includes("• <b>总参数量：</b> <code>405B</code>"));
    assert.ok(html.includes("• <b>激活参数：</b> <code>405B</code>"));
    assert.ok(html.includes("• <b>参数数据状态：</b> <code>官方公布</code>"));
  });

  await t.test("6. Parameters Unknown Graceful Handling (DeepSeek V4 Flash & Yi Large)", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("• <b>总参数量：</b> <code>官方未公开</code>"));
    assert.ok(html.includes("• <b>激活参数：</b> <code>官方未公开</code>"));
    assert.ok(html.includes("• <b>参数数据状态：</b> <code>官方未公开</code>"));

    const yiHtml = formatModelDetailHtml(yiModel);
    assert.ok(yiHtml.includes("• <b>总参数量：</b> <code>官方未公开</code>"));
  });

  await t.test("7. Context Known", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("• <b>上下文窗口：</b> <code>128k</code>"));
  });

  await t.test("8. Context Max Output Unknown Handling", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("• <b>最大输出：</b> <code>官方未公开</code>"));
  });

  await t.test("9. Lifecycle Active State", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("🟢 <code>当前可用 (Active)</code>"));
    assert.ok(html.includes("• <b>首次发现：</b> <code>2026-07-31</code>"));
  });

  await t.test("10. Lifecycle Observed Removed State", () => {
    const mockModel: ModelDetail = {
      ...dsModel,
      lifecycle: {
        ...dsModel.lifecycle,
        is_currently_active: false,
        removed_at: "2026-08-20T10:00:00+00:00",
      },
    };
    const html = formatModelDetailHtml(mockModel);
    assert.ok(html.includes("🟡 <b>监控观测下线 (Observed Removed)</b>"));
    assert.ok(html.includes("• <b>监控观测下线：</b> <code>2026-08-20 10:00:00 UTC</code>"));
  });

  await t.test("11. Lifecycle Officially Deprecated State", () => {
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
    assert.ok(html.includes("🔴 <b>官方已废弃 (Officially Deprecated)</b>"));
    assert.ok(html.includes("• <b>官方废弃日期：</b> <code>2026-08-15</code>"));
    assert.ok(html.includes("• <b>废弃公告：</b> <a href=\"https://nvidia.com/deprecated\">点击查看公告</a>"));
  });

  await t.test("12. API Calls Known (30d)", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("• <b>近 30 天：</b> <code>3.2M</code>"));
    assert.ok(html.includes("• <b>数据说明：</b> <code>NVIDIA 官方公开统计</code>"));
  });

  await t.test("13. API Calls Unknown Fields (24h/7d)", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("• <b>近 24 小时：</b> <code>官方未公开</code>"));
    assert.ok(html.includes("• <b>近 7 天：</b> <code>官方未公开</code>"));
  });

  await t.test("14. HTML Escaping Safety", () => {
    const mockSpecial: ModelDetail = {
      ...dsModel,
      display_name: "Special <Model> & Co 'Test' \"Quoted\"",
    };
    const html = formatModelDetailHtml(mockSpecial);
    assert.ok(html.includes("Special &lt;Model&gt; &amp; Co &#039;Test&#039; &quot;Quoted&quot;"));
  });

  await t.test("15. Official Links Rendering", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("🔗 <b>官方资源</b>"));
    assert.ok(html.includes("🌐 NVIDIA NIM 体验主页"));
    assert.ok(html.includes("🏠 模型官方网站"));
  });

  await t.test("16. Missing Optional Links Graceful Omission", () => {
    const mockNoLinks: ModelDetail = {
      ...dsModel,
      links: { nvidia: null, official: null, documentation: null, model_card: null },
      source_urls: {},
    };
    const html = formatModelDetailHtml(mockNoLinks);
    assert.ok(!html.includes("🔗 <b>官方资源</b>"));
  });

  await t.test("17. Source Confidence & Verification", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(html.includes("🔎 <b>数据来源</b>"));
    assert.ok(html.includes("• <b>架构数据：</b> <code>官方公布</code>"));
    assert.ok(html.includes("• <b>参数数据：</b> <code>未公开 / 未知</code>"));
    assert.ok(html.includes("• <b>最后核验：</b> <code>2026-08-23</code>"));
  });

  await t.test("18. No raw 'null' or 'undefined' Leakage", () => {
    const html = formatModelDetailHtml(dsModel);
    assert.ok(!html.includes("<code>null</code>"));
    assert.ok(!html.includes("<code>undefined</code>"));
    assert.ok(!html.includes("<b>null</b>"));
  });

  await t.test("19. /models Provider & Empty Search Formatters", () => {
    const providers = store.getProviders();
    const pMenu = formatProviderMenuHtml(providers, store.getAllModels().length);
    assert.ok(pMenu.includes("NVIDIA Free Models"));
    assert.ok(pMenu.includes("请选择模型提供商"));

    const empty = formatEmptySearchHtml("xyz-nonexistent");
    assert.ok(empty.includes("未找到匹配的模型"));
    assert.ok(empty.includes("xyz-nonexistent"));
  });

  await t.test("20. Expired Callback Index Graceful Alert Handling", async () => {
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

    // Test with invalid short index: 999999
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
