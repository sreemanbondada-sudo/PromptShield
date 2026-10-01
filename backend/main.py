from fastapi import FastAPI

from detector import analyze_prompt
from schemas import AnalyzeRequest, AnalyzeResponse


app = FastAPI(
    title="PromptShield API",
    description="Security API for detecting malicious AI prompts.",
    version="0.1.0",
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
    return analyze_prompt(request.prompt)