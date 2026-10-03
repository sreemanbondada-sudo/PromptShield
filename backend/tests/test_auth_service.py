from datetime import (
    datetime,
    timedelta,
    timezone,
)

import jwt
import pytest

from auth_service import (
    ADMIN_PASSWORD_HASH_ENVIRONMENT_VARIABLE,
    ADMIN_USERNAME_ENVIRONMENT_VARIABLE,
    JWT_ALGORITHM,
    JWT_SECRET_ENVIRONMENT_VARIABLE,
    AuthenticationError,
    authenticate_admin,
    create_access_token,
    decode_access_token,
    get_jwt_secret,
    hash_password,
    verify_password,
)


TEST_JWT_SECRET = (
    "test-jwt-secret-with-at-least-32-characters"
)


def test_password_hash_can_be_verified():
    password = "correct-horse-battery-staple"
    stored_hash = hash_password(password)

    assert verify_password(
        password,
        stored_hash,
    ) is True

    assert verify_password(
        "incorrect-password",
        stored_hash,
    ) is False


def test_empty_password_cannot_be_hashed():
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        hash_password("")


def test_invalid_password_hash_is_rejected():
    assert verify_password(
        "password",
        "not-a-valid-password-hash",
    ) is False


def test_configured_admin_can_authenticate(
    monkeypatch,
):
    username = "promptshield-admin"
    password = "secure-admin-password"
    stored_hash = hash_password(password)

    monkeypatch.setenv(
        ADMIN_USERNAME_ENVIRONMENT_VARIABLE,
        username,
    )

    monkeypatch.setenv(
        ADMIN_PASSWORD_HASH_ENVIRONMENT_VARIABLE,
        stored_hash,
    )

    assert authenticate_admin(
        username,
        password,
    ) is True


def test_incorrect_admin_credentials_are_rejected(
    monkeypatch,
):
    username = "promptshield-admin"
    password = "secure-admin-password"
    stored_hash = hash_password(password)

    monkeypatch.setenv(
        ADMIN_USERNAME_ENVIRONMENT_VARIABLE,
        username,
    )

    monkeypatch.setenv(
        ADMIN_PASSWORD_HASH_ENVIRONMENT_VARIABLE,
        stored_hash,
    )

    assert authenticate_admin(
        "incorrect-user",
        password,
    ) is False

    assert authenticate_admin(
        username,
        "incorrect-password",
    ) is False


def test_jwt_secret_is_loaded_from_environment(
    monkeypatch,
):
    monkeypatch.setenv(
        JWT_SECRET_ENVIRONMENT_VARIABLE,
        TEST_JWT_SECRET,
    )

    assert get_jwt_secret() == TEST_JWT_SECRET


def test_missing_jwt_secret_is_rejected(
    monkeypatch,
):
    monkeypatch.delenv(
        JWT_SECRET_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="is not configured",
    ):
        get_jwt_secret()


def test_short_jwt_secret_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        JWT_SECRET_ENVIRONMENT_VARIABLE,
        "short-secret",
    )

    with pytest.raises(
        RuntimeError,
        match="at least 32 characters",
    ):
        get_jwt_secret()


def test_access_token_can_be_created_and_decoded():
    token = create_access_token(
        subject="promptshield-admin",
        secret=TEST_JWT_SECRET,
    )

    payload = decode_access_token(
        token,
        secret=TEST_JWT_SECRET,
    )

    assert payload["sub"] == "promptshield-admin"
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload


def test_token_signed_with_wrong_secret_is_rejected():
    token = create_access_token(
        subject="promptshield-admin",
        secret=TEST_JWT_SECRET,
    )

    with pytest.raises(
        AuthenticationError,
        match="invalid or expired",
    ):
        decode_access_token(
            token,
            secret=(
                "different-secret-with-at-least-32-characters"
            ),
        )


def test_expired_token_is_rejected():
    old_time = datetime.now(
        timezone.utc
    ) - timedelta(hours=2)

    token = create_access_token(
        subject="promptshield-admin",
        secret=TEST_JWT_SECRET,
        issued_at=old_time,
        expires_delta=timedelta(minutes=5),
    )

    with pytest.raises(
        AuthenticationError,
        match="invalid or expired",
    ):
        decode_access_token(
            token,
            secret=TEST_JWT_SECRET,
        )


def test_missing_token_is_rejected():
    with pytest.raises(
        AuthenticationError,
        match="missing",
    ):
        decode_access_token(
            "",
            secret=TEST_JWT_SECRET,
        )


def test_incorrect_token_type_is_rejected():
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "promptshield-admin",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "refresh",
        },
        TEST_JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(
        AuthenticationError,
        match="Token type is invalid",
    ):
        decode_access_token(
            token,
            secret=TEST_JWT_SECRET,
        )