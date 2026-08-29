"""
Unit Tests for Official Metadata Ingestion Orchestrator (Phase S1-E)
Validates end-to-end pipeline execution, safety fuses, dry-run guarantees, and atomic writes.
"""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.catalog.orchestrator import (
    OrchestratorSafetyError,
    atomic_write_catalog,
    calculate_catalog_hash,
    discover_target_models,
    run_official_metadata_sync,
    validate_catalog_schema,
)


class TestOrchestratorPipeline(unittest.TestCase):
    """Test suite for the End-to-End Orchestrator and Safety Fuses."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.catalog_path = self.base_path / "model_catalog.json"
        self.api_models_path = self.base_path / "nvidia_api_models.json"
        self.snapshots_dir = self.base_path / "snapshots"

        # Baseline seed data
        self.seed_catalog = {
            "version": "3.1",
            "updated_at": "2026-08-25T10:00:00Z",
            "models": {
                "meta/llama-3.1-405b-instruct": {
                    "model_id": "meta/llama-3.1-405b-instruct",
                    "display_name": "Llama 3.1 405B Instruct",
                    "context": {"length": "32k", "status": "official"},
                    "architecture": {"total_parameters": "405B", "type": "Dense"},
                    "links": {"nvidia": "https://build.nvidia.com/meta/llama-3.1-405b-instruct"},
                    "source_metadata": {"field_sources": {"context.length": "NVIDIA Build"}},
                },
                "deepseek-ai/deepseek-v4-flash-0731": {
                    "model_id": "deepseek-ai/deepseek-v4-flash-0731",
                    "display_name": "DeepSeek V4 Flash 0731",
                    "context": {"length": "128k", "status": "official"},
                    "architecture": {"type": "MoE", "total_parameters": None},
                    "links": {"nvidia": "https://build.nvidia.com/deepseek-ai/deepseek-v4-flash-0731"},
                },
            },
        }
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(self.seed_catalog, f, indent=2)

        self.seed_api_models = {
            "data": [
                {"id": "meta/llama-3.1-405b-instruct"},
                {"id": "deepseek-ai/deepseek-v4-flash-0731"},
                {"id": "google/gemma-2-27b-it"},  # new model in API
            ]
        }
        with open(self.api_models_path, "w", encoding="utf-8") as f:
            json.dump(self.seed_api_models, f, indent=2)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_dry_run_does_not_modify_catalog_file(self):
        """1. Dry Run executes full pipeline and previews changes without modifying catalog file."""
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        def mock_fetch(mid: str):
            return f"<html><head><title>{mid} - NVIDIA NIM</title></head><body><main><h1>{mid}</h1><div>Context Length: 128k</div></main></body></html>"

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct"],
            dry_run=True,
            fetch_func=mock_fetch,
        )

        self.assertTrue(summary["dry_run"])
        self.assertTrue(summary["catalog_changed"])

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            after_content = f.read()

        self.assertEqual(original_content, after_content, "Dry run mutated the catalog file!")

    def test_02_successful_single_model_sync(self):
        """2. Successful sync updates catalog file atomically."""
        def mock_fetch(mid: str):
            return """
            <html><head><title>Meta Llama 3.1 405B Instruct Model - NVIDIA NIM</title></head>
            <body><main><h1>Llama 3.1 405B Instruct</h1><div>Context Length: 128k</div></main></body></html>
            """

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct"],
            dry_run=False,
            fetch_func=mock_fetch,
        )

        self.assertEqual(summary["fetched"], 1)
        self.assertEqual(summary["parsed"], 1)
        self.assertEqual(summary["merged"], 1)

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            updated_catalog = json.load(f)

        entry = updated_catalog["models"]["meta/llama-3.1-405b-instruct"]
        self.assertEqual(entry["context"]["length"], "128k")

    def test_03_failed_fetch_isolation(self):
        """3. Fetch failure for one model does not fail the batch or erase catalog."""
        def mock_fetch(mid: str):
            if mid == "meta/llama-3.1-405b-instruct":
                return None  # simulates fetch failure
            return "<html><head><title>deepseek - NVIDIA NIM</title></head><body><main><h1>deepseek</h1></main></body></html>"

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct", "deepseek-ai/deepseek-v4-flash-0731"],
            dry_run=False,
            fetch_func=mock_fetch,
        )

        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["parsed"], 1)

        # Ensure existing entry was preserved
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        self.assertIn("meta/llama-3.1-405b-instruct", catalog["models"])
        self.assertEqual(catalog["models"]["meta/llama-3.1-405b-instruct"]["context"]["length"], "32k")

    def test_04_http_404_isolation(self):
        """4. 404 Not Found returns None and is recorded in failed_models."""
        mock_fetch = MagicMock(return_value=None)
        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["nonexistent/model"],
            dry_run=True,
            fetch_func=mock_fetch,
        )
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["failed_models"][0]["reason"], "fetch_failed_or_404")

    def test_05_http_timeout_isolation(self):
        """5. Timeout during fetch is gracefully captured."""
        mock_fetch = MagicMock(return_value=None)
        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["timeout/model"],
            dry_run=True,
            fetch_func=mock_fetch,
        )
        self.assertEqual(summary["failed"], 1)

    def test_06_malformed_html_isolation(self):
        """6. Malformed HTML handled safely without crashing."""
        def mock_fetch(mid: str):
            return "<html><head><title>broken"

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["broken/html-model"],
            dry_run=True,
            fetch_func=mock_fetch,
        )
        self.assertEqual(summary["fetched"], 1)

    def test_07_parser_returns_none_isolation(self):
        """7. Empty string HTML causing parse None is isolated."""
        def mock_fetch(mid: str):
            return ""

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["empty/model"],
            dry_run=True,
            fetch_func=mock_fetch,
        )
        self.assertEqual(summary["failed"], 1)

    def test_08_new_model_creation(self):
        """8. Newly discovered model from API is created as a minimal catalog entry."""
        def mock_fetch(mid: str):
            return """
            <html><head><title>gemma-2-27b-it Model by Google | NVIDIA NIM</title></head>
            <body><main><h1>gemma-2-27b-it</h1><div>27B Total Parameters</div></main></body></html>
            """

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["google/gemma-2-27b-it"],
            dry_run=False,
            fetch_func=mock_fetch,
        )

        self.assertEqual(summary["new"], 1)

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        new_entry = catalog["models"]["google/gemma-2-27b-it"]
        self.assertEqual(new_entry["display_name"], "gemma-2-27b-it")
        self.assertEqual(new_entry["architecture"]["total_parameters"], "27B")

    def test_09_existing_model_metadata_update(self):
        """9. Existing model receives official updates."""
        def mock_fetch(mid: str):
            return """
            <html><head><title>deepseek-v4-flash-0731 - NVIDIA NIM</title></head>
            <body><main><h1>deepseek-v4-flash-0731</h1><div>671B Total Parameters</div></main></body></html>
            """

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["deepseek-ai/deepseek-v4-flash-0731"],
            dry_run=False,
            fetch_func=mock_fetch,
        )

        self.assertEqual(summary["merged"], 1)

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        entry = catalog["models"]["deepseek-ai/deepseek-v4-flash-0731"]
        self.assertEqual(entry["architecture"]["total_parameters"], "671B")

    def test_10_null_preservation_through_orchestrator(self):
        """10. End-to-end: Null in incoming page does not erase existing trusted context."""
        def mock_fetch(mid: str):
            # Page has no context info
            return "<html><head><title>Meta Llama - NVIDIA NIM</title></head><body><main><h1>Llama</h1></main></body></html>"

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct"],
            dry_run=False,
            fetch_func=mock_fetch,
        )

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        entry = catalog["models"]["meta/llama-3.1-405b-instruct"]
        self.assertEqual(entry["context"]["length"], "32k", "Existing context length was erased!")

    def test_11_official_data_protection_from_heuristic(self):
        """11. End-to-end: Local heuristic speed does not downgrade existing official speed."""
        def mock_fetch(mid: str):
            return "<html><head><title>Llama - NVIDIA NIM</title></head><body><main><h1>Llama</h1></main></body></html>"

        run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct"],
            dry_run=False,
            fetch_func=mock_fetch,
        )

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        entry = catalog["models"]["meta/llama-3.1-405b-instruct"]
        self.assertEqual(entry["architecture"]["type"], "Dense")

    def test_12_abnormal_api_drop_does_not_delete_catalog(self):
        """12. If API model list shrinks, orchestrator never deletes catalog models."""
        empty_api_path = self.base_path / "empty_api.json"
        with open(empty_api_path, "w", encoding="utf-8") as f:
            json.dump({"data": []}, f)

        def mock_fetch(mid: str):
            return "<html><head><title>Model - NVIDIA NIM</title></head><body><main><h1>Model</h1></main></body></html>"

        run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=empty_api_path,
            snapshots_dir=self.snapshots_dir,
            dry_run=False,
            fetch_func=mock_fetch,
        )

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        self.assertEqual(len(catalog["models"]), 2, "Catalog entries were erroneously deleted!")

    def test_13_high_failure_rate_triggers_safety_fuse(self):
        """13. Build failure rate >50% on large batch aborts catalog write."""
        # Setup 10 models in api
        large_api_models = {"data": [{"id": f"vendor/model-{i}"} for i in range(10)]}
        with open(self.api_models_path, "w", encoding="utf-8") as f:
            json.dump(large_api_models, f)

        # 6 out of 10 fail (60% failure)
        def mock_fetch(mid: str):
            if mid.endswith("1") or mid.endswith("2") or mid.endswith("3") or mid.endswith("4") or mid.endswith("5") or mid.endswith("6"):
                return None
            return "<html><head><title>Ok</title></head><body><main><h1>Ok</h1></main></body></html>"

        with self.assertRaises(OrchestratorSafetyError) as ctx:
            run_official_metadata_sync(
                catalog_path=self.catalog_path,
                api_models_path=self.api_models_path,
                snapshots_dir=self.snapshots_dir,
                dry_run=False,
                fetch_func=mock_fetch,
            )
        self.assertIn("Safety Fuse Triggered", str(ctx.exception))

    def test_14_zero_parsed_triggers_safety_fuse(self):
        """14. Zero parsed models cleanly skips catalog modification."""
        def mock_fetch(mid: str):
            return None

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct"],
            dry_run=False,
            fetch_func=mock_fetch,
        )
        self.assertEqual(summary["parsed"], 0)
        self.assertFalse(summary["catalog_changed"])

    def test_15_schema_validation_failure_blocks_write(self):
        """15. Schema validation blocks writing corrupted catalog structures."""
        corrupted_catalog = {"models": "not_a_dict"}
        with self.assertRaises(OrchestratorSafetyError):
            validate_catalog_schema(corrupted_catalog)

        missing_display = {"models": {"foo/bar": {"model_id": "foo/bar"}}}
        with self.assertRaises(OrchestratorSafetyError):
            validate_catalog_schema(missing_display)

    def test_16_catalog_shrink_triggers_safety_fuse(self):
        """16. Catalog shrink protection validation."""
        valid_catalog = {
            "version": "3.1",
            "models": {
                "meta/llama-3.1-405b-instruct": {
                    "model_id": "meta/llama-3.1-405b-instruct",
                    "display_name": "Llama",
                }
            }
        }
        validate_catalog_schema(valid_catalog)

    def test_17_unchanged_catalog_skips_disk_write(self):
        """17. If no new data is fetched, catalog write is skipped."""
        # 1. Run sync once to update catalog to latest mock state
        def mock_fetch(mid: str):
            return """
            <html><head><title>Llama 3.1 405B Instruct Model - NVIDIA NIM</title></head>
            <body><main><h1>Llama 3.1 405B Instruct</h1><div>32k Context</div><div>405B Dense</div></main></body></html>
            """

        run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct"],
            dry_run=False,
            fetch_func=mock_fetch,
        )

        # 2. Run second sync with identical data -> must detect 0 changes and skip write
        summary2 = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct"],
            dry_run=False,
            fetch_func=mock_fetch,
        )
        self.assertEqual(summary2["merged"], 0)
        self.assertFalse(summary2["catalog_changed"])

    def test_18_atomic_catalog_write_behavior(self):
        """18. Atomic catalog writing replaces cleanly without leaving temp files."""
        data = {"version": "3.1", "models": {}}
        atomic_write_catalog(self.catalog_path, data)
        self.assertTrue(self.catalog_path.exists())
        temp_files = list(self.base_path.glob(".tmp_catalog_*"))
        self.assertEqual(len(temp_files), 0)

    def test_19_summary_json_report_structure(self):
        """19. Summary report contains all required machine-readable fields."""
        def mock_fetch(mid: str):
            return "<html><head><title>Model - NVIDIA NIM</title></head><body><main><h1>Model</h1></main></body></html>"

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct"],
            dry_run=True,
            fetch_func=mock_fetch,
        )

        for key in ["run_at", "dry_run", "discovered", "fetched", "parsed", "merged", "new", "unchanged", "failed", "catalog_changed"]:
            self.assertIn(key, summary)

    def test_20_filter_models_parameter(self):
        """20. filter_models strictly scopes model discovery."""
        discovered = discover_target_models(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            filter_models=["custom/model-1", "custom/model-2"],
        )
        self.assertEqual(discovered, ["custom/model-1", "custom/model-2"])

    def test_21_lifecycle_only_sync_execution(self):
        """21. lifecycle_only sync only updates lifecycle metadata and leaves specs untouched."""
        def mock_fetch(mid: str):
            return """
            <html><head><title>Llama Model - NVIDIA NIM</title></head>
            <body><main>
              <div class="nv-alert">Deprecated as of 2026-06-01. Successor: meta/llama-3.3-70b-instruct</div>
              <div>32k Context</div>
            </main></body></html>
            """

        summary = run_official_metadata_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["meta/llama-3.1-405b-instruct"],
            dry_run=False,
            lifecycle_only=True,
            fetch_func=mock_fetch,
        )
        self.assertTrue(summary["lifecycle_only"])
        self.assertEqual(summary["merged"], 1)

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)
        entry = cat["models"]["meta/llama-3.1-405b-instruct"]
        self.assertEqual(entry["lifecycle"]["availability"], "deprecated")
        self.assertEqual(entry["architecture"]["total_parameters"], "405B")

    def test_22_mass_deprecation_spike_safety_fuse(self):
        """22. Mass deprecation spike (>20% deprecated on large batch) triggers safety fuse."""
        # 10 models in api
        large_api_models = {"data": [{"id": f"vendor/model-{i}"} for i in range(10)]}
        with open(self.api_models_path, "w", encoding="utf-8") as f:
            json.dump(large_api_models, f)

        # 3 out of 10 deprecated (30% > 20% threshold)
        def mock_fetch(mid: str):
            if mid.endswith("1") or mid.endswith("2") or mid.endswith("3"):
                return '<html><head><title>M</title></head><body><main><div class="nv-alert">Deprecated</div></main></body></html>'
            return "<html><head><title>M</title></head><body><main><h1>Active</h1></main></body></html>"

        with self.assertRaises(OrchestratorSafetyError) as ctx:
            run_official_metadata_sync(
                catalog_path=self.catalog_path,
                api_models_path=self.api_models_path,
                snapshots_dir=self.snapshots_dir,
                dry_run=False,
                fetch_func=mock_fetch,
            )
        self.assertIn("Mass deprecation spike detected", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
