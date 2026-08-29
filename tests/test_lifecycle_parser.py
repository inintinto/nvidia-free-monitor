"""
Unit Tests for Official Lifecycle Parser (Phase S2-F)
Validates Ground Truth extraction of deprecation, retirement, successors, and dates from official pages.
"""

import os
from pathlib import Path
import unittest

from src.catalog.lifecycle_parser import is_valid_iso_date, parse_official_lifecycle

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "nvidia_build"


def load_fixture(filename: str) -> str:
    path = FIXTURES_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestLifecycleParser(unittest.TestCase):
    """Test suite for lifecycle parsing logic."""

    def test_01_parse_deprecated_model_with_date_and_successor(self):
        """1. Deprecated model extracts status, date, and successor replacement model."""
        html_doc = load_fixture("deprecated_model_rsc.html")
        res = parse_official_lifecycle("meta/llama-2-70b-chat", html_doc)

        self.assertEqual(res["availability"], "deprecated")
        self.assertEqual(res["official_deprecation_date"], "2026-06-01")
        self.assertEqual(res["replacement_model_id"], "meta/llama-3.3-70b-instruct")
        self.assertEqual(res["confidence"], "high")
        self.assertIn("https://build.nvidia.com/meta/llama-2-70b-chat", res["deprecation_source_url"])

    def test_02_parse_retiring_model_with_sunset_date(self):
        """2. Retiring model extracts retiring status, sunset date, and successor."""
        html_doc = load_fixture("retiring_model_rsc.html")
        res = parse_official_lifecycle("google/gemma-7b-it", html_doc)

        self.assertEqual(res["availability"], "retiring")
        self.assertEqual(res["official_retirement_date"], "2026-10-01")
        self.assertEqual(res["replacement_model_id"], "google/gemma-2-9b-it")
        self.assertEqual(res["confidence"], "high")

    def test_03_parse_removed_discontinued_model(self):
        """3. Removed model extracts removed availability from official notices."""
        html_doc = load_fixture("removed_model_rsc.html")
        res = parse_official_lifecycle("legacy/discontinued-model", html_doc)

        self.assertEqual(res["availability"], "removed")
        self.assertEqual(res["confidence"], "high")

    def test_04_parse_normal_model_without_lifecycle_notices(self):
        """4. Normal model without deprecation notice returns None for all lifecycle fields."""
        html_doc = load_fixture("deepseek_v4_pro_0813_rsc.html")
        res = parse_official_lifecycle("deepseek-ai/deepseek-v4-pro-0813", html_doc)

        self.assertIsNone(res["availability"])
        self.assertIsNone(res["official_deprecation_date"])
        self.assertIsNone(res["replacement_model_id"])

    def test_05_empty_html_returns_none_values(self):
        """5. Empty HTML returns None for all lifecycle fields."""
        res = parse_official_lifecycle("empty/model", "")
        self.assertIsNone(res["availability"])
        self.assertIsNone(res["official_deprecation_date"])
        self.assertIsNone(res["replacement_model_id"])

    def test_06_date_validation_iso_format(self):
        """6. is_valid_iso_date strictly accepts YYYY-MM-DD and rejects invalid calendars."""
        self.assertTrue(is_valid_iso_date("2026-08-27"))
        self.assertTrue(is_valid_iso_date("2026-02-28"))
        self.assertFalse(is_valid_iso_date("2026-02-30"))  # Invalid day
        self.assertFalse(is_valid_iso_date("2026/08/27"))  # Wrong slash format
        self.assertFalse(is_valid_iso_date("invalid-date"))
        self.assertFalse(is_valid_iso_date(None))

    def test_07_successor_model_id_must_have_vendor_slash_format(self):
        """7. Replacement model ID must be formatted as vendor/model and cannot equal itself."""
        html_doc = """
        <main>
          <div class="nv-alert">Deprecated. Please use invalid_format instead.</div>
        </main>
        """
        res = parse_official_lifecycle("test/model", html_doc)
        self.assertIsNone(res["replacement_model_id"])

    def test_08_self_replacement_rejected(self):
        """8. Self replacement (model pointing to itself) is safely ignored."""
        html_doc = """
        <main>
          <div class="nv-alert">Deprecated. Recommended replacement: test/model</div>
        </main>
        """
        res = parse_official_lifecycle("test/model", html_doc)
        self.assertIsNone(res["replacement_model_id"])


if __name__ == "__main__":
    unittest.main()
