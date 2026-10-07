from unittest.mock import Mock

import storage


POSTGRESQL_TEST_URL = (
    "postgresql://promptshield:"
    "test-password@localhost/promptshield_test"
)


def use_sqlite(monkeypatch):
    monkeypatch.setattr(
        storage,
        "get_database_settings",
        lambda: {
            "backend": "sqlite",
            "database_url": None,
        },
    )


def use_postgresql(monkeypatch):
    monkeypatch.setattr(
        storage,
        "get_database_settings",
        lambda: {
            "backend": "postgresql",
            "database_url": POSTGRESQL_TEST_URL,
        },
    )


def test_reports_sqlite_backend(
    monkeypatch,
):
    use_sqlite(monkeypatch)

    assert (
        storage.get_storage_backend_name()
        == "sqlite"
    )


def test_reports_postgresql_backend(
    monkeypatch,
):
    use_postgresql(monkeypatch)

    assert (
        storage.get_storage_backend_name()
        == "postgresql"
    )


def test_initializes_sqlite_by_default(
    monkeypatch,
):
    use_sqlite(monkeypatch)

    sqlite_initialize = Mock()

    monkeypatch.setattr(
        storage.sqlite_database,
        "initialize_database",
        sqlite_initialize,
    )

    storage.initialize_database()

    sqlite_initialize.assert_called_once_with()


def test_initializes_postgresql_when_configured(
    monkeypatch,
):
    use_postgresql(monkeypatch)

    postgresql_initialize = Mock()

    monkeypatch.setattr(
        storage.postgres_database,
        "initialize_database",
        postgresql_initialize,
    )

    storage.initialize_database()

    postgresql_initialize.assert_called_once_with(
        database_url=POSTGRESQL_TEST_URL,
    )


def test_saves_event_to_postgresql_when_configured(
    monkeypatch,
):
    use_postgresql(monkeypatch)

    postgresql_save = Mock(
        return_value=42
    )

    monkeypatch.setattr(
        storage.postgres_database,
        "save_security_event",
        postgresql_save,
    )

    analysis_result = {
        "is_malicious": False,
    }

    event_id = storage.save_security_event(
        analysis_result=analysis_result,
        prompt_length=25,
    )

    assert event_id == 42

    postgresql_save.assert_called_once_with(
        analysis_result=analysis_result,
        prompt_length=25,
        database_url=POSTGRESQL_TEST_URL,
    )


def test_reads_recent_events_from_sqlite(
    monkeypatch,
):
    use_sqlite(monkeypatch)

    sqlite_events = Mock(
        return_value=[
            {
                "id": 1,
            },
        ]
    )

    monkeypatch.setattr(
        storage.sqlite_database,
        "get_recent_events",
        sqlite_events,
    )

    result = storage.get_recent_events(
        limit=5
    )

    assert result == [
        {
            "id": 1,
        },
    ]

    sqlite_events.assert_called_once_with(
        limit=5
    )


def test_routes_integrity_check_to_postgresql(
    monkeypatch,
):
    use_postgresql(monkeypatch)

    postgresql_integrity = Mock(
        return_value={
            "valid": True,
            "backend": "postgresql",
        }
    )

    monkeypatch.setattr(
        storage.postgres_database,
        "check_database_integrity",
        postgresql_integrity,
    )

    result = storage.check_database_integrity()

    assert result["valid"] is True
    assert result["backend"] == "postgresql"

    postgresql_integrity.assert_called_once_with(
        database_url=POSTGRESQL_TEST_URL,
    )


def test_reads_contextual_shadow_from_sqlite(
    monkeypatch,
):
    use_sqlite(monkeypatch)

    sqlite_shadow = Mock(
        return_value={
            "event_id": 7,
            "predicted_action": "block",
        }
    )

    monkeypatch.setattr(
        storage.sqlite_database,
        "get_contextual_action_shadow",
        sqlite_shadow,
    )

    result = storage.get_contextual_action_shadow(
        event_id=7
    )

    assert result == {
        "event_id": 7,
        "predicted_action": "block",
    }

    sqlite_shadow.assert_called_once_with(
        event_id=7,
    )


def test_reads_contextual_shadow_from_postgresql(
    monkeypatch,
):
    use_postgresql(monkeypatch)

    postgresql_shadow = Mock(
        return_value={
            "event_id": 9,
            "predicted_action": "redact",
        }
    )

    monkeypatch.setattr(
        storage.postgres_database,
        "get_contextual_action_shadow",
        postgresql_shadow,
    )

    result = storage.get_contextual_action_shadow(
        event_id=9
    )

    assert result == {
        "event_id": 9,
        "predicted_action": "redact",
    }

    postgresql_shadow.assert_called_once_with(
        event_id=9,
        database_url=POSTGRESQL_TEST_URL,
    )

def test_reads_shadow_statistics_from_sqlite(
    monkeypatch,
):
    use_sqlite(monkeypatch)

    sqlite_statistics = Mock(
        return_value={
            "total_predictions": 5,
            "agreement_rate": 0.8,
        }
    )

    monkeypatch.setattr(
        storage.sqlite_database,
        "get_contextual_shadow_statistics",
        sqlite_statistics,
    )

    result = (
        storage
        .get_contextual_shadow_statistics()
    )

    assert result == {
        "total_predictions": 5,
        "agreement_rate": 0.8,
    }

    sqlite_statistics.assert_called_once_with()


def test_reads_shadow_statistics_from_postgresql(
    monkeypatch,
):
    use_postgresql(monkeypatch)

    postgresql_statistics = Mock(
        return_value={
            "total_predictions": 8,
            "agreement_rate": 0.75,
        }
    )

    monkeypatch.setattr(
        storage.postgres_database,
        "get_contextual_shadow_statistics",
        postgresql_statistics,
    )

    result = (
        storage
        .get_contextual_shadow_statistics()
    )

    assert result == {
        "total_predictions": 8,
        "agreement_rate": 0.75,
    }

    postgresql_statistics.assert_called_once_with(
        database_url=POSTGRESQL_TEST_URL,
    )