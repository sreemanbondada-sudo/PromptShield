from pathlib import Path

from encryption_service import get_aes_key
from integrity_service import get_hmac_key
from ml_detector import DEFAULT_MODEL_PATH
import os

MINIMUM_HMAC_KEY_LENGTH = 32
ALLOWED_ORIGINS_ENVIRONMENT_VARIABLE = (
    "PROMPTSHIELD_ALLOWED_ORIGINS"
)

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

def get_allowed_origins() -> list[str]:
    """Return the explicitly permitted frontend origins."""
    configured_origins = os.getenv(
        ALLOWED_ORIGINS_ENVIRONMENT_VARIABLE
    )

    if configured_origins:
        origins = [
            origin.strip().rstrip("/")
            for origin in configured_origins.split(",")
            if origin.strip()
        ]

    else:
        origins = DEFAULT_ALLOWED_ORIGINS.copy()

    if not origins:
        raise RuntimeError(
            "At least one allowed CORS origin "
            "must be configured."
        )

    if "*" in origins:
        raise RuntimeError(
            "Wildcard CORS origins are not permitted."
        )

    return origins

def validate_configuration(
    model_path: Path = DEFAULT_MODEL_PATH,
) -> dict:
    """Validate required PromptShield configuration."""
    errors = []

    try:
        hmac_key = get_hmac_key()

        if len(hmac_key) < MINIMUM_HMAC_KEY_LENGTH:
            errors.append(
                "PROMPTSHIELD_HMAC_KEY must contain "
                f"at least {MINIMUM_HMAC_KEY_LENGTH} "
                "characters."
            )

    except RuntimeError as error:
        errors.append(str(error))

    try:
        aes_key = get_aes_key()

    except RuntimeError as error:
        errors.append(str(error))
        aes_key = None

    if not model_path.exists():
        errors.append(
            "The ML model file was not found. "
            "Run python train_model.py first."
        )

    if errors:
        formatted_errors = "\n".join(
            f"- {error}"
            for error in errors
        )

        raise RuntimeError(
            "Invalid PromptShield configuration:\n"
            f"{formatted_errors}"
        )

    return {
        "hmac_configured": True,
        "hmac_key_length": len(hmac_key),
        "aes_configured": True,
        "aes_key_bits": len(aes_key) * 8,
        "model_configured": True,
        "model_path": str(model_path),
    }