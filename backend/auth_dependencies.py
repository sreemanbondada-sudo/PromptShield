import hmac

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from auth_service import (
    AuthenticationError,
    decode_access_token,
    get_admin_credentials,
)


bearer_scheme = HTTPBearer(
    auto_error=False,
)


def authentication_error() -> HTTPException:
    """Return a consistent authentication failure."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Authentication credentials are invalid."
        ),
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def require_admin(
    credentials: (
        HTTPAuthorizationCredentials | None
    ) = Depends(bearer_scheme),
) -> str:
    """Require a valid PromptShield administrator token."""
    if credentials is None:
        raise authentication_error()

    if credentials.scheme.lower() != "bearer":
        raise authentication_error()

    try:
        payload = decode_access_token(
            credentials.credentials
        )

        configured_username, _ = (
            get_admin_credentials()
        )

    except AuthenticationError as error:
        raise authentication_error() from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Authentication service is unavailable."
            ),
        ) from error

    token_subject = payload["sub"]

    subject_matches = hmac.compare_digest(
        token_subject.encode("utf-8"),
        configured_username.encode("utf-8"),
    )

    if not subject_matches:
        raise authentication_error()

    return configured_username