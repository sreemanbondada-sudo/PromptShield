from fastapi import FastAPI

from detector import analyze_prompt
from schemas import AnalyzeRequest, AnalyzeResponse
from sensitive_detector import detect_sensitive_data


app = FastAPI(
    title="PromptShield API",
    description=(
        "Security API for detecting malicious AI prompts "
        "and sensitive-data exposure."
    ),
    version="0.2.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to PromptShield",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    prompt_result = analyze_prompt(request.prompt)
    sensitive_result = detect_sensitive_data(request.prompt)

    if prompt_result["is_malicious"]:
        recommended_action = "block"
    elif sensitive_result["contains_sensitive_data"]:
        recommended_action = "redact"
        prompt_result["risk_score"] = max(
            prompt_result["risk_score"],
            60,
        )
        prompt_result["risk_level"] = "medium"
        prompt_result["category"] = "sensitive_data_exposure"
        prompt_result["explanation"] = (
            "The prompt contains sensitive information that should be "
            "redacted before it is sent to an AI application."
        )
    else:
        recommended_action = "allow"

    return {
        **prompt_result,
        "contains_sensitive_data": (
            sensitive_result["contains_sensitive_data"]
        ),
        "sensitive_findings": sensitive_result["findings"],
        "redacted_prompt": sensitive_result["redacted_text"],
        "recommended_action": recommended_action,
    }
