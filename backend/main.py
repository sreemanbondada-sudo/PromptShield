import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware

from auth_dependencies import (
    authentication_error,
    require_admin,
)
from auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_admin,
    create_access_token,
)
from config import (
    get_allowed_origins,
    get_rate_limit_settings,
    validate_configuration,
)
from contextual_action_service import (
    analyze_contextual_action,
)
from detector import analyze_prompt
from error_handlers import register_error_handlers
from integrity_service import verify_signature
from ml_detector import analyze_prompt_with_ml
from rate_limiter import RateLimitMiddleware
from request_controls import (
    RequestSizeLimitMiddleware,
)
from request_logging import (
    PrivacySafeRequestLoggingMiddleware,
)
from schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    IntegrityVerifyRequest,
    IntegrityVerifyResponse,
    LoginRequest,
    MLAnalysisResponse,
    TokenResponse,
    ContextualShadowStatisticsResponse,
)
from security_headers import (
    SecurityHeadersMiddleware,
)
from sensitive_detector import detect_sensitive_data
from storage import (
    check_database_integrity,
    get_recent_events,
    get_statistics,
    initialize_database,
    save_security_event,
    verify_audit_chain,
    get_contextual_shadow_statistics,
)


logger = logging.getLogger(__name__)


load_dotenv()

rate_limit_settings = get_rate_limit_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate configuration and initialize storage."""
    validate_configuration()
    initialize_database()

    database_integrity = check_database_integrity()

    if not database_integrity["valid"]:
        raise RuntimeError(
            "PromptShield database integrity "
            "verification failed."
        )

    yield


app = FastAPI(
    title="PromptShield API",
    description=(
        "Security API for detecting malicious AI prompts, "
        "sensitive-data exposure and integrity violations."
    ),
    version="0.8.0",
    lifespan=lifespan,
)


register_error_handlers(app)


app.add_middleware(
    RateLimitMiddleware,
    maximum_requests=(
        rate_limit_settings["maximum_requests"]
    ),
    window_seconds=(
        rate_limit_settings["window_seconds"]
    ),
)


app.add_middleware(
    RequestSizeLimitMiddleware,
)


app.add_middleware(
    PrivacySafeRequestLoggingMiddleware,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
    ],
    allow_headers=[
        "Content-Type",
        "Authorization",
    ],
)


app.add_middleware(
    SecurityHeadersMiddleware,
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
    "/auth/login",
    response_model=TokenResponse,
)
def login(request: LoginRequest):
    """Authenticate the configured administrator."""
    try:
        authenticated = authenticate_admin(
            username=request.username,
            password=request.password,
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication service is unavailable."
            ),
        ) from error

    if not authenticated:
        raise authentication_error()

    access_token = create_access_token(
        subject=request.username,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": (
            ACCESS_TOKEN_EXPIRE_MINUTES * 60
        ),
    }


def run_contextual_action_shadow(
    prompt: str,
    production_action: str,
) -> dict:
    """
    Run the contextual classifier without controlling production.

    A shadow-model failure must not interrupt the existing
    production analysis pipeline.
    """
    try:
        contextual_result = analyze_contextual_action(
            prompt
        )

    except Exception:
        logger.warning(
            "Contextual action shadow analysis failed.",
            exc_info=True,
        )

        return {
            "available": False,
            "predicted_action": None,
            "probabilities": {},
            "confidence": None,
            "probability_margin": None,
            "is_confident": None,
            "requires_review": None,
            "agrees_with_production": None,
            "model_name": None,
            "mode": "shadow",
        }

    predicted_action = contextual_result[
        "predicted_action"
    ]

    return {
        "available": True,
        "predicted_action": predicted_action,
        "probabilities": contextual_result[
            "probabilities"
        ],
        "confidence": contextual_result[
            "confidence"
        ],
        "probability_margin": contextual_result[
            "probability_margin"
        ],
        "is_confident": contextual_result[
            "is_confident"
        ],
        "requires_review": contextual_result[
            "requires_review"
        ],
        "agrees_with_production": (
            predicted_action == production_action
        ),
        "model_name": contextual_result[
            "model_name"
        ],
        "mode": "shadow",
    }


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
)
def analyze(
    request: AnalyzeRequest,
    _admin: str = Depends(require_admin),
):
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

    contextual_shadow = (
        run_contextual_action_shadow(
            prompt=request.prompt,
            production_action=recommended_action,
        )
    )

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
        "contextual_shadow": contextual_shadow,
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
    _admin: str = Depends(require_admin),
):
    return {
        "events": get_recent_events(limit=limit),
    }


@app.get("/statistics")
def statistics(
    _admin: str = Depends(require_admin),
):
    return get_statistics()

@app.get(
    "/statistics/contextual-shadow",
    response_model=ContextualShadowStatisticsResponse,
)
def contextual_shadow_statistics(
    _admin: str = Depends(require_admin),
):
    """Return privacy-safe contextual shadow statistics."""
    return get_contextual_shadow_statistics()

@app.post(
    "/integrity/verify",
    response_model=IntegrityVerifyResponse,
)
def verify_integrity(
    request: IntegrityVerifyRequest,
    _admin: str = Depends(require_admin),
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
def verify_database_audit_chain(
    _admin: str = Depends(require_admin),
):
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
    _admin: str = Depends(require_admin),
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