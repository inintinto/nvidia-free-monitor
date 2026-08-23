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


# -------------------------------------------------------------
# Stage 3A Standardized Sub-Schemas
# -------------------------------------------------------------

@dataclass
class ProviderInfo:
    id: str = "unknown"
    name: str = "Unknown"


@dataclass
class ClassificationInfo:
    family: Optional[str] = None
    tier: str = "standard"  # flagship, large, medium, small, embedding, specialized, unknown
    model_type: str = "chat"  # chat, reasoning, coding, vision, embedding, multimodal
    speed: str = "standard"  # fast, standard, unknown


@dataclass
class ArchitectureInfo:
    type: Optional[str] = None  # Dense, MoE, Embedding, etc.
    total_parameters: Optional[str] = None
    active_parameters: Optional[str] = None
    parameter_status: str = "unknown"  # official, observed, unknown


@dataclass
class ContextInfo:
    length: Optional[str] = None
    max_output: Optional[str] = None
    status: str = "unknown"  # official, observed, unknown


@dataclass
class ReleaseInfo:
    first_seen: Optional[str] = None
    release_date: Optional[str] = None
    status: str = "unknown"  # official, observed, unknown


@dataclass
class LinksInfo:
    nvidia: Optional[str] = None
    official: Optional[str] = None
    documentation: Optional[str] = None
    model_card: Optional[str] = None


@dataclass
class SourceMetadata:
    field_sources: dict[str, str] = field(default_factory=dict)
    confidence: str = "unknown"  # high, medium, low, unknown
    last_verified: Optional[str] = None


# -------------------------------------------------------------
# Stage 3A Comprehensive ModelDetail
# -------------------------------------------------------------

@dataclass
class ModelDetail:
    """Rich Model Metadata and specifications (Stage 3A Standardized)."""
    model_id: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    slug: Optional[str] = None
    platform: str = "NVIDIA NIM"

    # Nested structured schemas
    provider_info: ProviderInfo = field(default_factory=ProviderInfo)
    classification: ClassificationInfo = field(default_factory=ClassificationInfo)
    arch_info: ArchitectureInfo = field(default_factory=ArchitectureInfo)
    context_info: ContextInfo = field(default_factory=ContextInfo)
    release_info: ReleaseInfo = field(default_factory=ReleaseInfo)
    links: LinksInfo = field(default_factory=LinksInfo)
    source_metadata: SourceMetadata = field(default_factory=SourceMetadata)

    capabilities: list[str] = field(default_factory=lambda: ["Chat"])
    free_endpoint: bool = True
    usage: UsageStats = field(default_factory=UsageStats)
    lifecycle: LifecycleRecord = field(default_factory=lambda: LifecycleRecord(model_id=""))

    def __post_init__(self):
        if not self.lifecycle.model_id:
            self.lifecycle.model_id = self.model_id
        if not self.slug:
            self.slug = self.model_id.split("/")[-1] if "/" in self.model_id else self.model_id

    # Backward compatibility properties
    @property
    def provider(self) -> str:
        return self.provider_info.name

    @property
    def provider_id(self) -> str:
        return self.provider_info.id

    @property
    def model_family(self) -> Optional[str]:
        return self.classification.family

    @property
    def architecture(self) -> Optional[str]:
        return self.arch_info.type

    @property
    def parameter_count(self) -> Optional[str]:
        return self.arch_info.total_parameters

    @property
    def context_length(self) -> Optional[str]:
        return self.context_info.length

    @property
    def source_urls(self) -> dict[str, str]:
        urls = {}
        if self.links.nvidia:
            urls["nvidia_nim"] = self.links.nvidia
        if self.links.official:
            urls["official_site"] = self.links.official
        return urls

    @classmethod
    def from_dict(
        cls,
        model_id: str,
        catalog_data: Optional[dict] = None,
        lifecycle_data: Optional[dict] = None,
    ) -> "ModelDetail":
        catalog = catalog_data or {}
        lifecycle_record = LifecycleRecord.from_dict(model_id, lifecycle_data)

        # Default fallbacks
        default_provider_id = model_id.split("/")[0] if "/" in model_id else "nvidia"
        default_provider_name = default_provider_id.replace("-", " ").title()
        raw_name = model_id.split("/")[-1] if "/" in model_id else model_id
        default_display = raw_name.replace("-", " ").replace("_", " ").title()

        # Parse provider info (support nested or flat)
        p_raw = catalog.get("provider")
        if isinstance(p_raw, dict):
            provider_info = ProviderInfo(
                id=p_raw.get("id", default_provider_id),
                name=p_raw.get("name", default_provider_name),
            )
        elif isinstance(p_raw, str):
            provider_info = ProviderInfo(
                id=catalog.get("provider_id", default_provider_id),
                name=p_raw,
            )
        else:
            provider_info = ProviderInfo(id=default_provider_id, name=default_provider_name)

        # Parse classification
        c_raw = catalog.get("classification") or {}
        classification = ClassificationInfo(
            family=c_raw.get("family", catalog.get("model_family")),
            tier=c_raw.get("tier", "standard"),
            model_type=c_raw.get("model_type", "chat"),
            speed=c_raw.get("speed", "standard"),
        )

        # Parse architecture
        a_raw = catalog.get("architecture")
        if isinstance(a_raw, dict):
            arch_info = ArchitectureInfo(
                type=a_raw.get("type"),
                total_parameters=a_raw.get("total_parameters"),
                active_parameters=a_raw.get("active_parameters"),
                parameter_status=a_raw.get("parameter_status", "unknown"),
            )
        elif isinstance(a_raw, str):
            arch_info = ArchitectureInfo(
                type=a_raw,
                total_parameters=catalog.get("parameter_count"),
                active_parameters=catalog.get("parameter_count"),
                parameter_status="official" if catalog.get("parameter_count") else "unknown",
            )
        else:
            arch_info = ArchitectureInfo(
                type=None,
                total_parameters=catalog.get("parameter_count"),
                active_parameters=catalog.get("parameter_count"),
                parameter_status="unknown",
            )

        # Parse context
        ctx_raw = catalog.get("context")
        if isinstance(ctx_raw, dict):
            context_info = ContextInfo(
                length=ctx_raw.get("length"),
                max_output=ctx_raw.get("max_output"),
                status=ctx_raw.get("status", "unknown"),
            )
        else:
            context_info = ContextInfo(
                length=catalog.get("context_length"),
                max_output=None,
                status="official" if catalog.get("context_length") else "unknown",
            )

        # Parse release
        rel_raw = catalog.get("release") or {}
        release_info = ReleaseInfo(
            first_seen=rel_raw.get("first_seen"),
            release_date=rel_raw.get("release_date"),
            status=rel_raw.get("status", "unknown"),
        )

        # Parse links
        l_raw = catalog.get("links") or {}
        old_urls = catalog.get("source_urls") or {}
        links = LinksInfo(
            nvidia=l_raw.get("nvidia", old_urls.get("nvidia_nim")),
            official=l_raw.get("official", old_urls.get("official_site")),
            documentation=l_raw.get("documentation"),
            model_card=l_raw.get("model_card"),
        )

        # Parse source metadata
        src_raw = catalog.get("source_metadata") or {}
        source_metadata = SourceMetadata(
            field_sources=src_raw.get("field_sources", {}),
            confidence=src_raw.get("confidence", "unknown"),
            last_verified=src_raw.get("last_verified"),
        )

        # Parse usage
        ep_raw = catalog.get("endpoint") or {}
        usage_data = catalog.get("usage") or {
            "api_calls_24h": ep_raw.get("api_calls_24h"),
            "api_calls_daily": ep_raw.get("api_calls_daily"),
            "api_calls_7d": ep_raw.get("api_calls_7d"),
            "api_calls_30d": ep_raw.get("api_calls_30d"),
        }
        usage = UsageStats.from_dict(usage_data)

        return cls(
            model_id=model_id,
            display_name=catalog.get("display_name", default_display),
            aliases=catalog.get("aliases", []),
            slug=catalog.get("slug", raw_name),
            platform=catalog.get("platform", "NVIDIA NIM"),
            provider_info=provider_info,
            classification=classification,
            arch_info=arch_info,
            context_info=context_info,
            release_info=release_info,
            links=links,
            source_metadata=source_metadata,
            capabilities=catalog.get("capabilities", ["Chat"]),
            free_endpoint=catalog.get("free_endpoint", ep_raw.get("available", True)),
            usage=usage,
            lifecycle=lifecycle_record,
        )

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "aliases": self.aliases,
            "slug": self.slug,
            "platform": self.platform,
            "provider": {
                "id": self.provider_info.id,
                "name": self.provider_info.name,
            },
            "classification": {
                "family": self.classification.family,
                "tier": self.classification.tier,
                "model_type": self.classification.model_type,
                "speed": self.classification.speed,
            },
            "architecture": {
                "type": self.arch_info.type,
                "total_parameters": self.arch_info.total_parameters,
                "active_parameters": self.arch_info.active_parameters,
                "parameter_status": self.arch_info.parameter_status,
            },
            "context": {
                "length": self.context_info.length,
                "max_output": self.context_info.max_output,
                "status": self.context_info.status,
            },
            "capabilities": self.capabilities,
            "release": {
                "first_seen": self.release_info.first_seen,
                "release_date": self.release_info.release_date,
                "status": self.release_info.status,
            },
            "links": {
                "nvidia": self.links.nvidia,
                "official": self.links.official,
                "documentation": self.links.documentation,
                "model_card": self.links.model_card,
            },
            "source_metadata": {
                "field_sources": self.source_metadata.field_sources,
                "confidence": self.source_metadata.confidence,
                "last_verified": self.source_metadata.last_verified,
            },
            "free_endpoint": self.free_endpoint,
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
