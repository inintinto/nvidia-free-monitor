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
        "icon": "🟩",
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
        "icon": "🔵",
        "official_url": "https://deepmind.google/technologies/gemma/",
    },
    "01-ai": {
        "id": "01-ai",
        "name": "01.AI",
        "short_name": "01.AI",
        "icon": "🟡",
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
        "icon": "🌊",
        "official_url": "https://mistral.ai",
    },
    "cohere": {
        "id": "cohere",
        "name": "Cohere",
        "short_name": "Cohere",
        "icon": "🟣",
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
        "icon": "🟢",
        "official_url": "https://openai.com",
    },
}

TIER_ICONS = {
    "flagship": "👑",
    "large": "🏛️",
    "balanced": "⚖️",
    "medium": "⚡",
    "small": "🔹",
    "fast": "⚡",
    "embedding": "🧬",
    "reasoning": "🧠",
    "coding": "💻",
    "vision": "👁️",
    "specialized": "🛠️",
    "standard": "🔹",
    "unknown": "📦",
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


def get_tier_icon(tier: Optional[str]) -> str:
    if not tier:
        return "📦"
    return TIER_ICONS.get(tier.lower().strip(), "📦")


def get_capability_icon(cap: str) -> str:
    if not cap:
        return "📦"
    return CAPABILITY_ICONS.get(cap.lower().strip(), "✨")
