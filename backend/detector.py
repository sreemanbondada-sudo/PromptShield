import re


RULES = [
    # Prompt-injection rules
    {
    "pattern": (
        r"\b(ignore|disregard|forget|override)\s+"
        r"(?:"
        r"all\s+(?:(?:previous|prior|earlier|above)\s+)?"
        r"|"
        r"(?:previous|prior|earlier|above)\s+"
        r")"
        r"(instructions?|rules?|directions?)\b"
    ),
    "name": "instruction override",
    "category": "prompt_injection",
    "score": 80,
},
    {
        "pattern": (
            r"\b(these|my|new)\s+instructions?\s+"
            r"(replace|override|supersede)\s+"
            r"(the\s+)?(previous|original|system)\s+instructions?\b"
        ),
        "name": "instruction replacement",
        "category": "prompt_injection",
        "score": 80,
    },
    {
        "pattern": (
            r"\b(do\s+not|don't|never)\s+(follow|obey)\s+"
            r"(your\s+)?(rules?|instructions?|guidelines?)\b"
        ),
        "name": "rule rejection",
        "category": "prompt_injection",
        "score": 70,
    },

    # System-prompt extraction rules
    {
        "pattern": (
            r"\b(reveal|show|print|display|disclose)\s+(your\s+)?"
            r"(hidden\s+|original\s+)?"
            r"(system|developer)\s+(prompt|instructions?)\b"
        ),
        "name": "system-prompt extraction",
        "category": "system_prompt_extraction",
        "score": 90,
    },
    {
        "pattern": (
            r"\bwhat\s+(is|are|were)\s+(your\s+)?"
            r"(hidden\s+|original\s+)?"
            r"(system|developer)\s+(prompt|instructions?)\b"
        ),
        "name": "hidden-instruction request",
        "category": "system_prompt_extraction",
        "score": 85,
    },
    {
        "pattern": (
            r"\b(repeat|copy|output)\s+(the\s+)?"
            r"(initial|original|system|developer)\s+"
            r"(prompt|instructions?)\b"
        ),
        "name": "initial-prompt repetition",
        "category": "system_prompt_extraction",
        "score": 85,
    },

    # Jailbreak rules
    {
        "pattern": (
            r"\b(bypass|disable|remove|override|circumvent)\s+"
            r"(your\s+|the\s+)?"
            r"(safety|security|policy|policies|restrictions?|guardrails?)\b"
        ),
        "name": "safety-control bypass",
        "category": "jailbreak",
        "score": 85,
    },
    {
        "pattern": (
            r"\bpretend\s+(that\s+)?you\s+have\s+no\s+"
            r"(rules?|restrictions?|limitations?|guidelines?)\b"
        ),
        "name": "unrestricted-role request",
        "category": "jailbreak",
        "score": 75,
    },
    {
        "pattern": (
            r"\b(enable|enter|activate|switch\s+to)\s+"
            r"(dan|developer|jailbreak|unrestricted)\s+mode\b"
        ),
        "name": "jailbreak-mode activation",
        "category": "jailbreak",
        "score": 80,
    },
    {
        "pattern": (
            r"\byou\s+are\s+now\s+(dan|unfiltered|unrestricted|uncensored)\b"
        ),
        "name": "unrestricted-persona assignment",
        "category": "jailbreak",
        "score": 75,
    },

    # Role-manipulation rules
    {
        "pattern": (
            r"\b(act|behave|respond)\s+as\s+(the\s+)?"
            r"(system|developer|administrator|root\s+user)\b"
        ),
        "name": "privileged-role manipulation",
        "category": "role_manipulation",
        "score": 60,
    },
]


EXPLANATIONS = {
    "prompt_injection": (
        "The prompt attempts to replace, ignore or override the AI "
        "application's original instructions."
    ),
    "system_prompt_extraction": (
        "The prompt attempts to obtain hidden system or developer instructions."
    ),
    "jailbreak": (
        "The prompt attempts to bypass safety controls or activate an "
        "unrestricted AI mode."
    ),
    "role_manipulation": (
        "The prompt attempts to assign the AI a privileged role that could "
        "change its intended behaviour."
    ),
    "safe": "No known malicious patterns were detected.",
}


def normalize_prompt(prompt: str) -> str:
    """Convert a prompt into a consistent form before scanning it."""
    return " ".join(prompt.casefold().split())


def calculate_risk_level(risk_score: int) -> str:
    """Convert a numerical score into a readable risk level."""
    if risk_score >= 70:
        return "high"

    if risk_score >= 40:
        return "medium"

    return "low"


def analyze_prompt(prompt: str) -> dict:
    """Analyze a prompt using the initial rule-based security engine."""
    normalized_prompt = normalize_prompt(prompt)
    matches = []

    for rule in RULES:
        if re.search(rule["pattern"], normalized_prompt):
            matches.append(rule)

    if not matches:
        return {
            "is_malicious": False,
            "risk_level": "low",
            "risk_score": 0,
            "category": "safe",
            "matched_patterns": [],
            "explanation": EXPLANATIONS["safe"],
        }

    risk_score = min(sum(rule["score"] for rule in matches), 100)
    strongest_match = max(matches, key=lambda rule: rule["score"])
    category = strongest_match["category"]

    return {
        "is_malicious": risk_score >= 40,
        "risk_level": calculate_risk_level(risk_score),
        "risk_score": risk_score,
        "category": category,
        "matched_patterns": [rule["name"] for rule in matches],
        "explanation": EXPLANATIONS[category],
    }