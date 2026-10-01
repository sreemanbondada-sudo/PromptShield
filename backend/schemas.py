from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=5000,
        description="The prompt that PromptShield should analyze.",
    )


class AnalyzeResponse(BaseModel):
    is_malicious: bool
    risk_level: str
    risk_score: int
    category: str
    matched_patterns: list[str]
    explanation: str