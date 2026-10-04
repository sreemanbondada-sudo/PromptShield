import math
import re
from collections import Counter


SENSITIVE_PATTERNS = [
    {
        "name": "email_address",
        "pattern": (
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+"
            r"\.[A-Za-z]{2,}\b"
        ),
    },
    {
        "name": "phone_number",
        "pattern": (
            r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"
        ),
    },
    {
        "name": "openai_api_key",
        "pattern": r"\bsk-[A-Za-z0-9_-]{20,}\b",
    },
    {
        "name": "aws_access_key",
        "pattern": r"\bAKIA[0-9A-Z]{16}\b",
    },
    {
        "name": "github_token",
        "pattern": r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    },
    {
        "name": "private_key",
        "pattern": (
            r"-----BEGIN "
            r"(?:RSA |EC |OPENSSH )?"
            r"PRIVATE KEY-----"
        ),
    },
    {
        "name": "password_assignment",
        "pattern": (
            r"\b(password|passwd|pwd)\s*[:=]\s*"
            r"[\"']?[^\s,\"']{6,}[\"']?"
        ),
    },
    {
        "name": "secret_assignment",
        "pattern": (
            r"\b(api[_-]?key|access[_-]?token|secret)"
            r"\s*[:=]\s*"
            r"[\"']?[^\s,\"']{8,}[\"']?"
        ),
    },
    {
        "name": "aadhaar_number",
        "pattern": (
            r"\b(?:aadhaar|aadhar|uid)\s*"
            r"(?:number|no\.?)?\s*"
            r"(?:is\s*)?[:=-]?\s*"
            r"(?P<value>"
            r"[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}"
            r")\b"
        ),
        "value_group": "value",
    },
    {
        "name": "bearer_token",
        "pattern": (
            r"\bbearer\s+"
            r"(?P<value>[A-Za-z0-9._~-]{20,})\b"
        ),
        "value_group": "value",
    },
    {
    "name": "passport_number",
    "pattern": (
        r"\bpassport\s*"
        r"(?:number|no\.?)\s*"
        r"(?:is\s*)?[:=-]?\s*"
        r"(?P<value>"
        r"(?:[A-Z]\d{7}"
        r"|"
        r"\d{4}(?:[\s-]?\d{4}){1,2})"
        r")\b"
    ),
    "value_group": "value",
},
]


TOKEN_PATTERN = re.compile(
    r"\b[A-Za-z0-9_-]{20,}\b"
)


def calculate_entropy(value: str) -> float:
    """Calculate the Shannon entropy of a string."""
    if not value:
        return 0.0

    frequencies = Counter(value)
    length = len(value)

    return -sum(
        (count / length) * math.log2(count / length)
        for count in frequencies.values()
    )


def is_high_entropy_secret(value: str) -> bool:
    """Determine whether a token looks random."""
    character_classes = [
        any(
            character.islower()
            for character in value
        ),
        any(
            character.isupper()
            for character in value
        ),
        any(
            character.isdigit()
            for character in value
        ),
        any(
            character in "_-"
            for character in value
        ),
    ]

    return (
        len(value) >= 20
        and calculate_entropy(value) >= 3.5
        and any(
            character.isalpha()
            for character in value
        )
        and any(
            character.isdigit()
            for character in value
        )
        and sum(character_classes) >= 3
    )


def redact_value(value: str) -> str:
    """Hide most of a detected sensitive value."""
    if len(value) <= 4:
        return "*" * len(value)

    return (
        value[:2]
        + ("*" * (len(value) - 4))
        + value[-2:]
    )


def detect_sensitive_data(text: str) -> dict:
    """Detect and redact sensitive values in text."""
    findings = []
    redacted_text = text

    for sensitive_pattern in SENSITIVE_PATTERNS:
        matches = list(
            re.finditer(
                sensitive_pattern["pattern"],
                text,
                flags=re.IGNORECASE,
            )
        )

        for match in matches:
            value_group = sensitive_pattern.get(
                "value_group"
            )

            if value_group:
                detected_value = match.group(
                    value_group
                )

                start, end = match.span(
                    value_group
                )

            else:
                detected_value = match.group(0)
                start, end = match.span(0)

            if detected_value not in redacted_text:
                continue

            findings.append(
                {
                    "type": sensitive_pattern["name"],
                    "redacted_value": redact_value(
                        detected_value
                    ),
                    "start": start,
                    "end": end,
                    "detection_method": "pattern",
                }
            )

            redacted_text = redacted_text.replace(
                detected_value,
                "[REDACTED]",
            )

    for match in TOKEN_PATTERN.finditer(text):
        candidate = match.group(0)

        if candidate not in redacted_text:
            continue

        if is_high_entropy_secret(candidate):
            findings.append(
                {
                    "type": "high_entropy_secret",
                    "redacted_value": redact_value(
                        candidate
                    ),
                    "start": match.start(),
                    "end": match.end(),
                    "detection_method": "entropy",
                }
            )

            redacted_text = redacted_text.replace(
                candidate,
                "[REDACTED]",
            )

    unique_findings = []

    for finding in findings:
        if finding not in unique_findings:
            unique_findings.append(finding)

    return {
        "contains_sensitive_data": bool(
            unique_findings
        ),
        "findings": unique_findings,
        "redacted_text": redacted_text,
    }