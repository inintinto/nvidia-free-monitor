"""
Test Suite for S4-A: Timestamp Canonicalization & Replay Hardening.
Validates multi-timezone parsing, Canonical UTC standardization, physical chronology,
and deterministic replay permutation invariance across diverse ISO-8601 representations.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest

from src.catalog.evidence import EvidenceState, SourceTier
from src.catalog.evidence_ledger import (
    LedgerCorruptedError,
    LedgerRecord,
    append_evidence,
    calculate_materialized_state_hash,
    canonicalize_iso_timestamp,
    load_ledger,
    rebuild_materialized_state,
    replay_evidence,
)


class TestTimestampCanonicalization(unittest.TestCase):
    """Test suite containing 16 comprehensive unit tests for S4-A."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)
        self.ledger_path = self.base_dir / "test_ledger.jsonl"
        self.state_path = self.base_dir / "test_state.json"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_canonicalize_z_suffix(self):
        """1. ISO string with 'Z' suffix is standardized to +00:00 with 6-digit microseconds."""
        canon = canonicalize_iso_timestamp("2026-08-27T03:00:00Z")
        self.assertEqual(canon, "2026-08-27T03:00:00.000000+00:00")

    def test_02_canonicalize_plus_zero_offset(self):
        """2. ISO string with '+00:00' is standardized cleanly."""
        canon = canonicalize_iso_timestamp("2026-08-27T03:00:00+00:00")
        self.assertEqual(canon, "2026-08-27T03:00:00.000000+00:00")

    def test_03_canonicalize_plus_eight_offset(self):
        """3. Beijing time (+08:00) 11:00:00 converts accurately to UTC 03:00:00."""
        canon = canonicalize_iso_timestamp("2026-08-27T11:00:00+08:00")
        self.assertEqual(canon, "2026-08-27T03:00:00.000000+00:00")

    def test_04_canonicalize_minus_eight_offset(self):
        """4. US Pacific time (-08:00) 2026-08-26 19:00:00 converts to UTC 2026-08-27 03:00:00."""
        canon = canonicalize_iso_timestamp("2026-08-26T19:00:00-08:00")
        self.assertEqual(canon, "2026-08-27T03:00:00.000000+00:00")

    def test_05_canonicalize_with_microseconds(self):
        """5. ISO string with microseconds preserves fractional precision up to 6 digits."""
        canon = canonicalize_iso_timestamp("2026-08-27T03:00:00.123456Z")
        self.assertEqual(canon, "2026-08-27T03:00:00.123456+00:00")

    def test_06_canonicalize_without_microseconds(self):
        """6. ISO string without microseconds pads .000000 to maintain fixed 32-char length."""
        canon = canonicalize_iso_timestamp("2026-08-27T03:00:00Z")
        self.assertEqual(len(canon), 32)
        self.assertTrue(canon.endswith(".000000+00:00"))

    def test_07_equivalent_physical_times_equal_canonical_string(self):
        """7. Four distinct representations of the same physical instant output identical strings."""
        t_z = "2026-08-27T03:00:00Z"
        t_utc = "2026-08-27T03:00:00+00:00"
        t_bj = "2026-08-27T11:00:00+08:00"
        t_pst = "2026-08-26T19:00:00-08:00"

        c_z = canonicalize_iso_timestamp(t_z)
        c_utc = canonicalize_iso_timestamp(t_utc)
        c_bj = canonicalize_iso_timestamp(t_bj)
        c_pst = canonicalize_iso_timestamp(t_pst)

        self.assertEqual(c_z, c_utc)
        self.assertEqual(c_utc, c_bj)
        self.assertEqual(c_bj, c_pst)

    def test_08_cross_timezone_physical_chronology(self):
        """8. Beijing 08:01 (+08:00 -> UTC 00:01) is chronologically earlier than UTC 00:02."""
        t_earlier_bj = "2026-08-27T08:01:00+08:00"  # UTC 00:01:00
        t_later_utc = "2026-08-27T00:02:00Z"         # UTC 00:02:00

        c_earlier = canonicalize_iso_timestamp(t_earlier_bj)
        c_later = canonicalize_iso_timestamp(t_later_utc)

        self.assertLess(c_earlier, c_later)

    def test_09_invalid_timestamp_raises_value_error(self):
        """9. Malformed strings raise ValueError."""
        with self.assertRaises(ValueError):
            canonicalize_iso_timestamp("NOT_A_TIMESTAMP")

    def test_10_empty_and_whitespace_timestamp_raises_value_error(self):
        """10. Empty strings, whitespace, or None raise ValueError."""
        with self.assertRaises(ValueError):
            canonicalize_iso_timestamp("")
        with self.assertRaises(ValueError):
            canonicalize_iso_timestamp("   ")
        with self.assertRaises(ValueError):
            canonicalize_iso_timestamp(None)

    def test_11_replay_mixed_iso_formats_identical_physical_time(self):
        """11. Replaying records created with different timezone representations produces identical states."""
        r1 = LedgerRecord.create("model/a", "context.length", "128k", "s1", SourceTier.COMMUNITY_FORUM, "u1", "2026-08-27T03:00:00Z")
        r2 = LedgerRecord.create("model/a", "context.length", "128k", "s2", SourceTier.COMMUNITY_SCRAPER, "u2", "2026-08-27T11:00:00+08:00")

        st = replay_evidence([r1, r2])
        field = st["model/a"].fields["context.length"]
        self.assertEqual(field.state, EvidenceState.CORROBORATED)
        self.assertEqual(field.current_value, "128k")

    def test_12_replay_same_physical_time_different_tier_preserves_weight_priority(self):
        """12. Identical physical time across different tiers strictly prioritizes higher tier."""
        r_comm = LedgerRecord.create("model/a", "context.length", "64k", "reddit:1", SourceTier.COMMUNITY_FORUM, "https://reddit.com", "2026-08-27T11:00:00+08:00")
        r_off = LedgerRecord.create("model/a", "context.length", "128k", "nvidia_build", SourceTier.NVIDIA_BUILD, "https://build.nvidia.com", "2026-08-27T03:00:00Z")

        # Same physical instant (2026-08-27 03:00:00 UTC)
        st = replay_evidence([r_comm, r_off])
        self.assertEqual(st["model/a"].fields["context.length"].state, EvidenceState.VERIFIED)
        self.assertEqual(st["model/a"].fields["context.length"].current_value, "128k")

    def test_13_replay_same_physical_time_same_tier_tie_break_by_evidence_id(self):
        """13. Identical physical time and tier broken deterministically by evidence_id."""
        r1 = LedgerRecord.create("model/a", "context.length", "128k", "reddit:a", SourceTier.COMMUNITY_FORUM, "https://reddit.com/a", "2026-08-27T03:00:00Z")
        r2 = LedgerRecord.create("model/a", "context.length", "128k", "reddit:b", SourceTier.COMMUNITY_FORUM, "https://reddit.com/b", "2026-08-27T11:00:00+08:00")

        st1 = replay_evidence([r1, r2])
        st2 = replay_evidence([r2, r1])

        h1 = calculate_materialized_state_hash({k: v.to_dict() for k, v in st1.items()})
        h2 = calculate_materialized_state_hash({k: v.to_dict() for k, v in st2.items()})
        self.assertEqual(h1, h2)

    def test_14_replay_random_shuffled_with_mixed_timezones(self):
        """14. Shuffling records with mixed timezones produces identical state hash every time."""
        records = [
            LedgerRecord.create("model/a", "context.length", "128k", "s1", SourceTier.COMMUNITY_FORUM, "u1", "2026-08-27T01:00:00Z"),
            LedgerRecord.create("model/a", "context.length", "128k", "s2", SourceTier.COMMUNITY_SCRAPER, "u2", "2026-08-27T09:00:00+08:00"), # UTC 01:00
            LedgerRecord.create("model/b", "architecture.type", "MoE", "s3", SourceTier.NVIDIA_BUILD, "u3", "2026-08-26T17:00:00-08:00"), # UTC 01:00
            LedgerRecord.create("model/b", "architecture.type", "Dense", "s4", SourceTier.COMMUNITY_FORUM, "u4", "2026-08-27T03:00:00Z"),
        ]
        base_hash = calculate_materialized_state_hash({k: v.to_dict() for k, v in replay_evidence(records).items()})

        for _ in range(10):
            shuffled = list(records)
            random.shuffle(shuffled)
            s_hash = calculate_materialized_state_hash({k: v.to_dict() for k, v in replay_evidence(shuffled).items()})
            self.assertEqual(base_hash, s_hash)

    def test_15_replay_reversed_with_mixed_timezones(self):
        """15. Reversing mixed timezone records produces identical state hash to forward order."""
        records = [
            LedgerRecord.create("model/a", "context.length", "128k", "s1", SourceTier.COMMUNITY_FORUM, "u1", "2026-08-27T01:00:00Z"),
            LedgerRecord.create("model/a", "context.length", "128k", "s2", SourceTier.COMMUNITY_SCRAPER, "u2", "2026-08-27T09:00:00+08:00"),
            LedgerRecord.create("model/a", "context.length", "128k", "s3", SourceTier.NVIDIA_BUILD, "u3", "2026-08-27T02:00:00Z"),
        ]
        fwd_hash = calculate_materialized_state_hash({k: v.to_dict() for k, v in replay_evidence(records).items()})
        rev_hash = calculate_materialized_state_hash({k: v.to_dict() for k, v in replay_evidence(list(reversed(records))).items()})
        self.assertEqual(fwd_hash, rev_hash)

    def test_16_rebuild_materialized_state_with_mixed_timezones_idempotency(self):
        """16. rebuild_materialized_state on mixed timezone ledger file is completely idempotent."""
        r1 = LedgerRecord.create("model/a", "context.length", "128k", "s1", SourceTier.COMMUNITY_FORUM, "u1", "2026-08-27T01:00:00Z")
        r2 = LedgerRecord.create("model/a", "context.length", "128k", "s2", SourceTier.COMMUNITY_SCRAPER, "u2", "2026-08-27T09:00:00+08:00")
        append_evidence(self.ledger_path, r1)
        append_evidence(self.ledger_path, r2)

        fixed_as_of = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
        res1 = rebuild_materialized_state(self.ledger_path, self.state_path, as_of=fixed_as_of)
        res2 = rebuild_materialized_state(self.ledger_path, self.state_path, as_of=fixed_as_of)

        self.assertEqual(res1["state_hash"], res2["state_hash"])


if __name__ == "__main__":
    unittest.main()
