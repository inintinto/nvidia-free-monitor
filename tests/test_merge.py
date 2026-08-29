"""
Unit Tests for Safe Catalog Merge Engine (Phase S1-D)
Verifies strict null-protection, source trust hierarchy, immutability, and nested field merging.
"""

import copy
import unittest

from src.catalog.merge import merge_catalog, merge_model


class TestSafeCatalogMerge(unittest.TestCase):
    """Comprehensive test suite for Safe Catalog Merge Engine."""

    def test_01_existing_plus_official_new_value(self):
        """1. Official new value successfully updates existing catalog entry."""
        existing = {
            "model_id": "meta/llama-3.1-405b-instruct",
            "context": {"length": "32k", "status": "official"},
            "source_metadata": {"field_sources": {"context.length": "NVIDIA Build"}},
        }
        incoming = {
            "model_id": "meta/llama-3.1-405b-instruct",
            "context": {"length": "128k", "status": "official"},
            "source_metadata": {"field_sources": {"context.length": "NVIDIA Build"}},
        }

        merged, diff = merge_model(existing, incoming)
        self.assertTrue(diff["changed"])
        self.assertIn("context.length", diff["updated_fields"])
        self.assertEqual(merged["context"]["length"], "128k")
        self.assertEqual(diff["field_diffs"]["context.length"]["old"], "32k")
        self.assertEqual(diff["field_diffs"]["context.length"]["new"], "128k")

    def test_02_official_null_does_not_erase_existing(self):
        """2. Strict Ground Truth Law: Official null must NEVER erase existing value."""
        existing = {
            "model_id": "meta/llama-3.1-405b-instruct",
            "context": {"length": "128k", "max_output": "4096", "status": "official"},
            "architecture": {"total_parameters": "405B", "type": "Dense"},
        }
        incoming = {
            "model_id": "meta/llama-3.1-405b-instruct",
            "context": {"length": None, "max_output": None},
            "architecture": {"total_parameters": None, "type": None},
        }

        merged, diff = merge_model(existing, incoming)
        self.assertFalse(diff["changed"])
        self.assertEqual(merged["context"]["length"], "128k")
        self.assertEqual(merged["context"]["max_output"], "4096")
        self.assertEqual(merged["architecture"]["total_parameters"], "405B")
        self.assertEqual(merged["architecture"]["type"], "Dense")

    def test_03_missing_field_does_not_erase_existing(self):
        """3. Missing field in incoming data must preserve existing field completely."""
        existing = {
            "model_id": "google/gemma-2-27b-it",
            "endpoint": {"api_calls_30d": "1.5M"},
            "release": {"first_seen": "2026-06-01T00:00:00Z"},
        }
        incoming = {
            "model_id": "google/gemma-2-27b-it",
            "display_name": "Gemma 2 27B",
        }

        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["endpoint"]["api_calls_30d"], "1.5M")
        self.assertEqual(merged["release"]["first_seen"], "2026-06-01T00:00:00Z")
        self.assertEqual(merged["display_name"], "Gemma 2 27B")

    def test_04_parser_failure_preserves_existing(self):
        """4. Parser returning None preserves existing catalog entry without changes."""
        existing = {
            "model_id": "test/model",
            "display_name": "Test Model",
        }
        merged, diff = merge_model(existing, None)
        self.assertFalse(diff["changed"])
        self.assertEqual(merged, existing)

    def test_05_http_failure_preserves_existing(self):
        """5. HTTP failure/empty payload preserves existing catalog entry."""
        existing = {
            "model_id": "test/model",
            "display_name": "Test Model",
        }
        merged, diff = merge_model(existing, {})
        self.assertFalse(diff["changed"])
        self.assertEqual(merged, existing)

    def test_06_new_model_creates_minimal_entry(self):
        """6. Unregistered new model creates standard minimal safe entry."""
        incoming = {
            "model_id": "new-vendor/smart-model-1b",
            "display_name": "Smart Model 1B",
            "capabilities": ["Chat", "Reasoning"],
            "links": {"nvidia": "https://build.nvidia.com/new-vendor/smart-model-1b"},
        }

        merged, diff = merge_model(None, incoming)
        self.assertTrue(diff["created"])
        self.assertEqual(merged["model_id"], "new-vendor/smart-model-1b")
        self.assertEqual(merged["provider"]["id"], "new-vendor")
        self.assertEqual(merged["provider"]["name"], "New Vendor")
        self.assertEqual(merged["slug"], "smart-model-1b")
        self.assertEqual(merged["capabilities"], ["Chat", "Reasoning"])
        self.assertIsNone(merged["context"]["length"])
        self.assertIsNone(merged["architecture"]["total_parameters"])

    def test_07_existing_model_does_not_duplicate(self):
        """7. Existing model update flag is set to created=False."""
        existing = {"model_id": "meta/llama", "display_name": "Llama"}
        incoming = {"model_id": "meta/llama", "display_name": "Llama 3"}

        merged, diff = merge_model(existing, incoming)
        self.assertFalse(diff["created"])
        self.assertTrue(diff["changed"])

    def test_08_official_beats_heuristic(self):
        """8. Official source data takes precedence over local heuristic."""
        existing = {
            "model_id": "test/model",
            "classification": {"speed": "fast"},
            "source_metadata": {"field_sources": {"classification.speed": "local_heuristic"}},
        }
        incoming = {
            "model_id": "test/model",
            "classification": {"speed": "standard"},
            "source_metadata": {"field_sources": {"classification.speed": "NVIDIA Build"}},
        }

        merged, diff = merge_model(existing, incoming)
        self.assertTrue(diff["changed"])
        self.assertEqual(merged["classification"]["speed"], "standard")
        self.assertEqual(merged["source_metadata"]["field_sources"]["classification.speed"], "NVIDIA Build")

    def test_09_heuristic_cannot_overwrite_official(self):
        """9. Local heuristic data CANNOT overwrite existing official source data."""
        existing = {
            "model_id": "test/model",
            "classification": {"speed": "standard"},
            "source_metadata": {"field_sources": {"classification.speed": "NVIDIA Build"}},
        }
        incoming = {
            "model_id": "test/model",
            "classification": {"speed": "fast"},
            "source_metadata": {"field_sources": {"classification.speed": "local_heuristic"}},
        }

        merged, diff = merge_model(existing, incoming)
        self.assertFalse(diff["changed"])
        self.assertEqual(merged["classification"]["speed"], "standard")
        self.assertEqual(merged["source_metadata"]["field_sources"]["classification.speed"], "NVIDIA Build")

    def test_10_nested_architecture_merge(self):
        """10. Architecture nested fields merged field-by-field."""
        existing = {
            "model_id": "deepseek-ai/deepseek-v4",
            "architecture": {"type": "MoE", "total_parameters": None},
        }
        incoming = {
            "model_id": "deepseek-ai/deepseek-v4",
            "architecture": {"type": None, "total_parameters": "671B", "parameter_status": "official"},
        }

        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["architecture"]["type"], "MoE")
        self.assertEqual(merged["architecture"]["total_parameters"], "671B")
        self.assertEqual(merged["architecture"]["parameter_status"], "official")

    def test_11_nested_context_merge(self):
        """11. Context nested fields merged field-by-field."""
        existing = {
            "model_id": "meta/llama",
            "context": {"length": "128k", "max_output": None},
        }
        incoming = {
            "model_id": "meta/llama",
            "context": {"length": None, "max_output": "4096"},
        }

        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["context"]["length"], "128k")
        self.assertEqual(merged["context"]["max_output"], "4096")

    def test_12_nested_links_merge(self):
        """12. External links merged safely without wiping existing official URLs."""
        existing = {
            "model_id": "deepseek-ai/deepseek-v4",
            "links": {
                "nvidia": "https://build.nvidia.com/deepseek-ai/deepseek-v4",
                "official": "https://www.deepseek.com",
                "documentation": None,
            },
        }
        incoming = {
            "model_id": "deepseek-ai/deepseek-v4",
            "links": {
                "nvidia": "https://build.nvidia.com/deepseek-ai/deepseek-v4",
                "official": None,
                "documentation": "https://docs.api.nvidia.com/nim/deepseek-ai/deepseek-v4",
            },
        }

        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["links"]["official"], "https://www.deepseek.com")
        self.assertEqual(merged["links"]["documentation"], "https://docs.api.nvidia.com/nim/deepseek-ai/deepseek-v4")

    def test_13_nested_source_metadata_merge(self):
        """13. source_metadata.field_sources merged incrementally."""
        existing = {
            "model_id": "test/model",
            "source_metadata": {
                "field_sources": {
                    "architecture.type": "manual_audit",
                    "context.length": "official",
                },
                "confidence": "high",
            },
        }
        incoming = {
            "model_id": "test/model",
            "display_name": "Official Title",
            "source_metadata": {
                "field_sources": {
                    "display_name": "NVIDIA Build",
                },
            },
        }

        merged, diff = merge_model(existing, incoming)
        fs = merged["source_metadata"]["field_sources"]
        self.assertEqual(fs.get("architecture.type"), "manual_audit")
        self.assertEqual(fs.get("context.length"), "official")
        self.assertEqual(fs.get("display_name"), "NVIDIA Build")

    def test_14_field_sources_accurately_updated(self):
        """14. Newly updated fields recorded with source in field_sources."""
        existing = {"model_id": "test/model", "context": {"length": "4k"}}
        incoming = {
            "model_id": "test/model",
            "context": {"length": "128k"},
            "source_metadata": {"field_sources": {"context.length": "NVIDIA Build"}},
        }

        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["source_metadata"]["field_sources"]["context.length"], "NVIDIA Build")

    def test_15_last_verified_updated(self):
        """15. last_verified timestamp is updated on merge."""
        existing = {
            "model_id": "test/model",
            "source_metadata": {"last_verified": "2026-01-01T00:00:00Z"},
        }
        incoming = {"model_id": "test/model", "display_name": "New Name"}

        merged, diff = merge_model(existing, incoming)
        self.assertNotEqual(merged["source_metadata"]["last_verified"], "2026-01-01T00:00:00Z")

    def test_16_capabilities_merge_and_deduplicate(self):
        """16. Capabilities combined as union with order preserved."""
        existing = {"model_id": "test/model", "capabilities": ["Chat", "Vision"]}
        incoming = {"model_id": "test/model", "capabilities": ["Chat", "Reasoning", "Coding"]}

        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["capabilities"], ["Chat", "Vision", "Reasoning", "Coding"])

    def test_17_empty_string_does_not_erase_trusted_value(self):
        """17. Empty string '' does NOT erase existing trusted value."""
        existing = {"model_id": "test/model", "display_name": "Trusted Name"}
        incoming = {"model_id": "test/model", "display_name": ""}

        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["display_name"], "Trusted Name")

    def test_18_unknown_status_does_not_erase_trusted_value(self):
        """18. 'unknown' / 'Unknown' does NOT erase existing trusted value."""
        existing = {"model_id": "test/model", "architecture": {"type": "Dense"}}
        incoming = {"model_id": "test/model", "architecture": {"type": "unknown"}}

        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["architecture"]["type"], "Dense")

    def test_19_input_objects_are_immutable(self):
        """19. Pure function guarantee: existing and incoming objects are NOT mutated."""
        existing = {"model_id": "test/model", "context": {"length": "32k"}}
        incoming = {"model_id": "test/model", "context": {"length": "128k"}}

        existing_copy = copy.deepcopy(existing)
        incoming_copy = copy.deepcopy(incoming)

        merge_model(existing, incoming)

        self.assertEqual(existing, existing_copy)
        self.assertEqual(incoming, incoming_copy)

    def test_20_merge_is_idempotent(self):
        """20. Multiple consecutive merges produce identical result."""
        existing = {"model_id": "test/model", "context": {"length": "32k"}}
        incoming = {"model_id": "test/model", "context": {"length": "128k"}}

        pass1, diff1 = merge_model(existing, incoming)
        pass2, diff2 = merge_model(pass1, incoming)

        self.assertEqual(pass1["context"]["length"], pass2["context"]["length"])
        self.assertFalse(diff2["changed"])

    def test_21_catalog_level_batch_merge(self):
        """21. merge_catalog batch processing handles mix of updates, creations, preserves."""
        catalog = {
            "version": "3.1",
            "models": {
                "meta/llama-3.1-405b-instruct": {
                    "model_id": "meta/llama-3.1-405b-instruct",
                    "display_name": "Llama 405B",
                    "context": {"length": "32k"},
                },
                "deepseek-ai/deepseek-v4": {
                    "model_id": "deepseek-ai/deepseek-v4",
                    "display_name": "DeepSeek V4",
                },
            },
        }

        incoming_batch = [
            # 1. Update existing
            {
                "model_id": "meta/llama-3.1-405b-instruct",
                "context": {"length": "128k"},
            },
            # 2. No changes for existing
            {
                "model_id": "deepseek-ai/deepseek-v4",
                "display_name": "DeepSeek V4",
            },
            # 3. Create new model
            {
                "model_id": "google/gemma-2-27b-it",
                "display_name": "Gemma 2 27B",
            },
        ]

        new_catalog, summary = merge_catalog(catalog, incoming_batch)

        self.assertTrue(summary["changed"])
        self.assertEqual(summary["total_incoming"], 3)
        self.assertEqual(summary["total_updated"], 1)
        self.assertEqual(summary["total_created"], 1)
        self.assertEqual(summary["total_preserved"], 1)
        self.assertEqual(len(new_catalog["models"]), 3)

        models = new_catalog["models"]
        self.assertIn("google/gemma-2-27b-it", models)
        self.assertEqual(models["meta/llama-3.1-405b-instruct"]["context"]["length"], "128k")

    def test_22_null_params_updated_by_official_1_65t(self):
        """22. Existing null parameters updated safely by official 1.65T."""
        existing = {
            "model_id": "deepseek-ai/deepseek-v4-pro-0813",
            "architecture": {"total_parameters": None, "parameter_status": "unknown"},
        }
        incoming = {
            "model_id": "deepseek-ai/deepseek-v4-pro-0813",
            "architecture": {"total_parameters": "1.65T", "parameter_status": "official"},
            "source_metadata": {"field_sources": {"architecture.total_parameters": "NVIDIA Build"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["architecture"]["total_parameters"], "1.65T")
        self.assertEqual(merged["architecture"]["parameter_status"], "official")

    def test_23_null_context_updated_by_official_1m(self):
        """23. Existing null context updated safely by official 1M."""
        existing = {
            "model_id": "deepseek-ai/deepseek-v4-pro-0813",
            "context": {"length": None, "status": "unknown"},
        }
        incoming = {
            "model_id": "deepseek-ai/deepseek-v4-pro-0813",
            "context": {"length": "1M", "status": "official"},
            "source_metadata": {"field_sources": {"context.length": "NVIDIA Build"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["context"]["length"], "1M")
        self.assertEqual(merged["context"]["status"], "official")

    def test_24_spurious_heuristic_vision_corrected_by_official_text_modal(self):
        """24. Spurious heuristic vision corrected by official Text/Text model_type."""
        existing = {
            "model_id": "deepseek-ai/deepseek-v4-pro-0813",
            "classification": {"model_type": "vision"},
            "source_metadata": {"field_sources": {"classification.model_type": "local_heuristic"}},
        }
        incoming = {
            "model_id": "deepseek-ai/deepseek-v4-pro-0813",
            "classification": {"model_type": "chat"},
            "source_metadata": {"field_sources": {"classification.model_type": "NVIDIA Build"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["classification"]["model_type"], "chat")

    def test_25_incoming_null_preserves_official_existing_values(self):
        """25. Incoming null never overwrites existing official parameters or context."""
        existing = {
            "model_id": "meta/llama-3.1-405b-instruct",
            "architecture": {"total_parameters": "405B", "parameter_status": "official"},
            "context": {"length": "128k", "status": "official"},
            "source_metadata": {"field_sources": {"architecture.total_parameters": "NVIDIA Build"}},
        }
        incoming = {
            "model_id": "meta/llama-3.1-405b-instruct",
            "architecture": {"total_parameters": None},
            "context": {"length": None},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["architecture"]["total_parameters"], "405B")
        self.assertEqual(merged["context"]["length"], "128k")

    def test_26_official_capabilities_purge_spurious_vision(self):
        """26. Official non-vision capabilities purge spurious legacy Vision from list."""
        existing = {
            "model_id": "deepseek-ai/deepseek-v4-pro-0813",
            "capabilities": ["Vision", "Coding", "Reasoning"],
            "classification": {"model_type": "vision"},
        }
        incoming = {
            "model_id": "deepseek-ai/deepseek-v4-pro-0813",
            "capabilities": ["Chat", "Coding", "Reasoning", "Agentic"],
            "classification": {"model_type": "chat"},
            "source_metadata": {"field_sources": {"capabilities": "NVIDIA Build"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertNotIn("Vision", merged["capabilities"])
        self.assertIn("Chat", merged["capabilities"])
        self.assertIn("Agentic", merged["capabilities"])


if __name__ == "__main__":
    unittest.main()
