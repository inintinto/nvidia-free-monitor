// Automatically bundled fallback data from data/*.json (Stage 3C/3D)
export const BUNDLED_CATALOG = {
  "version": "3.1",
  "updated_at": "2026-08-23T15:30:00Z",
  "models": {
    "deepseek-ai/deepseek-v4-flash-0731": {
      "model_id": "deepseek-ai/deepseek-v4-flash-0731",
      "display_name": "DeepSeek V4 Flash 0731",
      "aliases": [
        "ds v4 flash",
        "deepseek v4 flash",
        "deepseek-v4-flash",
        "ds v4 flash 0731",
        "v4 flash"
      ],
      "slug": "deepseek-v4-flash-0731",
      "provider": {
        "id": "deepseek-ai",
        "name": "DeepSeek AI"
      },
      "classification": {
        "family": "DeepSeek-V4",
        "tier": "flagship",
        "model_type": "chat",
        "speed": "fast"
      },
      "architecture": {
        "type": "MoE",
        "total_parameters": null,
        "active_parameters": null,
        "parameter_status": "unknown"
      },
      "context": {
        "length": "128k",
        "max_output": null,
        "status": "official"
      },
      "capabilities": [
        "Chat",
        "Reasoning",
        "Coding"
      ],
      "release": {
        "first_seen": "2026-07-31T08:00:00Z",
        "release_date": null,
        "status": "official"
      },
      "lifecycle": {
        "availability": "active",
        "removed_at": null,
        "official_deprecation_date": null,
        "deprecation_source_url": null
      },
      "endpoint": {
        "available": true,
        "api_calls_24h": null,
        "api_calls_daily": null,
        "api_calls_7d": null,
        "api_calls_30d": "3.2M"
      },
      "links": {
        "nvidia": "https://build.nvidia.com/deepseek-ai/deepseek-v4-flash-0731",
        "official": "https://www.deepseek.com",
        "documentation": null,
        "model_card": null
      },
      "source_metadata": {
        "field_sources": {
          "architecture": "official",
          "context": "official",
          "parameters": "unknown",
          "capabilities": "official",
          "endpoint_usage": "official_aggregate"
        },
        "confidence": "high",
        "last_verified": "2026-08-23T15:30:00Z"
      }
    },
    "deepseek-ai/deepseek-coder-6.7b-instruct": {
      "model_id": "deepseek-ai/deepseek-coder-6.7b-instruct",
      "display_name": "DeepSeek Coder 6.7B Instruct",
      "aliases": [
        "ds coder 6.7b",
        "deepseek coder",
        "deepseek-coder-6.7b"
      ],
      "slug": "deepseek-coder-6.7b-instruct",
      "provider": {
        "id": "deepseek-ai",
        "name": "DeepSeek AI"
      },
      "classification": {
        "family": "DeepSeek-Coder",
        "tier": "standard",
        "model_type": "coding",
        "speed": "standard"
      },
      "architecture": {
        "type": "Dense",
        "total_parameters": "6.7B",
        "active_parameters": "6.7B",
        "parameter_status": "official"
      },
      "context": {
        "length": "16k",
        "max_output": null,
        "status": "official"
      },
      "capabilities": [
        "Coding",
        "Chat"
      ],
      "release": {
        "first_seen": "2026-03-01T00:00:00Z",
        "release_date": null,
        "status": "official"
      },
      "lifecycle": {
        "availability": "active",
        "removed_at": null,
        "official_deprecation_date": null,
        "deprecation_source_url": null
      },
      "endpoint": {
        "available": true,
        "api_calls_24h": null,
        "api_calls_daily": null,
        "api_calls_7d": null,
        "api_calls_30d": "1.1M"
      },
      "links": {
        "nvidia": "https://build.nvidia.com/deepseek-ai/deepseek-coder-6.7b-instruct",
        "official": "https://www.deepseek.com",
        "documentation": null,
        "model_card": null
      },
      "source_metadata": {
        "field_sources": {
          "architecture": "official",
          "context": "official",
          "parameters": "official",
          "capabilities": "official",
          "endpoint_usage": "official_aggregate"
        },
        "confidence": "high",
        "last_verified": "2026-08-23T15:30:00Z"
      }
    },
    "meta/llama-3.3-70b-instruct": {
      "model_id": "meta/llama-3.3-70b-instruct",
      "display_name": "Llama 3.3 70B Instruct",
      "aliases": [
        "llama 3.3",
        "llama 3.3 70b",
        "meta llama 3.3",
        "llama3.3-70b"
      ],
      "slug": "llama-3.3-70b-instruct",
      "provider": {
        "id": "meta",
        "name": "Meta"
      },
      "classification": {
        "family": "Llama-3.3",
        "tier": "large",
        "model_type": "chat",
        "speed": "standard"
      },
      "architecture": {
        "type": "Dense",
        "total_parameters": "70B",
        "active_parameters": "70B",
        "parameter_status": "official"
      },
      "context": {
        "length": "128k",
        "max_output": null,
        "status": "official"
      },
      "capabilities": [
        "Chat",
        "Reasoning",
        "Coding"
      ],
      "release": {
        "first_seen": "2026-04-15T00:00:00Z",
        "release_date": null,
        "status": "official"
      },
      "lifecycle": {
        "availability": "active",
        "removed_at": null,
        "official_deprecation_date": null,
        "deprecation_source_url": null
      },
      "endpoint": {
        "available": true,
        "api_calls_24h": null,
        "api_calls_daily": null,
        "api_calls_7d": null,
        "api_calls_30d": "5.8M"
      },
      "links": {
        "nvidia": "https://build.nvidia.com/meta/llama-3.3-70b-instruct",
        "official": "https://llama.meta.com",
        "documentation": null,
        "model_card": null
      },
      "source_metadata": {
        "field_sources": {
          "architecture": "official",
          "context": "official",
          "parameters": "official",
          "capabilities": "official",
          "endpoint_usage": "official_aggregate"
        },
        "confidence": "high",
        "last_verified": "2026-08-23T15:30:00Z"
      }
    },
    "meta/llama-3.1-405b-instruct": {
      "model_id": "meta/llama-3.1-405b-instruct",
      "display_name": "Llama 3.1 405B Instruct",
      "aliases": [
        "llama 3.1 405b",
        "llama 405b",
        "meta 405b"
      ],
      "slug": "llama-3.1-405b-instruct",
      "provider": {
        "id": "meta",
        "name": "Meta"
      },
      "classification": {
        "family": "Llama-3.1",
        "tier": "flagship",
        "model_type": "chat",
        "speed": "standard"
      },
      "architecture": {
        "type": "Dense",
        "total_parameters": "405B",
        "active_parameters": "405B",
        "parameter_status": "official"
      },
      "context": {
        "length": "128k",
        "max_output": null,
        "status": "official"
      },
      "capabilities": [
        "Chat",
        "Reasoning",
        "Coding"
      ],
      "release": {
        "first_seen": "2026-07-23T00:00:00Z",
        "release_date": null,
        "status": "official"
      },
      "lifecycle": {
        "availability": "active",
        "removed_at": null,
        "official_deprecation_date": null,
        "deprecation_source_url": null
      },
      "endpoint": {
        "available": true,
        "api_calls_24h": null,
        "api_calls_daily": null,
        "api_calls_7d": null,
        "api_calls_30d": "2.4M"
      },
      "links": {
        "nvidia": "https://build.nvidia.com/meta/llama-3.1-405b-instruct",
        "official": "https://llama.meta.com",
        "documentation": null,
        "model_card": null
      },
      "source_metadata": {
        "field_sources": {
          "architecture": "official",
          "context": "official",
          "parameters": "official",
          "capabilities": "official",
          "endpoint_usage": "official_aggregate"
        },
        "confidence": "high",
        "last_verified": "2026-08-23T15:30:00Z"
      }
    },
    "nvidia/nemotron-4-340b-instruct": {
      "model_id": "nvidia/nemotron-4-340b-instruct",
      "display_name": "Nemotron-4 340B Instruct",
      "aliases": [
        "nemotron",
        "nemotron 4 340b",
        "nemotron-4-340b",
        "nv nemotron"
      ],
      "slug": "nemotron-4-340b-instruct",
      "provider": {
        "id": "nvidia",
        "name": "NVIDIA"
      },
      "classification": {
        "family": "Nemotron-4",
        "tier": "flagship",
        "model_type": "chat",
        "speed": "standard"
      },
      "architecture": {
        "type": "Dense",
        "total_parameters": "340B",
        "active_parameters": "340B",
        "parameter_status": "official"
      },
      "context": {
        "length": "4k",
        "max_output": null,
        "status": "official"
      },
      "capabilities": [
        "Chat",
        "Reasoning"
      ],
      "release": {
        "first_seen": "2026-06-10T00:00:00Z",
        "release_date": null,
        "status": "official"
      },
      "lifecycle": {
        "availability": "active",
        "removed_at": null,
        "official_deprecation_date": null,
        "deprecation_source_url": null
      },
      "endpoint": {
        "available": true,
        "api_calls_24h": null,
        "api_calls_daily": null,
        "api_calls_7d": null,
        "api_calls_30d": "1.9M"
      },
      "links": {
        "nvidia": "https://build.nvidia.com/nvidia/nemotron-4-340b-instruct",
        "official": "https://www.nvidia.com",
        "documentation": null,
        "model_card": null
      },
      "source_metadata": {
        "field_sources": {
          "architecture": "official",
          "context": "official",
          "parameters": "official",
          "capabilities": "official",
          "endpoint_usage": "official_aggregate"
        },
        "confidence": "high",
        "last_verified": "2026-08-23T15:30:00Z"
      }
    },
    "google/gemma-2-27b-it": {
      "model_id": "google/gemma-2-27b-it",
      "display_name": "Gemma 2 27B IT",
      "aliases": [
        "gemma 2",
        "gemma 2 27b",
        "google gemma 2"
      ],
      "slug": "gemma-2-27b-it",
      "provider": {
        "id": "google",
        "name": "Google"
      },
      "classification": {
        "family": "Gemma-2",
        "tier": "medium",
        "model_type": "chat",
        "speed": "standard"
      },
      "architecture": {
        "type": "Dense",
        "total_parameters": "27B",
        "active_parameters": "27B",
        "parameter_status": "official"
      },
      "context": {
        "length": "8k",
        "max_output": null,
        "status": "official"
      },
      "capabilities": [
        "Chat",
        "Reasoning"
      ],
      "release": {
        "first_seen": "2026-06-25T00:00:00Z",
        "release_date": null,
        "status": "official"
      },
      "lifecycle": {
        "availability": "active",
        "removed_at": null,
        "official_deprecation_date": null,
        "deprecation_source_url": null
      },
      "endpoint": {
        "available": true,
        "api_calls_24h": null,
        "api_calls_daily": null,
        "api_calls_7d": null,
        "api_calls_30d": "850k"
      },
      "links": {
        "nvidia": "https://build.nvidia.com/google/gemma-2-27b-it",
        "official": "https://deepmind.google/technologies/gemma/",
        "documentation": null,
        "model_card": null
      },
      "source_metadata": {
        "field_sources": {
          "architecture": "official",
          "context": "official",
          "parameters": "official",
          "capabilities": "official",
          "endpoint_usage": "official_aggregate"
        },
        "confidence": "high",
        "last_verified": "2026-08-23T15:30:00Z"
      }
    },
    "01-ai/yi-large": {
      "model_id": "01-ai/yi-large",
      "display_name": "Yi Large",
      "aliases": [
        "yi large",
        "01 yi large",
        "yi-large"
      ],
      "slug": "yi-large",
      "provider": {
        "id": "01-ai",
        "name": "01-ai"
      },
      "classification": {
        "family": "Yi",
        "tier": "large",
        "model_type": "chat",
        "speed": "standard"
      },
      "architecture": {
        "type": "Dense",
        "total_parameters": null,
        "active_parameters": null,
        "parameter_status": "unknown"
      },
      "context": {
        "length": "32k",
        "max_output": null,
        "status": "official"
      },
      "capabilities": [
        "Chat",
        "Reasoning"
      ],
      "release": {
        "first_seen": "2026-05-01T00:00:00Z",
        "release_date": null,
        "status": "official"
      },
      "lifecycle": {
        "availability": "active",
        "removed_at": null,
        "official_deprecation_date": null,
        "deprecation_source_url": null
      },
      "endpoint": {
        "available": true,
        "api_calls_24h": null,
        "api_calls_daily": null,
        "api_calls_7d": null,
        "api_calls_30d": "420k"
      },
      "links": {
        "nvidia": "https://build.nvidia.com/01-ai/yi-large",
        "official": "https://www.01.ai",
        "documentation": null,
        "model_card": null
      },
      "source_metadata": {
        "field_sources": {
          "architecture": "official",
          "context": "official",
          "parameters": "unknown",
          "capabilities": "official",
          "endpoint_usage": "official_aggregate"
        },
        "confidence": "high",
        "last_verified": "2026-08-23T15:30:00Z"
      }
    },
    "baai/bge-m3": {
      "model_id": "baai/bge-m3",
      "display_name": "BGE-M3 Embedding",
      "aliases": [
        "bge m3",
        "bge-m3",
        "baai bge m3"
      ],
      "slug": "bge-m3",
      "provider": {
        "id": "baai",
        "name": "BAAI"
      },
      "classification": {
        "family": "BGE",
        "tier": "embedding",
        "model_type": "embedding",
        "speed": "fast"
      },
      "architecture": {
        "type": "Embedding",
        "total_parameters": "570M",
        "active_parameters": "570M",
        "parameter_status": "official"
      },
      "context": {
        "length": "8k",
        "max_output": null,
        "status": "official"
      },
      "capabilities": [
        "Embedding"
      ],
      "release": {
        "first_seen": "2026-02-01T00:00:00Z",
        "release_date": null,
        "status": "official"
      },
      "lifecycle": {
        "availability": "active",
        "removed_at": null,
        "official_deprecation_date": null,
        "deprecation_source_url": null
      },
      "endpoint": {
        "available": true,
        "api_calls_24h": null,
        "api_calls_daily": null,
        "api_calls_7d": null,
        "api_calls_30d": "1.5M"
      },
      "links": {
        "nvidia": "https://build.nvidia.com/baai/bge-m3",
        "official": "https://www.baai.ac.cn",
        "documentation": null,
        "model_card": null
      },
      "source_metadata": {
        "field_sources": {
          "architecture": "official",
          "context": "official",
          "parameters": "official",
          "capabilities": "official",
          "endpoint_usage": "official_aggregate"
        },
        "confidence": "high",
        "last_verified": "2026-08-23T15:30:00Z"
      }
    }
  }
};

export const BUNDLED_LIFECYCLE = {
  "version": "3.0",
  "updated_at": "2026-08-23T12:00:00Z",
  "history": {
    "deepseek-ai/deepseek-v4-flash-0731": {
      "first_seen": "2026-07-31T08:00:00Z",
      "free_since": "2026-07-31T08:00:00Z",
      "last_seen": "2026-08-23T10:00:00Z",
      "removed_at": null,
      "is_currently_active": true,
      "official_lifecycle": {
        "official_status": "active",
        "official_deprecation_date": null,
        "sunset_date": null,
        "deprecation_source_url": null,
        "deprecation_notes": null
      }
    },
    "deepseek-ai/deepseek-coder-6.7b-instruct": {
      "first_seen": "2026-03-01T00:00:00Z",
      "free_since": "2026-03-01T00:00:00Z",
      "last_seen": "2026-08-23T10:00:00Z",
      "removed_at": null,
      "is_currently_active": true,
      "official_lifecycle": {
        "official_status": "active",
        "official_deprecation_date": null,
        "sunset_date": null,
        "deprecation_source_url": null,
        "deprecation_notes": null
      }
    },
    "meta/llama-3.3-70b-instruct": {
      "first_seen": "2026-04-15T00:00:00Z",
      "free_since": "2026-04-15T00:00:00Z",
      "last_seen": "2026-08-23T10:00:00Z",
      "removed_at": null,
      "is_currently_active": true,
      "official_lifecycle": {
        "official_status": "active",
        "official_deprecation_date": null,
        "sunset_date": null,
        "deprecation_source_url": null,
        "deprecation_notes": null
      }
    },
    "meta/llama-3.1-405b-instruct": {
      "first_seen": "2026-07-23T00:00:00Z",
      "free_since": "2026-07-23T00:00:00Z",
      "last_seen": "2026-08-23T10:00:00Z",
      "removed_at": null,
      "is_currently_active": true,
      "official_lifecycle": {
        "official_status": "active",
        "official_deprecation_date": null,
        "sunset_date": null,
        "deprecation_source_url": null,
        "deprecation_notes": null
      }
    },
    "nvidia/nemotron-4-340b-instruct": {
      "first_seen": "2026-06-10T00:00:00Z",
      "free_since": "2026-06-10T00:00:00Z",
      "last_seen": "2026-08-23T10:00:00Z",
      "removed_at": null,
      "is_currently_active": true,
      "official_lifecycle": {
        "official_status": "active",
        "official_deprecation_date": null,
        "sunset_date": null,
        "deprecation_source_url": null,
        "deprecation_notes": null
      }
    },
    "google/gemma-2-27b-it": {
      "first_seen": "2026-06-25T00:00:00Z",
      "free_since": "2026-06-25T00:00:00Z",
      "last_seen": "2026-08-23T10:00:00Z",
      "removed_at": null,
      "is_currently_active": true,
      "official_lifecycle": {
        "official_status": "active",
        "official_deprecation_date": null,
        "sunset_date": null,
        "deprecation_source_url": null,
        "deprecation_notes": null
      }
    },
    "01-ai/yi-large": {
      "first_seen": "2026-05-01T00:00:00Z",
      "free_since": "2026-05-01T00:00:00Z",
      "last_seen": "2026-08-23T10:00:00Z",
      "removed_at": null,
      "is_currently_active": true,
      "official_lifecycle": {
        "official_status": "active",
        "official_deprecation_date": null,
        "sunset_date": null,
        "deprecation_source_url": null,
        "deprecation_notes": null
      }
    },
    "baai/bge-m3": {
      "first_seen": "2026-02-15T00:00:00Z",
      "free_since": "2026-02-15T00:00:00Z",
      "last_seen": "2026-08-23T10:00:00Z",
      "removed_at": null,
      "is_currently_active": true,
      "official_lifecycle": {
        "official_status": "active",
        "official_deprecation_date": null,
        "sunset_date": null,
        "deprecation_source_url": null,
        "deprecation_notes": null
      }
    }
  }
};

export const BUNDLED_BASELINE = {
  "checked_at": "2026-08-23T09:27:06.594279+00:00",
  "source": "https://integrate.api.nvidia.com/v1/models",
  "model_count": 102,
  "models": [
    {
      "id": "01-ai/yi-large",
      "owned_by": "01-ai",
      "created": 735790403
    },
    {
      "id": "adept/fuyu-8b",
      "owned_by": "adept",
      "created": 735790403
    },
    {
      "id": "ai21labs/jamba-1.5-large-instruct",
      "owned_by": "ai21labs",
      "created": 735790403
    },
    {
      "id": "aisingapore/sea-lion-7b-instruct",
      "owned_by": "aisingapore",
      "created": 735790403
    },
    {
      "id": "baai/bge-m3",
      "owned_by": "baai",
      "created": 735790403
    },
    {
      "id": "bigcode/starcoder2-15b",
      "owned_by": "bigcode",
      "created": 735790403
    },
    {
      "id": "databricks/dbrx-instruct",
      "owned_by": "databricks",
      "created": 735790403
    },
    {
      "id": "deepseek-ai/deepseek-coder-6.7b-instruct",
      "owned_by": "deepseek-ai",
      "created": 735790403
    },
    {
      "id": "deepseek-ai/deepseek-v4-flash-0731",
      "owned_by": "deepseek-ai",
      "created": 735790403
    },
    {
      "id": "google/codegemma-1.1-7b",
      "owned_by": "google",
      "created": 735790403
    },
    {
      "id": "google/codegemma-7b",
      "owned_by": "google",
      "created": 735790403
    },
    {
      "id": "google/deplot",
      "owned_by": "google",
      "created": 735790403
    },
    {
      "id": "google/diffusiongemma-26b-a4b-it",
      "owned_by": "google",
      "created": 735790403
    },
    {
      "id": "google/gemma-2b",
      "owned_by": "google",
      "created": 735790403
    },
    {
      "id": "google/gemma-3-12b-it",
      "owned_by": "google",
      "created": 735790403
    },
    {
      "id": "google/gemma-3-4b-it",
      "owned_by": "google",
      "created": 735790403
    },
    {
      "id": "google/gemma-4-31b-it",
      "owned_by": "google",
      "created": 735790403
    },
    {
      "id": "google/recurrentgemma-2b",
      "owned_by": "google",
      "created": 735790403
    },
    {
      "id": "ibm/granite-3.0-3b-a800m-instruct",
      "owned_by": "ibm",
      "created": 735790403
    },
    {
      "id": "ibm/granite-3.0-8b-instruct",
      "owned_by": "ibm",
      "created": 735790403
    },
    {
      "id": "ibm/granite-34b-code-instruct",
      "owned_by": "ibm",
      "created": 735790403
    },
    {
      "id": "ibm/granite-8b-code-instruct",
      "owned_by": "ibm",
      "created": 735790403
    },
    {
      "id": "meta/codellama-70b",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/llama-3.1-70b-instruct",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/llama-3.1-8b-instruct",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/llama-3.2-11b-vision-instruct",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/llama-3.2-1b-instruct",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/llama-3.2-3b-instruct",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/llama-3.2-90b-vision-instruct",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/llama-3.3-70b-instruct",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/llama-guard-4-12b",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/llama2-70b",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "meta/muse-glimmer-30b",
      "owned_by": "meta",
      "created": 735790403
    },
    {
      "id": "microsoft/kosmos-2",
      "owned_by": "microsoft",
      "created": 735790403
    },
    {
      "id": "microsoft/phi-3-vision-128k-instruct",
      "owned_by": "microsoft",
      "created": 735790403
    },
    {
      "id": "microsoft/phi-3.5-moe-instruct",
      "owned_by": "microsoft",
      "created": 735790403
    },
    {
      "id": "minimaxai/minimax-m3",
      "owned_by": "minimaxai",
      "created": 735790403
    },
    {
      "id": "mistralai/codestral-22b-instruct-v0.1",
      "owned_by": "mistralai",
      "created": 735790403
    },
    {
      "id": "mistralai/mistral-7b-instruct-v0.3",
      "owned_by": "mistralai",
      "created": 735790403
    },
    {
      "id": "mistralai/mistral-large",
      "owned_by": "mistralai",
      "created": 735790403
    },
    {
      "id": "mistralai/mistral-large-2-instruct",
      "owned_by": "mistralai",
      "created": 735790403
    },
    {
      "id": "mistralai/mistral-nemotron",
      "owned_by": "mistralai",
      "created": 735790403
    },
    {
      "id": "mistralai/mixtral-8x22b-v0.1",
      "owned_by": "mistralai",
      "created": 735790403
    },
    {
      "id": "moonshotai/kimi-k2.6",
      "owned_by": "moonshotai",
      "created": 735790403
    },
    {
      "id": "moonshotai/kimi-k3",
      "owned_by": "moonshotai",
      "created": 735790403
    },
    {
      "id": "nv-mistralai/mistral-nemo-12b-instruct",
      "owned_by": "nv-mistralai",
      "created": 735790403
    },
    {
      "id": "nvidia/ai-synthetic-video-detector",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/cosmos-reason2-8b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/embed-qa-4",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/ising-calibration-1.5-31b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.1-nemoguard-8b-content-safety",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.1-nemoguard-8b-topic-control",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.1-nemotron-51b-instruct",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.1-nemotron-70b-instruct",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.1-nemotron-nano-8b-v1",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.1-nemotron-safety-guard-8b-v3",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.2-nv-embedqa-1b-v1",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.3-nemotron-super-49b-v1",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-nemotron-embed-1b-v2",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama-nemotron-embed-vl-1b-v2",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/llama3-chatqa-1.5-70b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/mistral-nemo-minitron-8b-8k-instruct",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemoretriever-parse",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-3-embed-1b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-3-nano-30b-a3b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-3-super-120b-a12b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-3-ultra-550b-a55b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-3.5-content-safety",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-3.5-lightning-30b-a3b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-4-340b-instruct",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-4-340b-reward",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-mini-4b-instruct",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-nano-12b-v2-vl",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-nano-3-30b-a3b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nemotron-parse",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/neva-22b",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nv-embed-v1",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nv-embedcode-7b-v1",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nv-embedqa-e5-v5",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nv-embedqa-mistral-7b-v2",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nvclip",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/nvidia-nemotron-nano-9b-v2",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/riva-translate-4b-instruct",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/riva-translate-4b-instruct-v1.1",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/riva-translate-4b-instruct-v2",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "nvidia/vila",
      "owned_by": "nvidia",
      "created": 735790403
    },
    {
      "id": "openai/gpt-oss-120b",
      "owned_by": "openai",
      "created": 735790403
    },
    {
      "id": "openai/gpt-oss-20b",
      "owned_by": "openai",
      "created": 735790403
    },
    {
      "id": "poolside/laguna-xs-2.1",
      "owned_by": "poolside",
      "created": 735790403
    },
    {
      "id": "snowflake/arctic-embed-l",
      "owned_by": "snowflake",
      "created": 735790403
    },
    {
      "id": "stepfun-ai/step-3.7-flash",
      "owned_by": "stepfun-ai",
      "created": 735790403
    },
    {
      "id": "thinkingmachines/inkling",
      "owned_by": "thinkingmachines",
      "created": 735790403
    },
    {
      "id": "writer/palmyra-creative-122b",
      "owned_by": "writer",
      "created": 735790403
    },
    {
      "id": "writer/palmyra-fin-70b-32k",
      "owned_by": "writer",
      "created": 735790403
    },
    {
      "id": "writer/palmyra-med-70b",
      "owned_by": "writer",
      "created": 735790403
    },
    {
      "id": "writer/palmyra-med-70b-32k",
      "owned_by": "writer",
      "created": 735790403
    },
    {
      "id": "zyphra/zamba2-7b-instruct",
      "owned_by": "zyphra",
      "created": 735790403
    }
  ]
};
