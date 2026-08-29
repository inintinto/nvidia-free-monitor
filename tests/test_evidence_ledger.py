"""
Comprehensive Test Suite for Evidence Ledger & Materialized View (Phase S3-D)
Validates immutability, deterministic evidence ID, canonical JSON, atomic append,
replay permutation invariance, conflict arbitration, rebuild idempotency, and audit verification.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import tempfile
import unittest

from src.catalog.evidence import (
    EvidenceItem,
    EvidenceState,
    FieldEvidence,
    ModelEvidenceRecord,
    SourceTier,
)
from src.catalog.evidence_ledger import (
    DuplicateEvidenceError,
    LedgerCorruptedError,
    LedgerRecord,
    append_evidence,
    calculate_materialized_state_hash,
    canonical_json_dumps,
    compute_evidence_id,
    compute_sha256_str,
    get_ledger_stats,
    load_ledger,
    rebuild_materialized_state,
    replay_evidence,
    validate_ledger_record,
    verify_ledger,
)


class TestEvidenceLedger(unittest.TestCase):
    """Test suite containing 28+ test cases for Evidence Ledger operations."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)
        self.ledger_path = self.base_dir / "evidence_ledger.jsonl"
        self.state_path = self.base_dir / "evidence_state.json"

        self.t1 = "2026-08-27T02:00:00+00:00"
        self.t2 = "2026-08-27T03:00:00+00:00"
        self.t3 = "2026-08-27T04:00:00+00:00"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_deterministic_evidence_id(self):
        """1. Evidence ID is strictly deterministic given identical canonical parameters."""
        id1 = compute_evidence_id(
            model_id="deepseek-ai/deepseek-v4-pro-0813",
            field_name="context.length",
            claim="1M",
            source_id="nvidia_build",
            source_tier="nvidia_build",
            source_url="https://build.nvidia.com",
            observed_at=self.t1,
            raw_evidence_sha256="a" * 64,
        )
        id2 = compute_evidence_id(
            model_id="deepseek-ai/deepseek-v4-pro-0813",
            field_name="context.length",
            claim="1M",
            source_id="nvidia_build",
            source_tier="nvidia_build",
            source_url="https://build.nvidia.com",
            observed_at=self.t1,
            raw_evidence_sha256="a" * 64,
        )
        self.assertEqual(id1, id2)
        self.assertEqual(len(id1), 64)

    def test_02_canonical_json_key_sorting(self):
        """2. Canonical JSON serializer produces key-sorted string with no extra whitespace."""
        d1 = {"b": 2, "a": 1, "c": {"y": 20, "x": 10}}
        d2 = {"c": {"x": 10, "y": 20}, "a": 1, "b": 2}
        self.assertEqual(canonical_json_dumps(d1), canonical_json_dumps(d2))
        self.assertEqual(canonical_json_dumps(d1), '{"a":1,"b":2,"c":{"x":10,"y":20}}')

    def test_03_append_success(self):
        """3. Single record is appended cleanly to JSONL ledger."""
        rec = LedgerRecord.create(
            model_id="deepseek-ai/deepseek-v4-pro-0813",
            field_name="context.length",
            claim="1M",
            source_id="nvidia_build",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com",
            observed_at=self.t1,
        )
        inserted, msg = append_evidence(self.ledger_path, rec)
        self.assertTrue(inserted)
        self.assertEqual(msg, "inserted")
        self.assertTrue(self.ledger_path.exists())

        records = load_ledger(self.ledger_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].evidence_id, rec.evidence_id)

    def test_04_duplicate_append_rejected(self):
        """4. Duplicate record append is safely rejected with already_exists without corrupting ledger."""
        rec = LedgerRecord.create(
            model_id="meta/llama-3.1-405b-instruct",
            field_name="context.length",
            claim="128k",
            source_id="nvidia_build",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com",
            observed_at=self.t1,
        )
        ins1, msg1 = append_evidence(self.ledger_path, rec)
        self.assertTrue(ins1)

        ins2, msg2 = append_evidence(self.ledger_path, rec)
        self.assertFalse(ins2)
        self.assertEqual(msg2, "already_exists")

        records = load_ledger(self.ledger_path)
        self.assertEqual(len(records), 1)

    def test_05_atomic_write_no_leftover_temp_files(self):
        """5. Ledger operations clean up temporary files."""
        rec = LedgerRecord.create(
            model_id="google/gemma-2-27b-it",
            field_name="architecture.type",
            claim="Dense",
            source_id="nvidia_build",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com",
            observed_at=self.t1,
        )
        append_evidence(self.ledger_path, rec)
        tmp_files = list(self.base_dir.glob(".tmp_*"))
        self.assertEqual(len(tmp_files), 0)

    def test_06_malformed_json_detection(self):
        """6. Malformed JSON line in ledger raises LedgerCorruptedError."""
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write('{"valid": 1}\n')
            f.write("BROKEN_SYNTAX_JSON_LINE\n")

        with self.assertRaises(LedgerCorruptedError):
            load_ledger(self.ledger_path)

    def test_07_corrupted_evidence_id_detection(self):
        """7. Tampered evidence_id is immediately detected and rejected."""
        rec = LedgerRecord.create(
            model_id="test/model",
            field_name="test.field",
            claim="value",
            source_id="source",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com",
            observed_at=self.t1,
        )
        tampered = rec.to_dict()
        tampered["evidence_id"] = "bad_checksum_hash"

        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(tampered) + "\n")

        with self.assertRaises(LedgerCorruptedError) as ctx:
            load_ledger(self.ledger_path)
        self.assertIn("Evidence ID mismatch", str(ctx.exception))

    def test_08_invalid_source_tier_detection(self):
        """8. Invalid source_tier raises LedgerCorruptedError."""
        rec = LedgerRecord.create(
            model_id="test/model",
            field_name="test.field",
            claim="val",
            source_id="s",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com",
            observed_at=self.t1,
        )
        bad_tier_data = rec.to_dict()
        bad_tier_data["source"]["source_tier"] = "unauthorized_tier"
        bad_tier_data["evidence_id"] = compute_evidence_id(
            model_id="test/model",
            field_name="test.field",
            claim="val",
            source_id="s",
            source_tier="unauthorized_tier",
            source_url="https://build.nvidia.com",
            observed_at=self.t1,
        )

        with self.assertRaises(LedgerCorruptedError) as ctx:
            validate_ledger_record(LedgerRecord.from_dict(bad_tier_data))
        self.assertIn("Invalid source_tier", str(ctx.exception))

    def test_09_invalid_model_id_format(self):
        """9. Missing vendor slash in model_id raises LedgerCorruptedError."""
        with self.assertRaises(LedgerCorruptedError) as ctx:
            rec = LedgerRecord.create(
                model_id="invalid_no_slash_model",
                field_name="context.length",
                claim="128k",
                source_id="s",
                source_tier=SourceTier.NVIDIA_BUILD,
                source_url="https://build.nvidia.com",
                observed_at=self.t1,
            )
            validate_ledger_record(rec)
        self.assertIn("Invalid model_id format", str(ctx.exception))

    def test_10_invalid_timestamp_detection(self):
        """10. Malformed ISO timestamp raises LedgerCorruptedError."""
        with self.assertRaises(LedgerCorruptedError) as ctx:
            rec = LedgerRecord.create(
                model_id="vendor/model",
                field_name="context.length",
                claim="128k",
                source_id="s",
                source_tier=SourceTier.NVIDIA_BUILD,
                source_url="https://build.nvidia.com",
                observed_at="NOT_A_TIMESTAMP",
            )
            validate_ledger_record(rec)
        self.assertIn("Invalid observed_at timestamp", str(ctx.exception))

    def test_11_raw_evidence_sha256_validation(self):
        """11. Non-hex 64-char raw_evidence_sha256 raises LedgerCorruptedError."""
        with self.assertRaises(LedgerCorruptedError) as ctx:
            rec = LedgerRecord.create(
                model_id="vendor/model",
                field_name="context.length",
                claim="128k",
                source_id="s",
                source_tier=SourceTier.NVIDIA_BUILD,
                source_url="https://build.nvidia.com",
                observed_at=self.t1,
                raw_evidence_sha256="short_hash_123",
            )
            validate_ledger_record(rec)
        self.assertIn("Invalid raw_evidence_sha256 hex format", str(ctx.exception))

    def test_12_chronological_replay(self):
        """12. Chronological replay builds accurate materialized states."""
        r1 = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com", self.t1)
        r2 = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nimstats:1", SourceTier.COMMUNITY_SCRAPER, "https://nimstats.com", self.t2)

        mat = replay_evidence([r1, r2])
        field = mat["meta/llama-3.1-405b-instruct"].fields["context.length"]
        self.assertEqual(field.state, EvidenceState.CORROBORATED)
        self.assertEqual(field.current_value, "128k")

    def test_13_reverse_order_replay_invariance(self):
        """13. Replaying in reverse order produces byte-for-byte identical state hash as chronological."""
        r1 = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com", self.t1)
        r2 = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nimstats:1", SourceTier.COMMUNITY_SCRAPER, "https://nimstats.com", self.t2)
        r3 = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t3)

        mat_fwd = replay_evidence([r1, r2, r3])
        mat_rev = replay_evidence([r3, r2, r1])

        h_fwd = calculate_materialized_state_hash({k: v.to_dict() for k, v in mat_fwd.items()})
        h_rev = calculate_materialized_state_hash({k: v.to_dict() for k, v in mat_rev.items()})
        self.assertEqual(h_fwd, h_rev)

    def test_14_shuffled_order_replay_invariance(self):
        """14. Shuffling evidence records yields identical deterministic materialized state."""
        records = [
            LedgerRecord.create("model/a", "context.length", "1M", "s1", SourceTier.COMMUNITY_FORUM, "u1", self.t1),
            LedgerRecord.create("model/a", "context.length", "1M", "s2", SourceTier.COMMUNITY_SCRAPER, "u2", self.t2),
            LedgerRecord.create("model/b", "architecture.type", "MoE", "s3", SourceTier.NVIDIA_BUILD, "u3", self.t1),
            LedgerRecord.create("model/b", "architecture.type", "Dense", "s4", SourceTier.COMMUNITY_FORUM, "u4", self.t2),
        ]
        base_mat = replay_evidence(records)
        base_hash = calculate_materialized_state_hash({k: v.to_dict() for k, v in base_mat.items()})

        for _ in range(5):
            shuffled = list(records)
            random.shuffle(shuffled)
            shuffled_mat = replay_evidence(shuffled)
            shuffled_hash = calculate_materialized_state_hash({k: v.to_dict() for k, v in shuffled_mat.items()})
            self.assertEqual(base_hash, shuffled_hash)

    def test_15_duplicate_evidence_replay_idempotency(self):
        """15. Replaying with duplicate records is idempotent and yields identical state hash."""
        r1 = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)

        mat_single = replay_evidence([r1])
        mat_dup = replay_evidence([r1, r1, r1])

        h1 = calculate_materialized_state_hash({k: v.to_dict() for k, v in mat_single.items()})
        h2 = calculate_materialized_state_hash({k: v.to_dict() for k, v in mat_dup.items()})
        self.assertEqual(h1, h2)

    def test_16_official_supremacy_over_community_in_replay(self):
        """16. Official Ground Truth suppresses conflicting community claims in replay."""
        r_comm = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "64k", "reddit:rumor", SourceTier.COMMUNITY_FORUM, "https://reddit.com", self.t1)
        r_off = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t2)

        mat = replay_evidence([r_comm, r_off])
        field = mat["deepseek-ai/deepseek-v4-pro-0813"].fields["context.length"]
        self.assertEqual(field.state, EvidenceState.VERIFIED)
        self.assertEqual(field.current_value, "1M")
        self.assertEqual(len(field.conflicting_evidence), 1)
        self.assertEqual(field.conflicting_evidence[0].source_id, "reddit:rumor")

    def test_17_community_conflict_in_replay(self):
        """17. Conflicting community claims of equal tier transition to CONFLICTED."""
        r1 = LedgerRecord.create("google/gemma-2-27b-it", "context.length", "32k", "reddit:a", SourceTier.COMMUNITY_FORUM, "https://reddit.com/a", self.t1)
        r2 = LedgerRecord.create("google/gemma-2-27b-it", "context.length", "8k", "reddit:b", SourceTier.COMMUNITY_FORUM, "https://reddit.com/b", self.t2)

        mat = replay_evidence([r1, r2])
        field = mat["google/gemma-2-27b-it"].fields["context.length"]
        self.assertEqual(field.state, EvidenceState.CONFLICTED)
        self.assertEqual(len(field.conflicting_evidence), 1)

    def test_18_conflicted_to_official_verified_recovery(self):
        """18. Conflicted field is resolved to VERIFIED when official evidence arrives."""
        r1 = LedgerRecord.create("google/gemma-2-27b-it", "context.length", "32k", "reddit:a", SourceTier.COMMUNITY_FORUM, "https://reddit.com/a", self.t1)
        r2 = LedgerRecord.create("google/gemma-2-27b-it", "context.length", "8k", "reddit:b", SourceTier.COMMUNITY_FORUM, "https://reddit.com/b", self.t2)
        r_off = LedgerRecord.create("google/gemma-2-27b-it", "context.length", "8k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t3)

        mat = replay_evidence([r1, r2, r_off])
        field = mat["google/gemma-2-27b-it"].fields["context.length"]
        self.assertEqual(field.state, EvidenceState.VERIFIED)
        self.assertEqual(field.current_value, "8k")
        self.assertEqual(len(field.conflicting_evidence), 1)
        self.assertEqual(field.conflicting_evidence[0].source_id, "reddit:a")
        self.assertEqual(len(field.corroborating_evidence), 1)
        self.assertEqual(field.corroborating_evidence[0].source_id, "reddit:b")

    def test_19_stale_to_corroborated_recovery_in_replay(self):
        """19. Stale observation is recovered to CORROBORATED by fresh community observation."""
        t_old = "2026-06-01T00:00:00+00:00"
        t_fresh = "2026-08-27T00:00:00+00:00"
        ref_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

        r_old = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "reddit:old", SourceTier.COMMUNITY_FORUM, "https://reddit.com", t_old)
        r_fresh = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nimstats:fresh", SourceTier.COMMUNITY_SCRAPER, "https://nimstats.com", t_fresh)

        mat = replay_evidence([r_old, r_fresh], as_of=ref_time)
        field = mat["meta/llama-3.1-405b-instruct"].fields["context.length"]
        self.assertEqual(field.state, EvidenceState.CORROBORATED)
        self.assertEqual(field.current_value, "128k")

    def test_20_stale_to_verified_recovery_in_replay(self):
        """20. Stale observation is recovered to VERIFIED by official evidence."""
        t_old = "2026-06-01T00:00:00+00:00"
        t_off = "2026-08-27T00:00:00+00:00"
        ref_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

        r_old = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "32k", "reddit:old", SourceTier.COMMUNITY_FORUM, "https://reddit.com", t_old)
        r_off = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", t_off)

        mat = replay_evidence([r_old, r_off], as_of=ref_time)
        field = mat["meta/llama-3.1-405b-instruct"].fields["context.length"]
        self.assertEqual(field.state, EvidenceState.VERIFIED)
        self.assertEqual(field.current_value, "128k")

    def test_21_rebuild_materialized_state(self):
        """21. rebuild_materialized_state outputs clean evidence_state.json with state_hash."""
        rec = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, rec)

        state_dict = rebuild_materialized_state(self.ledger_path, self.state_path)
        self.assertTrue(self.state_path.exists())
        self.assertEqual(state_dict["total_records_replayed"], 1)
        self.assertIn("meta/llama-3.1-405b-instruct", state_dict["models"])
        self.assertTrue(state_dict["state_hash"])

    def test_22_rebuild_sha256_equality_after_deletion(self):
        """22. Deleting evidence_state.json and rebuilding yields identical state_hash."""
        r1 = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r2 = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t2)
        append_evidence(self.ledger_path, r1)
        append_evidence(self.ledger_path, r2)

        fixed_now = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
        s1 = rebuild_materialized_state(self.ledger_path, self.state_path, as_of=fixed_now)
        hash1 = s1["state_hash"]

        # Delete state file and rebuild
        self.state_path.unlink()
        self.assertFalse(self.state_path.exists())

        s2 = rebuild_materialized_state(self.ledger_path, self.state_path, as_of=fixed_now)
        hash2 = s2["state_hash"]

        self.assertEqual(hash1, hash2)

    def test_23_verify_ledger_valid(self):
        """23. verify_ledger passes on valid, uncorrupted ledger."""
        r = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "architecture.type", "MoE", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        append_evidence(self.ledger_path, r)

        audit = verify_ledger(self.ledger_path)
        self.assertTrue(audit["verified"])
        self.assertEqual(audit["records_count"], 1)

    def test_24_stats_computation(self):
        """24. get_ledger_stats calculates accurate aggregates."""
        r1 = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r2 = LedgerRecord.create("meta/llama-3.1-405b-instruct", "context.length", "128k", "nimstats:1", SourceTier.COMMUNITY_SCRAPER, "https://nimstats.com", self.t2)
        r3 = LedgerRecord.create("google/gemma-2-27b-it", "context.length", "32k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com", self.t1)
        r4 = LedgerRecord.create("google/gemma-2-27b-it", "context.length", "8k", "reddit:2", SourceTier.COMMUNITY_FORUM, "https://reddit.com", self.t2)

        for r in [r1, r2, r3, r4]:
            append_evidence(self.ledger_path, r)

        stats = get_ledger_stats(self.ledger_path)
        self.assertEqual(stats["total_evidence"], 4)
        self.assertEqual(stats["unique_models"], 2)
        self.assertEqual(stats["unique_fields"], 1)
        self.assertEqual(stats["official_evidence"], 1)
        self.assertEqual(stats["community_evidence"], 3)
        self.assertEqual(stats["verified_fields"], 1)
        self.assertEqual(stats["conflicts"], 1)

    def test_25_empty_ledger_handling(self):
        """25. Empty ledger returns empty list, 0 stats, and valid verification."""
        records = load_ledger(self.ledger_path)
        self.assertEqual(len(records), 0)

        stats = get_ledger_stats(self.ledger_path)
        self.assertEqual(stats["total_evidence"], 0)

        audit = verify_ledger(self.ledger_path)
        self.assertTrue(audit["verified"])

    def test_26_multiple_fields_for_single_model(self):
        """26. Ledger tracks multiple fields for a single model independently."""
        r1 = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "context.length", "1M", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r2 = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "architecture.total_parameters", "1.65T", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        r3 = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "lifecycle.availability", "active", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)

        mat = replay_evidence([r1, r2, r3])
        model_ledger = mat["deepseek-ai/deepseek-v4-pro-0813"]
        self.assertEqual(len(model_ledger.fields), 3)
        self.assertEqual(model_ledger.fields["context.length"].state, EvidenceState.VERIFIED)
        self.assertEqual(model_ledger.fields["architecture.total_parameters"].state, EvidenceState.VERIFIED)
        self.assertEqual(model_ledger.fields["lifecycle.availability"].state, EvidenceState.VERIFIED)

    def test_27_pure_immutability_of_input_records(self):
        """27. replay_evidence guarantees input record dictionary/dataclass immutability."""
        rec = LedgerRecord.create("vendor/model", "context.length", "128k", "s", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
        rec_copy = deepcopy(rec)

        replay_evidence([rec])
        self.assertEqual(rec, rec_copy)

    def test_28_catalog_file_isolation_guarantee(self):
        """28. Ledger operations strictly NEVER touch data/model_catalog.json."""
        catalog_path = Path("data") / "model_catalog.json"
        if catalog_path.exists():
            sha_before = hashlib.sha256(catalog_path.read_bytes()).hexdigest()

            rec = LedgerRecord.create("test/model", "test.field", "123", "s", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", self.t1)
            append_evidence(self.ledger_path, rec)
            rebuild_materialized_state(self.ledger_path, self.state_path)
            get_ledger_stats(self.ledger_path)
            verify_ledger(self.ledger_path)

            sha_after = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
            self.assertEqual(sha_before, sha_after)


if __name__ == "__main__":
    unittest.main()
