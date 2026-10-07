from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=100,
        description=(
            "The PromptShield administrator username."
        ),
    )

    password: str = Field(
        min_length=8,
        max_length=256,
        description=(
            "The PromptShield administrator password."
        ),
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    expires_in: int = Field(
        gt=0,
        description=(
            "Access-token lifetime in seconds."
        ),
    )


class AnalyzeRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=5000,
        description=(
            "The prompt that PromptShield should analyze."
        ),
    )


class SensitiveFinding(BaseModel):
    type: str
    redacted_value: str
    start: int
    end: int
    detection_method: str


class ContextualActionShadow(BaseModel):
    available: bool
    predicted_action: str | None = None

    probabilities: dict[str, float] = Field(
        default_factory=dict,
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    probability_margin: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    is_confident: bool | None = None
    requires_review: bool | None = None
    agrees_with_production: bool | None = None
    model_name: str | None = None
    mode: str = "shadow"


class AnalyzeResponse(BaseModel):
    event_id: int
    is_malicious: bool
    risk_level: str
    risk_score: int
    category: str
    matched_patterns: list[str]
    explanation: str
    contains_sensitive_data: bool
    sensitive_findings: list[SensitiveFinding]
    redacted_prompt: str
    recommended_action: str
    ml_prediction: bool

    ml_probability: float = Field(
        ge=0.0,
        le=1.0,
    )

    detection_sources: list[str]
    contextual_shadow: ContextualActionShadow

class IntegrityVerifyRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=10000,
        description="The trusted message to verify.",
    )

    signature: str = Field(
        pattern=r"^[0-9a-fA-F]{64}$",
        description=(
            "The expected HMAC-SHA-256 signature."
        ),
    )


class IntegrityVerifyResponse(BaseModel):
    valid: bool
    algorithm: str


class MLAnalysisResponse(BaseModel):
    is_malicious: bool

    malicious_probability: float = Field(
        ge=0.0,
        le=1.0,
    )

    threshold: float = Field(
        ge=0.0,
        le=1.0,
    )

    model_type: str