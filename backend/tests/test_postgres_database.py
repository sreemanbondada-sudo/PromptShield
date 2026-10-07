from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import postgres_database


POSTGRESQL_TEST_URL = (
    "postgresql://promptshield:"
    "test-password@localhost/promptshield_test"
)


class FakeCursor:
    def __init__(
        self,
        row=None,
        rows=None,
    ):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, execute_handler):
        self.execute_handler = execute_handler
        self.executed_queries = []

    def __enter__(self):
        return self

    def __exit__(
        self,
        exception_type,
        exception,
        traceback,
    ):
        return False

    def execute(
        self,
        query,
        parameters=None,
    ):
        normalized_query = " ".join(
            query.split()
        )

        self.executed_queries.append(
            (
                normalized_query,
                parameters,
            )
        )

        return self.execute_handler(
            normalized_query,
            parameters,
        )


def test_legacy_postgres_url_is_normalized():
    result = postgres_database.get_database_url(
        "postgres://user:password@host/database"
    )

    assert result == (
        "postgresql://user:password@host/database"
    )


def test_postgresql_url_is_preserved():
    result = postgres_database.get_database_url(
        POSTGRESQL_TEST_URL
    )

    assert result == POSTGRESQL_TEST_URL


def test_timestamp_is_formatted_as_utc():
    india_timezone = timezone(
        timedelta(hours=5, minutes=30)
    )

    timestamp = datetime(
        2026,
        10,
        4,
        17,
        30,
        45,
        tzinfo=india_timezone,
    )

    assert (
        postgres_database.format_created_at(
            timestamp
        )
        == "2026-10-04 12:00:45"
    )


def test_saves_event_with_audit_lock_and_preview(
    monkeypatch,
):
    inserted_event_id = 7

    def execute_handler(
        query,
        parameters,
    ):
        if "pg_advisory_xact_lock" in query:
            return FakeCursor()

        if (
            "SELECT event_hash"
            in query
        ):
            return FakeCursor(
                row=None
            )

        if (
            "INSERT INTO security_events"
            in query
        ):
            return FakeCursor(
                row={
                    "id": inserted_event_id,
                }
            )

        if (
            "INSERT INTO encrypted_event_previews"
            in query
        ):
            return FakeCursor()

        raise AssertionError(
            f"Unexpected query: {query}"
        )

    fake_connection = FakeConnection(
        execute_handler
    )

    monkeypatch.setattr(
        postgres_database,
        "initialize_database",
        Mock(),
    )

    monkeypatch.setattr(
        postgres_database,
        "get_connection",
        lambda database_url=None: fake_connection,
    )

    encrypted_payload = (
        "encrypted-test-preview"
    )

    encrypt_mock = Mock(
        return_value=encrypted_payload
    )

    monkeypatch.setattr(
        postgres_database,
        "encrypt_text",
        encrypt_mock,
    )

    analysis_result = {
        "is_malicious": True,
        "risk_level": "high",
        "risk_score": 100,
        "category": "prompt_injection",
        "recommended_action": "block",
        "contains_sensitive_data": True,
        "matched_patterns": [
            "previous-instruction override",
        ],
        "sensitive_findings": [
            {
                "type": "email_address",
            },
        ],
        "redacted_prompt": (
            "Ignore instructions and contact "
            "[REDACTED]."
        ),
    }

    event_id = (
        postgres_database.save_security_event(
            analysis_result=analysis_result,
            prompt_length=48,
            database_url=POSTGRESQL_TEST_URL,
        )
    )

    assert event_id == inserted_event_id

    queries = [
        query
        for query, _ in (
            fake_connection.executed_queries
        )
    ]

    assert any(
        "pg_advisory_xact_lock" in query
        for query in queries
    )

    assert any(
        "INSERT INTO security_events" in query
        and "RETURNING id" in query
        for query in queries
    )

    preview_insert = next(
        parameters
        for query, parameters in (
            fake_connection.executed_queries
        )
        if (
            "INSERT INTO encrypted_event_previews"
            in query
        )
    )

    assert preview_insert[0] == inserted_event_id
    assert preview_insert[2] == encrypted_payload

    encrypt_mock.assert_called_once()

    associated_data = (
        encrypt_mock.call_args.kwargs[
            "associated_data"
        ]
    )

    assert associated_data.startswith(
        "promptshield:event-preview:7:"
    )


def test_recent_events_are_deserialized(
    monkeypatch,
):
    event_row = {
        "id": 3,
        "created_at": datetime(
            2026,
            10,
            4,
            12,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        "is_malicious": 1,
        "risk_level": "high",
        "risk_score": 100,
        "category": "prompt_injection",
        "recommended_action": "block",
        "contains_sensitive_data": 0,
        "matched_patterns": (
            '["system-prompt extraction"]'
        ),
        "sensitive_data_types": "[]",
        "prompt_length": 42,
        "previous_hash": "previous-hash",
        "event_hash": "event-hash",
    }

    def execute_handler(
        query,
        parameters,
    ):
        assert "SELECT *" in query
        assert parameters == (5,)

        return FakeCursor(
            rows=[event_row]
        )

    fake_connection = FakeConnection(
        execute_handler
    )

    monkeypatch.setattr(
        postgres_database,
        "initialize_database",
        Mock(),
    )

    monkeypatch.setattr(
        postgres_database,
        "get_connection",
        lambda database_url=None: fake_connection,
    )

    events = postgres_database.get_recent_events(
        limit=5,
        database_url=POSTGRESQL_TEST_URL,
    )

    assert len(events) == 1
    assert events[0]["id"] == 3
    assert events[0]["is_malicious"] is True

    assert (
        events[0]["contains_sensitive_data"]
        is False
    )

    assert events[0]["created_at"] == (
        "2026-10-04 12:00:00"
    )

    assert events[0]["matched_patterns"] == [
        "system-prompt extraction",
    ]

    assert (
        events[0]["sensitive_data_types"]
        == []
    )


def test_postgresql_integrity_check_passes(
    monkeypatch,
):
    def execute_handler(
        query,
        parameters,
    ):
        assert "to_regclass" in query

        return FakeCursor(
            row={
                "security_events_exists": True,
                "encrypted_previews_exists": True,
            }
        )

    fake_connection = FakeConnection(
        execute_handler
    )

    monkeypatch.setattr(
        postgres_database,
        "initialize_database",
        Mock(),
    )

    monkeypatch.setattr(
        postgres_database,
        "get_connection",
        lambda database_url=None: fake_connection,
    )

    result = (
        postgres_database
        .check_database_integrity(
            database_url=POSTGRESQL_TEST_URL,
        )
    )

    assert result == {
        "valid": True,
        "quick_check": ["ok"],
        "foreign_key_violations": 0,
        "backend": "postgresql",
    }

def test_saves_privacy_safe_contextual_shadow(
    monkeypatch,
):
    inserted_event_id = 17
    secret_marker = "DO-NOT-STORE-ORIGINAL-PROMPT"

    def execute_handler(
        query,
        parameters,
    ):
        if "pg_advisory_xact_lock" in query:
            return FakeCursor()

        if "SELECT event_hash" in query:
            return FakeCursor(
                row=None
            )

        if "INSERT INTO security_events" in query:
            return FakeCursor(
                row={
                    "id": inserted_event_id,
                }
            )

        if (
            "INSERT INTO encrypted_event_previews"
            in query
        ):
            return FakeCursor()

        if (
            "INSERT INTO contextual_action_shadows"
            in query
        ):
            return FakeCursor()

        raise AssertionError(
            f"Unexpected query: {query}"
        )

    fake_connection = FakeConnection(
        execute_handler
    )

    monkeypatch.setattr(
        postgres_database,
        "initialize_database",
        Mock(),
    )

    monkeypatch.setattr(
        postgres_database,
        "get_connection",
        lambda database_url=None: fake_connection,
    )

    monkeypatch.setattr(
        postgres_database,
        "encrypt_text",
        Mock(
            return_value="encrypted-preview"
        ),
    )

    analysis_result = {
        "is_malicious": False,
        "risk_level": "low",
        "risk_score": 0,
        "category": "safe",
        "recommended_action": "allow",
        "contains_sensitive_data": False,
        "matched_patterns": [],
        "sensitive_findings": [],
        "redacted_prompt": "[REDACTED]",
        "contextual_shadow": {
            "available": True,
            "predicted_action": "block",
            "probabilities": {
                "allow": 0.05,
                "review": 0.10,
                "redact": 0.05,
                "block": 0.80,
            },
            "confidence": 0.80,
            "probability_margin": 0.70,
            "is_confident": True,
            "requires_review": False,
            "agrees_with_production": False,
            "model_name": "test_contextual_model",
            "mode": "shadow",
        },
    }

    event_id = (
        postgres_database.save_security_event(
            analysis_result=analysis_result,
            prompt_length=len(secret_marker),
            database_url=POSTGRESQL_TEST_URL,
        )
    )

    assert event_id == inserted_event_id

    shadow_inserts = [
        (
            query,
            parameters,
        )
        for query, parameters
        in fake_connection.executed_queries
        if (
            "INSERT INTO contextual_action_shadows"
            in query
        )
    ]

    assert len(shadow_inserts) == 1

    _query, parameters = shadow_inserts[0]

    assert parameters[0] == inserted_event_id
    assert parameters[1] == "allow"
    assert parameters[2] == "block"
    assert parameters[4] == 0.80
    assert parameters[5] == 0.70
    assert parameters[6] == 1
    assert parameters[7] == 0
    assert parameters[8] == 0
    assert parameters[9] == "test_contextual_model"
    assert parameters[10] == "shadow"

    all_parameters = repr(
        [
            parameters
            for _query, parameters
            in fake_connection.executed_queries
        ]
    )

    assert secret_marker not in all_parameters