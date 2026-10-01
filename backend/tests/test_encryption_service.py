import base64
import secrets

import pytest

from encryption_service import (
    AES_KEY_ENVIRONMENT_VARIABLE,
    decrypt_text,
    encrypt_text,
    get_aes_key,
)


def test_encrypted_text_can_be_decrypted():
    secret_key = secrets.token_bytes(32)
    original_text = "PromptShield confidential information"

    encrypted_text = encrypt_text(
        original_text,
        secret_key=secret_key,
    )

    decrypted_text = decrypt_text(
        encrypted_text,
        secret_key=secret_key,
    )

    assert decrypted_text == original_text
    assert encrypted_text != original_text


def test_same_text_produces_different_ciphertexts():
    secret_key = secrets.token_bytes(32)
    plaintext = "Confidential prompt"

    first_ciphertext = encrypt_text(
        plaintext,
        secret_key=secret_key,
    )

    second_ciphertext = encrypt_text(
        plaintext,
        secret_key=secret_key,
    )

    assert first_ciphertext != second_ciphertext


def test_modified_ciphertext_is_rejected():
    secret_key = secrets.token_bytes(32)

    encrypted_text = encrypt_text(
        "Original protected message",
        secret_key=secret_key,
    )

    modified_text = encrypted_text[:-2] + "AA"

    with pytest.raises(
        ValueError,
        match="invalid or has been modified",
    ):
        decrypt_text(
            modified_text,
            secret_key=secret_key,
        )


def test_incorrect_key_is_rejected():
    correct_key = secrets.token_bytes(32)
    incorrect_key = secrets.token_bytes(32)

    encrypted_text = encrypt_text(
        "Protected message",
        secret_key=correct_key,
    )

    with pytest.raises(ValueError):
        decrypt_text(
            encrypted_text,
            secret_key=incorrect_key,
        )


def test_associated_data_must_match():
    secret_key = secrets.token_bytes(32)

    encrypted_text = encrypt_text(
        "Protected security event",
        associated_data="event-123",
        secret_key=secret_key,
    )

    with pytest.raises(ValueError):
        decrypt_text(
            encrypted_text,
            associated_data="event-456",
            secret_key=secret_key,
        )


def test_key_can_be_loaded_from_environment(monkeypatch):
    secret_key = secrets.token_bytes(32)

    encoded_key = base64.urlsafe_b64encode(
        secret_key
    ).decode("utf-8")

    monkeypatch.setenv(
        AES_KEY_ENVIRONMENT_VARIABLE,
        encoded_key,
    )

    assert get_aes_key() == secret_key


def test_missing_environment_key_raises_error(monkeypatch):
    monkeypatch.delenv(
        AES_KEY_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="is not configured",
    ):
        get_aes_key()