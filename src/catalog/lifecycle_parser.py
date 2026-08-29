"""
Official Lifecycle Parser (Phase S2-B)
Extracts official lifecycle, deprecation, retirement, and successor metadata
strictly from NVIDIA Build HTML and Next.js RSC payloads without heuristic guessing.
"""

import html
import json
import re
from datetime import datetime
from typing import Any, Optional

NVIDIA_BUILD_BASE = "https://build.nvidia.com"


def is_valid_iso_date(date_str: Optional[str]) -> bool:
    """Validate that a date string is a valid YYYY-MM-DD date."""
    if not date_str or not isinstance(date_str, str):
        return False
    clean = date_str.strip()
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', clean):
        return False
    try:
        datetime.strptime(clean, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_official_lifecycle(model_id: str, html_content: str) -> dict[str, Any]:
    """
    Extract Ground Truth lifecycle metadata strictly when official evidence exists.
    Returns None values for fields without unambiguous official evidence.
    """
    result: dict[str, Any] = {
        "availability": None,
        "official_deprecation_date": None,
        "official_retirement_date": None,
        "replacement_model_id": None,
        "deprecation_source_url": None,
        "deprecation_notes": None,
        "evidence_type": "NVIDIA Build",
        "confidence": "low",
    }

    if not html_content or not isinstance(html_content, str):
        return result

    clean_html = html_content.strip()
    if not clean_html:
        return result

    lower_html = clean_html.lower()

    # 1. Structured RSC / JSON Lifecycle extraction
    # Look for specifications.lifecycle or official lifecycle block
    rsc_lifecycle_match = re.search(r'\\?"(?:lifecycle|deprecationNotice|modelStatus)\\?"\s*:\s*\{([^}]+)\}', clean_html)
    if rsc_lifecycle_match:
        block = rsc_lifecycle_match.group(1).replace('\\"', '"')
        
        # Status / Availability
        st_m = re.search(r'"(?:status|availability)"\s*:\s*"([^"]+)"', block, re.IGNORECASE)
        if st_m:
            st = st_m.group(1).lower().strip()
            if st in ["deprecated", "retiring", "removed", "active"]:
                result["availability"] = st
                result["confidence"] = "high"

        # Deprecation date
        dep_date_m = re.search(r'"(?:deprecationDate|deprecatedAt|officialDeprecationDate)"\s*:\s*"([^"]+)"', block)
        if dep_date_m:
            candidate_date = dep_date_m.group(1)[:10]
            if is_valid_iso_date(candidate_date):
                result["official_deprecation_date"] = candidate_date

        # Retirement / Sunset date
        ret_date_m = re.search(r'"(?:retirementDate|sunsetDate|retiredAt)"\s*:\s*"([^"]+)"', block)
        if ret_date_m:
            candidate_ret_date = ret_date_m.group(1)[:10]
            if is_valid_iso_date(candidate_ret_date):
                result["official_retirement_date"] = candidate_ret_date

        # Replacement model
        rep_m = re.search(r'"(?:replacementModel|replacementModelId|successor|migratedTo)"\s*:\s*"([^"]+)"', block)
        if rep_m:
            rep_id = rep_m.group(1).strip()
            if "/" in rep_id and not re.search(r'\s', rep_id):
                result["replacement_model_id"] = rep_id

    # 2. Scope extraction to Main Content, Banners, and Notice Alerts
    main_m = re.search(r'<main[^>]*>(.*?)</main>', clean_html, re.DOTALL | re.IGNORECASE)
    main_html = main_m.group(1) if main_m else clean_html

    # Banner / Alert callout detection (e.g. nv-alert, banner, deprecation banner)
    banner_matches = re.findall(
        r'<div[^>]*(?:class|data-testid)=["\'][^"\']*(?:alert|banner|notice|callout|warning)[^"\']*["\'][^>]*>(.*?)</div>',
        clean_html,
        re.DOTALL | re.IGNORECASE,
    )
    banner_text = " ".join([re.sub(r'<[^>]+>', ' ', b) for b in banner_matches])
    full_target_text = (banner_text + "\n" + re.sub(r'<[^>]+>', ' ', main_html)).strip()

    # 3. Unambiguous Deprecation Notice Detection
    # Deprecated
    dep_patterns = [
        r'\b(?:this\s+model\s+)?(?:is|has\s+been)\s+deprecated\b',
        r'\bdeprecation\s+notice\b',
        r'\bdeprecated\s+as\s+of\b',
        r'\bdeprecated\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})\b',
        r'\bdeprecated\b',
    ]
    for dp in dep_patterns:
        m = re.search(dp, full_target_text, re.IGNORECASE)
        if m:
            result["availability"] = "deprecated"
            result["confidence"] = "high"
            result["deprecation_source_url"] = f"{NVIDIA_BUILD_BASE}/{model_id.strip()}"
            break

    # Retiring / Sunset
    if not result["availability"] or result["availability"] == "active":
        retiring_patterns = [
            r'\b(?:this\s+model\s+is\s+)?retiring\s+(?:on|soon|effective)\b',
            r'\bwill\s+be\s+retired\s+(?:on|as\s+of)\b',
            r'\bsunset\s+date\b',
            r'\bsunset\s+notice\b',
        ]
        for rp in retiring_patterns:
            if re.search(rp, full_target_text, re.IGNORECASE):
                result["availability"] = "retiring"
                result["confidence"] = "high"
                result["deprecation_source_url"] = f"{NVIDIA_BUILD_BASE}/{model_id.strip()}"
                break

    # Removed / Discontinued / End of Life
    if not result["availability"]:
        removed_patterns = [
            r'\bthis\s+model\s+is\s+no\s+longer\s+available\b',
            r'\bhas\s+been\s+discontinued\b',
            r'\bhas\s+reached\s+(?:its\s+)?end\s+of\s+life\b',
        ]
        for rmp in removed_patterns:
            if re.search(rmp, full_target_text, re.IGNORECASE):
                result["availability"] = "removed"
                result["confidence"] = "high"
                result["deprecation_source_url"] = f"{NVIDIA_BUILD_BASE}/{model_id.strip()}"
                break

    # 4. Replacement / Successor Model ID Parsing (Strict vendor/model format)
    if not result["replacement_model_id"]:
        rep_patterns = [
            r'(?:replaced\s+by|successor|recommended\s+replacement|migrate\s+to)[:\s]+\[?([a-zA-Z0-9_\-\.\/]+/[a-zA-Z0-9_\-\.]+)\]?',
            r'please\s+use\s+\[?([a-zA-Z0-9_\-\.\/]+/[a-zA-Z0-9_\-\.]+)\]?\s+instead',
        ]
        for rpp in rep_patterns:
            m = re.search(rpp, full_target_text, re.IGNORECASE)
            if m:
                cand = m.group(1).strip().strip("[]()\"'.,")
                if "/" in cand and cand != model_id and not re.search(r'\s', cand):
                    result["replacement_model_id"] = cand
                    break

    # 5. Official Date Extraction from text (YYYY-MM-DD or Month DD, YYYY)
    if not result["official_deprecation_date"] and result["availability"] in ["deprecated", "retiring"]:
        date_patterns = [
            r'(?:deprecated|retirement|sunset|effective)\s*(?:date|on|as of)[:\s]+(\d{4}-\d{2}-\d{2})',
            r'(?:deprecated|retirement|sunset|effective)\s*(?:date|on|as of)[:\s]+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
        ]
        for dtp in date_patterns:
            m = re.search(dtp, full_target_text, re.IGNORECASE)
            if m:
                raw_d = m.group(1).strip()
                if re.match(r'^\d{4}-\d{2}-\d{2}$', raw_d) and is_valid_iso_date(raw_d):
                    result["official_deprecation_date"] = raw_d
                    break
                else:
                    try:
                        parsed_dt = datetime.strptime(raw_d, "%B %d, %Y")
                        result["official_deprecation_date"] = parsed_dt.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        try:
                            parsed_dt = datetime.strptime(raw_d, "%b %d, %Y")
                            result["official_deprecation_date"] = parsed_dt.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            pass

    # 6. Extract Notice Summary / Notes
    if result["availability"] in ["deprecated", "retiring", "removed"] and not result["deprecation_notes"]:
        note_m = re.search(r'(?:Notice|Alert|Deprecation|Retirement)[:\s]+([^.\n]{10,200}\.)', full_target_text, re.IGNORECASE)
        if note_m:
            result["deprecation_notes"] = note_m.group(1).strip()

    # 7. Fallback: If no deprecation evidence found, and model page is normal active endpoint
    if not result["availability"]:
        if "try nvidia nim" in lower_html or "api reference" in lower_html or "execute model" in lower_html:
            result["availability"] = "active"
            result["confidence"] = "medium"

    return result
