import base64

import pytest

import database
import main
from encryption_service import (
    AES_KEY_ENVIRONMENT_VARIABLE,
)
from integrity_service import (
    HMAC_KEY_ENVIRONMENT_VARIABLE,
)


@pytest.fixture(autouse=True)
def configure_test_environment(
    monkeypatch,
    tmp_path,
):
    """Use test secrets and an isolated temporary database."""
    monkeypatch.setenv(
        HMAC_KEY_ENVIRONMENT_VARIABLE,
        "promptshield-test-only-hmac-key",
    )

    test_aes_key = base64.urlsafe_b64encode(
        bytes(range(32))
    ).decode("utf-8")

    monkeypatch.setenv(
        AES_KEY_ENVIRONMENT_VARIABLE,
        test_aes_key,
    )

    test_database_path = tmp_path / "promptshield-test.db"

    def save_test_event(
        analysis_result: dict,
        prompt_length: int,
    ) -> int:
        return database.save_security_event(
            analysis_result=analysis_result,
            prompt_length=prompt_length,
            database_path=test_database_path,
        )

    def get_test_events(limit: int = 20):
        return database.get_recent_events(
            limit=limit,
            database_path=test_database_path,
        )

    def get_test_statistics():
        return database.get_statistics(
            database_path=test_database_path,
        )

    def verify_test_audit_chain():
        return database.verify_audit_chain(
            database_path=test_database_path,
        )

    monkeypatch.setattr(
        main,
        "save_security_event",
        save_test_event,
    )

    monkeypatch.setattr(
        main,
        "get_recent_events",
        get_test_events,
    )

    monkeypatch.setattr(
        main,
        "get_statistics",
        get_test_statistics,
    )

    monkeypatch.setattr(
        main,
        "verify_audit_chain",
        verify_test_audit_chain,
    )
    