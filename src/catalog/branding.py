"""Provider Branding and Model Classification system for Python Catalog."""

from typing import Optional


PROVIDER_REGISTRY = {
    "deepseek-ai": {
        "id": "deepseek-ai",
        "name": "DeepSeek AI",
        "short_name": "DeepSeek",
        "icon": "🐋",
        "official_url": "https://www.deepseek.com",
    },
    "nvidia": {
        "id": "nvidia",
        "name": "NVIDIA",
        "short_name": "NVIDIA",
        "icon": "🦾",
        "official_url": "https://www.nvidia.com",
    },
    "meta": {
        "id": "meta",
        "name": "Meta",
        "short_name": "Meta",
        "icon": "♾️",
        "official_url": "https://llama.meta.com",
    },
    "google": {
        "id": "google",
        "name": "Google",
        "short_name": "Google",
        "icon": "🕊️",
        "official_url": "https://deepmind.google/technologies/gemma/",
    },
    "01-ai": {
        "id": "01-ai",
        "name": "01.AI",
        "short_name": "01.AI",
        "icon": "🐯",
        "official_url": "https://www.01.ai",
    },
    "baai": {
        "id": "baai",
        "name": "BAAI",
        "short_name": "BAAI",
        "icon": "🧬",
        "official_url": "https://www.baai.ac.cn",
    },
    "mistralai": {
        "id": "mistralai",
        "name": "Mistral AI",
        "short_name": "Mistral",
        "icon": "🌪️",
        "official_url": "https://mistral.ai",
    },
    "nv-mistralai": {
        "id": "nv-mistralai",
        "name": "Mistral AI (NVIDIA)",
        "short_name": "Mistral",
        "icon": "🌪️",
        "official_url": "https://mistral.ai",
    },
    "cohere": {
        "id": "cohere",
        "name": "Cohere",
        "short_name": "Cohere",
        "icon": "🪶",
        "official_url": "https://cohere.com",
    },
    "moonshotai": {
        "id": "moonshotai",
        "name": "Moonshot AI",
        "short_name": "Moonshot",
        "icon": "🌙",
        "official_url": "https://www.moonshot.cn",
    },
    "qwen": {
        "id": "qwen",
        "name": "Qwen",
        "short_name": "Qwen",
        "icon": "🐉",
        "official_url": "https://github.com/QwenLM",
    },
    "microsoft": {
        "id": "microsoft",
        "name": "Microsoft",
        "short_name": "Microsoft",
        "icon": "🪟",
        "official_url": "https://www.microsoft.com",
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI",
        "short_name": "OpenAI",
        "icon": "🌀",
        "official_url": "https://openai.com",
    },
    "anthropic": {
        "id": "anthropic",
        "name": "Anthropic",
        "short_name": "Anthropic",
        "icon": "🧠",
        "official_url": "https://www.anthropic.com",
    },
    "xai": {
        "id": "xai",
        "name": "xAI",
        "short_name": "xAI",
        "icon": "✖️",
        "official_url": "https://x.ai",
    },
    "bytedance": {
        "id": "bytedance",
        "name": "ByteDance",
        "short_name": "ByteDance",
        "icon": "🪩",
        "official_url": "https://www.volcengine.com",
    },
    "ibm": {
        "id": "ibm",
        "name": "IBM",
        "short_name": "IBM",
        "icon": "💼",
        "official_url": "https://www.ibm.com/granite",
    },
    "writer": {
        "id": "writer",
        "name": "Writer",
        "short_name": "Writer",
        "icon": "✍️",
        "official_url": "https://writer.com",
    },
    "adept": {
        "id": "adept",
        "name": "Adept",
        "short_name": "Adept",
        "icon": "🎯",
        "official_url": "https://www.adept.ai",
    },
    "ai21labs": {
        "id": "ai21labs",
        "name": "AI21 Labs",
        "short_name": "AI21 Labs",
        "icon": "🦖",
        "official_url": "https://www.ai21.com",
    },
    "aisingapore": {
        "id": "aisingapore",
        "name": "AI Singapore",
        "short_name": "AI Singapore",
        "icon": "🦁",
        "official_url": "https://aisingapore.org",
    },
    "bigcode": {
        "id": "bigcode",
        "name": "BigCode",
        "short_name": "BigCode",
        "icon": "⭐",
        "official_url": "https://www.bigcode-project.org",
    },
    "databricks": {
        "id": "databricks",
        "name": "Databricks",
        "short_name": "Databricks",
        "icon": "🧱",
        "official_url": "https://www.databricks.com",
    },
    "minimaxai": {
        "id": "minimaxai",
        "name": "MiniMax",
        "short_name": "MiniMax",
        "icon": "🐚",
        "official_url": "https://www.minimaxi.com",
    },
    "poolside": {
        "id": "poolside",
        "name": "Poolside",
        "short_name": "Poolside",
        "icon": "🏊",
        "official_url": "https://poolside.ai",
    },
    "snowflake": {
        "id": "snowflake",
        "name": "Snowflake",
        "short_name": "Snowflake",
        "icon": "❄️",
        "official_url": "https://www.snowflake.com",
    },
    "stepfun-ai": {
        "id": "stepfun-ai",
        "name": "StepFun",
        "short_name": "StepFun",
        "icon": "🪜",
        "official_url": "https://www.stepfun.com",
    },
    "thinkingmachines": {
        "id": "thinkingmachines",
        "name": "Thinking Machines",
        "short_name": "Thinking Machines",
        "icon": "💡",
        "official_url": "https://thinkingmachin.es",
    },
    "zyphra": {
        "id": "zyphra",
        "name": "Zyphra",
        "short_name": "Zyphra",
        "icon": "⚡",
        "official_url": "https://www.zyphra.com",
    },
    "upstage": {
        "id": "upstage",
        "name": "Upstage",
        "short_name": "Upstage",
        "icon": "☀️",
        "official_url": "https://www.upstage.ai",
    },
}

TIER_ICONS = {
    "flagship": "👑",
    "large": "🏛️",
    "balanced": "⚖️",
    "medium": "⚙️",
    "small": "🪶",
    "embedding": "🧬",
    "specialized": "🛠️",
    "unknown": "📦",
}

SPEED_BADGES = {
    "fast": "⚡ 高速",
    "standard": "◽ 标准",
    "slow": "🐢 慢速",
    "unknown": "◽ 标准",
}

CAPABILITY_ICONS = {
    "chat": "💬",
    "reasoning": "🧠",
    "coding": "💻",
    "vision": "👁️",
    "embedding": "🧬",
    "audio": "🎧",
    "multimodal": "🎨",
    "tool calling": "🔧",
    "rerank": "📊",
    "unknown": "📦",
}

STATUS_ICONS = {
    "active": "🟢",
    "observed_removed": "🟡",
    "deprecated": "🔴",
    "unknown": "⚪",
}


def infer_tier_from_model_id(model_id: str) -> str:
    norm = model_id.lower()
    if any(k in norm for k in ["405b", "340b", "dbrx", "flagship"]):
        return "flagship"
    if any(k in norm for k in ["70b", "65b", "large", "34b", "32b"]):
        return "large"
    if any(k in norm for k in ["27b", "15b", "14b", "13b", "12b", "medium"]):
        return "medium"
    if any(k in norm for k in ["7b", "8b", "6.7b", "3b", "2b", "1b", "small", "mini", "flash", "nano"]):
        return "small"
    if any(k in norm for k in ["embed", "bge", "e5", "clip"]):
        return "embedding"
    if any(k in norm for k in ["rerank", "vision", "fuyu", "deplot", "coder", "code", "guard", "reward", "safety"]):
        return "specialized"
    return "balanced"


def get_provider_brand(provider_id: str) -> dict:
    if not provider_id:
        return {"id": "unknown", "name": "Unknown", "short_name": "Unknown", "icon": "🌐"}
    key = provider_id.lower().strip()
    if key in PROVIDER_REGISTRY:
        return PROVIDER_REGISTRY[key]
    for pid, brand in PROVIDER_REGISTRY.items():
        if pid in key or key in pid:
            return brand
    formatted = provider_id.replace("-", " ").title()
    return {"id": provider_id, "name": formatted, "short_name": formatted, "icon": "🌐"}


def get_provider_icon(provider_id: str) -> str:
    return get_provider_brand(provider_id).get("icon", "🌐")


def get_provider_display_name(provider_id: str) -> str:
    return get_provider_brand(provider_id).get("name", "Unknown")


def get_provider_short_name(provider_id: str) -> str:
    return get_provider_brand(provider_id).get("short_name", "Unknown")


def get_tier_icon(tier: Optional[str], model_id: Optional[str] = None) -> str:
    if tier and tier != "unknown":
        return TIER_ICONS.get(tier.lower().strip(), "📦")
    if model_id:
        inferred = infer_tier_from_model_id(model_id)
        return TIER_ICONS.get(inferred, "⚙️")
    return "📦"


def get_speed_badge(speed: Optional[str], model_id: Optional[str] = None) -> str:
    if speed and speed != "unknown":
        return SPEED_BADGES.get(speed.lower().strip(), SPEED_BADGES["unknown"])
    if model_id:
        norm = model_id.lower()
        if any(k in norm for k in ["flash", "turbo", "mini", "fast", "embed"]):
            return "⚡ 高速"
    return SPEED_BADGES["standard"]


def get_capability_icon(cap: str) -> str:
    if not cap:
        return "📦"
    return CAPABILITY_ICONS.get(cap.lower().strip(), "✨")


def get_status_icon(status: str) -> str:
    return STATUS_ICONS.get(status.lower().strip(), "⚪")
