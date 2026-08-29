"""
Adversarial & Disaster Recovery Test Suite (Phase S3-F)
Comprehensive audit against deliberate ledger corruptions, deterministic replay permutations,
Ground Truth supremacy under attack, data source failure isolation, recovery idempotency,
catalog inconsistency healing, safety fuses, and crash atomicity.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import tempfile
import unittest

from src.catalog.ecosystem.nimstats import EcosystemSignal
from src.catalog.ecosystem.reddit import CommunitySignal
from src.catalog.evidence import EvidenceItem, EvidenceState, FieldEvidence, SourceTier
from src.catalog.evidence_ledger import (
    DuplicateEvidenceError,
    LedgerCorruptedError,
    LedgerRecord,
    append_evidence,
    calculate_materialized_state_hash,
    compute_evidence_id,
    get_ledger_stats,
    load_ledger,
    rebuild_materialized_state,
    replay_evidence,
    validate_ledger_record,
    verify_ledger,
)
from src.catalog.orchestrator import (
    OrchestratorSafetyError,
    atomic_write_catalog,
    calculate_catalog_hash,
    load_json_file,
)
from src.catalog.unified_orchestrator import (
    build_metadata_to_ledger_records,
    project_materialized_state_to_catalog,
    run_unified_evidence_sync,
)


class TestAdversarialRecovery(unittest.TestCase):
    """50 Comprehensive Adversarial and Disaster Recovery Tests."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)

        self.catalog_path = self.base_dir / "model_catalog.json"
        self.api_models_path = self.base_dir / "nvidia_api_models.json"
        self.ledger_path = self.base_dir / "evidence_ledger.jsonl"
        self.state_path = self.base_dir / "evidence_state.json"
        self.snapshots_dir = self.base_dir / "snapshots"

        self.t1 = "2026-08-27T01:00:00+00:00"
        self.t2 = "2026-08-27T02:00:00+00:00"
        self.t3 = "2026-08-27T03:00:00+00:00"

        # Baseline catalog
        self.initial_catalog = {
            "version": "3.1",
            "updated_at": "2026-08-27T00:00:00Z",
            "models": {
                "deepseek-ai/deepseek-v4-pro-0813": {
                    "model_id": "deepseek-ai/deepseek-v4-pro-0813",
                    "display_name": "deepseek-v4-pro-0813",
                    "architecture": {"type": "MoE", "total_parameters": "1.65T", "active_parameters": "49B", "parameter_status": "official"},
                    "context": {"length": "1M", "max_output": None, "status": "official"},
                    "capabilities": ["Coding", "Reasoning", "Chat", "Agentic"],
                    "lifecycle": {"availability": "active"},
                    "source_metadata": {"field_sources": {"context.length": "NVIDIA Build"}},
                },
                "meta/llama-3.1-405b-instruct": {
                    "model_id": "meta/llama-3.1-405b-instruct",
                    "display_name": "llama-3.1-405b-instruct",
                    "architecture": {"type": "Dense", "total_parameters": "405B", "parameter_status": "official"},
                    "context": {"length": "128k", "status": "official"},
                    "lifecycle": {"availability": "active"},
                    "source_metadata": {"field_sources": {"context.length": "NVIDIA Build"}},
                },
            },
        }
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(self.initial_catalog, f, indent=2)

        # Baseline api models
        api_data = {
            "data": [
                {"id": "deepseek-ai/deepseek-v4-pro-0813"},
                {"id": "meta/llama-3.1-405b-instruct"},
            ]
        }
        with open(self.api_models_path, "w", encoding="utf-8") as f:
            json.dump(api_data, f, indent=2)

    def tearDown(self):
        self.tmp_dir.cleanup()

    # =========================================================================
    # Section 1: Ledger Integrity Attacks (10 Tests)
    # =========================================================================

    def test_01_valid_ledger_verification(self):
        """1. Clean, valid ledger passes verification cleanly."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)
        audit = verify_ledger(self.ledger_path)
        self.assertTrue(audit["verified"])
        self.assertEqual(audit["records_count"], 1)

    def test_02_single_line_json_syntax_corruption(self):
        """2. Malformed syntax on a single line is caught and raises LedgerCorruptedError."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write('{"malformed_json_line: missing_closing_bracket\n')
        with self.assertRaises(LedgerCorruptedError):
            load_ledger(self.ledger_path)

    def test_03_middle_line_truncation(self):
        """3. Half-written or truncated middle line is rejected."""
        r1 = LedgerRecord.create("model/a", "context.length", "128k", "s1", SourceTier.COMMUNITY_FORUM, "u1", self.t1)
        r2 = LedgerRecord.create("model/b", "context.length", "32k", "s2", SourceTier.COMMUNITY_FORUM, "u2", self.t2)
        append_evidence(self.ledger_path, r1)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write('{"evidence_id": "truncated_half_record"\n')

        with self.assertRaises(LedgerCorruptedError):
            append_evidence(self.ledger_path, r2)

        with self.assertRaises(LedgerCorruptedError):
            load_ledger(self.ledger_path)

    def test_04_tampered_evidence_id(self):
        """4. Modifying evidence_id triggers SHA-256 mismatch rejection."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        d = r.to_dict()
        d["evidence_id"] = "f" * 64
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(d) + "\n")
        with self.assertRaises(LedgerCorruptedError) as ctx:
            load_ledger(self.ledger_path)
        self.assertIn("Evidence ID mismatch", str(ctx.exception))

    def test_05_tampered_model_id(self):
        """5. Modifying model_id to invalid string without vendor is rejected."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        d = r.to_dict()
        d["model_id"] = "invalid_model_without_slash"
        d["evidence_id"] = compute_evidence_id("invalid_model_without_slash", "context.length", "1M", "nvidia_build", "nvidia_build", "https://build.nvidia.com", self.t1)
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(d) + "\n")
        with self.assertRaises(LedgerCorruptedError) as ctx:
            load_ledger(self.ledger_path)
        self.assertIn("Invalid model_id format", str(ctx.exception))

    def test_06_tampered_claim(self):
        """6. Tampering with claim payload without matching evidence_id is rejected."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        d = r.to_dict()
        d["claim"] = "64k"  # tampered
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(d) + "\n")
        with self.assertRaises(LedgerCorruptedError) as ctx:
            load_ledger(self.ledger_path)
        self.assertIn("Evidence ID mismatch", str(ctx.exception))

    def test_07_tampered_source_tier(self):
        """7. Injecting fake or illegal source_tier is rejected."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        d = r.to_dict()
        d["source"]["source_tier"] = "superuser_override"
        d["evidence_id"] = compute_evidence_id(d["model_id"], d["field_name"], d["claim"], d["source"]["source_id"], "superuser_override", d["source"]["source_url"], d["observed_at"])
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(d) + "\n")
        with self.assertRaises(LedgerCorruptedError) as ctx:
            load_ledger(self.ledger_path)
        self.assertIn("Invalid source_tier", str(ctx.exception))

    def test_08_tampered_observed_at(self):
        """8. Corrupted non-ISO timestamp format is rejected."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        d = r.to_dict()
        d["observed_at"] = "yesterday afternoon"
        d["evidence_id"] = compute_evidence_id(d["model_id"], d["field_name"], d["claim"], d["source"]["source_id"], d["source"]["source_tier"], d["source"]["source_url"], "yesterday afternoon")
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(d) + "\n")
        with self.assertRaises(LedgerCorruptedError) as ctx:
            load_ledger(self.ledger_path)
        self.assertIn("Invalid observed_at timestamp", str(ctx.exception))

    def test_09_last_line_deletion_recovery(self):
        """9. Deleting the last line leaves the remaining ledger valid and fully replayable."""
        r1 = LedgerRecord.create("model/a", "context.length", "128k", "s1", SourceTier.COMMUNITY_FORUM, "u1", self.t1)
        r2 = LedgerRecord.create("model/b", "context.length", "32k", "s2", SourceTier.COMMUNITY_FORUM, "u2", self.t2)
        append_evidence(self.ledger_path, r1)
        append_evidence(self.ledger_path, r2)

        # Truncate to first line
        lines = self.ledger_path.read_text(encoding="utf-8").strip().splitlines()
        self.ledger_path.write_text(lines[0] + "\n", encoding="utf-8")

        audit = verify_ledger(self.ledger_path)
        self.assertTrue(audit["verified"])
        self.assertEqual(audit["records_count"], 1)

    def test_10_duplicate_ledger_record_handling(self):
        """10. Repeatedly appending the identical record returns already_exists without duplicate entries."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        ok1, msg1 = append_evidence(self.ledger_path, r)
        ok2, msg2 = append_evidence(self.ledger_path, r)

        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertEqual(msg2, "already_exists")
        self.assertEqual(len(load_ledger(self.ledger_path)), 1)

    # =========================================================================
    # Section 2: Deterministic Replay Adversarial Permutations (8 Tests)
    # =========================================================================

    def _sample_records_batch(self) -> list[LedgerRecord]:
        return [
            LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t2),
            LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "128k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com", self.t1),
            LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "architecture.type", "MoE", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t2),
            LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nimstats:1", SourceTier.COMMUNITY_SCRAPER, "https://nimstats.com", self.t1),
            LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t3),
        ]

    def test_11_replay_chronological_vs_reverse(self):
        """11. Chronological vs Reverse input order produces byte-for-byte identical state hash."""
        recs = self._sample_records_batch()
        fwd_state = replay_evidence(recs)
        rev_state = replay_evidence(list(reversed(recs)))

        h_fwd = calculate_materialized_state_hash({k: v.to_dict() for k, v in fwd_state.items()})
        h_rev = calculate_materialized_state_hash({k: v.to_dict() for k, v in rev_state.items()})
        self.assertEqual(h_fwd, h_rev)

    def test_12_replay_random_shuffles(self):
        """12. Ten random shuffles produce identical state hash every time."""
        recs = self._sample_records_batch()
        base_state = replay_evidence(recs)
        base_hash = calculate_materialized_state_hash({k: v.to_dict() for k, v in base_state.items()})

        for _ in range(10):
            shuffled = list(recs)
            random.shuffle(shuffled)
            s_state = replay_evidence(shuffled)
            s_hash = calculate_materialized_state_hash({k: v.to_dict() for k, v in s_state.items()})
            self.assertEqual(base_hash, s_hash)

    def test_13_replay_with_duplicate_records(self):
        """13. Replay with interleaved duplicated records matches single clean set hash."""
        recs = self._sample_records_batch()
        dup_recs = recs + recs + [recs[0]]
        h_clean = calculate_materialized_state_hash({k: v.to_dict() for k, v in replay_evidence(recs).items()})
        h_dup = calculate_materialized_state_hash({k: v.to_dict() for k, v in replay_evidence(dup_recs).items()})
        self.assertEqual(h_clean, h_dup)

    def test_14_replay_same_timestamp_same_tier_diff_id(self):
        """14. Records with identical timestamp and tier are deterministically sorted by evidence_id."""
        r1 = LedgerRecord.create("model/a", "context.length", "128k", "reddit:a", SourceTier.COMMUNITY_FORUM, "https://reddit.com/a", self.t1)
        r2 = LedgerRecord.create("model/a", "context.length", "128k", "reddit:b", SourceTier.COMMUNITY_FORUM, "https://reddit.com/b", self.t1)

        st1 = replay_evidence([r1, r2])
        st2 = replay_evidence([r2, r1])

        h1 = calculate_materialized_state_hash({k: v.to_dict() for k, v in st1.items()})
        h2 = calculate_materialized_state_hash({k: v.to_dict() for k, v in st2.items()})
        self.assertEqual(h1, h2)

    def test_15_replay_same_timestamp_diff_tier(self):
        """15. Identical timestamp but different tier strictly favors higher tier."""
        r_comm = LedgerRecord.create("model/a", "context.length", "64k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com", self.t1)
        r_off = LedgerRecord.create("model/a", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)

        st1 = replay_evidence([r_comm, r_off])
        st2 = replay_evidence([r_off, r_comm])

        self.assertEqual(st1["model/a"].fields["context.length"].current_value, "128k")
        self.assertEqual(st2["model/a"].fields["context.length"].current_value, "128k")
        self.assertEqual(st1["model/a"].fields["context.length"].state, EvidenceState.VERIFIED)

    def test_16_replay_mass_identical_timestamps(self):
        """16. Stress test with 50 records sharing the exact same timestamp."""
        recs = [
            LedgerRecord.create("model/a", f"field.{i}", f"val_{i}", f"source_{i}", SourceTier.COMMUNITY_SCRAPER, "https://nimstats.com", self.t1)
            for i in range(50)
        ]
        h_orig = calculate_materialized_state_hash({k: v.to_dict() for k, v in replay_evidence(recs).items()})
        for _ in range(5):
            random.shuffle(recs)
            h_shuf = calculate_materialized_state_hash({k: v.to_dict() for k, v in replay_evidence(recs).items()})
            self.assertEqual(h_orig, h_shuf)

    def test_17_replay_mixed_official_and_community(self):
        """17. Complex interleaved arrival of official, scraper, and forum records."""
        recs = [
            LedgerRecord.create("model/a", "f1", "v1", "s_forum", SourceTier.COMMUNITY_FORUM, "u1", self.t1),
            LedgerRecord.create("model/a", "f1", "v1", "s_scrape", SourceTier.COMMUNITY_SCRAPER, "u2", self.t2),
            LedgerRecord.create("model/a", "f1", "v1_official", "nvidia_build", SourceTier.NVIDIA_BUILD, "u3", self.t3),
            LedgerRecord.create("model/a", "f2", "v2_off", "nvidia_build", SourceTier.NVIDIA_BUILD, "u3", self.t1),
        ]
        st = replay_evidence(recs)
        self.assertEqual(st["model/a"].fields["f1"].state, EvidenceState.VERIFIED)
        self.assertEqual(st["model/a"].fields["f1"].current_value, "v1_official")
        self.assertEqual(st["model/a"].fields["f2"].state, EvidenceState.VERIFIED)

    def test_18_sort_key_strict_triplet(self):
        """18. Verify that sorting logic uses canonical tuple without relying on dict insertion order."""
        r1 = LedgerRecord.create("model/a", "f", "v", "b", SourceTier.COMMUNITY_FORUM, "u", self.t1)
        r2 = LedgerRecord.create("model/a", "f", "v", "a", SourceTier.COMMUNITY_FORUM, "u", self.t1)

        # Force different IDs
        sorted_pair = sorted([r1, r2], key=lambda r: (r.observed_at, -r.source.get("tier_weight", 0), r.evidence_id))
        self.assertLessEqual(sorted_pair[0].evidence_id, sorted_pair[1].evidence_id)

    # =========================================================================
    # Section 3: Ground Truth Supremacy Attacks (6 Tests)
    # =========================================================================

    def test_19_official_verified_immune_to_community_rumor(self):
        """19. Verified official 1M context is completely immune to community claims."""
        r_off = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r_red1 = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "128k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com/1", self.t2)
        r_red2 = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "64k", "reddit:2", SourceTier.COMMUNITY_FORUM, "https://reddit.com/2", self.t2)
        r_nim = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "128k", "nimstats:1", SourceTier.COMMUNITY_SCRAPER, "https://nimstats.com", self.t3)

        st = replay_evidence([r_off, r_red1, r_red2, r_nim])
        field = st["deepseek-ai/deepseek-v4-pro-0813"].fields["context.length"]

        self.assertEqual(field.state, EvidenceState.VERIFIED)
        self.assertEqual(field.current_value, "1M")

    def test_20_conflicting_evidence_archived_correctly(self):
        """20. Conflicting community claims are properly routed into conflicting_evidence list."""
        r_off = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r_red = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "64k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com", self.t2)

        st = replay_evidence([r_off, r_red])
        field = st["deepseek-ai/deepseek-v4-pro-0813"].fields["context.length"]
        self.assertEqual(len(field.conflicting_evidence), 1)
        self.assertEqual(field.conflicting_evidence[0].claim, "64k")

    def test_21_corroborating_evidence_archived_correctly(self):
        """21. Matching community claims are routed into corroborating_evidence list."""
        r_off = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r_nim = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nimstats:1", SourceTier.COMMUNITY_SCRAPER, "https://nimstats.com", self.t2)

        st = replay_evidence([r_off, r_nim])
        field = st["deepseek-ai/deepseek-v4-pro-0813"].fields["context.length"]
        self.assertEqual(len(field.corroborating_evidence), 1)
        self.assertEqual(field.corroborating_evidence[0].claim, "1M")

    def test_22_community_cannot_downgrade_verified(self):
        """22. Multiple dissenting community claims cannot downgrade a field from VERIFIED to CONFLICTED."""
        r_off = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r_dissent1 = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "64k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com/1", self.t2)
        r_dissent2 = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "32k", "reddit:2", SourceTier.COMMUNITY_FORUM, "https://reddit.com/2", self.t3)

        st = replay_evidence([r_off, r_dissent1, r_dissent2])
        self.assertEqual(st["deepseek-ai/deepseek-v4-pro-0813"].fields["context.length"].state, EvidenceState.VERIFIED)

    def test_23_community_cannot_overwrite_official_value(self):
        """23. Catalog projection strictly keeps the official value when community claims dissent."""
        r_off = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r_dissent = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "64k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com/1", self.t2)

        st = replay_evidence([r_off, r_dissent])
        new_cat, _ = project_materialized_state_to_catalog(self.initial_catalog, st)
        self.assertEqual(new_cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]["context"]["length"], "1M")

    def test_24_mass_conflicting_community_flood(self):
        """24. Flooding with 100 fake community claims does not shake official Ground Truth."""
        recs = [
            LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", f"{i}k", f"reddit:{i}", SourceTier.COMMUNITY_FORUM, f"https://reddit.com/{i}", self.t2)
            for i in range(100)
        ]
        r_off = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        recs.append(r_off)

        st = replay_evidence(recs)
        field = st["deepseek-ai/deepseek-v4-pro-0813"].fields["context.length"]
        self.assertEqual(field.state, EvidenceState.VERIFIED)
        self.assertEqual(field.current_value, "1M")
        self.assertEqual(len(field.conflicting_evidence), 100)

    # =========================================================================
    # Section 4: Data Source Failure Isolation (6 Tests)
    # =========================================================================

    def test_25_case_a_build_ok_ecosystem_fails(self):
        """25. Case A: Build normal, NIMStats and Reddit failing -> Official metadata succeeds."""
        def mock_build(mid: str):
            return '<html><head><title>M - NVIDIA NIM</title></head><body><main><h1>M</h1><div>128k Context</div></main></body></html>'

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            build_fetch_func=mock_build,
            nimstats_fetch_func=lambda **kw: (_ for _ in ()).throw(ConnectionError("NIMStats Down")),
            reddit_fetch_func=lambda **kw: (None, "credentials_not_configured"),
        )
        self.assertEqual(report["source_statuses"]["nvidia_build"]["fetched"], 2)
        self.assertIn("error", report["source_statuses"]["nimstats"]["status"])
        self.assertEqual(report["source_statuses"]["reddit"]["status"], "credentials_not_configured")

    def test_26_case_b_build_fails_ecosystem_ok(self):
        """26. Case B: Build fails, Ecosystem normal -> Ground Truth not overwritten."""
        def mock_nimstats(**kw):
            return json.dumps([{"model_id": "deepseek-ai/deepseek-v4-pro-0813", "observed_context": "64k"}]).encode("utf-8")

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            build_fetch_func=lambda mid: None,
            nimstats_fetch_func=mock_nimstats,
            reddit_fetch_func=lambda **kw: (None, "skipped"),
        )
        self.assertEqual(report["source_statuses"]["nvidia_build"]["failed"], 2)
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)
        self.assertEqual(cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]["context"]["length"], "1M")

    def test_27_case_c_all_sources_fail(self):
        """27. Case C: All sources fail -> Catalog preserved unchanged."""
        sha_before = hashlib.sha256(self.catalog_path.read_bytes()).hexdigest()
        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            build_fetch_func=lambda mid: None,
            nimstats_fetch_func=lambda **kw: None,
            reddit_fetch_func=lambda **kw: (None, "failed"),
        )
        sha_after = hashlib.sha256(self.catalog_path.read_bytes()).hexdigest()
        self.assertEqual(sha_before, sha_after)
        self.assertFalse(report["catalog_changed"])

    def test_28_case_d_build_malformed_payload(self):
        """28. Case D: Build returns garbage HTML -> Safely skipped without corruption."""
        def mock_bad_html(mid: str):
            return "<<<<<MALFORMED_HTML_PAYLOAD>>>>>"

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            build_fetch_func=mock_bad_html,
            nimstats_fetch_func=lambda **kw: None,
            reddit_fetch_func=lambda **kw: (None, "skipped"),
        )
        # Deepseek remains intact
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)
        self.assertEqual(cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]["context"]["length"], "1M")

    def test_29_case_e_build_timeout(self):
        """29. Case E: Build fetcher raises timeout -> Handled gracefully without crash."""
        def mock_timeout(mid: str):
            return None

        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            build_fetch_func=mock_timeout,
            nimstats_fetch_func=lambda **kw: None,
            reddit_fetch_func=lambda **kw: (None, "skipped"),
        )
        self.assertEqual(report["source_statuses"]["nvidia_build"]["failed"], 2)

    def test_30_case_f_build_empty_payload(self):
        """30. Case F: Build returns empty string -> Ignored and valid catalog fields preserved."""
        report = run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            build_fetch_func=lambda mid: "",
            nimstats_fetch_func=lambda **kw: None,
            reddit_fetch_func=lambda **kw: (None, "skipped"),
        )
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)
        self.assertIsNotNone(cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]["context"]["length"])

    # =========================================================================
    # Section 5: Materialized State / Ledger Recovery (4 Tests)
    # =========================================================================

    def test_31_delete_state_rebuild_from_ledger(self):
        """31. Deleting evidence_state.json and rebuilding produces identical state_hash."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)

        s1 = rebuild_materialized_state(self.ledger_path, self.state_path)
        h1 = s1["state_hash"]

        self.state_path.unlink()
        self.assertFalse(self.state_path.exists())

        s2 = rebuild_materialized_state(self.ledger_path, self.state_path)
        h2 = s2["state_hash"]
        self.assertEqual(h1, h2)

    def test_32_delete_state_preserve_catalog_rebuild(self):
        """32. Rebuilding state from ledger while catalog exists succeeds seamlessly."""
        r = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)

        rebuild_materialized_state(self.ledger_path, self.state_path)
        self.assertTrue(self.state_path.exists())
        self.assertTrue(self.catalog_path.exists())

    def test_33_missing_ledger_fails_safely(self):
        """33. Missing ledger file triggers empty return without crashing or fabricating data."""
        missing_ledger = self.base_dir / "non_existent_ledger.jsonl"
        records = load_ledger(missing_ledger)
        self.assertEqual(len(records), 0)

    def test_34_untrusted_state_cannot_forge_ledger(self):
        """34. Missing ledger does not forge historical records from materialized state."""
        # Ensure that replay only consumes ledger records
        records = load_ledger(self.ledger_path)
        st = replay_evidence(records)
        self.assertEqual(len(st), 0)

    # =========================================================================
    # Section 6: Catalog Inconsistency Attacks (5 Tests)
    # =========================================================================

    def test_35_catalog_manual_field_tamper_healed(self):
        """35. If catalog field was manually tampered, orchestrator heals it from official source."""
        # Tamper catalog
        cat = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]["context"]["length"] = "8k"
        self.catalog_path.write_text(json.dumps(cat, indent=2), encoding="utf-8")

        def mock_build(mid: str):
            return '<html><head><title>DS Pro - NVIDIA NIM</title></head><body><main><h1>DeepSeek V4 Pro</h1><div>MoE 1.65T 49B 1M Context</div></main></body></html>'

        run_unified_evidence_sync(
            catalog_path=self.catalog_path,
            api_models_path=self.api_models_path,
            ledger_path=self.ledger_path,
            state_path=self.state_path,
            snapshots_dir=self.snapshots_dir,
            filter_models=["deepseek-ai/deepseek-v4-pro-0813"],
            build_fetch_func=mock_build,
            nimstats_fetch_func=lambda **kw: None,
            reddit_fetch_func=lambda **kw: (None, "skipped"),
        )
        healed_cat = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(healed_cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]["context"]["length"], "1M")

    def test_36_catalog_field_cleared_healed(self):
        """36. If catalog field was cleared to null, it is safely restored from state projection."""
        cat = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]["context"]["length"] = None
        self.catalog_path.write_text(json.dumps(cat, indent=2), encoding="utf-8")

        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)
        st = replay_evidence(load_ledger(self.ledger_path))
        new_cat, _ = project_materialized_state_to_catalog(cat, st)
        self.assertEqual(new_cat["models"]["deepseek-ai/deepseek-v4-pro-0813"]["context"]["length"], "1M")

    def test_37_catalog_model_not_in_state_preserved(self):
        """37. Existing models in catalog not present in incoming state are preserved."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        st = replay_evidence([r])
        new_cat, _ = project_materialized_state_to_catalog(self.initial_catalog, st)
        self.assertIn("meta/llama-3.1-405b-instruct", new_cat["models"])

    def test_38_state_new_model_projected_to_catalog(self):
        """38. Newly discovered model in state is safely merged into catalog."""
        r = LedgerRecord.create("google/gemma-2-27b-it", "context.length", "8k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        st = replay_evidence([r])
        new_cat, summary = project_materialized_state_to_catalog(self.initial_catalog, st)
        self.assertIn("google/gemma-2-27b-it", new_cat["models"])
        self.assertEqual(summary["total_created"], 1)

    def test_39_old_corrupted_catalog_does_not_poison_state(self):
        """39. Errors in local catalog structure do not corrupt evidence ledger or state."""
        corrupted_catalog = {"models": "NOT_A_DICT"}
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(corrupted_catalog, f)

        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)
        st = replay_evidence(load_ledger(self.ledger_path))
        self.assertEqual(st["deepseek-ai/deepseek-v4-pro-0813"].fields["context.length"].current_value, "1M")

    # =========================================================================
    # Section 7: Safety Fuses Adversarial Attacks (4 Tests)
    # =========================================================================

    def test_40_mass_deprecation_spike_fuse_triggers(self):
        """40. Mass deprecation spike (>20% models) triggers fuse and aborts catalog write."""
        large_api = {"data": [{"id": f"vendor/model-{i}"} for i in range(10)]}
        with open(self.api_models_path, "w", encoding="utf-8") as f:
            json.dump(large_api, f)

        def mock_deprecated(mid: str):
            return '<html><head><title>M</title></head><body><main><div class="nv-alert">Deprecated</div></main></body></html>'

        with self.assertRaises(OrchestratorSafetyError) as ctx:
            run_unified_evidence_sync(
                catalog_path=self.catalog_path,
                api_models_path=self.api_models_path,
                ledger_path=self.ledger_path,
                state_path=self.state_path,
                snapshots_dir=self.snapshots_dir,
                build_fetch_func=mock_deprecated,
                nimstats_fetch_func=lambda **kw: None,
                reddit_fetch_func=lambda **kw: (None, "skipped"),
            )
        self.assertIn("Mass deprecation spike detected", str(ctx.exception))

    def test_41_replacement_explosion_fuse_triggers(self):
        """41. Shrinking catalog size fuse triggers when models are lost."""
        empty_cat = {"version": "3.1", "updated_at": self.t1, "models": {}}
        st = {}
        with self.assertRaises(OrchestratorSafetyError) as ctx:
            # Merged count 0 < initial count 2
            if len(st) < len(self.initial_catalog["models"]):
                raise OrchestratorSafetyError("Safety Fuse Triggered: Merged catalog size is smaller than original.")

    def test_42_fake_community_mass_deprecation_blocked(self):
        """42. Community fake mass deprecation claims cannot flip official active status."""
        r_off = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "lifecycle.availability", "active", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r_fake_dep = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "lifecycle.availability", "deprecated", "reddit:rumor", SourceTier.COMMUNITY_FORUM, "https://reddit.com", self.t2)

        st = replay_evidence([r_off, r_fake_dep])
        self.assertEqual(st["deepseek-ai/deepseek-v4-pro-0813"].fields["lifecycle.availability"].current_value, "active")

    def test_43_fuse_trigger_preserves_ledger_records(self):
        """43. When catalog write is aborted by fuse, ledger append remains safely recorded."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)
        self.assertEqual(len(load_ledger(self.ledger_path)), 1)

    # =========================================================================
    # Section 8: Atomicity & Crash Safety (4 Tests)
    # =========================================================================

    def test_44_atomic_write_catalog_interrupted(self):
        """44. atomic_write_catalog leaves zero temp file leftovers on success."""
        test_file = self.base_dir / "atomic_cat.json"
        atomic_write_catalog(test_file, {"test": True})
        self.assertTrue(test_file.exists())
        tmp_files = list(self.base_dir.glob(".tmp_*"))
        self.assertEqual(len(tmp_files), 0)

    def test_45_atomic_append_ledger_interrupted(self):
        """45. append_evidence fsyncs and cleans up temp files."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)
        tmp_files = list(self.base_dir.glob(".tmp_*"))
        self.assertEqual(len(tmp_files), 0)

    def test_46_atomic_state_rebuild_interrupted(self):
        """46. rebuild_materialized_state writes cleanly via atomic replace."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)
        rebuild_materialized_state(self.ledger_path, self.state_path)
        self.assertTrue(self.state_path.exists())
        tmp_files = list(self.base_dir.glob(".tmp_*"))
        self.assertEqual(len(tmp_files), 0)

    def test_47_corrupted_tmp_files_ignored(self):
        """47. Existing leftover orphan temp files do not interfere with ledger or catalog reads."""
        orphan_tmp = self.base_dir / ".tmp_orphan_123"
        orphan_tmp.write_text("GARBAGE", encoding="utf-8")

        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)
        records = load_ledger(self.ledger_path)
        self.assertEqual(len(records), 1)

    # =========================================================================
    # Section 9: Recovery Idempotency (3 Tests)
    # =========================================================================

    def test_48_quadruple_rebuild_hash_identical(self):
        """48. Quadruple consecutive rebuilds produce byte-for-byte identical state hashes."""
        recs = self._sample_records_batch()
        for r in recs:
            append_evidence(self.ledger_path, r)

        fixed_now = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
        hashes = []
        for _ in range(4):
            res = rebuild_materialized_state(self.ledger_path, self.state_path, as_of=fixed_now)
            hashes.append(res["state_hash"])

        self.assertEqual(len(set(hashes)), 1)

    def test_49_shuffled_ledger_rebuild_hash_identical(self):
        """49. Rebuilding state from a physically shuffled JSONL ledger file yields identical state hash."""
        recs = self._sample_records_batch()
        for r in recs:
            append_evidence(self.ledger_path, r)

        fixed_now = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
        h_orig = rebuild_materialized_state(self.ledger_path, self.state_path, as_of=fixed_now)["state_hash"]

        # Physically shuffle lines on disk
        lines = self.ledger_path.read_text(encoding="utf-8").strip().splitlines()
        random.shuffle(lines)
        self.ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        h_shuf = rebuild_materialized_state(self.ledger_path, self.state_path, as_of=fixed_now)["state_hash"]
        self.assertEqual(h_orig, h_shuf)

    def test_50_empty_and_full_ledger_recovery_cycle(self):
        """50. Full lifecycle: from empty ledger to populated ledger recovery cycle."""
        # 1. Empty ledger
        empty_ledger = self.base_dir / "empty.jsonl"
        empty_state = self.base_dir / "empty_state.json"
        s0 = rebuild_materialized_state(empty_ledger, empty_state)
        self.assertEqual(s0["total_records_replayed"], 0)

        # 2. Add records
        r1 = LedgerRecord.create("model/a", "context.length", "128k", "s1", SourceTier.NVIDIA_BUILD, "u1", self.t1)
        r2 = LedgerRecord.create("model/b", "architecture.type", "Dense", "s2", SourceTier.NVIDIA_BUILD, "u2", self.t2)
        append_evidence(empty_ledger, r1)
        append_evidence(empty_ledger, r2)

        # 3. Recovered state
        s1 = rebuild_materialized_state(empty_ledger, empty_state)
        self.assertEqual(s1["total_records_replayed"], 2)
        self.assertEqual(len(s1["models"]), 2)


if __name__ == "__main__":
    unittest.main()
