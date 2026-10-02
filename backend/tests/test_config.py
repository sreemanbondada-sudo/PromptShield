import base64

import pytest

from config import (
    ALLOWED_ORIGINS_ENVIRONMENT_VARIABLE,
    DEFAULT_ALLOWED_ORIGINS,
    DEFAULT_RATE_LIMIT_MAXIMUM_REQUESTS,
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
    MINIMUM_HMAC_KEY_LENGTH,
    RATE_LIMIT_MAXIMUM_REQUESTS_ENVIRONMENT_VARIABLE,
    RATE_LIMIT_WINDOW_SECONDS_ENVIRONMENT_VARIABLE,
    get_allowed_origins,
    get_rate_limit_settings,
    validate_configuration,
)


from encryption_service import (
    AES_KEY_ENVIRONMENT_VARIABLE,
)
from integrity_service import (
    HMAC_KEY_ENVIRONMENT_VARIABLE,
)


def test_valid_configuration_is_accepted(
    monkeypatch,
    tmp_path,
):
    model_path = tmp_path / "test-model.joblib"
    model_path.write_bytes(b"test-model")

    aes_key = base64.urlsafe_b64encode(
        bytes(range(32))
    ).decode("utf-8")

    monkeypatch.setenv(
        HMAC_KEY_ENVIRONMENT_VARIABLE,
        "h" * MINIMUM_HMAC_KEY_LENGTH,
    )

    monkeypatch.setenv(
        AES_KEY_ENVIRONMENT_VARIABLE,
        aes_key,
    )

    result = validate_configuration(
        model_path=model_path,
    )

    assert result["hmac_configured"] is True
    assert result["aes_configured"] is True
    assert result["aes_key_bits"] == 256
    assert result["model_configured"] is True


def test_weak_hmac_key_is_rejected(
    monkeypatch,
    tmp_path,
):
    model_path = tmp_path / "test-model.joblib"
    model_path.write_bytes(b"test-model")

    monkeypatch.setenv(
        HMAC_KEY_ENVIRONMENT_VARIABLE,
        "short-key",
    )

    with pytest.raises(
        RuntimeError,
        match="at least 32 characters",
    ):
        validate_configuration(
            model_path=model_path,
        )


def test_invalid_aes_key_is_rejected(
    monkeypatch,
    tmp_path,
):
    model_path = tmp_path / "test-model.joblib"
    model_path.write_bytes(b"test-model")

    monkeypatch.setenv(
        AES_KEY_ENVIRONMENT_VARIABLE,
        base64.urlsafe_b64encode(
            b"too-short"
        ).decode("utf-8"),
    )

    with pytest.raises(
        RuntimeError,
        match="32-byte key",
    ):
        validate_configuration(
            model_path=model_path,
        )


def test_missing_model_is_rejected(
    tmp_path,
):
    missing_model_path = (
        tmp_path / "missing-model.joblib"
    )

    with pytest.raises(
        RuntimeError,
        match="ML model file was not found",
    ):
        validate_configuration(
            model_path=missing_model_path,
        )

def test_default_cors_origins_are_used(
    monkeypatch,
):
    monkeypatch.delenv(
        ALLOWED_ORIGINS_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    assert get_allowed_origins() == (
        DEFAULT_ALLOWED_ORIGINS
    )


def test_configured_cors_origins_are_parsed(
    monkeypatch,
):
    monkeypatch.setenv(
        ALLOWED_ORIGINS_ENVIRONMENT_VARIABLE,
        (
            "https://dashboard.example.com/, "
            "http://localhost:5173"
        ),
    )

    assert get_allowed_origins() == [
        "https://dashboard.example.com",
        "http://localhost:5173",
    ]


def test_wildcard_cors_origin_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        ALLOWED_ORIGINS_ENVIRONMENT_VARIABLE,
        "*",
    )

    with pytest.raises(
        RuntimeError,
        match="Wildcard CORS origins",
    ):
        get_allowed_origins()

def test_default_rate_limit_settings_are_used(
    monkeypatch,
):
    monkeypatch.delenv(
        RATE_LIMIT_MAXIMUM_REQUESTS_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    monkeypatch.delenv(
        RATE_LIMIT_WINDOW_SECONDS_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    assert get_rate_limit_settings() == {
        "maximum_requests": (
            DEFAULT_RATE_LIMIT_MAXIMUM_REQUESTS
        ),
        "window_seconds": (
            DEFAULT_RATE_LIMIT_WINDOW_SECONDS
        ),
    }


def test_configured_rate_limit_settings_are_parsed(
    monkeypatch,
):
    monkeypatch.setenv(
        RATE_LIMIT_MAXIMUM_REQUESTS_ENVIRONMENT_VARIABLE,
        "45",
    )

    monkeypatch.setenv(
        RATE_LIMIT_WINDOW_SECONDS_ENVIRONMENT_VARIABLE,
        "120",
    )

    assert get_rate_limit_settings() == {
        "maximum_requests": 45,
        "window_seconds": 120,
    }


def test_non_integer_rate_limit_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        RATE_LIMIT_MAXIMUM_REQUESTS_ENVIRONMENT_VARIABLE,
        "many",
    )

    with pytest.raises(
        RuntimeError,
        match="must be a positive integer",
    ):
        get_rate_limit_settings()


def test_zero_rate_limit_window_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        RATE_LIMIT_WINDOW_SECONDS_ENVIRONMENT_VARIABLE,
        "0",
    )

    with pytest.raises(
        RuntimeError,
        match="must be a positive integer",
    ):
        get_rate_limit_settings()