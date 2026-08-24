import test from "node:test";
import assert from "node:assert/strict";
import {
  formatModelButtonText,
  getCapabilityIcon,
  getCapabilityLabel,
  getModelBadge,
  getModelTitle,
  getProviderBrand,
  getProviderDisplayName,
  getProviderIcon,
  getProviderShortName,
  getStatusBadge,
  getTierBadge,
  getTierIcon,
  getTierLabel,
  getTierZhLabel,
  PROVIDER_REGISTRY,
  TIER_ICONS,
} from "../src/branding.ts";
import { CatalogStore } from "../src/catalog.ts";
import { BUNDLED_BASELINE, BUNDLED_CATALOG, BUNDLED_LIFECYCLE } from "../src/default_data.ts";

test("Stage 3 Visual Branding System Tests", async (t) => {
  const store = new CatalogStore(
    BUNDLED_CATALOG as any,
    BUNDLED_LIFECYCLE as any,
    BUNDLED_BASELINE as any
  );

  await t.test("1. All Providers have unique, stable, non-color-dot emojis", () => {
    const forbiddenDots = ["🟢", "🔵", "🟣", "🟡", "🔴", "⚪", "⚫", "🟤", "🟠"];
    const seenIcons = new Set<string>();

    for (const [id, brand] of Object.entries(PROVIDER_REGISTRY)) {
      assert.ok(brand.icon, `Provider ${id} must have an icon`);
      assert.ok(
        !forbiddenDots.includes(brand.icon),
        `Provider ${id} is using forbidden color dot ${brand.icon}`
      );
      assert.ok(
        !seenIcons.has(brand.icon),
        `Duplicate Provider icon detected: ${brand.icon} for ${id}`
      );
      seenIcons.add(brand.icon);
    }
  });

  await t.test("2. Provider Persona Verification", () => {
    assert.equal(getProviderIcon("deepseek-ai"), "🐋");
    assert.equal(getProviderIcon("nvidia"), "🦾");
    assert.equal(getProviderIcon("meta"), "♾️");
    assert.equal(getProviderIcon("google"), "🕊️");
    assert.equal(getProviderIcon("01-ai"), "🐯");
    assert.equal(getProviderIcon("baai"), "🧬");
    assert.equal(getProviderIcon("mistralai"), "🌪️");
    assert.equal(getProviderIcon("cohere"), "🪶");
    assert.equal(getProviderIcon("moonshotai"), "🌙");
    assert.equal(getProviderIcon("qwen"), "🐉");
    assert.equal(getProviderIcon("microsoft"), "🪟");
    assert.equal(getProviderIcon("openai"), "🌀");
  });

  await t.test("3. Unknown Provider Fallback", () => {
    const brand = getProviderBrand("custom-unregistered-vendor");
    assert.equal(brand.icon, "🌐");
    assert.equal(brand.name, "Custom Unregistered Vendor");
  });

  await t.test("4. Model Tier Emojis are independent and distinct", () => {
    assert.equal(getTierIcon("flagship"), "👑");
    assert.equal(getTierIcon("large"), "🏛️");
    assert.equal(getTierIcon("balanced"), "⚖️");
    assert.equal(getTierIcon("medium"), "⚙️");
    assert.equal(getTierIcon("fast"), "⚡");
    assert.equal(getTierIcon("small"), "🪶");
    assert.equal(getTierIcon("embedding"), "🧬");
    assert.equal(getTierIcon("specialized"), "🛠️");
    assert.equal(getTierIcon("unknown"), "📦");
    assert.equal(getTierIcon(null), "📦");
  });

  await t.test("5. Capability Emojis Verification", () => {
    assert.equal(getCapabilityIcon("Chat"), "💬");
    assert.equal(getCapabilityIcon("Reasoning"), "🧠");
    assert.equal(getCapabilityIcon("Coding"), "💻");
    assert.equal(getCapabilityIcon("Vision"), "👁️");
    assert.equal(getCapabilityIcon("Embedding"), "🧬");
    assert.equal(getCapabilityIcon("Audio"), "🎧");
    assert.equal(getCapabilityIcon("Multimodal"), "🎨");
    assert.equal(getCapabilityIcon("Tool Calling"), "🔧");
    assert.equal(getCapabilityIcon("Rerank"), "📊");
  });

  await t.test("6. Status Emojis used exclusively for lifecycle status", () => {
    assert.equal(getStatusBadge("active").icon, "🟢");
    assert.equal(getStatusBadge("observed_removed").icon, "🟡");
    assert.equal(getStatusBadge("deprecated").icon, "🔴");
    assert.equal(getStatusBadge("unknown").icon, "⚪");
  });

  await t.test("7. Model Title strict format: Provider Emoji + Tier Emoji + Model Name", () => {
    const dsModel = store.getModel("deepseek-ai/deepseek-v4-flash-0731")!;
    assert.equal(getModelTitle(dsModel), "🐋 👑 DeepSeek V4 Flash 0731");

    const llama405 = store.getModel("meta/llama-3.1-405b-instruct")!;
    assert.equal(getModelTitle(llama405), "♾️ 👑 Llama 3.1 405B Instruct");

    const gemma2 = store.getModel("google/gemma-2-27b-it")!;
    assert.equal(getModelTitle(gemma2), "🕊️ ⚙️ Gemma 2 27B IT");

    const bge = store.getModel("baai/bge-m3")!;
    assert.equal(getModelTitle(bge), "🧬 🧬 BGE-M3");
  });

  await t.test("8. Model Button Formatter format verification", () => {
    const dsModel = store.getModel("deepseek-ai/deepseek-v4-flash-0731")!;
    assert.equal(formatModelButtonText(dsModel), "🐋 👑 DeepSeek V4 Flash 0731");

    const coderModel = store.getModel("deepseek-ai/deepseek-coder-6.7b-instruct")!;
    assert.equal(formatModelButtonText(coderModel), "🐋 🪶 DeepSeek Coder 6.7B Instruct");

    const gemma2 = store.getModel("google/gemma-2-27b-it")!;
    assert.equal(formatModelButtonText(gemma2), "🕊️ ⚙️ Gemma 2 27B IT");
  });

  await t.test("9. Decoupled Speed Badges Verification", () => {
    const { getSpeedBadge } = require("../src/branding.ts");
    assert.equal(getSpeedBadge("fast"), "⚡ 高速");
    assert.equal(getSpeedBadge("standard"), "◽ 标准");
    assert.equal(getSpeedBadge("slow"), "🐢 慢速");
    assert.equal(getSpeedBadge("unknown"), "❔ 未知");
    assert.equal(getSpeedBadge(null), "❔ 未知");
  });
});
