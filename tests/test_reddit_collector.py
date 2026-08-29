"""
Unit Tests for Reddit Community Ecosystem Signals & Evidence Adapter (Phase S3-C)
Validates parser, claim extraction, SHA-256 integrity, Evidence State Machine integration,
multi-source corroboration, conflict handling, and Ground Truth supremacy.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest

from src.catalog.ecosystem.reddit import (
    CommunitySignal,
    compute_sha256,
    fetch_reddit_data,
    parse_reddit_payload,
    reddit_to_evidence_items,
    save_reddit_raw_evidence,
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


class TestRedditCollector(unittest.TestCase):
    """Test suite for Reddit community signals and evidence state machine integration."""

    def setUp(self):
        self.now_dt = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
        self.now_iso = self.now_dt.isoformat()

    def test_01_parse_valid_reddit_fixture(self):
        """1. Valid Reddit fixture extracts model IDs, context length claims, and post metadata."""
        raw_bytes = load_fixture_bytes("reddit_valid.json")
        signals, malformed = parse_reddit_payload(raw_bytes)

        self.assertEqual(len(signals), 2)
        self.assertEqual(len(malformed), 0)

        s_llama = next(s for s in signals if s.model_id == "meta/llama-3.1-405b-instruct")
        self.assertEqual(s_llama.claim_type, "context.length")
        self.assertEqual(s_llama.claim_value, "128k")
        self.assertEqual(s_llama.subreddit, "LocalLLaMA")
        self.assertEqual(s_llama.post_id, "post_llama_128k")

        s_ds = next(s for s in signals if s.model_id == "deepseek-ai/deepseek-v4-pro-0813")
        self.assertEqual(s_ds.claim_type, "context.length")
        self.assertEqual(s_ds.claim_value, "1M")

    def test_02_parse_empty_fixture(self):
        """2. Empty listing returns zero signals and zero errors."""
        raw_bytes = load_fixture_bytes("reddit_empty.json")
        signals, malformed = parse_reddit_payload(raw_bytes)

        self.assertEqual(len(signals), 0)
        self.assertEqual(len(malformed), 0)

    def test_03_parse_malformed_fixture_safe_rejection(self):
        """3. Posts lacking model ID or actionable claims are safely recorded as malformed without crashing."""
        raw_bytes = load_fixture_bytes("reddit_malformed.json")
        signals, malformed = parse_reddit_payload(raw_bytes)

        self.assertEqual(len(signals), 0)
        self.assertEqual(len(malformed), 2)

    def test_04_parse_conflict_fixture_with_replacements(self):
        """4. Reddit conflict fixture extracts claims including deprecation and replacement models."""
        raw_bytes = load_fixture_bytes("reddit_conflict.json")
        signals, malformed = parse_reddit_payload(raw_bytes)

        # 2 context claims for gemma + 1 deprecation claim + 1 replacement claim for llama-2
        self.assertEqual(len(signals), 4)

        llama2_rep = next(s for s in signals if s.claim_type == "lifecycle.replacement_model_id")
        self.assertEqual(llama2_rep.model_id, "meta/llama-2-70b-chat")
        self.assertEqual(llama2_rep.claim_value, "meta/llama-3.3-70b-instruct")

    def test_05_save_raw_evidence_and_sha256_integrity(self):
        """5. Reddit raw evidence is atomically stored with exact SHA-256 metadata."""
        raw_bytes = load_fixture_bytes("reddit_valid.json")
        expected_hash = compute_sha256(raw_bytes)

        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            target_file, saved_hash = save_reddit_raw_evidence(
                raw_bytes=raw_bytes,
                base_dir=base_path,
                source_url="https://reddit.com/r/LocalLLaMA",
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
            self.assertEqual(meta["source"], "Reddit")

    def test_06_evidence_adapter_strictly_uses_community_forum_tier(self):
        """6. Reddit adapter converts CommunitySignal strictly into SourceTier.COMMUNITY_FORUM."""
        sig = CommunitySignal(
            model_id="deepseek-ai/deepseek-v4-pro-0813",
            claim_type="context.length",
            claim_value="1M",
            source_id="reddit:r/LocalLLaMA:post_123",
            source_url="https://reddit.com/r/LocalLLaMA/comments/123",
            subreddit="LocalLLaMA",
            post_id="post_123",
            observed_at=self.now_iso,
        )

        pairs = reddit_to_evidence_items(sig, now=self.now_dt)
        self.assertEqual(len(pairs), 1)

        fn, ev = pairs[0]
        self.assertEqual(fn, "context.length")
        self.assertEqual(ev.source_tier, SourceTier.COMMUNITY_FORUM)
        self.assertEqual(ev.claim, "1M")
        self.assertEqual(ev.confidence, 0.60)

    def test_07_reddit_cannot_override_official_verified_ground_truth(self):
        """7. Conflicting Reddit rumor CANNOT mutate or downgrade an officially VERIFIED field."""
        official_field = FieldEvidence(
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

        reddit_rumor = EvidenceItem(
            source_id="reddit:r/LocalLLaMA:post_fake",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/fake",
            observed_at=self.now_iso,
            claim="64k",  # Inaccurate community rumor
        )

        res = add_evidence(official_field, reddit_rumor, now=self.now_dt)
        self.assertEqual(res.state, EvidenceState.VERIFIED)
        self.assertEqual(res.current_value, "1M")  # Ground Truth unchanged
        self.assertEqual(len(res.conflicting_evidence), 1)
        self.assertEqual(res.conflicting_evidence[0].source_id, "reddit:r/LocalLLaMA:post_fake")

    def test_08_reddit_matching_official_becomes_corroboration(self):
        """8. Matching Reddit post is filed under corroborating_evidence without mutating VERIFIED."""
        official_field = FieldEvidence(
            field_name="context.length",
            current_value="128k",
            state=EvidenceState.VERIFIED,
            active_evidence=EvidenceItem(
                source_id="nvidia_build",
                source_tier=SourceTier.NVIDIA_BUILD,
                source_url="https://build.nvidia.com/meta/llama-3.1-405b-instruct",
                observed_at=self.now_iso,
                claim="128k",
            ),
        )

        reddit_match = EvidenceItem(
            source_id="reddit:r/LocalLLaMA:post_match",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/match",
            observed_at=self.now_iso,
            claim="128k",
        )

        res = add_evidence(official_field, reddit_match, now=self.now_dt)
        self.assertEqual(res.state, EvidenceState.VERIFIED)
        self.assertEqual(len(res.corroborating_evidence), 1)

    def test_09_multiple_independent_reddit_sources_transition_to_corroborated(self):
        """9. Multiple independent Reddit posts agreeing on a claim elevate unverified field to CORROBORATED."""
        field_ev = FieldEvidence(field_name="context.length")
        post1 = EvidenceItem(
            source_id="reddit:r/LocalLLaMA:p1",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/p1",
            observed_at=self.now_iso,
            claim="128k",
        )
        post2 = EvidenceItem(
            source_id="reddit:r/ArtificialInteligence:p2",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/p2",
            observed_at=self.now_iso,
            claim="128k",
        )

        s1 = add_evidence(field_ev, post1, now=self.now_dt)
        self.assertEqual(s1.state, EvidenceState.OBSERVED)

        s2 = add_evidence(s1, post2, now=self.now_dt)
        self.assertEqual(s2.state, EvidenceState.CORROBORATED)
        self.assertEqual(s2.current_value, "128k")

    def test_10_conflicting_reddit_sources_transition_to_conflicted(self):
        """10. Equal-tier conflicting Reddit posts transition field to CONFLICTED state."""
        field_ev = FieldEvidence(field_name="context.length")
        post1 = EvidenceItem(
            source_id="reddit:r/LocalLLaMA:claim_32k",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/32k",
            observed_at=self.now_iso,
            claim="32k",
        )
        post2 = EvidenceItem(
            source_id="reddit:r/LocalLLaMA:claim_8k",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/8k",
            observed_at=self.now_iso,
            claim="8k",
        )

        s1 = add_evidence(field_ev, post1, now=self.now_dt)
        self.assertEqual(s1.state, EvidenceState.OBSERVED)

        s2 = add_evidence(s1, post2, now=self.now_dt)
        self.assertEqual(s2.state, EvidenceState.CONFLICTED)
        self.assertEqual(len(s2.conflicting_evidence), 1)

    def test_11_reddit_alone_never_sets_verified_state(self):
        """11. Reddit evidence alone CANNOT promote a field to VERIFIED state."""
        field_ev = FieldEvidence(field_name="architecture.total_parameters")
        post = EvidenceItem(
            source_id="reddit:r/LocalLLaMA:post",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/post",
            observed_at=self.now_iso,
            claim="405B",
        )

        res = add_evidence(field_ev, post, now=self.now_dt)
        self.assertNotEqual(res.state, EvidenceState.VERIFIED)
        self.assertEqual(res.state, EvidenceState.OBSERVED)

    def test_12_fetcher_handles_missing_credentials_gracefully(self):
        """12. Fetcher safely returns credentials_not_configured when OAuth env vars are absent."""
        data, status = fetch_reddit_data(subreddit="LocalLLaMA", query="test", timeout=2)
        if not (os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET")):
            self.assertIsNone(data)
            self.assertEqual(status, "credentials_not_configured")


if __name__ == "__main__":
    unittest.main()
