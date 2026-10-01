import re


RULES = [
    {
        "pattern": r"\bignore\s+(all\s+)?(previous|prior)\s+instructions?\b",
        "name": "instruction override",
        "category": "prompt_injection",
        "score": 70,
    },
    {
        "pattern": (
            r"\b(reveal|show|print|display)\s+(your\s+)?"
            r"(hidden\s+)?(system|developer)\s+(prompt|instructions?)\b"
        ),
        "name": "system prompt extraction",
        "category": "system_prompt_extraction",
        "score": 80,
    },
    {
        "pattern": (
            r"\b(bypass|disable|override|remove)\s+(your\s+)?"
            r"(safety|security|rules?|restrictions?|guardrails?)\b"
        ),
        "name": "safety bypass",
        "category": "jailbreak",
        "score": 75,
    },
    {
        "pattern": r"\bdo\s+not\s+follow\s+(your\s+)?(rules?|instructions?)\b",
        "name": "rule rejection",
        "category": "prompt_injection",
        "score": 65,
    },
    {
        "pattern": r"\bpretend\s+(that\s+)?you\s+have\s+no\s+(rules?|restrictions?)\b",
        "name": "unrestricted-role request",
        "category": "jailbreak",
        "score": 65,
    },
]


EXPLANATIONS = {
    "prompt_injection": (
        "The prompt appears to contain instructions that attempt to "
        "override the AI application's original instructions."
    ),
    "system_prompt_extraction": (
        "The prompt appears to request hidden system or developer instructions."
    ),
    "jailbreak": (
        "The prompt appears to request that the AI bypass its safety controls."
    ),
    "safe": "No known malicious patterns were detected.",
}


def analyze_prompt(prompt: str) -> dict:
    normalized_prompt = " ".join(prompt.lower().split())
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

    if risk_score >= 70:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "is_malicious": risk_score >= 40,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "category": category,
        "matched_patterns": [rule["name"] for rule in matches],
        "explanation": EXPLANATIONS[category],
    }