from pathlib import Path

from encryption_service import get_aes_key
from integrity_service import get_hmac_key
from ml_detector import DEFAULT_MODEL_PATH


MINIMUM_HMAC_KEY_LENGTH = 32


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