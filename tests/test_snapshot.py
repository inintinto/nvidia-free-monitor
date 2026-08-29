"""
Unit Tests for Raw Snapshot Evidence Layer (S1-C)
Tests atomic writing, SHA-256 integrity verification, path traversal defenses, and parser integration.
"""

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from src.catalog.build_parser import enrich_from_snapshot
from src.catalog.snapshot import (
    InvalidModelIdError,
    InvalidSourceUrlError,
    SnapshotCorruptedError,
    list_snapshots,
    load_snapshot,
    sanitize_model_id,
    save_snapshot,
    validate_source_url,
)


class TestSnapshotEvidenceLayer(unittest.TestCase):
    """Test suite for Raw Snapshot storage, validation, and offline reading."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_save_and_load_normal_snapshot(self):
        """1. Normal snapshot saving and loading with byte-for-byte fidelity."""
        model_id = "meta/llama-3.1-405b-instruct"
        sample_html = "<html><head><title>Meta Llama 3.1 405B</title></head><body><h1>405B Dense</h1></body></html>"
        fetched_at = "2026-08-26T10:00:00+00:00"

        saved = save_snapshot(
            model_id=model_id,
            raw_html=sample_html,
            fetched_at=fetched_at,
            base_dir=self.base_dir,
        )

        self.assertEqual(saved["model_id"], model_id)
        self.assertTrue(os.path.exists(saved["html_path"]))
        self.assertTrue(os.path.exists(saved["meta_path"]))

        # Load back
        loaded = load_snapshot(model_id=model_id, base_dir=self.base_dir)
        self.assertEqual(loaded["raw_html"], sample_html)
        self.assertEqual(loaded["metadata"]["model_id"], model_id)
        self.assertEqual(loaded["metadata"]["content_length"], len(sample_html.encode("utf-8")))

    def test_02_sha256_verification_integrity(self):
        """2. SHA-256 hash must be accurately calculated and stored."""
        model_id = "google/gemma-2-27b-it"
        sample_html = "<html><body>Gemma 2 27B Spec</body></html>"
        expected_hash = hashlib.sha256(sample_html.encode("utf-8")).hexdigest()

        saved = save_snapshot(model_id=model_id, raw_html=sample_html, base_dir=self.base_dir)
        self.assertEqual(saved["sha256"], expected_hash)

        loaded = load_snapshot(model_id=model_id, base_dir=self.base_dir)
        self.assertEqual(loaded["metadata"]["sha256"], expected_hash)

    def test_03_model_id_path_sanitization(self):
        """3. Slash in model_id must be safely converted to double underscores."""
        self.assertEqual(sanitize_model_id("meta/llama-3.1-405b"), "meta__llama-3.1-405b")
        self.assertEqual(sanitize_model_id("single-slug-model"), "single-slug-model")
        self.assertEqual(sanitize_model_id("baai/bge-m3"), "baai__bge-m3")

    def test_04_path_traversal_attack_blocked(self):
        """4. UNIX style path traversal attempts must be strictly blocked."""
        malicious_ids = [
            "../etc/passwd",
            "../../secret",
            "/absolute/root/path",
            "foo/../../bar",
            "meta/../../../etc",
        ]
        for mid in malicious_ids:
            with self.assertRaises(InvalidModelIdError):
                sanitize_model_id(mid)

    def test_05_windows_style_path_traversal_blocked(self):
        """5. Windows style path traversal and drive letters must be blocked."""
        malicious_ids = [
            "..\\..\\windows\\system32",
            "C:\\evil",
            "D:/work/secret",
            "foo\\bar",
            "model:name",
            "model*wildcard",
        ]
        for mid in malicious_ids:
            with self.assertRaises(InvalidModelIdError):
                sanitize_model_id(mid)

    def test_06_invalid_source_url_rejected(self):
        """6. Only official NVIDIA Build URLs must be permitted."""
        model_id = "meta/llama-3.1-405b-instruct"
        # Valid URL
        validate_source_url(model_id, "https://build.nvidia.com/meta/llama-3.1-405b-instruct")
        validate_source_url(model_id, "https://build.nvidia.com/meta/llama-3.1-405b-instruct/")

        # Invalid URLs
        invalid_urls = [
            "https://evil.com/meta/llama-3.1-405b-instruct",
            "http://build.nvidia.com/meta/llama-3.1-405b-instruct",
            "https://build.nvidia.com/other/model",
            "ftp://build.nvidia.com/meta/llama-3.1-405b-instruct",
        ]
        for url in invalid_urls:
            with self.assertRaises(InvalidSourceUrlError):
                validate_source_url(model_id, url)

    def test_07_empty_html_snapshot(self):
        """7. Empty string HTML should save safely without corruption."""
        model_id = "test/empty-model"
        save_snapshot(model_id=model_id, raw_html="", base_dir=self.base_dir)
        loaded = load_snapshot(model_id=model_id, base_dir=self.base_dir)
        self.assertEqual(loaded["raw_html"], "")
        self.assertEqual(loaded["metadata"]["content_length"], 0)

    def test_08_unicode_html_snapshot(self):
        """8. Multi-byte Unicode, Chinese, and Emoji content integrity."""
        model_id = "z-ai/glm-4"
        unicode_html = "<html><body>智谱 AI 旗舰模型 🧬 🚀 128k 上下文</body></html>"
        save_snapshot(model_id=model_id, raw_html=unicode_html, base_dir=self.base_dir)
        loaded = load_snapshot(model_id=model_id, base_dir=self.base_dir)
        self.assertEqual(loaded["raw_html"], unicode_html)

    def test_09_large_html_snapshot(self):
        """9. Larger HTML payloads (e.g. 500KB) atomic write and hash check."""
        model_id = "large/payload-model"
        large_html = "<!-- padding -->\n" + ("<div>Token Data Chunk</div>\n" * 20000)
        save_snapshot(model_id=model_id, raw_html=large_html, base_dir=self.base_dir)
        loaded = load_snapshot(model_id=model_id, base_dir=self.base_dir)
        self.assertEqual(len(loaded["raw_html"]), len(large_html))

    def test_10_missing_metadata_detection(self):
        """10. Missing metadata JSON file must raise SnapshotCorruptedError."""
        model_id = "test/missing-meta"
        saved = save_snapshot(model_id=model_id, raw_html="<html/>", base_dir=self.base_dir)
        os.remove(saved["meta_path"])

        with self.assertRaises(SnapshotCorruptedError):
            load_snapshot(model_id=model_id, base_dir=self.base_dir)

    def test_11_missing_html_file_detection(self):
        """11. Missing raw HTML file must raise SnapshotCorruptedError."""
        model_id = "test/missing-html"
        saved = save_snapshot(model_id=model_id, raw_html="<html/>", base_dir=self.base_dir)
        os.remove(saved["html_path"])

        with self.assertRaises(SnapshotCorruptedError):
            load_snapshot(model_id=model_id, base_dir=self.base_dir)

    def test_12_sha256_mismatch_corruption_detection(self):
        """12. Tampered HTML file must be detected and rejected immediately."""
        model_id = "meta/tampered-model"
        saved = save_snapshot(model_id=model_id, raw_html="Original Safe Content", base_dir=self.base_dir)
        
        # Tamper the HTML file
        with open(saved["html_path"], "w", encoding="utf-8") as f:
            f.write("Tampered Malicious Content")

        with self.assertRaises(SnapshotCorruptedError):
            load_snapshot(model_id=model_id, base_dir=self.base_dir)

    def test_13_corrupted_json_syntax_detection(self):
        """13. Invalid JSON metadata syntax raises SnapshotCorruptedError."""
        model_id = "meta/broken-json"
        saved = save_snapshot(model_id=model_id, raw_html="<html/>", base_dir=self.base_dir)
        
        with open(saved["meta_path"], "w", encoding="utf-8") as f:
            f.write("{broken_unclosed_json:")

        with self.assertRaises(SnapshotCorruptedError):
            load_snapshot(model_id=model_id, base_dir=self.base_dir)

    def test_14_atomic_write_no_temp_leftovers(self):
        """14. Atomic writing must not leave temporary files behind."""
        model_id = "meta/clean-write"
        save_snapshot(model_id=model_id, raw_html="<h1>Clean</h1>", base_dir=self.base_dir)
        
        model_dir = self.base_dir / sanitize_model_id(model_id)
        temp_files = list(model_dir.glob(".tmp_*"))
        self.assertEqual(len(temp_files), 0)

    def test_15_list_snapshots_ordering(self):
        """15. list_snapshots must return items ordered by timestamp descending."""
        model_id = "meta/llama-3.1-405b-instruct"
        save_snapshot(model_id=model_id, raw_html="Version 1", fetched_at="2026-08-25T10:00:00+00:00", base_dir=self.base_dir)
        save_snapshot(model_id=model_id, raw_html="Version 2", fetched_at="2026-08-26T10:00:00+00:00", base_dir=self.base_dir)

        snaps = list_snapshots(model_id=model_id, base_dir=self.base_dir)
        self.assertEqual(len(snaps), 2)
        self.assertTrue(snaps[0]["tag"] > snaps[1]["tag"])

    def test_16_parser_offline_integration_via_snapshot(self):
        """16. Parser can enrich model directly from snapshot evidence offline."""
        model_id = "meta/llama-3.1-405b-instruct"
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Meta Llama 3.1 405B Instruct Model - NVIDIA NIM</title></head>
        <body>
          <main>
            <h1>Llama 3.1 405B Instruct</h1>
            <p>405B Dense foundation model by Meta.</p>
            <div>Context Length: 128k</div>
          </main>
        </body>
        </html>
        """
        save_snapshot(model_id=model_id, raw_html=sample_html, base_dir=self.base_dir)
        
        parsed = enrich_from_snapshot(model_id=model_id, base_dir=self.base_dir)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["display_name"], "Meta Llama 3.1 405B Instruct")
        self.assertEqual(parsed["architecture"]["type"], "Dense")
        self.assertEqual(parsed["architecture"]["total_parameters"], "405B")
        self.assertEqual(parsed["context"]["length"], "128k")

    def test_17_ground_truth_isolation(self):
        """17. Raw snapshot operations must NEVER mutate data/model_catalog.json."""
        catalog_path = Path("data") / "model_catalog.json"
        original_content = None
        if catalog_path.exists():
            with open(catalog_path, "r", encoding="utf-8") as f:
                original_content = f.read()

        # Perform multiple snapshot operations
        model_id = "test/isolation-check"
        save_snapshot(model_id=model_id, raw_html="<div>Test</div>", base_dir=self.base_dir)
        load_snapshot(model_id=model_id, base_dir=self.base_dir)
        enrich_from_snapshot(model_id=model_id, base_dir=self.base_dir)

        if catalog_path.exists():
            with open(catalog_path, "r", encoding="utf-8") as f:
                current_content = f.read()
            self.assertEqual(original_content, current_content, "data/model_catalog.json was mutated!")


if __name__ == "__main__":
    unittest.main()
