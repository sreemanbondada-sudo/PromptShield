import hashlib
import hmac
import json

from integrity_service import get_hmac_key


GENESIS_HASH = "0" * 64


def create_event_hash(
    event_data: dict,
    previous_hash: str = GENESIS_HASH,
    secret_key: str | None = None,
) -> str:
    """Create an HMAC-SHA-256 hash for one audit event."""
    key = secret_key or get_hmac_key()

    canonical_event = json.dumps(
        event_data,
        sort_keys=True,
        separators=(",", ":"),
    )

    chain_message = f"{previous_hash}:{canonical_event}"

    return hmac.new(
        key.encode("utf-8"),
        chain_message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_event_hash(
    event_data: dict,
    stored_hash: str,
    previous_hash: str = GENESIS_HASH,
    secret_key: str | None = None,
) -> bool:
    """Verify that an audit event has not been modified."""
    if not stored_hash:
        return False

    expected_hash = create_event_hash(
        event_data=event_data,
        previous_hash=previous_hash,
        secret_key=secret_key,
    )

    return hmac.compare_digest(
        expected_hash,
        stored_hash,
    )