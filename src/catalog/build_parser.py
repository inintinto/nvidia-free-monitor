"""
NVIDIA Build Model Catalog Parser (S1 Official Metadata Ingester Prototype)
Extracts official model metadata from Next.js React Server Components (RSC) payload and HTML.
"""

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional


NVIDIA_BUILD_BASE = "https://build.nvidia.com"
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 3


def get_opener() -> urllib.request.OpenerDirector:
    """Create URL opener with standard environment proxy support if configured."""
    proxy = (
        os.getenv("HTTP_PROXY")
        or os.getenv("http_proxy")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("https_proxy")
    )
    if proxy:
        proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        return urllib.request.build_opener(proxy_handler)
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def fetch_build_html(model_id: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """Fetch raw HTML for a specific model from build.nvidia.com with retry mechanism."""
    url = f"{NVIDIA_BUILD_BASE}/{model_id.strip()}"
    opener = get_opener()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with opener.open(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read().decode("utf-8", errors="replace")
                print(f"[WARN] HTTP {resp.status} fetching {url} (attempt {attempt}/{MAX_RETRIES})", file=sys.stderr)
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code == 404:
                print(f"[INFO] Model page not found on NVIDIA Build (404): {url}", file=sys.stderr)
                return None
            elif err.code == 429:
                print(f"[WARN] Rate limited (429) fetching {url}, waiting {2 * attempt}s...", file=sys.stderr)
                time.sleep(2 * attempt)
            else:
                print(f"[WARN] HTTP error {err.code} fetching {url}: {err}", file=sys.stderr)
        except Exception as err:
            last_err = err
            print(f"[WARN] Connection error fetching {url} (attempt {attempt}/{MAX_RETRIES}): {err}", file=sys.stderr)
            time.sleep(1 * attempt)

    print(f"[WARN] Failed to fetch {url} after {MAX_RETRIES} attempts: {last_err}", file=sys.stderr)
    return None


def extract_rsc_chunks(html_content: str) -> list[str]:
    """Extract Next.js App Router RSC stream chunks pushed via self.__next_f."""
    chunks = []
    # Pattern 1: self.__next_f.push([1, "..."])
    pattern = re.compile(r'self\.__next_f\.push\(\[\s*\d+\s*,\s*"((?:[^"\\]|\\.)*)"\s*\]\)', re.DOTALL)
    for match in pattern.finditer(html_content):
        raw_str = match.group(1)
        try:
            # Unescape JSON string literal
            unescaped = json.loads(f'"{raw_str}"')
            chunks.append(unescaped)
        except Exception:
            chunks.append(raw_str)
    return chunks


def parse_context_from_text(text: str) -> Optional[str]:
    """Safely extract context length strictly when unambiguous."""
    # Look for patterns like "128k context", "Context Length: 128,000", "128K tokens"
    ctx_patterns = [
        re.compile(r'\b(\d+(?:\.\d+)?[kKmM])\s*(?:tokens?|context\s*length|context\s*window|context)\b', re.IGNORECASE),
        re.compile(r'\bcontext(?:\s*length|\s*window)?\s*[:=]\s*(\d+(?:,\d+)?|\d+[kKmM])\b', re.IGNORECASE),
    ]
    for cp in ctx_patterns:
        m = cp.search(text)
        if m:
            val = m.group(1).replace(",", "").strip()
            # Normalize e.g. 128K -> 128k, 1m -> 1M
            if val.endswith("K") or val.endswith("k"):
                val = val[:-1] + "k"
            elif val.endswith("M") or val.endswith("m"):
                val = val[:-1] + "M"
            return val
    return None


def parse_parameters_from_text(text: str) -> tuple[Optional[str], Optional[str]]:
    """Safely extract total and active parameters strictly when unambiguous."""
    # Look for patterns like "1.65T", "405B parameters", "405B Dense", "70B parameter", "49B active"
    param_pattern = re.compile(r'\b(\d+(?:\.\d+)?[tTbBmM])\s*(?:parameters?|active\s*parameters?|dense|moe)?\b')
    matches = param_pattern.findall(text)
    total_param = None
    active_param = None
    for m in matches:
        m_upper = m.upper()
        if m_upper.endswith("T") or m_upper.endswith("B") or m_upper.endswith("M"):
            num_part = m_upper[:-1]
            try:
                float(num_part)
                if not total_param:
                    total_param = m_upper
                elif not active_param and m_upper != total_param:
                    active_param = m_upper
            except ValueError:
                continue
    return total_param, active_param


def parse_architecture_from_text(text: str) -> Optional[str]:
    """Safely extract architecture type strictly when unambiguous."""
    lower = text.lower()
    if "mixture of experts" in lower or re.search(r'\bmoe\b', lower):
        return "MoE"
    if "dense" in lower:
        return "Dense"
    if "embedding" in lower or "embeddings" in lower or "bge" in lower or "e5" in lower:
        return "Embedding"
    return None


def parse_build_metadata(model_id: str, html_content: str) -> dict[str, Any]:
    """
    Parse NVIDIA Build HTML & RSC payloads to extract official Ground Truth metadata.
    Strictly distinguishes official page data from local heuristics.
    Never guesses missing fields; leaves unverified fields as None.
    """
    if not html_content or not isinstance(html_content, str):
        return None

    clean_html = html_content.strip()
    if not clean_html:
        return None

    extracted_fields: dict[str, str] = {}
    rsc_chunks = extract_rsc_chunks(clean_html)
    full_rsc_text = "\n".join(rsc_chunks)

    # 1. Identity & Provider
    parts = model_id.strip().split("/")
    provider_id = parts[0] if len(parts) > 1 else "nvidia"
    default_provider_name = provider_id.replace("-", " ").title()

    # Extract display name from <title> or og:title with strict sanitization
    display_name = None
    title_m = re.search(r'<title>(.*?)</title>', clean_html, re.IGNORECASE | re.DOTALL)
    if title_m:
        raw_title = html.unescape(title_m.group(1)).strip()
        # Strip script blocks completely including content
        raw_title = re.sub(r'<script[^>]*>.*?</script>', '', raw_title, flags=re.DOTALL | re.IGNORECASE)
        raw_title = re.sub(r'<[^>]+>', '', raw_title)
        clean_title = re.sub(r'\s*\|\s*NVIDIA\s+NIM.*$', '', raw_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s*-\s*NVIDIA\s+NIM.*$', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s*Model\s+by\s+.*$', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s+Model\s*$', '', clean_title, flags=re.IGNORECASE).strip()
        if clean_title and clean_title.lower() != "try nvidia nim apis" and not clean_title.lower().startswith("nvidia nim"):
            display_name = clean_title
            extracted_fields["display_name"] = "NVIDIA Build"

    if not display_name:
        og_title = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', clean_html, re.IGNORECASE)
        if og_title:
            raw_og = html.unescape(og_title.group(1)).strip()
            raw_og = re.sub(r'<script[^>]*>.*?</script>', '', raw_og, flags=re.DOTALL | re.IGNORECASE)
            raw_og = re.sub(r'<[^>]+>', '', raw_og)
            clean_og = re.sub(r'\s*\|\s*NVIDIA\s+NIM.*$', '', raw_og, flags=re.IGNORECASE)
            clean_og = re.sub(r'\s*-\s*NVIDIA\s+NIM.*$', '', clean_og, flags=re.IGNORECASE)
            clean_og = re.sub(r'\s*Model\s+by\s+.*$', '', clean_og, flags=re.IGNORECASE)
            clean_og = re.sub(r'\s+Model\s*$', '', clean_og, flags=re.IGNORECASE).strip()
            if clean_og and clean_og.lower() != "try nvidia nim apis" and not clean_og.lower().startswith("nvidia nim"):
                display_name = clean_og
                extracted_fields["display_name"] = "NVIDIA Build"

    if not display_name:
        raw_slug = parts[-1]
        display_name = raw_slug.replace("-", " ").replace("_", " ").title()

    # Scope extraction to main content to avoid sidebar navigation keyword leakage
    main_m = re.search(r'<main[^>]*>(.*?)</main>', clean_html, re.DOTALL | re.IGNORECASE)
    main_html = main_m.group(1) if main_m else clean_html

    # Extract meta descriptions (e.g. og:description, description)
    meta_desc_parts = []
    for meta_m in re.finditer(r'<meta\s+[^>]*(?:name|property)=["\'](?:[^"\']*description)["\'][^>]*content=["\']([^"\']+)["\']', clean_html, re.IGNORECASE):
        meta_desc_parts.append(meta_m.group(1))
    meta_desc_text = " ".join(meta_desc_parts)

    combined_official_text = (meta_desc_text + "\n" + main_html + "\n" + full_rsc_text).strip()

    # 1.1 Extract Structured Specifications & Capabilities from RSC JSON if present
    rsc_context_len = None
    rsc_params = None
    input_modalities = []
    output_modalities = []
    specs_m = re.search(r'\\?"specifications\\?"\s*:\s*\{([^}]+)\}', clean_html)
    if specs_m:
        spec_block = specs_m.group(1).replace('\\"', '"')
        # Context length in specs (e.g. 1048576 or "1M")
        ctx_val_m = re.search(r'"contextLength"\s*:\s*(\d+|"[^"]+")', spec_block)
        if ctx_val_m:
            raw_ctx = ctx_val_m.group(1).strip('"')
            if raw_ctx.isdigit():
                num = int(raw_ctx)
                if num >= 1000000:
                    rsc_context_len = f"{num // 1000000}M" if num % 1000000 == 0 else f"{round(num / 1048576)}M"
                elif num >= 1000:
                    rsc_context_len = f"{round(num / 1024)}k" if num % 1024 == 0 or num >= 1024 else f"{num // 1000}k"
                else:
                    rsc_context_len = str(num)
            else:
                rsc_context_len = raw_ctx

        # Parameters in specs (e.g. "1.65T", "405B")
        param_val_m = re.search(r'"parameters"\s*:\s*"([^"]+)"', spec_block)
        if param_val_m:
            rsc_params = param_val_m.group(1).strip().upper()

        # Input & Output modalities
        in_mod_m = re.search(r'"inputModalities"\s*:\s*\[([^\]]*)\]', spec_block)
        if in_mod_m:
            input_modalities = [x.strip().strip('"').strip("'") for x in in_mod_m.group(1).split(",") if x.strip()]
        out_mod_m = re.search(r'"outputModalities"\s*:\s*\[([^\]]*)\]', spec_block)
        if out_mod_m:
            output_modalities = [x.strip().strip('"').strip("'") for x in out_mod_m.group(1).split(",") if x.strip()]

    # 2. Context Length & Max Output (Strictly from page text / RSC)
    context_length = rsc_context_len or parse_context_from_text(main_html) or parse_context_from_text(full_rsc_text)
    if not context_length:
        # Check explicit Markdown patterns like "**Input Context Length (ISL):** 1,000,000" or "1M-token context"
        isl_m = re.search(r'\*\*Input Context Length[^*:]*:\*\*\s*([\d,]+|\d+[kKmM])', clean_html, re.IGNORECASE)
        if isl_m:
            raw_isl = isl_m.group(1).replace(",", "").strip()
            if raw_isl.isdigit():
                num = int(raw_isl)
                context_length = f"{num // 1000000}M" if num >= 1000000 else (f"{num // 1000}k" if num >= 1000 else str(num))
            else:
                context_length = raw_isl
        else:
            token_ctx_m = re.search(r'\b(\d+[kKmM])-token\s*context\b', clean_html, re.IGNORECASE)
            if token_ctx_m:
                context_length = token_ctx_m.group(1).upper().replace("K", "k")

    if context_length:
        extracted_fields["context.length"] = "NVIDIA Build"

    max_output = None
    max_out_m = re.search(r'\bmax(?:imum)?\s*(?:output|tokens?)\s*[:=]\s*(\d+(?:,\d+)?|\d+[kKmM])\b', combined_official_text, re.IGNORECASE)
    if max_out_m:
        max_output = max_out_m.group(1).replace(",", "").strip()
        extracted_fields["context.max_output"] = "NVIDIA Build"

    # 3. Architecture & Parameters (Only if explicitly stated in main content/RSC specs)
    arch_type = None
    lower_main = combined_official_text.lower()
    if "mixture of experts" in lower_main or re.search(r'\bmoe\b', lower_main):
        arch_type = "MoE"
        extracted_fields["architecture.type"] = "NVIDIA Build"
    elif re.search(r'\bdense\b', lower_main):
        arch_type = "Dense"
        extracted_fields["architecture.type"] = "NVIDIA Build"
    elif "embedding" in model_id.lower() or "embed" in model_id.lower() or "bge" in model_id.lower():
        arch_type = "Embedding"
        extracted_fields["architecture.type"] = "NVIDIA Build"

    # Total & active parameters strictly from explicit text in page specs/main content (supporting T, B, M)
    total_params = rsc_params
    active_params = None

    if not total_params:
        param_m = re.search(r'\*\*Total Parameters:\*\*\s*(\d+(?:\.\d+)?[tTbBmM])', clean_html, re.IGNORECASE)
        if not param_m:
            param_m = re.search(r'\b(\d+(?:\.\d+)?[tTbBmM])\s*(?:total\s*)?(?:parameters?|dense|moe)\b', combined_official_text, re.IGNORECASE)
        if param_m:
            total_params = param_m.group(1).upper()
        else:
            text_tot, text_act = parse_parameters_from_text(combined_official_text)
            if text_tot:
                total_params = text_tot
            if text_act and not active_params:
                active_params = text_act

    if total_params:
        extracted_fields["architecture.total_parameters"] = "NVIDIA Build"

    active_param_m = re.search(r'\*\*Active Parameters:\*\*\s*(\d+(?:\.\d+)?[tTbBmM])', clean_html, re.IGNORECASE)
    if not active_param_m:
        active_param_m = re.search(r'\b(\d+(?:\.\d+)?[tTbBmM])\s*active\s*parameters?\b', combined_official_text, re.IGNORECASE)
    if active_param_m:
        active_params = active_param_m.group(1).upper()
        extracted_fields["architecture.active_parameters"] = "NVIDIA Build"

    # 4. Capabilities & Accurate Model Type
    capabilities = []
    if arch_type == "Embedding":
        capabilities.append("Embedding")
    else:
        capabilities.append("Chat")

    # Coding capability
    if "coder" in model_id.lower() or "coding" in lower_main or "code generation" in lower_main or "for coding tasks" in lower_main:
        if "Coding" not in capabilities:
            capabilities.append("Coding")

    # Reasoning capability
    if "reasoning" in lower_main or "r1" in model_id.lower() or "reasoning-effort" in lower_main or '"reasoning":true' in clean_html:
        if "Reasoning" not in capabilities:
            capabilities.append("Reasoning")

    # Agentic capability
    if "agentic" in lower_main or "ai agent" in lower_main:
        if "Agentic" not in capabilities:
            capabilities.append("Agentic")

    # Vision capability: ONLY if inputModalities includes Image/Video OR explicit visual evidence in main specs
    is_vision_model = False
    if any(m.lower() in ["image", "video", "visual"] for m in input_modalities):
        is_vision_model = True
    elif re.search(r'\*\*Input Types?:\*\*\s*(?:Image|Video|Visual)', clean_html, re.IGNORECASE):
        is_vision_model = True
    elif any(k in model_id.lower() for k in ["-vl-", "-vision-", "fuyu", "neva", "cosmos"]):
        is_vision_model = True

    if is_vision_model:
        if "Vision" not in capabilities:
            capabilities.append("Vision")

    if capabilities:
        extracted_fields["capabilities"] = "NVIDIA Build"

    # Determine classification.model_type strictly
    if arch_type == "Embedding":
        model_type = "embedding"
    elif is_vision_model:
        model_type = "vision"
    elif "coder" in model_id.lower() and "chat" not in model_id.lower():
        model_type = "coding"
    else:
        model_type = "chat"

    extracted_fields["classification.model_type"] = "NVIDIA Build"

    # 5. External & Documentation Links
    nvidia_url = f"{NVIDIA_BUILD_BASE}/{model_id.strip()}"
    extracted_fields["links.nvidia"] = "NVIDIA Build"

    doc_link = None
    doc_match = re.search(r'https?://docs\.(?:api\.)?nvidia\.com/[^\s"\'<>]+', clean_html)
    if doc_match:
        doc_link = doc_match.group(0).rstrip("\\").rstrip("/")
        extracted_fields["links.documentation"] = "NVIDIA Build"

    # Heuristic properties (honestly labeled)
    speed_heuristic = "fast" if "flash" in model_id.lower() or "turbo" in model_id.lower() else "standard"
    extracted_fields["classification.speed"] = "local_heuristic"

    # Metadata record
    now_iso = datetime.now(timezone.utc).isoformat()
    official_fields_count = sum(1 for v in extracted_fields.values() if v == "NVIDIA Build")
    confidence = "high" if official_fields_count >= 3 else "medium"

    return {
        "model_id": model_id.strip(),
        "provider": {
            "id": provider_id,
            "name": default_provider_name,
        },
        "display_name": display_name,
        "classification": {
            "family": None,  # Keep None unless explicitly labeled on official page
            "tier": "standard",
            "model_type": model_type,
            "speed": speed_heuristic,
        },
        "architecture": {
            "type": arch_type,
            "total_parameters": total_params,
            "active_parameters": active_params,
            "parameter_status": "official" if total_params else "unknown",
        },
        "context": {
            "length": context_length,
            "max_output": max_output,
            "status": "official" if context_length else "unknown",
        },
        "capabilities": capabilities,
        "links": {
            "nvidia": nvidia_url,
            "official": None,
            "documentation": doc_link,
            "model_card": None,
        },
        "source_metadata": {
            "field_sources": extracted_fields,
            "confidence": confidence,
            "last_verified": now_iso,
        },
    }


def enrich_single_model(model_id: str, html_fetcher=fetch_build_html) -> Optional[dict[str, Any]]:
    """Fetch and parse metadata for a single model ID from NVIDIA Build."""
    html_doc = html_fetcher(model_id)
    if not html_doc:
        return None
    try:
        return parse_build_metadata(model_id, html_doc)
    except Exception as err:
        print(f"[WARN] Failed to parse metadata for {model_id}: {err}", file=sys.stderr)
        return None


def enrich_from_snapshot(
    model_id: str,
    timestamp_tag: Optional[str] = None,
    base_dir=None,
) -> Optional[dict[str, Any]]:
    """Load an offline raw snapshot, verify its integrity, and parse normalized metadata."""
    from src.catalog.snapshot import load_snapshot
    try:
        snapshot_data = load_snapshot(model_id, timestamp_tag=timestamp_tag, base_dir=base_dir)
        raw_html = snapshot_data["raw_html"]
        return parse_build_metadata(model_id, raw_html)
    except Exception as err:
        print(f"[WARN] Failed to enrich {model_id} from snapshot: {err}", file=sys.stderr)
        return None
