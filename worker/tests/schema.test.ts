import test from "node:test";
import assert from "node:assert/strict";
import { CatalogStore } from "../src/catalog.ts";
import { BUNDLED_BASELINE, BUNDLED_CATALOG, BUNDLED_LIFECYCLE } from "../src/default_data.ts";

test("Stage 3A: Model Metadata Schema & Catalog Tests", async (t) => {
  const store = new CatalogStore(
    BUNDLED_CATALOG as any,
    BUNDLED_LIFECYCLE as any,
    BUNDLED_BASELINE as any
  );

  await t.test("1. Full Model Schema Test (DeepSeek V4 Flash 0731)", () => {
    const model = store.getModel("deepseek-ai/deepseek-v4-flash-0731");
    assert.ok(model, "Model should exist in store");

    // Identity
    assert.equal(model.model_id, "deepseek-ai/deepseek-v4-flash-0731");
    assert.equal(model.display_name, "DeepSeek V4 Flash 0731");
    assert.equal(model.slug, "deepseek-v4-flash-0731");
    assert.equal(model.platform, "NVIDIA NIM");

    // Provider
    assert.equal(model.provider_info.id, "deepseek-ai");
    assert.equal(model.provider_info.name, "DeepSeek AI");
    assert.equal(model.provider, "DeepSeek AI");

    // Classification
    assert.equal(model.classification.family, "DeepSeek-V4");
    assert.equal(model.classification.tier, "flagship");
    assert.equal(model.classification.model_type, "chat");
    assert.equal(model.classification.speed, "fast");

    // Architecture & Parameters (Unknown parameter distinction)
    assert.equal(model.arch_info.type, "MoE");
    assert.equal(model.arch_info.total_parameters, null);
    assert.equal(model.arch_info.active_parameters, null);
    assert.equal(model.arch_info.parameter_status, "unknown");

    // Context
    assert.equal(model.context_info.length, "128k");
    assert.equal(model.context_info.status, "official");

    // Capabilities
    assert.deepEqual(model.capabilities, ["Chat", "Reasoning", "Coding"]);

    // Lifecycle
    assert.equal(model.lifecycle.first_seen, "2026-07-31T08:00:00Z");
    assert.equal(model.lifecycle.removed_at, null);
    assert.equal(model.lifecycle.official_lifecycle.official_status, "active");
    assert.equal(model.lifecycle.official_lifecycle.official_deprecation_date, null);

    // Endpoint API Calls
    assert.equal(model.usage.api_calls_30d, "3.2M");
    assert.equal(model.usage.api_calls_24h, null);
    assert.equal(model.usage.api_calls_daily, null);
    assert.equal(model.usage.api_calls_7d, null);

    // Links
    assert.equal(model.links.nvidia, "https://build.nvidia.com/deepseek-ai/deepseek-v4-flash-0731");
    assert.equal(model.links.official, "https://www.deepseek.com");

    // Source Metadata
    assert.equal(model.source_metadata.confidence, "high");
    assert.equal(model.source_metadata.field_sources.parameters, "unknown");
    assert.equal(model.source_metadata.field_sources.architecture, "official");
  });

  await t.test("2. Total and Active Parameters Official Distinction (Llama 3.1 405B)", () => {
    const model = store.getModel("meta/llama-3.1-405b-instruct");
    assert.ok(model);
    assert.equal(model.arch_info.type, "Dense");
    assert.equal(model.arch_info.total_parameters, "405B");
    assert.equal(model.arch_info.active_parameters, "405B");
    assert.equal(model.arch_info.parameter_status, "official");
    assert.equal(model.classification.tier, "flagship");
  });

  await t.test("3. Unknown Parameters & Null Handling (Yi Large)", () => {
    const model = store.getModel("01-ai/yi-large");
    assert.ok(model);
    assert.equal(model.arch_info.total_parameters, null);
    assert.equal(model.arch_info.active_parameters, null);
    assert.equal(model.arch_info.parameter_status, "unknown");
    assert.equal(model.source_metadata.field_sources.parameters, "unknown");
  });

  await t.test("4. Embedding Model Classification (BGE-M3)", () => {
    const model = store.getModel("baai/bge-m3");
    assert.ok(model);
    assert.equal(model.classification.tier, "embedding");
    assert.equal(model.classification.model_type, "embedding");
    assert.equal(model.arch_info.type, "Embedding");
    assert.equal(model.arch_info.total_parameters, "570M");
  });

  await t.test("5. Unregistered Baseline Model Fallback Graceful Handling", () => {
    // A model only present in baseline (unregistered)
    const model = store.getModel("unregistered/new-ai-model");
    if (model) {
      assert.equal(model.provider_info.id, "unregistered");
      assert.equal(model.provider_info.name, "Unregistered");
      assert.equal(model.arch_info.total_parameters, null);
      assert.equal(model.arch_info.parameter_status, "unknown");
      assert.equal(model.context_info.length, null);
      assert.equal(model.context_info.status, "unknown");
      assert.equal(model.usage.api_calls_30d, null);
    }
  });

  await t.test("6. Lifecycle Dual-Date Semantic Separation Test", () => {
    const mockStore = new CatalogStore(
      {
        models: {
          "test/deprecated-model": {
            display_name: "Test Deprecated Model",
            lifecycle: {
              availability: "removed",
              removed_at: "2026-08-20T12:00:00Z",
              official_deprecation_date: "2026-08-15T00:00:00Z",
              deprecation_source_url: "https://nvidia.com/notice",
            },
          },
        },
      },
      {}
    );

    const model = mockStore.getModel("test/deprecated-model");
    assert.ok(model);
    assert.equal(model.lifecycle.removed_at, "2026-08-20T12:00:00Z");
    assert.equal(model.lifecycle.official_lifecycle.official_deprecation_date, "2026-08-15T00:00:00Z");
    assert.equal(model.lifecycle.official_lifecycle.deprecation_source_url, "https://nvidia.com/notice");
    assert.equal(model.lifecycle.is_currently_active, false);
  });
});
