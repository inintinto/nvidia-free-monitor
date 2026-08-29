"""
Unit Tests for Lifecycle Safe Merge and State Machine (Phase S2-F)
Validates trust precedence, monotonic state progression, null protections, and date validations.
"""

import copy
import unittest

from src.catalog.merge import merge_model


class TestLifecycleSafeMerge(unittest.TestCase):
    """Test suite for lifecycle merging and state machine rules."""

    def test_01_official_deprecated_overwrites_observed_active(self):
        """1. Official NVIDIA Build deprecated status overwrites observed active."""
        existing = {
            "model_id": "meta/llama-2-70b-chat",
            "lifecycle": {"availability": "active"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "observed"}},
        }
        incoming = {
            "model_id": "meta/llama-2-70b-chat",
            "lifecycle": {
                "availability": "deprecated",
                "official_deprecation_date": "2026-06-01",
                "replacement_model_id": "meta/llama-3.3-70b-instruct",
            },
            "source_metadata": {
                "field_sources": {
                    "lifecycle.availability": "NVIDIA Build",
                    "lifecycle.official_deprecation_date": "NVIDIA Build",
                    "lifecycle.replacement_model_id": "NVIDIA Build",
                }
            },
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["lifecycle"]["availability"], "deprecated")
        self.assertEqual(merged["lifecycle"]["official_deprecation_date"], "2026-06-01")
        self.assertEqual(merged["lifecycle"]["replacement_model_id"], "meta/llama-3.3-70b-instruct")
        self.assertEqual(merged["source_metadata"]["field_sources"]["lifecycle.availability"], "NVIDIA Build")

    def test_02_official_retiring_overwrites_observed_active(self):
        """2. Official retiring status overwrites observed active."""
        existing = {
            "model_id": "google/gemma-7b-it",
            "lifecycle": {"availability": "active"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "observed"}},
        }
        incoming = {
            "model_id": "google/gemma-7b-it",
            "lifecycle": {"availability": "retiring", "official_retirement_date": "2026-10-01"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "NVIDIA Build"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["lifecycle"]["availability"], "retiring")
        self.assertEqual(merged["lifecycle"]["official_retirement_date"], "2026-10-01")

    def test_03_official_removed_overwrites_observed_active(self):
        """3. Official removed status overwrites observed active."""
        existing = {
            "model_id": "test/model",
            "lifecycle": {"availability": "active"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "observed"}},
        }
        incoming = {
            "model_id": "test/model",
            "lifecycle": {"availability": "removed"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "NVIDIA Build"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["lifecycle"]["availability"], "removed")

    def test_04_incoming_null_lifecycle_preserves_existing(self):
        """4. Incoming null lifecycle preserves existing values intact."""
        existing = {
            "model_id": "test/model",
            "lifecycle": {
                "availability": "deprecated",
                "official_deprecation_date": "2026-05-01",
                "replacement_model_id": "test/replacement",
            },
        }
        incoming = {
            "model_id": "test/model",
            "lifecycle": {
                "availability": None,
                "official_deprecation_date": None,
                "replacement_model_id": None,
            },
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["lifecycle"]["availability"], "deprecated")
        self.assertEqual(merged["lifecycle"]["official_deprecation_date"], "2026-05-01")
        self.assertEqual(merged["lifecycle"]["replacement_model_id"], "test/replacement")

    def test_05_parser_failure_preserves_existing_lifecycle(self):
        """5. Complete absence of lifecycle field in incoming preserves existing."""
        existing = {
            "model_id": "test/model",
            "lifecycle": {"availability": "deprecated"},
        }
        incoming = {"model_id": "test/model"}
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["lifecycle"]["availability"], "deprecated")

    def test_06_low_trust_source_cannot_downgrade_deprecated_to_active(self):
        """6. Low-trust observed or heuristic source cannot downgrade official deprecated status."""
        existing = {
            "model_id": "test/model",
            "lifecycle": {"availability": "deprecated"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "NVIDIA Build"}},
        }
        incoming = {
            "model_id": "test/model",
            "lifecycle": {"availability": "active"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "observed"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["lifecycle"]["availability"], "deprecated")

    def test_07_low_trust_source_cannot_downgrade_removed_to_active(self):
        """7. Low-trust source cannot downgrade official removed status to active."""
        existing = {
            "model_id": "test/model",
            "lifecycle": {"availability": "removed"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "NVIDIA Build"}},
        }
        incoming = {
            "model_id": "test/model",
            "lifecycle": {"availability": "active"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "local_heuristic"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["lifecycle"]["availability"], "removed")

    def test_08_monotonic_progression_retiring_to_deprecated(self):
        """8. Monotonic progression: retiring can progress forward to deprecated."""
        existing = {
            "model_id": "test/model",
            "lifecycle": {"availability": "retiring"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "NVIDIA Build"}},
        }
        incoming = {
            "model_id": "test/model",
            "lifecycle": {"availability": "deprecated"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "NVIDIA Build"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["lifecycle"]["availability"], "deprecated")

    def test_09_monotonic_progression_deprecated_to_removed(self):
        """9. Monotonic progression: deprecated can progress forward to removed."""
        existing = {
            "model_id": "test/model",
            "lifecycle": {"availability": "deprecated"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "NVIDIA Build"}},
        }
        incoming = {
            "model_id": "test/model",
            "lifecycle": {"availability": "removed"},
            "source_metadata": {"field_sources": {"lifecycle.availability": "NVIDIA Build"}},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["lifecycle"]["availability"], "removed")

    def test_10_immutable_objects_during_lifecycle_merge(self):
        """10. Merge guarantees pure function immutability."""
        existing = {"model_id": "test/model", "lifecycle": {"availability": "active"}}
        incoming = {"model_id": "test/model", "lifecycle": {"availability": "deprecated"}}

        e_copy = copy.deepcopy(existing)
        i_copy = copy.deepcopy(incoming)

        merge_model(existing, incoming)

        self.assertEqual(existing, e_copy)
        self.assertEqual(incoming, i_copy)

    def test_11_catalog_unrelated_fields_unpolluted(self):
        """11. Lifecycle merge leaves all architecture, context, and provider fields intact."""
        existing = {
            "model_id": "test/model",
            "display_name": "Test Model",
            "architecture": {"type": "MoE", "total_parameters": "1.65T"},
            "context": {"length": "1M"},
            "lifecycle": {"availability": "active"},
        }
        incoming = {
            "model_id": "test/model",
            "lifecycle": {"availability": "retiring", "official_retirement_date": "2026-12-31"},
        }
        merged, diff = merge_model(existing, incoming)
        self.assertEqual(merged["display_name"], "Test Model")
        self.assertEqual(merged["architecture"]["total_parameters"], "1.65T")
        self.assertEqual(merged["context"]["length"], "1M")
        self.assertEqual(merged["lifecycle"]["availability"], "retiring")


if __name__ == "__main__":
    unittest.main()
