from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

from config import validate_configuration
from database import (
    get_recent_events,
    get_statistics,
    initialize_database,
    save_security_event,
    verify_audit_chain,
)
from detector import analyze_prompt
from integrity_service import verify_signature
from ml_detector import analyze_prompt_with_ml
from schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    IntegrityVerifyRequest,
    IntegrityVerifyResponse,
    MLAnalysisResponse,
)
from sensitive_detector import detect_sensitive_data


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate configuration and initialize storage."""
    validate_configuration()
    initialize_database()

    yield


app = FastAPI(
    title="PromptShield API",
    description=(
        "Security API for detecting malicious AI prompts, "
        "sensitive-data exposure and integrity violations."
    ),
    version="0.7.0",
    lifespan=lifespan,
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


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
)
def analyze(request: AnalyzeRequest):
    prompt_result = analyze_prompt(request.prompt)

    sensitive_result = detect_sensitive_data(
        request.prompt
    )

    try:
        ml_result = analyze_prompt_with_ml(
            request.prompt
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    detection_sources = []

    if prompt_result["is_malicious"]:
        detection_sources.append("rule_engine")

    if sensitive_result["contains_sensitive_data"]:
        detection_sources.append(
            "sensitive_data_detector"
        )

    if ml_result["is_malicious"]:
        detection_sources.append(
            "machine_learning"
        )

    if prompt_result["is_malicious"]:
        recommended_action = "block"

    elif sensitive_result["contains_sensitive_data"]:
        recommended_action = "redact"

        prompt_result["risk_score"] = max(
            prompt_result["risk_score"],
            60,
        )

        prompt_result["risk_level"] = "medium"

        prompt_result["category"] = (
            "sensitive_data_exposure"
        )

        prompt_result["explanation"] = (
            "The prompt contains sensitive information "
            "that should be redacted before it is sent "
            "to an AI application."
        )

    elif ml_result["is_malicious"]:
        recommended_action = "review"

        ml_risk_score = round(
            ml_result["malicious_probability"] * 100
        )

        prompt_result["risk_score"] = max(
            prompt_result["risk_score"],
            ml_risk_score,
        )

        prompt_result["risk_level"] = "medium"

        prompt_result["category"] = (
            "ml_suspicious_prompt"
        )

        prompt_result["explanation"] = (
            "The machine-learning model marked this "
            "prompt as suspicious. Manual review is "
            "recommended because the model is advisory."
        )

    else:
        recommended_action = "allow"

    analysis_result = {
        **prompt_result,
        "contains_sensitive_data": (
            sensitive_result["contains_sensitive_data"]
        ),
        "sensitive_findings": (
            sensitive_result["findings"]
        ),
        "redacted_prompt": (
            sensitive_result["redacted_text"]
        ),
        "recommended_action": recommended_action,
        "ml_prediction": ml_result["is_malicious"],
        "ml_probability": (
            ml_result["malicious_probability"]
        ),
        "detection_sources": detection_sources,
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
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
):
    return {
        "events": get_recent_events(limit=limit),
    }


@app.get("/statistics")
def statistics():
    return get_statistics()


@app.post(
    "/integrity/verify",
    response_model=IntegrityVerifyResponse,
)
def verify_integrity(
    request: IntegrityVerifyRequest,
):
    try:
        valid = verify_signature(
            message=request.message,
            signature=request.signature,
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    return {
        "valid": valid,
        "algorithm": "HMAC-SHA-256",
    }


@app.get("/audit/verify")
def verify_database_audit_chain():
    try:
        return verify_audit_chain()

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error


@app.post(
    "/ml/analyze",
    response_model=MLAnalysisResponse,
)
def analyze_with_machine_learning(
    request: AnalyzeRequest,
):
    try:
        return analyze_prompt_with_ml(
            request.prompt
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error