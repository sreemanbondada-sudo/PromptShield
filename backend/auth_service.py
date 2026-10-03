import hmac
import os
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash


JWT_SECRET_ENVIRONMENT_VARIABLE = (
    "PROMPTSHIELD_JWT_SECRET"
)

ADMIN_USERNAME_ENVIRONMENT_VARIABLE = (
    "PROMPTSHIELD_ADMIN_USERNAME"
)

ADMIN_PASSWORD_HASH_ENVIRONMENT_VARIABLE = (
    "PROMPTSHIELD_ADMIN_PASSWORD_HASH"
)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
MINIMUM_JWT_SECRET_LENGTH = 32

password_hash = PasswordHash.recommended()


class AuthenticationError(Exception):
    """Raised when authentication cannot be completed."""


def hash_password(password: str) -> str:
    """Create a secure Argon2 password hash."""
    if not password:
        raise ValueError(
            "Password must not be empty."
        )

    return password_hash.hash(password)


def verify_password(
    password: str,
    stored_password_hash: str,
) -> bool:
    """Verify a password against an Argon2 hash."""
    if not password or not stored_password_hash:
        return False

    try:
        return password_hash.verify(
            password,
            stored_password_hash,
        )

    except Exception:
        return False


def get_jwt_secret() -> str:
    """Load and validate the JWT signing secret."""
    secret = os.getenv(
        JWT_SECRET_ENVIRONMENT_VARIABLE
    )

    if not secret:
        raise RuntimeError(
            f"{JWT_SECRET_ENVIRONMENT_VARIABLE} "
            "is not configured."
        )

    if len(secret) < MINIMUM_JWT_SECRET_LENGTH:
        raise RuntimeError(
            f"{JWT_SECRET_ENVIRONMENT_VARIABLE} must "
            f"contain at least "
            f"{MINIMUM_JWT_SECRET_LENGTH} characters."
        )

    return secret


def get_admin_credentials() -> tuple[str, str]:
    """Load the configured administrator credentials."""
    username = os.getenv(
        ADMIN_USERNAME_ENVIRONMENT_VARIABLE
    )

    stored_password_hash = os.getenv(
        ADMIN_PASSWORD_HASH_ENVIRONMENT_VARIABLE
    )

    if not username:
        raise RuntimeError(
            f"{ADMIN_USERNAME_ENVIRONMENT_VARIABLE} "
            "is not configured."
        )

    if not stored_password_hash:
        raise RuntimeError(
            f"{ADMIN_PASSWORD_HASH_ENVIRONMENT_VARIABLE} "
            "is not configured."
        )

    return username, stored_password_hash


def authenticate_admin(
    username: str,
    password: str,
) -> bool:
    """Verify administrator username and password."""
    configured_username, stored_password_hash = (
        get_admin_credentials()
    )

    username_matches = hmac.compare_digest(
        username.encode("utf-8"),
        configured_username.encode("utf-8"),
    )

    password_matches = verify_password(
        password,
        stored_password_hash,
    )

    return username_matches and password_matches


def create_access_token(
    subject: str,
    secret: str | None = None,
    expires_delta: timedelta | None = None,
    issued_at: datetime | None = None,
) -> str:
    """Create a signed short-lived JWT access token."""
    if not subject:
        raise ValueError(
            "Token subject must not be empty."
        )

    signing_secret = secret or get_jwt_secret()

    token_issued_at = issued_at or datetime.now(
        timezone.utc
    )

    token_expiry = token_issued_at + (
        expires_delta
        or timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": subject,
        "iat": token_issued_at,
        "exp": token_expiry,
        "type": "access",
    }

    return jwt.encode(
        payload,
        signing_secret,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(
    token: str,
    secret: str | None = None,
) -> dict:
    """Verify and decode a JWT access token."""
    if not token:
        raise AuthenticationError(
            "Access token is missing."
        )

    signing_secret = secret or get_jwt_secret()

    try:
        payload = jwt.decode(
            token,
            signing_secret,
            algorithms=[JWT_ALGORITHM],
            options={
                "require": [
                    "sub",
                    "iat",
                    "exp",
                    "type",
                ],
            },
        )

    except InvalidTokenError as error:
        raise AuthenticationError(
            "Access token is invalid or expired."
        ) from error

    if payload.get("type") != "access":
        raise AuthenticationError(
            "Token type is invalid."
        )

    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject:
        raise AuthenticationError(
            "Token subject is invalid."
        )

    return payload