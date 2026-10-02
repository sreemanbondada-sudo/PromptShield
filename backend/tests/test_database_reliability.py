import sqlite3

import pytest

from fastapi.testclient import TestClient

import main

from database import (
    DATABASE_BUSY_TIMEOUT_MILLISECONDS,
    check_database_integrity,
    get_connection,
    initialize_database,
)


def test_database_connection_uses_safe_settings(
    tmp_path,
):
    database_path = (
        tmp_path / "reliability-test.db"
    )

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        foreign_keys = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

        busy_timeout = connection.execute(
            "PRAGMA busy_timeout"
        ).fetchone()[0]

        journal_mode = connection.execute(
            "PRAGMA journal_mode"
        ).fetchone()[0]

        synchronous = connection.execute(
            "PRAGMA synchronous"
        ).fetchone()[0]

    assert foreign_keys == 1

    assert (
        busy_timeout
        == DATABASE_BUSY_TIMEOUT_MILLISECONDS
    )

    assert journal_mode.lower() == "wal"

    assert synchronous == 1


def test_valid_database_passes_integrity_check(
    tmp_path,
):
    database_path = (
        tmp_path / "integrity-test.db"
    )

    initialize_database(database_path)

    result = check_database_integrity(
        database_path
    )

    assert result == {
        "valid": True,
        "quick_check": ["ok"],
        "foreign_key_violations": 0,
    }


def test_foreign_key_violation_is_detected(
    tmp_path,
):
    database_path = (
        tmp_path / "foreign-key-test.db"
    )

    initialize_database(database_path)

    raw_connection = sqlite3.connect(
        database_path
    )

    try:
        raw_connection.execute(
            "PRAGMA foreign_keys = OFF"
        )

        raw_connection.execute(
            """
            INSERT INTO encrypted_event_previews (
                event_id,
                event_reference,
                encrypted_preview
            )
            VALUES (?, ?, ?)
            """,
            (
                999,
                "invalid-event-reference",
                "invalid-encrypted-preview",
            ),
        )

        raw_connection.commit()

    finally:
        raw_connection.close()

    result = check_database_integrity(
        database_path
    )

    assert result["valid"] is False
    assert result["quick_check"] == ["ok"]
    assert result["foreign_key_violations"] == 1

def test_application_rejects_invalid_database(
    monkeypatch,
):
    monkeypatch.setattr(
        main,
        "validate_configuration",
        lambda: {},
    )

    monkeypatch.setattr(
        main,
        "initialize_database",
        lambda: None,
    )

    monkeypatch.setattr(
        main,
        "check_database_integrity",
        lambda: {
            "valid": False,
            "quick_check": ["damaged"],
            "foreign_key_violations": 0,
        },
    )

    with pytest.raises(
        RuntimeError,
        match="database integrity",
    ):
        with TestClient(main.app):
            pass