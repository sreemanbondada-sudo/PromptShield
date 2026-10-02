import base64

import pytest

from config import (
    MINIMUM_HMAC_KEY_LENGTH,
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