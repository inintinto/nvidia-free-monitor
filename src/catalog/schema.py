from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class UsageStats:
    """NVIDIA Global API Calls Usage Metrics (Public Aggregate Only)."""
    api_calls_24h: Optional[str] = None
    api_calls_daily: Optional[str] = None
    api_calls_7d: Optional[str] = None
    api_calls_30d: Optional[str] = None
    usage_updated_at: Optional[str] = None
    usage_source: Optional[str] = "NVIDIA API Catalog Public Aggregate"

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "UsageStats":
        if not isinstance(data, dict):
            return cls()
        return cls(
            api_calls_24h=data.get("api_calls_24h"),
            api_calls_daily=data.get("api_calls_daily"),
            api_calls_7d=data.get("api_calls_7d"),
            api_calls_30d=data.get("api_calls_30d"),
            usage_updated_at=data.get("usage_updated_at"),
            usage_source=data.get("usage_source", "NVIDIA API Catalog Public Aggregate"),
        )

    def to_dict(self) -> dict:
        return {
            "api_calls_24h": self.api_calls_24h,
            "api_calls_daily": self.api_calls_daily,
            "api_calls_7d": self.api_calls_7d,
            "api_calls_30d": self.api_calls_30d,
            "usage_updated_at": self.usage_updated_at,
            "usage_source": self.usage_source,
        }


@dataclass
class OfficialLifecycle:
    """Official vendor deprecation and lifecycle status."""
    official_status: str = "active"  # active, deprecated, sunset, unlisted
    official_deprecation_date: Optional[str] = None
    sunset_date: Optional[str] = None
    deprecation_source_url: Optional[str] = None
    deprecation_notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "OfficialLifecycle":
        if not isinstance(data, dict):
            return cls()
        return cls(
            official_status=data.get("official_status", "active"),
            official_deprecation_date=data.get("official_deprecation_date"),
            sunset_date=data.get("sunset_date"),
            deprecation_source_url=data.get("deprecation_source_url"),
            deprecation_notes=data.get("deprecation_notes"),
        )

    def to_dict(self) -> dict:
        return {
            "official_status": self.official_status,
            "official_deprecation_date": self.official_deprecation_date,
            "sunset_date": self.sunset_date,
            "deprecation_source_url": self.deprecation_source_url,
            "deprecation_notes": self.deprecation_notes,
        }


@dataclass
class LifecycleRecord:
    """Observed endpoint lifecycle and official status."""
    model_id: str
    first_seen: Optional[str] = None
    free_since: Optional[str] = None
    last_seen: Optional[str] = None
    removed_at: Optional[str] = None
    is_currently_active: bool = True
    official_lifecycle: OfficialLifecycle = field(default_factory=OfficialLifecycle)

    @classmethod
    def from_dict(cls, model_id: str, data: Optional[dict]) -> "LifecycleRecord":
        if not isinstance(data, dict):
            return cls(model_id=model_id)
        return cls(
            model_id=model_id,
            first_seen=data.get("first_seen"),
            free_since=data.get("free_since"),
            last_seen=data.get("last_seen"),
            removed_at=data.get("removed_at"),
            is_currently_active=data.get("is_currently_active", True),
            official_lifecycle=OfficialLifecycle.from_dict(data.get("official_lifecycle")),
        )

    def to_dict(self) -> dict:
        return {
            "first_seen": self.first_seen,
            "free_since": self.free_since,
            "last_seen": self.last_seen,
            "removed_at": self.removed_at,
            "is_currently_active": self.is_currently_active,
            "official_lifecycle": self.official_lifecycle.to_dict(),
        }


@dataclass
class ModelDetail:
    """Rich Model Metadata and specifications."""
    model_id: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    platform: str = "NVIDIA NIM"
    provider: str = "Unknown"
    provider_id: str = "unknown"
    model_family: Optional[str] = None
    architecture: Optional[str] = None
    parameter_count: Optional[str] = None
    context_length: Optional[str] = None
    capabilities: list[str] = field(default_factory=lambda: ["Chat"])
    free_endpoint: bool = True
    source_urls: dict[str, str] = field(default_factory=dict)
    usage: UsageStats = field(default_factory=UsageStats)
    lifecycle: LifecycleRecord = field(default_factory=lambda: LifecycleRecord(model_id=""))

    def __post_init__(self):
        if not self.lifecycle.model_id:
            self.lifecycle.model_id = self.model_id

    @classmethod
    def from_dict(
        cls,
        model_id: str,
        catalog_data: Optional[dict] = None,
        lifecycle_data: Optional[dict] = None,
    ) -> "ModelDetail":
        catalog = catalog_data or {}
        lifecycle_record = LifecycleRecord.from_dict(model_id, lifecycle_data)

        # Infer default provider and display name if missing
        default_provider_id = model_id.split("/")[0] if "/" in model_id else "nvidia"
        default_provider_name = default_provider_id.replace("-", " ").title()
        raw_name = model_id.split("/")[-1] if "/" in model_id else model_id
        default_display = raw_name.replace("-", " ").replace("_", " ").title()

        return cls(
            model_id=model_id,
            display_name=catalog.get("display_name", default_display),
            aliases=catalog.get("aliases", []),
            platform=catalog.get("platform", "NVIDIA NIM"),
            provider=catalog.get("provider", default_provider_name),
            provider_id=catalog.get("provider_id", default_provider_id),
            model_family=catalog.get("model_family"),
            architecture=catalog.get("architecture"),
            parameter_count=catalog.get("parameter_count"),
            context_length=catalog.get("context_length"),
            capabilities=catalog.get("capabilities", ["Chat"]),
            free_endpoint=catalog.get("free_endpoint", True),
            source_urls=catalog.get("source_urls", {}),
            usage=UsageStats.from_dict(catalog.get("usage")),
            lifecycle=lifecycle_record,
        )

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "aliases": self.aliases,
            "platform": self.platform,
            "provider": self.provider,
            "provider_id": self.provider_id,
            "model_family": self.model_family,
            "architecture": self.architecture,
            "parameter_count": self.parameter_count,
            "context_length": self.context_length,
            "capabilities": self.capabilities,
            "free_endpoint": self.free_endpoint,
            "source_urls": self.source_urls,
            "usage": self.usage.to_dict(),
        }


@dataclass
class ResolveResult:
    """Output structure of Model Resolver."""
    query: str
    match_type: str  # "EXACT", "MULTIPLE", "EMPTY"
    matched_models: list[ModelDetail] = field(default_factory=list)
    total_matches: int = 0
    filter_provider: Optional[str] = None
    filter_capability: Optional[str] = None
