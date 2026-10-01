import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


AES_KEY_ENVIRONMENT_VARIABLE = "PROMPTSHIELD_AES_KEY"
NONCE_SIZE = 12


def get_aes_key() -> bytes:
    """Load and validate the AES-256 key from the environment."""
    encoded_key = os.getenv(AES_KEY_ENVIRONMENT_VARIABLE)

    if not encoded_key:
        raise RuntimeError(
            f"{AES_KEY_ENVIRONMENT_VARIABLE} is not configured."
        )

    try:
        key = base64.urlsafe_b64decode(encoded_key)

    except (ValueError, TypeError) as error:
        raise RuntimeError(
            f"{AES_KEY_ENVIRONMENT_VARIABLE} is not valid Base64."
        ) from error

    if len(key) != 32:
        raise RuntimeError(
            f"{AES_KEY_ENVIRONMENT_VARIABLE} must contain a "
            "Base64-encoded 32-byte key."
        )

    return key


def encrypt_text(
    plaintext: str,
    associated_data: str | None = None,
    secret_key: bytes | None = None,
) -> str:
    """Encrypt text using AES-256-GCM."""
    key = secret_key or get_aes_key()
    nonce = secrets.token_bytes(NONCE_SIZE)

    associated_bytes = (
        associated_data.encode("utf-8")
        if associated_data is not None
        else None
    )

    ciphertext = AESGCM(key).encrypt(
        nonce,
        plaintext.encode("utf-8"),
        associated_bytes,
    )

    encrypted_payload = nonce + ciphertext

    return base64.urlsafe_b64encode(
        encrypted_payload
    ).decode("utf-8")


def decrypt_text(
    encrypted_payload: str,
    associated_data: str | None = None,
    secret_key: bytes | None = None,
) -> str:
    """Decrypt and authenticate an AES-256-GCM payload."""
    key = secret_key or get_aes_key()

    try:
        payload = base64.urlsafe_b64decode(encrypted_payload)
        nonce = payload[:NONCE_SIZE]
        ciphertext = payload[NONCE_SIZE:]

        associated_bytes = (
            associated_data.encode("utf-8")
            if associated_data is not None
            else None
        )

        plaintext = AESGCM(key).decrypt(
            nonce,
            ciphertext,
            associated_bytes,
        )

    except Exception as error:
        raise ValueError(
            "The encrypted payload is invalid or has been modified."
        ) from error

    return plaintext.decode("utf-8")