"""
Unit Tests for Evidence State Machine (Phase S3-A)
Validates 6 evidence lifecycle states, trust tiers, multi-source corroboration,
conflict detection, TTL staleness, official adjudication, and immutability.
"""

import copy
from datetime import datetime, timedelta, timezone
import unittest

from src.catalog.evidence import (
    EvidenceItem,
    EvidenceState,
    FieldEvidence,
    ModelEvidenceRecord,
    SourceTier,
    add_evidence,
    check_staleness,
)


class TestEvidenceStateMachine(unittest.TestCase):
    """Test suite for Evidence State Machine."""

    def setUp(self):
        self.now_dt = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
        self.now_iso = self.now_dt.isoformat()

    def test_01_initial_unverified_state(self):
        """1. Newly initialized field evidence starts in UNVERIFIED state with None current_value."""
        field_ev = FieldEvidence(field_name="context.length")
        self.assertEqual(field_ev.state, EvidenceState.UNVERIFIED)
        self.assertIsNone(field_ev.current_value)
        self.assertIsNone(field_ev.active_evidence)
        self.assertEqual(len(field_ev.corroborating_evidence), 0)
        self.assertEqual(len(field_ev.conflicting_evidence), 0)

    def test_02_single_observation_transitions_to_observed(self):
        """2. Single non-official observation transitions field from UNVERIFIED to OBSERVED."""
        field_ev = FieldEvidence(field_name="context.length")
        item = EvidenceItem(
            source_id="reddit:post_101",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/r/LocalLLaMA/comments/123",
            observed_at=self.now_iso,
            claim="128k",
            confidence=0.8,
        )

        res = add_evidence(field_ev, item, now=self.now_dt)
        self.assertEqual(res.state, EvidenceState.OBSERVED)
        self.assertEqual(res.current_value, "128k")
        self.assertEqual(res.active_evidence.source_id, "reddit:post_101")

    def test_03_multiple_agreeing_observations_transition_to_corroborated(self):
        """3. Multiple independent non-official observations with identical claim transition to CORROBORATED."""
        field_ev = FieldEvidence(field_name="context.length")
        item1 = EvidenceItem(
            source_id="reddit:post_101",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/r/LocalLLaMA/comments/123",
            observed_at=self.now_iso,
            claim="128k",
        )
        item2 = EvidenceItem(
            source_id="nimstats:scrape_55",
            source_tier=SourceTier.COMMUNITY_SCRAPER,
            source_url="https://nimstats.com/meta/llama-3.1-405b",
            observed_at=self.now_iso,
            claim="128k",
        )

        step1 = add_evidence(field_ev, item1, now=self.now_dt)
        self.assertEqual(step1.state, EvidenceState.OBSERVED)

        step2 = add_evidence(step1, item2, now=self.now_dt)
        self.assertEqual(step2.state, EvidenceState.CORROBORATED)
        self.assertEqual(step2.current_value, "128k")
        self.assertEqual(len(step2.corroborating_evidence), 1)

    def test_04_official_nvidia_build_transitions_to_verified(self):
        """4. Official NVIDIA Build evidence immediately transitions field to VERIFIED state."""
        field_ev = FieldEvidence(field_name="architecture.total_parameters")
        official_item = EvidenceItem(
            source_id="nvidia_build",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com/deepseek-ai/deepseek-v4-pro-0813",
            observed_at=self.now_iso,
            claim="1.65T",
            confidence=1.0,
        )

        res = add_evidence(field_ev, official_item, now=self.now_dt)
        self.assertEqual(res.state, EvidenceState.VERIFIED)
        self.assertEqual(res.current_value, "1.65T")
        self.assertEqual(res.active_evidence.source_tier, SourceTier.NVIDIA_BUILD)

    def test_05_official_verified_cannot_be_overridden_by_community_evidence(self):
        """5. Community sources CANNOT override or downgrade an officially VERIFIED field."""
        field_ev = FieldEvidence(
            field_name="architecture.total_parameters",
            current_value="1.65T",
            state=EvidenceState.VERIFIED,
            active_evidence=EvidenceItem(
                source_id="nvidia_build",
                source_tier=SourceTier.NVIDIA_BUILD,
                source_url="https://build.nvidia.com/deepseek-ai/deepseek-v4-pro-0813",
                observed_at=self.now_iso,
                claim="1.65T",
            ),
        )

        community_item = EvidenceItem(
            source_id="reddit:post_999",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/r/LocalLLaMA/comments/fake",
            observed_at=self.now_iso,
            claim="671B",  # Conflicting community rumor
        )

        res = add_evidence(field_ev, community_item, now=self.now_dt)
        self.assertEqual(res.state, EvidenceState.VERIFIED)
        self.assertEqual(res.current_value, "1.65T")  # Unchanged official Ground Truth
        self.assertEqual(len(res.conflicting_evidence), 1)
        self.assertEqual(res.conflicting_evidence[0].source_id, "reddit:post_999")

    def test_06_community_disagreement_with_verified_recorded_as_conflict(self):
        """6. When community agrees with official, it is recorded in corroborations without changing VERIFIED."""
        field_ev = FieldEvidence(
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

        community_item = EvidenceItem(
            source_id="nimstats:scrape_99",
            source_tier=SourceTier.COMMUNITY_SCRAPER,
            source_url="https://nimstats.com/deepseek",
            observed_at=self.now_iso,
            claim="1M",
        )

        res = add_evidence(field_ev, community_item, now=self.now_dt)
        self.assertEqual(res.state, EvidenceState.VERIFIED)
        self.assertEqual(len(res.corroborating_evidence), 1)

    def test_07_equal_tier_community_disagreement_transitions_to_conflicted(self):
        """7. Two non-official sources with equal tier disagreeing transitions state to CONFLICTED."""
        field_ev = FieldEvidence(field_name="context.length")
        item1 = EvidenceItem(
            source_id="reddit:post_1",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/post_1",
            observed_at=self.now_iso,
            claim="32k",
        )
        item2 = EvidenceItem(
            source_id="reddit:post_2",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/post_2",
            observed_at=self.now_iso,
            claim="128k",
        )

        step1 = add_evidence(field_ev, item1, now=self.now_dt)
        self.assertEqual(step1.state, EvidenceState.OBSERVED)

        step2 = add_evidence(step1, item2, now=self.now_dt)
        self.assertEqual(step2.state, EvidenceState.CONFLICTED)
        self.assertEqual(len(step2.conflicting_evidence), 1)

    def test_08_higher_tier_community_overrides_lower_tier_community(self):
        """8. Higher-trust non-official tier overrides lower-trust non-official tier."""
        field_ev = FieldEvidence(field_name="context.length")
        reddit_item = EvidenceItem(
            source_id="reddit:rumor",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/rumor",
            observed_at=self.now_iso,
            claim="32k",
        )
        probe_item = EvidenceItem(
            source_id="probe:active_test",
            source_tier=SourceTier.OBSERVED_PROBE,
            source_url="https://integrate.api.nvidia.com/probe",
            observed_at=self.now_iso,
            claim="128k",
        )

        step1 = add_evidence(field_ev, reddit_item, now=self.now_dt)
        self.assertEqual(step1.current_value, "32k")

        step2 = add_evidence(step1, probe_item, now=self.now_dt)
        self.assertEqual(step2.current_value, "128k")
        self.assertEqual(step2.active_evidence.source_tier, SourceTier.OBSERVED_PROBE)
        self.assertEqual(len(step2.conflicting_evidence), 1)

    def test_09_official_evidence_resolves_and_adjudicates_conflicted_state(self):
        """9. Incoming official evidence resolves prior CONFLICTED state and promotes to VERIFIED."""
        field_ev = FieldEvidence(field_name="context.length")
        item1 = EvidenceItem(
            source_id="reddit:post_1",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/post_1",
            observed_at=self.now_iso,
            claim="32k",
        )
        item2 = EvidenceItem(
            source_id="reddit:post_2",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/post_2",
            observed_at=self.now_iso,
            claim="128k",
        )
        conflicted_field = add_evidence(add_evidence(field_ev, item1, now=self.now_dt), item2, now=self.now_dt)
        self.assertEqual(conflicted_field.state, EvidenceState.CONFLICTED)

        # Official NVIDIA Build arrives
        official_item = EvidenceItem(
            source_id="nvidia_build",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com/meta/llama-3.1-405b",
            observed_at=self.now_iso,
            claim="128k",
        )

        resolved = add_evidence(conflicted_field, official_item, now=self.now_dt)
        self.assertEqual(resolved.state, EvidenceState.VERIFIED)
        self.assertEqual(resolved.current_value, "128k")
        self.assertIn("reddit:post_1", [e.source_id for e in resolved.conflicting_evidence])
        self.assertIn("reddit:post_2", [e.source_id for e in resolved.corroborating_evidence])

    def test_10_staleness_ttl_check_transitions_to_stale(self):
        """10. Non-official evidence older than TTL (30 days) transitions to STALE."""
        old_time = (self.now_dt - timedelta(days=35)).isoformat()
        field_ev = FieldEvidence(
            field_name="context.length",
            current_value="32k",
            state=EvidenceState.OBSERVED,
            active_evidence=EvidenceItem(
                source_id="reddit:old_post",
                source_tier=SourceTier.COMMUNITY_FORUM,
                source_url="https://reddit.com/old",
                observed_at=old_time,
                claim="32k",
            ),
            ttl_days=30,
        )

        stale_check = check_staleness(field_ev, as_of=self.now_dt)
        self.assertEqual(stale_check.state, EvidenceState.STALE)

    def test_11_verified_official_evidence_never_goes_stale(self):
        """11. Officially VERIFIED evidence NEVER goes stale regardless of age."""
        ancient_time = (self.now_dt - timedelta(days=365)).isoformat()
        field_ev = FieldEvidence(
            field_name="architecture.total_parameters",
            current_value="405B",
            state=EvidenceState.VERIFIED,
            active_evidence=EvidenceItem(
                source_id="nvidia_build",
                source_tier=SourceTier.NVIDIA_BUILD,
                source_url="https://build.nvidia.com/llama",
                observed_at=ancient_time,
                claim="405B",
            ),
            ttl_days=30,
        )

        stale_check = check_staleness(field_ev, as_of=self.now_dt)
        self.assertEqual(stale_check.state, EvidenceState.VERIFIED)

    def test_12_stale_evidence_recovered_by_new_official_evidence(self):
        """12. STALE evidence is immediately recovered and promoted to VERIFIED by new official evidence."""
        old_time = (self.now_dt - timedelta(days=40)).isoformat()
        stale_field = FieldEvidence(
            field_name="context.length",
            current_value="32k",
            state=EvidenceState.STALE,
            active_evidence=EvidenceItem(
                source_id="reddit:old",
                source_tier=SourceTier.COMMUNITY_FORUM,
                source_url="https://reddit.com/old",
                observed_at=old_time,
                claim="32k",
            ),
        )

        official_item = EvidenceItem(
            source_id="nvidia_build",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com/model",
            observed_at=self.now_iso,
            claim="128k",
        )

        recovered = add_evidence(stale_field, official_item, now=self.now_dt)
        self.assertEqual(recovered.state, EvidenceState.VERIFIED)
        self.assertEqual(recovered.current_value, "128k")

    def test_13_stale_evidence_recovered_by_fresh_corroboration(self):
        """13. STALE evidence is recovered to CORROBORATED when fresh matching observation arrives."""
        old_time = (self.now_dt - timedelta(days=40)).isoformat()
        stale_field = FieldEvidence(
            field_name="context.length",
            current_value="128k",
            state=EvidenceState.STALE,
            active_evidence=EvidenceItem(
                source_id="reddit:old",
                source_tier=SourceTier.COMMUNITY_FORUM,
                source_url="https://reddit.com/old",
                observed_at=old_time,
                claim="128k",
            ),
        )

        fresh_item = EvidenceItem(
            source_id="nimstats:fresh",
            source_tier=SourceTier.COMMUNITY_SCRAPER,
            source_url="https://nimstats.com/fresh",
            observed_at=self.now_iso,
            claim="128k",
        )

        recovered = add_evidence(stale_field, fresh_item, now=self.now_dt)
        self.assertEqual(recovered.state, EvidenceState.CORROBORATED)
        self.assertEqual(recovered.current_value, "128k")

    def test_14_pure_function_immutability_guarantee(self):
        """14. add_evidence guarantees pure function immutability on input records."""
        field_ev = FieldEvidence(
            field_name="context.length",
            current_value="32k",
            state=EvidenceState.OBSERVED,
            active_evidence=EvidenceItem(
                source_id="reddit:1",
                source_tier=SourceTier.COMMUNITY_FORUM,
                source_url="https://reddit.com/1",
                observed_at=self.now_iso,
                claim="32k",
            ),
        )
        incoming = EvidenceItem(
            source_id="nvidia_build",
            source_tier=SourceTier.NVIDIA_BUILD,
            source_url="https://build.nvidia.com",
            observed_at=self.now_iso,
            claim="128k",
        )

        field_ev_copy = copy.deepcopy(field_ev)
        incoming_copy = copy.deepcopy(incoming)

        add_evidence(field_ev, incoming, now=self.now_dt)

        self.assertEqual(field_ev.state, field_ev_copy.state)
        self.assertEqual(field_ev.current_value, field_ev_copy.current_value)
        self.assertEqual(incoming, incoming_copy)

    def test_15_model_evidence_record_ledger(self):
        """15. ModelEvidenceRecord aggregates multi-field evidence and serializes cleanly."""
        ledger = ModelEvidenceRecord(model_id="deepseek-ai/deepseek-v4-pro-0813")
        ledger.record_evidence(
            "architecture.type",
            EvidenceItem(
                source_id="nvidia_build",
                source_tier=SourceTier.NVIDIA_BUILD,
                source_url="https://build.nvidia.com",
                observed_at=self.now_iso,
                claim="MoE",
            ),
            now=self.now_dt,
        )
        ledger.record_evidence(
            "context.length",
            EvidenceItem(
                source_id="reddit:post",
                source_tier=SourceTier.COMMUNITY_FORUM,
                source_url="https://reddit.com",
                observed_at=self.now_iso,
                claim="1M",
            ),
            now=self.now_dt,
        )

        data = ledger.to_dict()
        self.assertEqual(data["model_id"], "deepseek-ai/deepseek-v4-pro-0813")
        self.assertEqual(data["fields"]["architecture.type"]["state"], "verified")
        self.assertEqual(data["fields"]["context.length"]["state"], "observed")

        reconstructed = ModelEvidenceRecord.from_dict(data)
        self.assertEqual(reconstructed.model_id, ledger.model_id)
        self.assertEqual(len(reconstructed.fields), 2)

    def test_16_empty_null_incoming_claim_ignored(self):
        """16. Empty strings or null claims are ignored and do not mutate state."""
        field_ev = FieldEvidence(
            field_name="context.length",
            current_value="128k",
            state=EvidenceState.VERIFIED,
        )
        null_item = EvidenceItem(
            source_id="bad_source",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://bad.com",
            observed_at=self.now_iso,
            claim=None,
        )

        res = add_evidence(field_ev, null_item, now=self.now_dt)
        self.assertEqual(res.state, EvidenceState.VERIFIED)
        self.assertEqual(res.current_value, "128k")

    def test_17_evidence_item_metadata_serialization(self):
        """17. EvidenceItem correctly preserves metadata fields through serialization."""
        item = EvidenceItem(
            source_id="reddit:test",
            source_tier=SourceTier.COMMUNITY_FORUM,
            source_url="https://reddit.com/r/LocalLLaMA",
            observed_at="2026-08-27T12:00:00+00:00",
            claim="MoE",
            confidence=0.85,
            raw_payload_snippet="DeepSeek V4 is MoE architecture",
        )
        d = item.to_dict()
        self.assertEqual(d["source_tier"], "community_forum")
        self.assertEqual(d["confidence"], 0.85)
        self.assertEqual(d["raw_payload_snippet"], "DeepSeek V4 is MoE architecture")

        item_back = EvidenceItem.from_dict(d)
        self.assertEqual(item_back.source_tier, SourceTier.COMMUNITY_FORUM)
        self.assertEqual(item_back.confidence, 0.85)


if __name__ == "__main__":
    unittest.main()
