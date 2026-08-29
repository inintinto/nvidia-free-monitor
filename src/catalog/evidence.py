"""
Evidence State Machine (Phase S3-A)
Manages field-level evidence lifecycle, source trust tiers, multi-source corroboration,
conflict detection, staleness tracking, and official Ground Truth supremacy.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union


class EvidenceState(str, Enum):
    """Lifecycle states of an evidence record."""
    UNVERIFIED = "unverified"       # Default state: field is missing or empty
    OBSERVED = "observed"           # Single non-official observation
    CORROBORATED = "corroborated"   # Multiple independent non-official sources agreeing
    VERIFIED = "verified"           # Official NVIDIA Build or API evidence (Supreme authority)
    CONFLICTED = "conflicted"       # Conflicting claims from non-official sources
    STALE = "stale"                 # Evidence exceeded TTL without official verification


class SourceTier(str, Enum):
    """Trust tiers ordered by authority."""
    NVIDIA_BUILD = "nvidia_build"             # Tier 0 (Official Ground Truth - Weight 100)
    OFFICIAL_AGGREGATE = "official_aggregate" # Tier 1 (Official API usage aggregate - Weight 80)
    OBSERVED_PROBE = "observed_probe"         # Tier 2 (Direct active endpoint probe - Weight 60)
    COMMUNITY_SCRAPER = "community_scraper"   # Tier 3 (NIMStats, Continue proxy - Weight 40)
    COMMUNITY_FORUM = "community_forum"       # Tier 4 (Reddit, Discord - Weight 20)
    LOCAL_HEURISTIC = "local_heuristic"       # Tier 5 (Fallback slug heuristic - Weight 10)
    UNKNOWN = "unknown"                       # Tier 6 (Weight 0)


TIER_WEIGHTS: dict[SourceTier, int] = {
    SourceTier.NVIDIA_BUILD: 100,
    SourceTier.OFFICIAL_AGGREGATE: 80,
    SourceTier.OBSERVED_PROBE: 60,
    SourceTier.COMMUNITY_SCRAPER: 40,
    SourceTier.COMMUNITY_FORUM: 20,
    SourceTier.LOCAL_HEURISTIC: 10,
    SourceTier.UNKNOWN: 0,
}


@dataclass(frozen=True)
class EvidenceItem:
    """An atomic piece of evidence from a specific source."""
    source_id: str                          # e.g. "nvidia_build", "reddit:post_948", "nimstats:scrape_1"
    source_tier: SourceTier                 # Trust tier
    source_url: str                         # Source URL citation
    observed_at: str                        # ISO-8601 timestamp
    claim: Any                              # The claimed value (e.g. "128k", "1.65T", "deprecated")
    confidence: float = 1.0                 # Confidence score (0.0 to 1.0)
    raw_payload_snippet: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_tier": self.source_tier.value if isinstance(self.source_tier, SourceTier) else str(self.source_tier),
            "source_url": self.source_url,
            "observed_at": self.observed_at,
            "claim": self.claim,
            "confidence": self.confidence,
            "raw_payload_snippet": self.raw_payload_snippet,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceItem":
        tier_val = data.get("source_tier", "unknown")
        try:
            tier = SourceTier(tier_val)
        except ValueError:
            tier = SourceTier.UNKNOWN
        return cls(
            source_id=data.get("source_id", "unknown"),
            source_tier=tier,
            source_url=data.get("source_url", ""),
            observed_at=data.get("observed_at", datetime.now(timezone.utc).isoformat()),
            claim=data.get("claim"),
            confidence=float(data.get("confidence", 1.0)),
            raw_payload_snippet=data.get("raw_payload_snippet"),
        )


@dataclass
class FieldEvidence:
    """Evidence lifecycle tracking for a single metadata field."""
    field_name: str
    current_value: Any = None
    state: EvidenceState = EvidenceState.UNVERIFIED
    active_evidence: Optional[EvidenceItem] = None
    corroborating_evidence: list[EvidenceItem] = field(default_factory=list)
    conflicting_evidence: list[EvidenceItem] = field(default_factory=list)
    last_evaluated_at: Optional[str] = None
    ttl_days: int = 30

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "current_value": self.current_value,
            "state": self.state.value if isinstance(self.state, EvidenceState) else str(self.state),
            "active_evidence": self.active_evidence.to_dict() if self.active_evidence else None,
            "corroborating_evidence": [e.to_dict() for e in self.corroborating_evidence],
            "conflicting_evidence": [e.to_dict() for e in self.conflicting_evidence],
            "last_evaluated_at": self.last_evaluated_at,
            "ttl_days": self.ttl_days,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldEvidence":
        state_val = data.get("state", "unverified")
        try:
            st = EvidenceState(state_val)
        except ValueError:
            st = EvidenceState.UNVERIFIED

        active_raw = data.get("active_evidence")
        active_ev = EvidenceItem.from_dict(active_raw) if active_raw else None

        corrob_raw = data.get("corroborating_evidence", [])
        corrob_ev = [EvidenceItem.from_dict(e) for e in corrob_raw if isinstance(e, dict)]

        conflict_raw = data.get("conflicting_evidence", [])
        conflict_ev = [EvidenceItem.from_dict(e) for e in conflict_raw if isinstance(e, dict)]

        return cls(
            field_name=data.get("field_name", ""),
            current_value=data.get("current_value"),
            state=st,
            active_evidence=active_ev,
            corroborating_evidence=corrob_ev,
            conflicting_evidence=conflict_ev,
            last_evaluated_at=data.get("last_evaluated_at"),
            ttl_days=int(data.get("ttl_days", 30)),
        )


def _is_empty_or_none(val: Any) -> bool:
    """Check if value is effectively empty or null."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() in ["", "unknown", "None", "null"]:
        return True
    return False


def _is_official_tier(tier: SourceTier) -> bool:
    """Check if source tier represents official authority."""
    return tier in [SourceTier.NVIDIA_BUILD, SourceTier.OFFICIAL_AGGREGATE]


def _claims_match(c1: Any, c2: Any) -> bool:
    """Compare claims case-insensitively for strings or structurally for collections."""
    if c1 == c2:
        return True
    if isinstance(c1, str) and isinstance(c2, str):
        return c1.strip().lower() == c2.strip().lower()
    return False


def add_evidence(
    record: FieldEvidence,
    incoming: EvidenceItem,
    now: Optional[datetime] = None,
) -> FieldEvidence:
    """
    Pure-function evidence evaluation and state transition.
    Returns a new mutated copy of FieldEvidence without modifying the input object.
    """
    now_dt = now or datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    new_record = deepcopy(record)
    new_record.last_evaluated_at = now_iso

    # Ignore empty or invalid incoming claims
    if _is_empty_or_none(incoming.claim):
        return new_record

    incoming_tier = incoming.source_tier
    incoming_weight = TIER_WEIGHTS.get(incoming_tier, 0)

    # 1. State: VERIFIED exists
    if new_record.state == EvidenceState.VERIFIED and new_record.active_evidence:
        active_tier = new_record.active_evidence.source_tier
        active_weight = TIER_WEIGHTS.get(active_tier, 0)

        # Official incoming updating or reaffirming official verified value
        if _is_official_tier(incoming_tier):
            if _claims_match(incoming.claim, new_record.current_value):
                # Reaffirm official claim with latest timestamp
                new_record.active_evidence = incoming
            else:
                # Official correction / update
                new_record.active_evidence = incoming
                new_record.current_value = incoming.claim
            return new_record

        # Non-official incoming trying to interact with VERIFIED
        if _claims_match(incoming.claim, new_record.current_value):
            # Same claim -> add to corroborations
            if not any(e.source_id == incoming.source_id for e in new_record.corroborating_evidence):
                new_record.corroborating_evidence.append(incoming)
        else:
            # Different claim -> record as conflict, but official value remains completely intact and verified
            if not any(e.source_id == incoming.source_id for e in new_record.conflicting_evidence):
                new_record.conflicting_evidence.append(incoming)
        return new_record

    # 2. Incoming is Official Ground Truth (Supreme resolution)
    if _is_official_tier(incoming_tier):
        # Capture all previous evidence before reassigning active
        old_active = new_record.active_evidence
        all_prev = ([old_active] if old_active else []) + \
                   new_record.corroborating_evidence + new_record.conflicting_evidence

        # Official overrides all previous non-official states (observed, corroborated, conflicted, stale, unverified)
        new_record.state = EvidenceState.VERIFIED
        new_record.current_value = incoming.claim
        new_record.active_evidence = incoming

        new_corrob = []
        new_conflict = []
        for e in all_prev:
            if e.source_id == incoming.source_id:
                continue
            if _claims_match(e.claim, incoming.claim):
                if not any(x.source_id == e.source_id for x in new_corrob):
                    new_corrob.append(e)
            else:
                if not any(x.source_id == e.source_id for x in new_conflict):
                    new_conflict.append(e)

        new_record.corroborating_evidence = new_corrob
        new_record.conflicting_evidence = new_conflict
        return new_record

    # 3. Incoming is Non-Official
    # 3.1 Initial Observation from UNVERIFIED or empty
    if new_record.state == EvidenceState.UNVERIFIED or new_record.active_evidence is None:
        new_record.state = EvidenceState.OBSERVED
        new_record.current_value = incoming.claim
        new_record.active_evidence = incoming
        return new_record

    # 3.2 Existing is OBSERVED / CORROBORATED / CONFLICTED / STALE
    active_claim = new_record.active_evidence.claim
    active_tier = new_record.active_evidence.source_tier
    active_weight = TIER_WEIGHTS.get(active_tier, 0)

    if _claims_match(incoming.claim, active_claim):
        # Corroborating identical claim
        if incoming_weight > active_weight:
            # Higher trust non-official source promotes to active
            old_active = new_record.active_evidence
            new_record.active_evidence = incoming
            if old_active and not any(e.source_id == old_active.source_id for e in new_record.corroborating_evidence):
                new_record.corroborating_evidence.append(old_active)
        else:
            if not any(e.source_id == incoming.source_id for e in new_record.corroborating_evidence):
                new_record.corroborating_evidence.append(incoming)

        # Multi-source agreement elevates OBSERVED or STALE to CORROBORATED
        new_record.state = EvidenceState.CORROBORATED
        new_record.current_value = active_claim
    else:
        # Conflicting claim from non-official sources
        if incoming_weight > active_weight:
            # Higher weight non-official overrides lower weight
            old_active = new_record.active_evidence
            new_record.active_evidence = incoming
            new_record.current_value = incoming.claim
            if old_active:
                new_record.conflicting_evidence.append(old_active)
            new_record.state = EvidenceState.OBSERVED
        elif incoming_weight == active_weight:
            # Equal weight conflict -> escalate to CONFLICTED
            new_record.state = EvidenceState.CONFLICTED
            if not any(e.source_id == incoming.source_id for e in new_record.conflicting_evidence):
                new_record.conflicting_evidence.append(incoming)
        else:
            # Lower weight non-official does not change active value, recorded as conflict
            if not any(e.source_id == incoming.source_id for e in new_record.conflicting_evidence):
                new_record.conflicting_evidence.append(incoming)

    return new_record


def check_staleness(
    record: FieldEvidence,
    as_of: Optional[datetime] = None,
) -> FieldEvidence:
    """
    Check if non-official evidence has exceeded TTL and mark STALE.
    Official VERIFIED evidence NEVER goes stale.
    """
    if record.state == EvidenceState.VERIFIED or record.active_evidence is None:
        return record

    as_of_dt = as_of or datetime.now(timezone.utc)
    obs_time_str = record.active_evidence.observed_at

    try:
        obs_dt = datetime.fromisoformat(obs_time_str.replace("Z", "+00:00"))
        if obs_dt.tzinfo is None:
            obs_dt = obs_dt.replace(tzinfo=timezone.utc)
        obs_dt = obs_dt.astimezone(timezone.utc)
    except Exception:
        return record

    age_days = (as_of_dt - obs_dt).total_seconds() / 86400.0
    if age_days > record.ttl_days:
        new_record = deepcopy(record)
        new_record.state = EvidenceState.STALE
        new_record.last_evaluated_at = as_of_dt.isoformat()
        return new_record

    return record


@dataclass
class ModelEvidenceRecord:
    """Complete multi-field evidence ledger for a single model."""
    model_id: str
    fields: dict[str, FieldEvidence] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_field_evidence(self, field_name: str) -> FieldEvidence:
        """Get or initialize a field evidence record."""
        if field_name not in self.fields:
            self.fields[field_name] = FieldEvidence(field_name=field_name)
        return self.fields[field_name]

    def record_evidence(
        self,
        field_name: str,
        incoming: EvidenceItem,
        now: Optional[datetime] = None,
    ) -> None:
        """Add evidence and transition state for a specific field."""
        curr = self.get_field_evidence(field_name)
        updated = add_evidence(curr, incoming, now=now)
        self.fields[field_name] = updated
        self.updated_at = (now or datetime.now(timezone.utc)).isoformat()

    def evaluate_all_staleness(self, as_of: Optional[datetime] = None) -> None:
        """Evaluate TTL staleness across all fields."""
        for fn, fe in list(self.fields.items()):
            self.fields[fn] = check_staleness(fe, as_of=as_of)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "updated_at": self.updated_at,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelEvidenceRecord":
        model_id = data.get("model_id", "unknown")
        updated_at = data.get("updated_at", datetime.now(timezone.utc).isoformat())
        fields_data = data.get("fields", {})
        parsed_fields = {}
        for k, v in fields_data.items():
            if isinstance(v, dict):
                parsed_fields[k] = FieldEvidence.from_dict(v)
        return cls(model_id=model_id, fields=parsed_fields, updated_at=updated_at)
