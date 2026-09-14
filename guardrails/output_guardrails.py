"""
Output Guardrails
-----------------
Validates the LLM response before returning it to the user.

Checks:
1. Output type
2. Empty output
3. Maximum output length
4. API keys
5. Secret keys
6. Access tokens
7. Passwords
8. Private keys
9. JWT tokens
10. Google API keys
11. Internal/system instruction exposure

Designed for:
    FastAPI + Gemini + LLM Guardrails
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

MAX_OUTPUT_LENGTH = 20000


# ============================================================
# SENSITIVE OUTPUT REGEX PATTERNS
# ============================================================

SENSITIVE_OUTPUT_PATTERNS = {
    # --------------------------------------------------------
    # Generic API key assignment
    # --------------------------------------------------------

    "api_key_assignment": re.compile(
        r"\b(api[\s_-]?key|apikey)\s*[:=]\s*"
        r"['\"]?[A-Za-z0-9_\-]{12,}['\"]?",
        flags=re.IGNORECASE,
    ),

    # --------------------------------------------------------
    # Secret key assignment
    # --------------------------------------------------------

    "secret_key_assignment": re.compile(
        r"\b(secret[\s_-]?key)\s*[:=]\s*"
        r"['\"]?[A-Za-z0-9_\-]{12,}['\"]?",
        flags=re.IGNORECASE,
    ),

    # --------------------------------------------------------
    # Access token assignment
    # --------------------------------------------------------

    "access_token_assignment": re.compile(
        r"\b(access[\s_-]?token|token)\s*[:=]\s*"
        r"['\"]?[A-Za-z0-9._\-]{20,}['\"]?",
        flags=re.IGNORECASE,
    ),

    # --------------------------------------------------------
    # Password assignment
    # --------------------------------------------------------

    "password_assignment": re.compile(
        r"\b(password|passwd|pwd)\s*[:=]\s*"
        r"['\"]?[^\s'\"]{6,}['\"]?",
        flags=re.IGNORECASE,
    ),

    # --------------------------------------------------------
    # Private key block
    # --------------------------------------------------------

    "private_key_block": re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----",
        flags=re.IGNORECASE,
    ),

    # --------------------------------------------------------
    # JWT token
    # --------------------------------------------------------

    "jwt_token": re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\."
        r"[A-Za-z0-9_-]{10,}\."
        r"[A-Za-z0-9_-]{10,}\b",
        flags=re.IGNORECASE,
    ),

    # --------------------------------------------------------
    # Google API key
    # --------------------------------------------------------

    "google_api_key": re.compile(
        r"\bAIza[A-Za-z0-9_-]{20,}\b",
        flags=re.IGNORECASE,
    ),

    # --------------------------------------------------------
    # Generic bearer token
    # --------------------------------------------------------

    "bearer_token": re.compile(
        r"\bBearer\s+[A-Za-z0-9._\-+/=]{20,}",
        flags=re.IGNORECASE,
    ),

    # --------------------------------------------------------
    # AWS-style access key
    # --------------------------------------------------------

    "aws_access_key": re.compile(
        r"\bAKIA[0-9A-Z]{16}\b",
        flags=re.IGNORECASE,
    ),
}


# ============================================================
# INTERNAL INFORMATION PATTERNS
# ============================================================

INTERNAL_INFORMATION_PATTERNS = [
    "system prompt:",
    "system instructions:",
    "developer instructions:",
    "developer prompt:",
    "hidden instructions:",
    "internal instructions:",
    "internal system prompt:",
    "confidential system prompt:",
]


# ============================================================
# RESULT HELPERS
# ============================================================

def safe_result(
    *,
    message: str = "Output passed all guardrails.",
) -> dict:
    """
    Create a standard SAFE result.
    """

    return {
        "allowed": True,
        "category": "SAFE",
        "severity": "LOW",
        "rule": None,
        "message": message,
    }


def blocked_result(
    *,
    category: str,
    severity: str,
    rule: str,
    message: str,
) -> dict:
    """
    Create a standard BLOCKED result.
    """

    return {
        "allowed": False,
        "category": category,
        "severity": severity,
        "rule": rule,
        "message": message,
    }


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_output(text: str) -> str:
    """
    Normalize model output before checking it.
    """

    text = unicodedata.normalize("NFKC", text)

    return text.strip()


# ============================================================
# FIND SENSITIVE PATTERN
# ============================================================

def find_sensitive_pattern(
    text: str,
) -> Optional[str]:
    """
    Return the first sensitive-information rule matched.
    """

    for rule_name, pattern in SENSITIVE_OUTPUT_PATTERNS.items():

        if pattern.search(text):
            return rule_name

    return None


# ============================================================
# FIND INTERNAL INFORMATION
# ============================================================

def find_internal_information(
    text: str,
) -> Optional[str]:
    """
    Detect obvious exposure of system/developer
    instructions.
    """

    normalized_text = text.lower()

    for pattern in INTERNAL_INFORMATION_PATTERNS:

        if pattern in normalized_text:
            return pattern

    return None


# ============================================================
# OUTPUT GUARDRAIL
# ============================================================

def check_output(output: str) -> dict:
    """
    Validate the model output before returning it
    to the user.

    Returns:
        {
            "allowed": bool,
            "category": str,
            "severity": str,
            "rule": str | None,
            "message": str
        }
    """

    # ========================================================
    # 1. Validate output type
    # ========================================================

    if not isinstance(output, str):

        return blocked_result(
            category="INVALID_OUTPUT",
            severity="MEDIUM",
            rule="output_type",
            message="Model output must be a string.",
        )

    # ========================================================
    # 2. Empty output
    # ========================================================

    if not output.strip():

        return blocked_result(
            category="EMPTY_OUTPUT",
            severity="MEDIUM",
            rule="empty_output",
            message="Model returned an empty response.",
        )

    # ========================================================
    # 3. Maximum output length
    # ========================================================

    if len(output) > MAX_OUTPUT_LENGTH:

        return blocked_result(
            category="OUTPUT_LENGTH",
            severity="MEDIUM",
            rule="maximum_output_length",
            message=(
                f"Model output exceeds the maximum "
                f"allowed length of {MAX_OUTPUT_LENGTH} characters."
            ),
        )

    # ========================================================
    # 4. Normalize output
    # ========================================================

    text = normalize_output(output)

    # ========================================================
    # 5. Sensitive Credentials
    # ========================================================

    detected_sensitive = find_sensitive_pattern(text)

    if detected_sensitive:

        return blocked_result(
            category="SENSITIVE_OUTPUT",
            severity="CRITICAL",
            rule=detected_sensitive,
            message=(
                "Potentially sensitive credentials or "
                "secret information detected in model output."
            ),
        )

    # ========================================================
    # 6. Internal Information
    # ========================================================

    detected_internal = find_internal_information(text)

    if detected_internal:

        return blocked_result(
            category="INTERNAL_INFORMATION",
            severity="HIGH",
            rule="internal_prompt_exposure",
            message=(
                "Potential internal system or developer "
                "instructions detected in model output."
            ),
        )

    # ========================================================
    # 7. SAFE
    # ========================================================

    return safe_result()