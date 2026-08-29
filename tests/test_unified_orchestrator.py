"""
Unit Tests for Unified Evidence Orchestrator (Phase S3-E)
Validates multi-source evidence adapters, failure isolation, ledger append-replay cycle,
Ground Truth supremacy, catalog projection, safety fuses, and dry-run integrity.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from src.catalog.ecosystem.nimstats import EcosystemSignal
from src.catalog.ecosystem.reddit import CommunitySignal
from src.catalog.evidence import EvidenceState, SourceTier
from src.catalog.evidence_ledger import LedgerRecord, load_ledger, rebuild_materialized_state
from src.catalog.orchestrator import OrchestratorSafetyError
from src.catalog.unified_orchestrator import (
    build_metadata_to_ledger_records,
    nimstats_signals_to_ledger_records,
    project_materialized_state_to_catalog,
    reddit_signals_to_ledger_records,
    run_unified_evidence_sync,
)


class TestUnifiedEvidenceOrchestrator(unittest.TestCase):
    """Test suite for Phase S3-E Unified Orchestrator."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)

        self.catalog_path = self.base_dir / "model_catalog.json"
        self.api_models_path = self.base_dir / "nvidia_api_models.json"
        self.ledger_path = self.base_dir / "evidence_ledger.jsonl"
        self.state_path = self.base_dir / "evidence_state.json"
        self.snapshots_dir = self.base_dir / "snapshots"

        # Seed catalog
        initial_catalog = {
            "version": "3.1",
            "updated_at": "2026-08-27T00:00:00Z",
            "models": {
                "meta/llama-3.1-405b-instruct": {
                    "model_id": "meta/llama-3.1-405b-instruct",
                    "display_name": "Llama 3.1 405B Instruct",
                    "architecture": {"type": "Dense", "total_parameters": "405B"},
                    "context": {"length": "128k"},
                    "lifecycle": {"availability": "active"},
                    "source_metadata": {"field_sources": {"context.length": "NVIDIA Build"}},
                }
            },
        }
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(initial_catalog, f, indent=2)

        # Seed api models
        api_data = {
            "data": [
                {"id": "meta/llama-3.1-405b-instruct"},
                {"id": "deepseek-ai/deepseek-v4-pro-0813"},
            ]
        }
        with open(self.api_models_path, "w", encoding="utf-8") as f:
            json.dump(api_data, f, indent=2)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_build_metadata_to_ledger_records_conversion(self):
        """1. Build metadata parser results convert cleanly into official LedgerRecords."""
        parsed_meta = {
            "display_name": "DeepSeek V4 Pro 0813",
            "architecture": {"type": "MoE", "total_parameters": "1.65T", "active_parameters": "49B"},
            "context": {"length": "1M"},
            "classification": {"model_type": "chat"},
            "capabilities": ["Coding", "Reasoning"],
            "lifecycle": {"availability": "active"},
        }
        recs = build_metadata_to_ledger_records("deepseek-ai/deepseek-v4-pro-0813", parsed_meta)

        self.assertGreater(len(recs), 4)
        for r in recs:
            self.assertEqual(r.source["source_tier"], "nvidia_build")
            self.assertEqual(r.source["source_kind"], "official")
            self.assertEqual(r.model_id, "deepseek-ai/deepseek-v4-pro-0813")

        ctx_rec = next(r for r in recs if r.field_name == "context.length")
        self.assertEqual(ctx_rec.claim, "1M")

    def test_02_nimstats_signals_to_ledger_records_conversion(self):
        """2. NIMStats EcosystemSignals convert into COMMUNITY_SCRAPER LedgerRecords."""
        sig = EcosystemSignal(
            model_id="deepseek-ai/deepseek-v4-pro-0813",
            observed_context="1M",
            observed_status="active",
            source_url="https://nimstats.com",
        )
        recs = nimstats_signals_to_ledger_records([sig])

        self.assertEqual(len(recs), 2)
        for r in recs:
            self.assertEqual(r.source["source_tier"], "community_scraper")
            self.assertEqual(r.source["source_kind"], "community_scraper")

    def test_03_reddit_signals_to_ledger_records_conversion(self):
        """3. Reddit CommunitySignals convert into COMMUNITY_FORUM LedgerRecords."""
        sig = CommunitySignal(
            model_id="deepseek-ai/deepseek-v4-pro-0813",
            claim_type="context.length",
            claim_value="1M",
            source_id="reddit:r/LocalLLaMA:p1",
            source_url="https://reddit.com/p1",
            subreddit="LocalLLaMA",
            post_id="p1",
        )
        recs = reddit_signals_to_ledger_records([sig])

        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].source["source_tier"], "community_forum")
        self.assertEqual(recs[0].claim, "1M")

    def test_04_e2e_unified_evidence_sync_pipeline(self):
        """4. Full unified pipeline ingests all sources, appends ledger, replays state, and updates catalog."""
        def mock_build_fetch(mid: str):
            if "deepseek" in mid:
                return '<html><head><title>DS Pro - NVIDIA NIM</title></head><body><main><h1>DeepSeek V4 Pro</h1><div>MoE 1.65T 49B 1M Context</div></main></body></html>'
            return '<html><head><title>Llama - NVIDIA NIM</title></head><body><main><h1>Llama 405B</h1><div>405B 128k Context</div></main></body></html>'

        def mock_nimstats_fetch(**kwargs):
            return json.dumps([{"model_id": "deepseek-ai/deepseek-v4-pro-0813", "tokens_per_sec": 85.0, "observed_context": "1M"}]).encode("utf-8")

        def mock_reddit_fetch(**kwargs):
            return json.dumps({"data": {"children": [{"data": {"id": "r1", "title": "deepseek-ai/deepseek-v4-pro-0813", "selftext": "1M context confirmed", "subreddit": "LocalLLaMA"}}]}}).encode("utf-8"), "success"

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            dry_run=False,
            include_community=True,
            build_fetch_func=mock_build_fetch,
            nimstats_fetch_func=mock_nimstats_fetch,
            reddit_fetch_func=mock_reddit_fetch,
        )

        self.assertTrue(report["catalog_changed"])
        self.assertTrue(self.ledger_path.exists())
        self.assertTrue(self.state_path.exists())

        ledger_records = load_ledger(self.ledger_path)
        self.assertGreater(len(ledger_records), 5)

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)
        ds = cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]
        self.assertEqual(ds["context"]["length"], "1M")
        self.assertEqual(ds["architecture"]["total_parameters"], "1.65T")

    def test_05_source_failure_isolation_nimstats_error(self):
        """5. Failure in NIMStats does not crash pipeline and official metadata sync proceeds normally."""
        def mock_build_fetch(mid: str):
            return '<html><head><title>Model - NVIDIA NIM</title></head><body><main><h1>Model</h1><div>128k Context</div></main></body></html>'

        def mock_nimstats_failing(**kwargs):
            raise ConnectionResetError("NIMStats remote host connection reset")

        def mock_reddit_fetch(**kwargs):
            return None, "credentials_not_configured"

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            dry_run=False,
            build_fetch_func=mock_build_fetch,
            nimstats_fetch_func=mock_nimstats_failing,
            reddit_fetch_func=mock_reddit_fetch,
        )

        self.assertIn("error", report["source_statuses"]["nimstats"]["status"])
        self.assertEqual(report["source_statuses"]["nvidia_build"]["fetched"], 2)

    def test_06_source_failure_isolation_reddit_missing_credentials(self):
        """6. Missing Reddit credentials gracefully marks status without throwing exceptions."""
        def mock_build_fetch(mid: str):
            return '<html><head><title>Model - NVIDIA NIM</title></head><body><main><h1>Model</h1></main></body></html>'

        def mock_reddit_fetch(**kwargs):
            return None, "credentials_not_configured"

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            dry_run=False,
            build_fetch_func=mock_build_fetch,
            nimstats_fetch_func=lambda **kw: None,
            reddit_fetch_func=mock_reddit_fetch,
        )
        self.assertEqual(report["source_statuses"]["reddit"]["status"], "credentials_not_configured")

    def test_07_official_ground_truth_supremacy_over_ecosystem_signals(self):
        """7. Inaccurate community rumors (e.g. 64k) NEVER overwrite verified Ground Truth (1M) in catalog."""
        def mock_build_fetch(mid: str):
            return '<html><head><title>DS Pro - NVIDIA NIM</title></head><body><main><h1>DeepSeek V4 Pro</h1><div>1M Context</div></main></body></html>'

        def mock_nimstats_fetch(**kwargs):
            # Accurate community corroboration
            return json.dumps([{"model_id": "deepseek-ai/deepseek-v4-pro-0813", "observed_context": "1M"}]).encode("utf-8")

        def mock_reddit_conflicting(**kwargs):
            # Inaccurate community rumor
            return json.dumps({"data": {"children": [{"data": {"id": "rumor_1", "title": "deepseek-ai/deepseek-v4-pro-0813", "selftext": "context is only 64k tokens", "subreddit": "LocalLLaMA"}}]}}).encode("utf-8"), "success"

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            dry_run=False,
            build_fetch_func=mock_build_fetch,
            nimstats_fetch_func=mock_nimstats_fetch,
            reddit_fetch_func=mock_reddit_conflicting,
        )

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)
        ds = cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]
        self.assertEqual(ds["context"]["length"], "1M")  # Supreme Ground Truth maintained

    def test_08_dry_run_leaves_catalog_and_ledger_untouched(self):
        """8. Dry-run mode produces full report without writing to disk."""
        sha_before = hashlib.sha256(self.catalog_path.read_bytes()).hexdigest()

        def mock_build_fetch(mid: str):
            return '<html><head><title>Model - NVIDIA NIM</title></head><body><main><h1>Model</h1><div>128k Context</div></main></body></html>'

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            dry_run=True,
            build_fetch_func=mock_build_fetch,
            nimstats_fetch_func=lambda **kw: None,
            reddit_fetch_func=lambda **kw: (None, "skipped"),
        )

        self.assertTrue(report["dry_run"])
        sha_after = hashlib.sha256(self.catalog_path.read_bytes()).hexdigest()
        self.assertEqual(sha_before, sha_after)
        self.assertFalse(self.ledger_path.exists())

    def test_09_mass_deprecation_spike_safety_fuse(self):
        """9. Mass deprecation spike triggers safety fuse and aborts catalog update."""
        # 10 models in api
        large_api = {"data": [{"id": f"vendor/model-{i}"} for i in range(10)]}
        with open(self.api_models_path, "w", encoding="utf-8") as f:
            json.dump(large_api, f)

        def mock_build_deprecated(mid: str):
            return '<html><head><title>M</title></head><body><main><div class="nv-alert">Deprecated</div></main></body></html>'

        with self.assertRaises(OrchestratorSafetyError) as ctx:
            run_unified_evidence_sync(
                catalog_path=self.catalog_path,
                api_models_path=self.api_models_path,
                ledger_path=self.ledger_path,
                state_path=self.state_path,
                snapshots_dir=self.snapshots_dir,
                dry_run=False,
                build_fetch_func=mock_build_deprecated,
                nimstats_fetch_func=lambda **kw: None,
                reddit_fetch_func=lambda **kw: (None, "skipped"),
            )
        self.assertIn("Mass deprecation spike detected", str(ctx.exception))

    def test_10_skip_community_flag(self):
        """10. include_community=False skips NIMStats and Reddit collection."""
        def mock_build_fetch(mid: str):
            return '<html><head><title>M</title></head><body><main><h1>M</h1></main></body></html>'

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            dry_run=False,
            include_community=False,
            build_fetch_func=mock_build_fetch,
        )
        self.assertEqual(report["source_statuses"]["nimstats"]["status"], "skipped")
        self.assertEqual(report["source_statuses"]["reddit"]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
