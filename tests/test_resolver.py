import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.catalog.catalog_manager import CatalogManager
from src.catalog.resolver import ModelResolver, normalize_text
from src.catalog.schema import ModelDetail, UsageStats


class TestModelResolver(unittest.TestCase):

    def setUp(self):
        """Set up CatalogManager and ModelResolver with current data repository."""
        self.catalog_mgr = CatalogManager()
        self.resolver = ModelResolver(self.catalog_mgr)

    # 1. Exact Model ID
    def test_01_exact_model_id(self):
        res = self.resolver.resolve("deepseek-ai/deepseek-v4-flash-0731")
        self.assertEqual(res.match_type, "EXACT")
        self.assertEqual(len(res.matched_models), 1)
        self.assertEqual(res.matched_models[0].model_id, "deepseek-ai/deepseek-v4-flash-0731")

    # 2. Alias Match
    def test_02_alias_match(self):
        res = self.resolver.resolve("DS V4 Flash")
        self.assertEqual(res.match_type, "EXACT")
        self.assertEqual(res.matched_models[0].model_id, "deepseek-ai/deepseek-v4-flash-0731")

        res_nemotron = self.resolver.resolve("nemotron")
        self.assertEqual(res_nemotron.match_type, "EXACT")
        self.assertEqual(res_nemotron.matched_models[0].model_id, "nvidia/nemotron-4-340b-instruct")

    # 3. Display Name Match
    def test_03_display_name_match(self):
        res = self.resolver.resolve("DeepSeek V4 Flash 0731")
        self.assertEqual(res.match_type, "EXACT")
        self.assertEqual(res.matched_models[0].model_id, "deepseek-ai/deepseek-v4-flash-0731")

    # 4. Slug Match
    def test_04_slug_match(self):
        res = self.resolver.resolve("deepseek-v4-flash-0731")
        self.assertEqual(res.match_type, "EXACT")
        self.assertEqual(res.matched_models[0].model_id, "deepseek-ai/deepseek-v4-flash-0731")

    # 5. Token Fuzzy Match
    def test_05_token_fuzzy_match(self):
        res = self.resolver.resolve("deepseek v4 flash")
        self.assertIn(res.match_type, ["EXACT", "MULTIPLE"])
        self.assertEqual(res.matched_models[0].model_id, "deepseek-ai/deepseek-v4-flash-0731")

    # 6. Multiple Results
    def test_06_multiple_results(self):
        # Querying "llama" should match Llama 3.3 and Llama 3.1 405B
        res = self.resolver.resolve("llama")
        self.assertEqual(res.match_type, "MULTIPLE")
        self.assertGreaterEqual(res.total_matches, 2)
        model_ids = [m.model_id for m in res.matched_models]
        self.assertIn("meta/llama-3.3-70b-instruct", model_ids)

    # 7. Empty Result
    def test_07_empty_result(self):
        res = self.resolver.resolve("unknown-non-existent-model-xyz-999")
        self.assertEqual(res.match_type, "EMPTY")
        self.assertEqual(len(res.matched_models), 0)
        self.assertEqual(res.total_matches, 0)

    # 8. Provider Filter
    def test_08_provider_filter(self):
        # Resolve under DeepSeek provider
        res = self.resolver.resolve("", provider="deepseek-ai")
        self.assertGreaterEqual(res.total_matches, 2)
        for m in res.matched_models:
            self.assertEqual(m.provider_id, "deepseek-ai")

        # Resolve query with provider filter
        res_filter = self.resolver.resolve("coder", provider="deepseek-ai")
        self.assertEqual(res_filter.match_type, "EXACT")
        self.assertEqual(res_filter.matched_models[0].model_id, "deepseek-ai/deepseek-coder-6.7b-instruct")

    # 9. Capability Filter
    def test_09_capability_filter(self):
        res_coding = self.resolver.resolve("", capability="Coding")
        self.assertGreaterEqual(res_coding.total_matches, 1)
        for m in res_coding.matched_models:
            self.assertIn("Coding", m.capabilities)

        res_embed = self.resolver.resolve("", capability="Embedding")
        embed_ids = [m.model_id for m in res_embed.matched_models]
        self.assertIn("baai/bge-m3", embed_ids)

    # 10. Case Insensitivity
    def test_10_case_insensitivity(self):
        res_lower = self.resolver.resolve("deepseek-ai/deepseek-v4-flash-0731")
        res_upper = self.resolver.resolve("DEEPSEEK-AI/DEEPSEEK-V4-FLASH-0731")
        res_mixed = self.resolver.resolve("DeEpSeEk-Ai/DeEpSeEk-V4-fLaSh-0731")

        self.assertEqual(res_lower.match_type, "EXACT")
        self.assertEqual(res_upper.match_type, "EXACT")
        self.assertEqual(res_mixed.match_type, "EXACT")
        self.assertEqual(res_lower.matched_models[0].model_id, res_upper.matched_models[0].model_id)

    # 11. Extra Whitespace Handling
    def test_11_extra_whitespace(self):
        res_spaces = self.resolver.resolve("   ds    v4   flash   0731   ")
        self.assertEqual(res_spaces.match_type, "EXACT")
        self.assertEqual(res_spaces.matched_models[0].model_id, "deepseek-ai/deepseek-v4-flash-0731")

    # 12. Punctuation & Normalization
    def test_12_normalization(self):
        self.assertEqual(normalize_text("DS_V4-Flash/0731!"), "ds v4 flash 0731")
        res = self.resolver.resolve("ds-v4_flash.0731")
        self.assertEqual(res.match_type, "EXACT")
        self.assertEqual(res.matched_models[0].model_id, "deepseek-ai/deepseek-v4-flash-0731")

    # 13. Unregistered baseline model resolution (Graceful Fallback)
    def test_13_unregistered_model_fallback(self):
        # Test a model in baseline that might not be explicitly curated in catalog.json
        res = self.resolver.resolve("adept/fuyu-8b")
        self.assertEqual(res.match_type, "EXACT")
        m = res.matched_models[0]
        self.assertEqual(m.model_id, "adept/fuyu-8b")
        self.assertEqual(m.platform, "NVIDIA NIM")
        self.assertIsNotNone(m.display_name)
        self.assertEqual(m.provider_id, "adept")

    # 14. Missing Lifecycle Fields Safety
    def test_14_missing_lifecycle_safety(self):
        detail = ModelDetail.from_dict("test-org/dummy-model", catalog_data={}, lifecycle_data=None)
        self.assertIsNotNone(detail.lifecycle)
        self.assertTrue(detail.lifecycle.is_currently_active)
        self.assertIsNone(detail.lifecycle.first_seen)
        self.assertEqual(detail.lifecycle.official_lifecycle.official_status, "active")

    # 15. Null Usage Safety & Specification
    def test_15_null_usage_safety(self):
        usage = UsageStats.from_dict(None)
        self.assertIsNone(usage.api_calls_24h)
        self.assertIsNone(usage.api_calls_daily)
        self.assertIsNone(usage.api_calls_7d)
        self.assertIsNone(usage.api_calls_30d)
        self.assertEqual(usage.usage_source, "NVIDIA API Catalog Public Aggregate")

    # 16. Stage 3B Python Branding System
    def test_16_branding_system(self):
        from src.catalog.branding import (
            get_provider_brand,
            get_provider_icon,
            get_tier_icon,
            get_speed_badge,
            get_capability_icon,
        )
        self.assertEqual(get_provider_icon("deepseek-ai"), "🐋")
        self.assertEqual(get_provider_icon("nvidia"), "🦾")
        self.assertEqual(get_provider_icon("meta"), "♾️")
        self.assertEqual(get_provider_icon("google"), "🕊️")
        self.assertEqual(get_provider_icon("01-ai"), "🐯")
        self.assertEqual(get_provider_icon("unknown-org"), "🌐")
        self.assertEqual(get_tier_icon("flagship"), "👑")
        self.assertEqual(get_tier_icon("small"), "🪶")
        self.assertEqual(get_tier_icon("embedding"), "🧬")
        self.assertEqual(get_speed_badge("fast"), "⚡ 高速")
        self.assertEqual(get_speed_badge("standard"), "◽ 标准")
        self.assertEqual(get_capability_icon("Reasoning"), "🧠")
        self.assertEqual(get_capability_icon("Coding"), "💻")


if __name__ == "__main__":
    unittest.main()
