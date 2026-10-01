import hashlib
import hmac
import os


HMAC_KEY_ENVIRONMENT_VARIABLE = "PROMPTSHIELD_HMAC_KEY"


def get_hmac_key() -> str:
    """Read the HMAC secret key from the environment."""
    secret_key = os.getenv(HMAC_KEY_ENVIRONMENT_VARIABLE)

    if not secret_key:
        raise RuntimeError(
            f"{HMAC_KEY_ENVIRONMENT_VARIABLE} is not configured."
        )

    return secret_key


def generate_signature(
    message: str,
    secret_key: str | None = None,
) -> str:
    """Generate an HMAC-SHA-256 signature for a message."""
    resolved_key = secret_key or get_hmac_key()

    return hmac.new(
        key=resolved_key.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_signature(
    message: str,
    signature: str,
    secret_key: str | None = None,
) -> bool:
    """Check whether a message matches its signature."""
    if not signature:
        return False

    expected_signature = generate_signature(
        message=message,
        secret_key=secret_key,
    )

    return hmac.compare_digest(
        expected_signature,
        signature,
    )