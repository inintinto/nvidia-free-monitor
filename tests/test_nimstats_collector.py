"""
Unit Tests for NIMStats Ecosystem Signal Ingestion & Evidence Adapter (Phase S3-B)
Validates parser, schema drift resilience, SHA-256 evidence integrity,
adapter conversion, Evidence State Machine corroboration/conflicts, and Ground Truth supremacy.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from src.catalog.ecosystem.nimstats import (
    EcosystemSignal,
    compute_sha256,
    fetch_nimstats_data,
    nimstats_to_evidence_items,
    parse_nimstats_payload,
    save_nimstats_raw_evidence,
)
from src.catalog.evidence import (
    EvidenceItem,
    EvidenceState,
    FieldEvidence,
    SourceTier,
    add_evidence,
    check_staleness,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ecosystem"


def load_fixture_bytes(filename: str) -> bytes:
    with open(FIXTURES_DIR / filename, "rb") as f:
        return f.read()


class TestNIMStatsCollector(unittest.TestCase):
    """Test suite for NIMStats ecosystem signals and evidence state machine integration."""

    def setUp(self):
        self.now_dt = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
        self.now_iso = self.now_dt.isoformat()

    def test_01_parse_valid_nimstats_fixture(self):
        """1. Valid NIMStats fixture parses all models, throughput, and observed fields correctly."""
        raw_bytes = load_fixture_bytes("nimstats_valid.json")
        signals, malformed = parse_nimstats_payload(raw_bytes)

        self.assertEqual(len(signals), 3)
        self.assertEqual(len(malformed), 0)

        ds = next(s for s in signals if s.model_id == "deepseek-ai/deepseek-v4-pro-0813")
        self.assertEqual(ds.tokens_per_sec, 88.0)
        self.assertEqual(ds.ttft_ms, 120.5)
        self.assertEqual(ds.success_rate, 1.0)
        self.assertEqual(ds.observed_context, "1M")
        self.assertEqual(ds.observed_status, "active")
        self.assertEqual(ds.speed_rank, 3)

    def test_02_parse_empty_fixture(self):
        """2. Empty fixture returns zero signals and zero errors safely."""
        raw_bytes = load_fixture_bytes("nimstats_empty.json")
        signals, malformed = parse_nimstats_payload(raw_bytes)

        self.assertEqual(len(signals), 0)
        self.assertEqual(len(malformed), 0)

    def test_03_parse_malformed_fixture_graceful_recovery(self):
        """3. Malformed rows without vendor/model are rejected while valid rows are extracted."""
        raw_bytes = load_fixture_bytes("nimstats_malformed.json")
        signals, malformed = parse_nimstats_payload(raw_bytes)

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].model_id, "meta/llama-3.1-405b-instruct")
        self.assertIsNone(signals[0].tokens_per_sec)  # String not float converted gracefully
        self.assertEqual(signals[0].observed_context, "128k")
        self.assertEqual(len(malformed), 2)

    def test_04_schema_drift_resilience(self):
        """4. Schema drift with alternative field names (model, tps, latency, uptime) parses correctly."""
        raw_bytes = load_fixture_bytes("nimstats_drift.json")
        signals, malformed = parse_nimstats_payload(raw_bytes)

        self.assertEqual(len(signals), 2)
        self.assertEqual(len(malformed), 0)

        llama = next(s for s in signals if s.model_id == "meta/llama-3.1-405b-instruct")
        self.assertEqual(llama.tokens_per_sec, 43.1)
        self.assertEqual(llama.ttft_ms, 178.0)
        self.assertEqual(llama.success_rate, 0.998)
        self.assertEqual(llama.observed_context, "128k")

    def test_05_save_raw_evidence_and_sha256_integrity(self):
        """5. Raw evidence is saved with exact byte fidelity and matching SHA-256 metadata."""
        raw_bytes = load_fixture_bytes("nimstats_valid.json")
        expected_hash = compute_sha256(raw_bytes)

        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            target_file, saved_hash = save_nimstats_raw_evidence(
                raw_bytes=raw_bytes,
                base_dir=base_path,
                source_url="https://nimstats.com/api/top",
                now=self.now_dt,
            )

            self.assertEqual(saved_hash, expected_hash)
            self.assertTrue(target_file.exists())
            self.assertEqual(compute_sha256(target_file.read_bytes()), expected_hash)

            meta_file = base_path / f"{target_file.stem}.meta.json"
            self.assertTrue(meta_file.exists())
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["sha256"], expected_hash)
            self.assertEqual(meta["source"], "NIMStats")

    def test_06_evidence_adapter_conversion(self):
        """6. nimstats_to_evidence_items generates appropriate EvidenceItems with COMMUNITY_SCRAPER tier."""
        signal = EcosystemSignal(
            model_id="deepseek-ai/deepseek-v4-pro-0813",
            observed_context="1M",
            observed_status="active",
            observed_at=self.now_iso,
        )

        pairs = nimstats_to_evidence_items(signal, now=self.now_dt)
        self.assertEqual(len(pairs), 2)

        fn1, ev1 = pairs[0]
        self.assertEqual(fn1, "context.length")
        self.assertEqual(ev1.source_tier, SourceTier.COMMUNITY_SCRAPER)
        self.assertEqual(ev1.claim, "1M")

        fn2, ev2 = pairs[1]
        self.assertEqual(fn2, "lifecycle.availability")
        self.assertEqual(ev2.source_tier, SourceTier.COMMUNITY_SCRAPER)
        self.assertEqual(ev2.claim, "active")

    def test_07_corroboration_with_existing_observation(self):
        """7. NIMStats evidence matching prior community observation elevates state to CORROBORATED."""
        field_ev = FieldEvidence(
            field_name="context.length",
            current_value="128k",
            state=EvidenceState.OBSERVED,
            active_evidence=EvidenceItem(
                source_id="reddit:post_1",
                source_tier=SourceTier.COMMUNITY_FORUM,
                source_url="https://reddit.com/post_1",
                observed_at=self.now_iso,
                claim="128k",
            ),
        )

        nimstats_ev = EvidenceItem(
            source_id="nimstats:meta/llama-3.1-405b-instruct",
            source_tier=SourceTier.COMMUNITY_SCRAPER,
            source_url="https://nimstats.com",
            observed_at=self.now_iso,
            claim="128k",
        )

        updated = add_evidence(field_ev, nimstats_ev, now=self.now_dt)
        self.assertEqual(updated.state, EvidenceState.CORROBORATED)
        self.assertEqual(updated.current_value, "128k")
        # COMMUNITY_SCRAPER has higher weight than COMMUNITY_FORUM, so becomes active_evidence
        self.assertEqual(updated.active_evidence.source_tier, SourceTier.COMMUNITY_SCRAPER)

    def test_08_ground_truth_supremacy_over_nimstats(self):
        """8. Official Ground Truth CANNOT be modified by NIMStats conflicting evidence."""
        official_ev = FieldEvidence(
            field_name="context.length",
            current_value="1M",
            state=EvidenceState.VERIFIED,
            active_evidence=EvidenceItem(
                source_id="nvidia_build",
                source_tier=SourceTier.NVIDIA_BUILD,
                source_url="https://build.nvidia.com/deepseek-ai/deepseek-v4-pro-0813",
                observed_at=self.now_iso,
                claim="1M",
            ),
        )

        conflicting_nimstats = EvidenceItem(
            source_id="nimstats:deepseek",
            source_tier=SourceTier.COMMUNITY_SCRAPER,
            source_url="https://nimstats.com",
            observed_at=self.now_iso,
            claim="128k",  # Stale or inaccurate community claim
        )

        res = add_evidence(official_ev, conflicting_nimstats, now=self.now_dt)
        self.assertEqual(res.state, EvidenceState.VERIFIED)
        self.assertEqual(res.current_value, "1M")  # Ground Truth strictly intact
        self.assertEqual(len(res.conflicting_evidence), 1)
        self.assertEqual(res.conflicting_evidence[0].source_id, "nimstats:deepseek")

    def test_09_nimstats_evidence_staleness(self):
        """9. NIMStats evidence older than 30 days transitions to STALE state."""
        old_time = (self.now_dt - timedelta(days=35)).isoformat()
        field_ev = FieldEvidence(
            field_name="context.length",
            current_value="128k",
            state=EvidenceState.OBSERVED,
            active_evidence=EvidenceItem(
                source_id="nimstats:meta/llama-3.1-405b-instruct",
                source_tier=SourceTier.COMMUNITY_SCRAPER,
                source_url="https://nimstats.com",
                observed_at=old_time,
                claim="128k",
            ),
            ttl_days=30,
        )

        stale_check = check_staleness(field_ev, as_of=self.now_dt)
        self.assertEqual(stale_check.state, EvidenceState.STALE)

    def test_10_fetcher_graceful_fallback(self):
        """10. Fetcher returns None on unreachable endpoint without raising unhandled exceptions."""
        res = fetch_nimstats_data("http://127.0.0.1:54321/nonexistent", timeout=1, max_retries=0)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
