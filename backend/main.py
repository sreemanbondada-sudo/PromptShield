from fastapi import FastAPI, Query

from database import (
    get_recent_events,
    get_statistics,
    save_security_event,
)
from detector import analyze_prompt
from schemas import AnalyzeRequest, AnalyzeResponse
from sensitive_detector import detect_sensitive_data


app = FastAPI(
    title="PromptShield API",
    description=(
        "Security API for detecting malicious AI prompts "
        "and sensitive-data exposure."
    ),
    version="0.3.0",
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

    analysis_result = {
        **prompt_result,
        "contains_sensitive_data": (
            sensitive_result["contains_sensitive_data"]
        ),
        "sensitive_findings": sensitive_result["findings"],
        "redacted_prompt": sensitive_result["redacted_text"],
        "recommended_action": recommended_action,
    }

    event_id = save_security_event(
        analysis_result=analysis_result,
        prompt_length=len(request.prompt),
    )

    return {
        "event_id": event_id,
        **analysis_result,
    }


@app.get("/events")
def events(
    limit: int = Query(default=20, ge=1, le=100),
):
    return {
        "events": get_recent_events(limit=limit),
    }


@app.get("/statistics")
def statistics():
    return get_statistics()
