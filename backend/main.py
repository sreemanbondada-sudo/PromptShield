from fastapi import FastAPI

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