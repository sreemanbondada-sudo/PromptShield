from audit_service import (
    GENESIS_HASH,
    create_event_hash,
    verify_event_hash,
)


SECRET_KEY = "audit-test-secret-key"

SAMPLE_EVENT = {
    "event_id": 1,
    "risk_level": "high",
    "risk_score": 90,
    "category": "prompt_injection",
    "recommended_action": "block",
}


def test_event_hash_is_deterministic():
    first_hash = create_event_hash(
        event_data=SAMPLE_EVENT,
        secret_key=SECRET_KEY,
    )

    second_hash = create_event_hash(
        event_data=SAMPLE_EVENT,
        secret_key=SECRET_KEY,
    )

    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_valid_event_hash_is_accepted():
    event_hash = create_event_hash(
        event_data=SAMPLE_EVENT,
        secret_key=SECRET_KEY,
    )

    assert verify_event_hash(
        event_data=SAMPLE_EVENT,
        stored_hash=event_hash,
        secret_key=SECRET_KEY,
    )


def test_modified_event_is_rejected():
    event_hash = create_event_hash(
        event_data=SAMPLE_EVENT,
        secret_key=SECRET_KEY,
    )

    modified_event = {
        **SAMPLE_EVENT,
        "risk_score": 10,
    }

    assert not verify_event_hash(
        event_data=modified_event,
        stored_hash=event_hash,
        secret_key=SECRET_KEY,
    )


def test_incorrect_previous_hash_is_rejected():
    event_hash = create_event_hash(
        event_data=SAMPLE_EVENT,
        previous_hash=GENESIS_HASH,
        secret_key=SECRET_KEY,
    )

    incorrect_previous_hash = "a" * 64

    assert not verify_event_hash(
        event_data=SAMPLE_EVENT,
        stored_hash=event_hash,
        previous_hash=incorrect_previous_hash,
        secret_key=SECRET_KEY,
    )


def test_dictionary_key_order_does_not_change_hash():
    reordered_event = {
        "recommended_action": "block",
        "category": "prompt_injection",
        "risk_score": 90,
        "risk_level": "high",
        "event_id": 1,
    }

    original_hash = create_event_hash(
        event_data=SAMPLE_EVENT,
        secret_key=SECRET_KEY,
    )

    reordered_hash = create_event_hash(
        event_data=reordered_event,
        secret_key=SECRET_KEY,
    )

    assert original_hash == reordered_hash