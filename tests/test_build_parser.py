"""
Offline Fixture Tests for NVIDIA Build Parser (S1-B)
Ensures 100% offline testability, strict Ground Truth preservation, and zero guessing.
"""

import os
import unittest
import urllib.request
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

from src.catalog.build_parser import (
    enrich_single_model,
    extract_rsc_chunks,
    get_opener,
    parse_build_metadata,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "nvidia_build"


def load_fixture(filename: str) -> str:
    """Load an offline fixture file as string."""
    filepath = FIXTURES_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


class TestBuildParserOfflineFixtures(unittest.TestCase):
    """Test suite using local offline fixtures to verify parser reliability."""

    def test_01_llama_405b_rsc_payload(self):
        """1. Normal RSC payload for Llama 3.1 405B."""
        html_doc = load_fixture("llama_405b_rsc.html")
        data = parse_build_metadata("meta/llama-3.1-405b-instruct", html_doc)
        
        self.assertIsNotNone(data)
        self.assertEqual(data["model_id"], "meta/llama-3.1-405b-instruct")
        self.assertEqual(data["provider"]["id"], "meta")
        self.assertEqual(data["provider"]["name"], "Meta")
        self.assertEqual(data["display_name"], "Meta Llama 3.1 405B Instruct")
        self.assertEqual(data["architecture"]["type"], "Dense")
        self.assertEqual(data["architecture"]["total_parameters"], "405B")
        self.assertEqual(data["architecture"]["parameter_status"], "official")
        self.assertEqual(data["context"]["length"], "128k")
        self.assertEqual(data["context"]["status"], "official")
        self.assertEqual(data["links"]["nvidia"], "https://build.nvidia.com/meta/llama-3.1-405b-instruct")
        self.assertEqual(data["links"]["documentation"], "https://docs.api.nvidia.com/nim/meta/llama-3.1-405b-instruct")
        self.assertEqual(data["source_metadata"]["field_sources"]["architecture.total_parameters"], "NVIDIA Build")

    def test_02_gemma_27b_rsc_payload(self):
        """2. Normal RSC payload for Gemma 2 27B."""
        html_doc = load_fixture("gemma_27b_rsc.html")
        data = parse_build_metadata("google/gemma-2-27b-it", html_doc)
        
        self.assertIsNotNone(data)
        self.assertEqual(data["model_id"], "google/gemma-2-27b-it")
        self.assertEqual(data["provider"]["id"], "google")
        self.assertEqual(data["provider"]["name"], "Google")
        self.assertEqual(data["display_name"], "gemma-2-27b-it")
        self.assertEqual(data["architecture"]["total_parameters"], "27B")
        self.assertEqual(data["architecture"]["parameter_status"], "official")
        self.assertEqual(data["context"]["length"], "8k")

    def test_03_deepseek_flash_moe_payload(self):
        """3. DeepSeek MoE Flash model with speed heuristic and null parameters."""
        html_doc = load_fixture("deepseek_flash_rsc.html")
        data = parse_build_metadata("deepseek-ai/deepseek-v4-flash-0731", html_doc)
        
        self.assertIsNotNone(data)
        self.assertEqual(data["architecture"]["type"], "MoE")
        # Ensure parameters are None when page does not explicitly give count
        self.assertIsNone(data["architecture"]["total_parameters"])
        self.assertEqual(data["architecture"]["parameter_status"], "unknown")
        # Ensure speed heuristic is honestly labeled
        self.assertEqual(data["classification"]["speed"], "fast")
        self.assertEqual(data["source_metadata"]["field_sources"]["classification.speed"], "local_heuristic")

    def test_04_complete_metadata_extraction(self):
        """4. Complete metadata fixture containing context length, max output, parameters."""
        html_doc = load_fixture("complete_metadata_rsc.html")
        data = parse_build_metadata("mistralai/mistral-large-2-instruct", html_doc)
        
        self.assertIsNotNone(data)
        self.assertEqual(data["display_name"], "Mistral Large 2 123B Instruct")
        self.assertEqual(data["architecture"]["type"], "Dense")
        self.assertEqual(data["architecture"]["total_parameters"], "123B")
        self.assertEqual(data["context"]["length"], "128k")
        self.assertEqual(data["context"]["max_output"], "4096")
        self.assertIn("Coding", data["capabilities"])
        self.assertEqual(data["source_metadata"]["confidence"], "high")

    def test_05_missing_metadata_safely_returns_null(self):
        """5. Missing fields must remain None, never guessed or fabricated."""
        html_doc = load_fixture("missing_metadata_rsc.html")
        data = parse_build_metadata("test/experimental-model", html_doc)
        
        self.assertIsNotNone(data)
        self.assertEqual(data["display_name"], "experimental-model")
        self.assertIsNone(data["architecture"]["type"])
        self.assertIsNone(data["architecture"]["total_parameters"])
        self.assertEqual(data["architecture"]["parameter_status"], "unknown")
        self.assertIsNone(data["context"]["length"])
        self.assertIsNone(data["context"]["max_output"])
        self.assertEqual(data["context"]["status"], "unknown")

    def test_06_malformed_rsc_payload_does_not_crash(self):
        """6. Broken / truncated RSC payload must not crash the parser."""
        html_doc = load_fixture("malformed_rsc.html")
        # Must not raise an unhandled JSON/Parsing error
        data = parse_build_metadata("test/corrupted-page", html_doc)
        self.assertIsNotNone(data)
        self.assertEqual(data["display_name"], "corrupted-page")
        self.assertIsNone(data["architecture"]["total_parameters"])

    def test_07_fallback_html_without_rsc(self):
        """7. Static HTML fallback when React Server Components are absent."""
        html_doc = load_fixture("fallback_html.html")
        data = parse_build_metadata("meta/legacy-model-card", html_doc)
        
        self.assertIsNotNone(data)
        self.assertEqual(data["display_name"], "Legacy Model Card")
        self.assertEqual(data["links"]["nvidia"], "https://build.nvidia.com/meta/legacy-model-card")

    def test_08_empty_or_invalid_html_safely_returns_none(self):
        """8. Empty or non-string HTML inputs safely return None."""
        self.assertIsNone(parse_build_metadata("test/empty", ""))
        self.assertIsNone(parse_build_metadata("test/none", None))
        self.assertIsNone(parse_build_metadata("test/whitespace", "   \n\t  "))

    def test_09_malicious_xss_and_html_tag_sanitization(self):
        """9. HTML tags and malicious scripts must be stripped from display_name."""
        html_doc = load_fixture("malicious_html.html")
        data = parse_build_metadata("hacker/xss-model", html_doc)
        
        self.assertIsNotNone(data)
        # Verify no unescaped script tag in display_name
        self.assertNotIn("<script>", data["display_name"])
        self.assertNotIn("alert(", data["display_name"])
        self.assertEqual(data["display_name"], "Super Model & Co")

    def test_10_http_404_offline_mock(self):
        """10. HTTP 404 returns None and does not throw."""
        mock_fetcher = MagicMock(return_value=None)
        result = enrich_single_model("nonexistent/model", html_fetcher=mock_fetcher)
        self.assertIsNone(result)
        mock_fetcher.assert_called_once_with("nonexistent/model")

    def test_11_single_model_failure_does_not_break_batch(self):
        """11. Single model parse failure does not prevent enriching remaining models."""
        models = [
            "meta/llama-3.1-405b-instruct",
            "broken/model",
            "google/gemma-2-27b-it",
        ]
        
        def mock_fetcher(mid: str) -> Optional[str]:
            if mid == "meta/llama-3.1-405b-instruct":
                return load_fixture("llama_405b_rsc.html")
            elif mid == "broken/model":
                return None  # simulates 404
            elif mid == "google/gemma-2-27b-it":
                return load_fixture("gemma_27b_rsc.html")
            return None

        results = {}
        for mid in models:
            res = enrich_single_model(mid, html_fetcher=mock_fetcher)
            if res:
                results[mid] = res

        self.assertEqual(len(results), 2)
        self.assertIn("meta/llama-3.1-405b-instruct", results)
        self.assertIn("google/gemma-2-27b-it", results)
        self.assertNotIn("broken/model", results)

    def test_12_no_guessing_parameter_safety(self):
        """12. Strict Ground Truth: Parameters must NOT be guessed from model_id."""
        # A model named something like 'foo-405b-bar' whose HTML has NO parameter specs
        minimal_html = "<html><head><title>foo-405b-bar - NVIDIA NIM</title></head><body><main><h1>Foo</h1></main></body></html>"
        data = parse_build_metadata("custom/foo-405b-bar", minimal_html)
        
        self.assertIsNotNone(data)
        # Even though 405b was in slug, page main content had no parameter statement
        self.assertIsNone(data["architecture"]["total_parameters"])
        self.assertEqual(data["architecture"]["parameter_status"], "unknown")

    def test_13_no_guessing_context_safety(self):
        """13. Strict Ground Truth: Context length must NOT be guessed."""
        minimal_html = "<html><head><title>Gemma 2 - NVIDIA NIM</title></head><body><main><h1>Gemma 2</h1></main></body></html>"
        data = parse_build_metadata("google/gemma-2-9b", minimal_html)
        
        self.assertIsNotNone(data)
        self.assertIsNone(data["context"]["length"])
        self.assertEqual(data["context"]["status"], "unknown")

    def test_14_source_metadata_field_sources_accuracy(self):
        """14. field_sources must accurately distinguish NVIDIA Build vs local_heuristic."""
        html_doc = load_fixture("llama_405b_rsc.html")
        data = parse_build_metadata("meta/llama-3.1-405b-instruct", html_doc)
        
        fs = data["source_metadata"]["field_sources"]
        self.assertEqual(fs.get("display_name"), "NVIDIA Build")
        self.assertEqual(fs.get("architecture.total_parameters"), "NVIDIA Build")
        self.assertEqual(fs.get("context.length"), "NVIDIA Build")
        self.assertEqual(fs.get("classification.speed"), "local_heuristic")

    def test_15_rsc_chunk_extraction_utility(self):
        """15. Unit test for extract_rsc_chunks regex unescaping."""
        sample_html = '<script>self.__next_f.push([1, "1:{\\"key\\":\\"value\\"}"])</script>'
        chunks = extract_rsc_chunks(sample_html)
        self.assertEqual(len(chunks), 1)
        self.assertIn('"key":"value"', chunks[0])

    def test_16_deepseek_v4_pro_0813_offline_fixture(self):
        """16. DeepSeek V4 Pro 0813: MoE, 1.65T, 1M context, Text/Text modal, non-vision."""
        html_doc = load_fixture("deepseek_v4_pro_0813_rsc.html")
        data = parse_build_metadata("deepseek-ai/deepseek-v4-pro-0813", html_doc)

        self.assertIsNotNone(data)
        self.assertEqual(data["architecture"]["type"], "MoE")
        self.assertEqual(data["architecture"]["total_parameters"], "1.65T")
        self.assertEqual(data["architecture"]["active_parameters"], "49B")
        self.assertEqual(data["architecture"]["parameter_status"], "official")
        self.assertEqual(data["context"]["length"], "1M")
        self.assertEqual(data["context"]["status"], "official")
        self.assertEqual(data["classification"]["model_type"], "chat")
        self.assertIn("Coding", data["capabilities"])
        self.assertIn("Reasoning", data["capabilities"])
        self.assertNotIn("Vision", data["capabilities"])
        self.assertEqual(data["source_metadata"]["field_sources"]["architecture.total_parameters"], "NVIDIA Build")
        self.assertEqual(data["source_metadata"]["field_sources"]["context.length"], "NVIDIA Build")

    def test_17_get_opener_no_proxy_env(self):
        """17. get_opener returns direct OpenerDirector without proxy handlers when no proxy env is set."""
        with patch.dict(os.environ, {}, clear=True):
            opener = get_opener()
            self.assertIsNotNone(opener)
            # Verify no ProxyHandler is added to handlers
            has_proxy_handler = any(isinstance(h, urllib.request.ProxyHandler) for h in opener.handlers)
            self.assertFalse(has_proxy_handler)

    def test_18_get_opener_with_proxy_env(self):
        """18. get_opener configures standard ProxyHandler when HTTP_PROXY / HTTPS_PROXY is present."""
        test_env = {"HTTP_PROXY": "http://proxy.test:8080", "HTTPS_PROXY": "http://proxy.test:8080"}
        with patch.dict(os.environ, test_env, clear=True):
            opener = get_opener()
            self.assertIsNotNone(opener)
            proxy_handlers = [h for h in opener.handlers if isinstance(h, urllib.request.ProxyHandler)]
            self.assertEqual(len(proxy_handlers), 1)
            self.assertEqual(proxy_handlers[0].proxies.get("http"), "http://proxy.test:8080")


if __name__ == "__main__":
    unittest.main()
