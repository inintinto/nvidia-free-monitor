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
  getTierBadge,
  getTierIcon,
  getTierLabel,
  getTierZhLabel,
} from "../src/branding.ts";
import { CatalogStore } from "../src/catalog.ts";
import { BUNDLED_BASELINE, BUNDLED_CATALOG, BUNDLED_LIFECYCLE } from "../src/default_data.ts";

test("Stage 3B: Provider Branding & Model Classification Tests", async (t) => {
  const store = new CatalogStore(
    BUNDLED_CATALOG as any,
    BUNDLED_LIFECYCLE as any,
    BUNDLED_BASELINE as any
  );

  await t.test("1. DeepSeek Provider Branding", () => {
    const brand = getProviderBrand("deepseek-ai");
    assert.equal(brand.icon, "🐋");
    assert.equal(brand.name, "DeepSeek AI");
    assert.equal(brand.short_name, "DeepSeek");
    assert.equal(getProviderIcon("deepseek-ai"), "🐋");
    assert.equal(getProviderShortName("deepseek-ai"), "DeepSeek");
    assert.equal(getProviderDisplayName("deepseek-ai"), "DeepSeek AI");
  });

  await t.test("2. NVIDIA Provider Branding", () => {
    const brand = getProviderBrand("nvidia");
    assert.equal(brand.icon, "🟩");
    assert.equal(brand.name, "NVIDIA");
    assert.equal(brand.short_name, "NVIDIA");
    assert.equal(getProviderIcon("nvidia"), "🟩");
  });

  await t.test("3. Meta Provider Branding", () => {
    const brand = getProviderBrand("meta");
    assert.equal(brand.icon, "♾️");
    assert.equal(brand.name, "Meta");
    assert.equal(brand.short_name, "Meta");
    assert.equal(getProviderIcon("meta"), "♾️");
  });

  await t.test("4. Google Provider Branding", () => {
    const brand = getProviderBrand("google");
    assert.equal(brand.icon, "🔵");
    assert.equal(brand.name, "Google");
    assert.equal(brand.short_name, "Google");
  });

  await t.test("5. Unknown Provider Fallback", () => {
    const brand = getProviderBrand("custom-unregistered-vendor");
    assert.equal(brand.icon, "🌐");
    assert.equal(brand.name, "Custom Unregistered Vendor");
    assert.equal(brand.short_name, "Custom Unregistered Vendor");
  });

  await t.test("6. Tier Classification Icons & Labels", () => {
    assert.equal(getTierIcon("flagship"), "👑");
    assert.equal(getTierLabel("flagship"), "Flagship");
    assert.equal(getTierZhLabel("flagship"), "旗舰模型");

    assert.equal(getTierIcon("large"), "🏛️");
    assert.equal(getTierLabel("large"), "Large");

    assert.equal(getTierIcon("fast"), "⚡");
    assert.equal(getTierZhLabel("fast"), "高速模型");

    assert.equal(getTierIcon("embedding"), "🧬");
    assert.equal(getTierZhLabel("embedding"), "向量模型");

    assert.equal(getTierIcon("unknown"), "📦");
    assert.equal(getTierIcon(null), "📦");
  });

  await t.test("7. Capability Branding Icons & Labels", () => {
    assert.equal(getCapabilityIcon("Chat"), "💬");
    assert.equal(getCapabilityIcon("Reasoning"), "🧠");
    assert.equal(getCapabilityIcon("Coding"), "💻");
    assert.equal(getCapabilityIcon("Vision"), "👁️");
    assert.equal(getCapabilityIcon("Embedding"), "🧬");
    assert.equal(getCapabilityLabel("Reasoning"), "🧠 Reasoning");
  });

  await t.test("8. Model Badge and Button Formatter Test", () => {
    const dsModel = store.getModel("deepseek-ai/deepseek-v4-flash-0731");
    assert.ok(dsModel);

    const badge = getModelBadge(dsModel);
    assert.equal(badge, "🐋");

    const title = getModelTitle(dsModel);
    assert.equal(title, "🐋 DeepSeek V4 Flash 0731");

    const tierBadge = getTierBadge(dsModel);
    assert.equal(tierBadge, "👑 旗舰模型");

    const globalBtnText = formatModelButtonText(dsModel, false);
    assert.equal(globalBtnText, "🐋 DeepSeek V4 Flash 0731");

    const providerBtnText = formatModelButtonText(dsModel, true);
    assert.equal(providerBtnText, "👑 DeepSeek V4 Flash 0731");
  });

  await t.test("9. Llama 405B & BGE-M3 Classification Badges", () => {
    const llama405 = store.getModel("meta/llama-3.1-405b-instruct");
    assert.ok(llama405);
    assert.equal(getModelBadge(llama405), "♾️");

    const bge = store.getModel("baai/bge-m3");
    assert.ok(bge);
    assert.equal(getModelBadge(bge), "🧬");
  });
});
