import os
from pathlib import Path

from auth_service import (
    ADMIN_PASSWORD_HASH_ENVIRONMENT_VARIABLE,
    ADMIN_USERNAME_ENVIRONMENT_VARIABLE,
    JWT_SECRET_ENVIRONMENT_VARIABLE,
    get_admin_credentials,
    get_jwt_secret,
)
from encryption_service import get_aes_key
from integrity_service import get_hmac_key
from ml_detector import DEFAULT_MODEL_PATH


MINIMUM_HMAC_KEY_LENGTH = 32

ALLOWED_ORIGINS_ENVIRONMENT_VARIABLE = (
    "PROMPTSHIELD_ALLOWED_ORIGINS"
)

RATE_LIMIT_MAXIMUM_REQUESTS_ENVIRONMENT_VARIABLE = (
    "PROMPTSHIELD_RATE_LIMIT_MAX_REQUESTS"
)

RATE_LIMIT_WINDOW_SECONDS_ENVIRONMENT_VARIABLE = (
    "PROMPTSHIELD_RATE_LIMIT_WINDOW_SECONDS"
)

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

DEFAULT_RATE_LIMIT_MAXIMUM_REQUESTS = 30
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60


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


def get_positive_integer_setting(
    variable_name: str,
    default_value: int,
) -> int:
    """Read and validate a positive integer setting."""
    configured_value = os.getenv(variable_name)

    if configured_value is None:
        return default_value

    try:
        value = int(configured_value)

    except ValueError as error:
        raise RuntimeError(
            f"{variable_name} must be a positive integer."
        ) from error

    if value < 1:
        raise RuntimeError(
            f"{variable_name} must be a positive integer."
        )

    return value


def get_rate_limit_settings() -> dict:
    """Return validated rate-limit configuration."""
    return {
        "maximum_requests": get_positive_integer_setting(
            RATE_LIMIT_MAXIMUM_REQUESTS_ENVIRONMENT_VARIABLE,
            DEFAULT_RATE_LIMIT_MAXIMUM_REQUESTS,
        ),
        "window_seconds": get_positive_integer_setting(
            RATE_LIMIT_WINDOW_SECONDS_ENVIRONMENT_VARIABLE,
            DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        ),
    }


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
        hmac_key = None

    try:
        aes_key = get_aes_key()

    except RuntimeError as error:
        errors.append(str(error))
        aes_key = None

    try:
        jwt_secret = get_jwt_secret()

    except RuntimeError as error:
        errors.append(str(error))
        jwt_secret = None

    try:
        admin_username, admin_password_hash = (
            get_admin_credentials()
        )

        if not admin_password_hash.startswith(
            "$argon2"
        ):
            errors.append(
                f"{ADMIN_PASSWORD_HASH_ENVIRONMENT_VARIABLE} "
                "must contain an Argon2 password hash."
            )

    except RuntimeError as error:
        errors.append(str(error))
        admin_username = None
        admin_password_hash = None

    try:
        rate_limit_settings = get_rate_limit_settings()

    except RuntimeError as error:
        errors.append(str(error))
        rate_limit_settings = None

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
        "authentication_configured": True,
        "jwt_secret_length": len(jwt_secret),
        "admin_username": admin_username,
        "admin_password_hash_configured": bool(
            admin_password_hash
        ),
        "model_configured": True,
        "model_path": str(model_path),
        "rate_limit_configured": True,
        "rate_limit_maximum_requests": (
            rate_limit_settings["maximum_requests"]
        ),
        "rate_limit_window_seconds": (
            rate_limit_settings["window_seconds"]
        ),
    }