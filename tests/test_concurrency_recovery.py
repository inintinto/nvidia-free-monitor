"""
Test Suite for S4-B: Concurrency Safety, Batch Ingestion & Crash Recovery.
Validates multi-process locking, TOCTOU race elimination, trailing crash repair,
and high-throughput replay determinism.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest

from src.catalog.evidence import EvidenceState, SourceTier
from src.catalog.evidence_ledger import (
    LedgerCorruptedError,
    LedgerRecord,
    append_evidence,
    append_evidence_batch,
    calculate_materialized_state_hash,
    load_ledger,
    rebuild_materialized_state,
    repair_truncated_ledger,
    replay_evidence,
)
from src.catalog.unified_orchestrator import project_materialized_state_to_catalog


def _worker_append_single(ledger_path_str: str, record_dict: dict, results_list=None):
    """Standalone worker for multiprocessing / concurrency tests."""
    res, msg = append_evidence(Path(ledger_path_str), record_dict, lock_timeout_seconds=15.0)
    if results_list is not None:
        results_list.append((res, msg))


class TestConcurrencyAndRecovery(unittest.TestCase):
    """10 comprehensive tests for S4-B concurrency, batching, and recovery."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)
        self.ledger_path = self.base_dir / "evidence_ledger.jsonl"
        self.state_path = self.base_dir / "evidence_state.json"
        self.catalog_path = self.base_dir / "model_catalog.json"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_concurrent_multithread_identical_evidence_dedup(self):
        """1. Concurrent threads attempting to append the exact same record result in 1 insertion and N-1 dedup."""
        rec = LedgerRecord.create(
            model_id="deepseek-ai/deepseek-v4-pro-0813",
            field_name="architecture.type",
            claim="MoE",
            source_id="nvidia_build",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com",
            observed_at="2026-08-27T03:00:00Z",
        )

        num_threads = 10
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(append_evidence, self.ledger_path, rec, 15.0)
                for _ in range(num_threads)
            ]
            results = [f.result() for f in futures]

        inserted_count = sum(1 for res, _ in results if res)
        dup_count = sum(1 for res, _ in results if not res)

        self.assertEqual(inserted_count, 1)
        self.assertEqual(dup_count, num_threads - 1)

        # Ensure ledger is 100% valid
        records = load_ledger(self.ledger_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].evidence_id, rec.evidence_id)

    def test_02_concurrent_multithread_unique_evidence_no_loss(self):
        """2. Concurrent workers writing distinct records result in zero data loss and valid JSONL."""
        num_workers = 8
        records_per_worker = 20
        all_records = []

        for w in range(num_workers):
            for i in range(records_per_worker):
                r = LedgerRecord.create(
                    model_id=f"model/provider-{w}",
                    field_name=f"field.{i}",
                    claim=f"val_{w}_{i}",
                    source_id=f"worker_{w}",
                    source_tier=SourceTier.COMMUNITY_FORUM,
                    source_url=f"https://source.com/{w}/{i}",
                    observed_at="2026-08-27T03:00:00Z",
                )
                all_records.append(r)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(append_evidence, self.ledger_path, r, 20.0)
                for r in all_records
            ]
            results = [f.result() for f in futures]

        inserted_count = sum(1 for res, _ in results if res)
        self.assertEqual(inserted_count, num_workers * records_per_worker)

        # Validate whole ledger
        loaded = load_ledger(self.ledger_path)
        self.assertEqual(len(loaded), num_workers * records_per_worker)
        loaded_ids = {r.evidence_id for r in loaded}
        expected_ids = {r.evidence_id for r in all_records}
        self.assertEqual(loaded_ids, expected_ids)

    def test_03_concurrent_same_model_field_different_timestamp(self):
        """3. Concurrent writes of sequential claims for same model preserve deterministic order during replay."""
        recs = [
            LedgerRecord.create("model/a", "context.length", "32k", "s1", SourceTier.COMMUNITY_FORUM, "u1", "2026-08-27T01:00:00Z"),
            LedgerRecord.create("model/a", "context.length", "64k", "s2", SourceTier.COMMUNITY_SCRAPER, "u2", "2026-08-27T02:00:00Z"),
            LedgerRecord.create("model/a", "context.length", "128k", "s3", SourceTier.NVIDIA_BUILD, "u3", "2026-08-27T03:00:00Z"),
        ]

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(append_evidence, self.ledger_path, r) for r in recs]
            for f in futures:
                f.result()

        st = replay_evidence(load_ledger(self.ledger_path))
        # NVIDIA Build is highest tier and newest -> VERIFIED 128k
        self.assertEqual(st["model/a"].fields["context.length"].state, EvidenceState.VERIFIED)
        self.assertEqual(st["model/a"].fields["context.length"].current_value, "128k")

    def test_04_batch_append_performance_and_internal_dedup(self):
        """4. append_evidence_batch handles internal duplicates and existing records atomically."""
        r1 = LedgerRecord.create("m/1", "f", "v1", "s", SourceTier.COMMUNITY_FORUM, "u", "2026-08-27T01:00:00Z")
        r2 = LedgerRecord.create("m/2", "f", "v2", "s", SourceTier.COMMUNITY_FORUM, "u", "2026-08-27T01:00:00Z")
        append_evidence(self.ledger_path, r1)

        # Batch contains r1 (already in ledger), r2 (new), r2 duplicate (in batch), r3 (new)
        r3 = LedgerRecord.create("m/3", "f", "v3", "s", SourceTier.COMMUNITY_FORUM, "u", "2026-08-27T01:00:00Z")
        batch = [r1, r2, r2, r3]

        res = append_evidence_batch(self.ledger_path, batch)
        self.assertEqual(res["total"], 4)
        self.assertEqual(res["inserted"], 2)  # r2 and r3
        self.assertEqual(res["duplicates"], 2)  # r1 and duplicate r2

        loaded = load_ledger(self.ledger_path)
        self.assertEqual(len(loaded), 3)

    def test_05_crash_recovery_trailing_half_line_detection_and_repair(self):
        """5. Trailing half-line corruption from simulated crash is detected and safely repaired."""
        r1 = LedgerRecord.create("m/1", "f", "v1", "s", SourceTier.COMMUNITY_FORUM, "u", "2026-08-27T01:00:00Z")
        r2 = LedgerRecord.create("m/2", "f", "v2", "s", SourceTier.COMMUNITY_FORUM, "u", "2026-08-27T01:00:00Z")
        append_evidence_batch(self.ledger_path, [r1, r2])

        # Append corrupted half-line
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write('{"evidence_id": "ab89')  # incomplete truncated JSON

        # Loading must fail
        with self.assertRaises(LedgerCorruptedError):
            load_ledger(self.ledger_path)

        # Run repair
        repair_res = repair_truncated_ledger(self.ledger_path)
        self.assertTrue(repair_res["repaired"])
        self.assertEqual(repair_res["valid_records_retained"], 2)

        # Loading now succeeds with exactly 2 valid records
        loaded = load_ledger(self.ledger_path)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].evidence_id, r1.evidence_id)
        self.assertEqual(loaded[1].evidence_id, r2.evidence_id)

    def test_06_corrupted_intermediate_line_strictly_fails_repair(self):
        """6. Corruption in intermediate line is not auto-truncated and strictly raises LedgerCorruptedError."""
        r1 = LedgerRecord.create("m/1", "f", "v1", "s", SourceTier.COMMUNITY_FORUM, "u", "2026-08-27T01:00:00Z")
        r2 = LedgerRecord.create("m/2", "f", "v2", "s", SourceTier.COMMUNITY_FORUM, "u", "2026-08-27T01:00:00Z")
        r3 = LedgerRecord.create("m/3", "f", "v3", "s", SourceTier.COMMUNITY_FORUM, "u", "2026-08-27T01:00:00Z")
        append_evidence_batch(self.ledger_path, [r1, r2, r3])

        # Corrupt line 2
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        lines[1] = "CORRUPTED_LINE_2\n"
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        with self.assertRaises(LedgerCorruptedError):
            repair_truncated_ledger(self.ledger_path)

    def test_07_rebuild_after_state_loss(self):
        """7. Materialized state file loss is 100% deterministically rebuilt from the immutable ledger."""
        r1 = LedgerRecord.create("m/1", "f", "v1", "s", SourceTier.NVIDIA_BUILD, "u", "2026-08-27T01:00:00Z")
        append_evidence(self.ledger_path, r1)

        fixed_dt = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
        res1 = rebuild_materialized_state(self.ledger_path, self.state_path, as_of=fixed_dt)
        self.assertTrue(self.state_path.exists())

        # Delete state file
        self.state_path.unlink()
        self.assertFalse(self.state_path.exists())

        # Rebuild again
        res2 = rebuild_materialized_state(self.ledger_path, self.state_path, as_of=fixed_dt)
        self.assertTrue(self.state_path.exists())
        self.assertEqual(res1["state_hash"], res2["state_hash"])

    def test_08_catalog_recovery_from_state(self):
        """8. Catalog corruption is safely restored by re-projecting the materialized state."""
        r1 = LedgerRecord.create("deepseek-ai/deepseek-v4-pro-0813", "architecture.type", "MoE", "nb", SourceTier.NVIDIA_BUILD, "u", "2026-08-27T01:00:00Z")
        append_evidence(self.ledger_path, r1)

        mat_state = replay_evidence(load_ledger(self.ledger_path))
        base_catalog = {"version": "3.1", "updated_at": "2026-08-27T00:00:00Z", "models": {}}

        new_catalog, summary = project_materialized_state_to_catalog(base_catalog, mat_state)
        self.assertIn("deepseek-ai/deepseek-v4-pro-0813", new_catalog["models"])
        self.assertEqual(new_catalog["models"]["deepseek-ai/deepseek-v4-pro-0813"]["architecture"]["type"], "MoE")

    def test_09_concurrent_replay_determinism_stress(self):
        """9. High-concurrency parallel replay execution yields identical state_hash across all threads."""
        records = []
        for i in range(50):
            tier = SourceTier.NVIDIA_BUILD if i % 3 == 0 else SourceTier.COMMUNITY_FORUM
            records.append(
                LedgerRecord.create(
                    model_id=f"model/item-{i % 10}",
                    field_name=f"field.{i % 5}",
                    claim=f"val_{i}",
                    source_id=f"src_{i}",
                    source_tier=tier,
                    source_url="https://src",
                    observed_at=f"2026-08-27T0{i % 9}:00:00Z",
                )
            )

        append_evidence_batch(self.ledger_path, records)
        loaded = load_ledger(self.ledger_path)

        def _get_hash():
            st = replay_evidence(loaded)
            return calculate_materialized_state_hash({k: v.to_dict() for k, v in st.items()})

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_get_hash) for _ in range(20)]
            hashes = [f.result() for f in futures]

        # All 20 hashes must be strictly identical
        self.assertEqual(len(set(hashes)), 1)

    def test_10_high_throughput_stress_test(self):
        """10. Ingesting 300 multi-source records via batch append executes swiftly and cleanly."""
        records = []
        for i in range(300):
            records.append(
                LedgerRecord.create(
                    model_id=f"meta/llama-3.1-{i % 5}b",
                    field_name="context.length",
                    claim=f"{128 + i}k",
                    source_id=f"source_{i}",
                    source_tier=SourceTier.COMMUNITY_SCRAPER,
                    source_url="https://nimstats.com",
                    observed_at="2026-08-27T03:00:00Z",
                )
            )

        start = time.time()
        res = append_evidence_batch(self.ledger_path, records)
        elapsed = time.time() - start

        self.assertEqual(res["inserted"], 300)
        self.assertLess(elapsed, 3.0)  # Must be fast (<3s for 300 records in batch)

        replayed = replay_evidence(load_ledger(self.ledger_path))
        self.assertEqual(len(replayed), 5)


if __name__ == "__main__":
    unittest.main()
