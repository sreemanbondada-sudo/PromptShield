from audit_service import GENESIS_HASH, verify_event_hash
from database import (
    get_connection,
    save_security_event,
    verify_audit_chain,
)


SAMPLE_ANALYSIS = {
    "is_malicious": True,
    "risk_level": "high",
    "risk_score": 90,
    "category": "prompt_injection",
    "recommended_action": "block",
    "contains_sensitive_data": False,
    "matched_patterns": ["ignore previous instructions"],
    "sensitive_findings": [],
}


def build_event_data(row) -> dict:
    """Reconstruct the exact data protected by the event hash."""
    return {
        "is_malicious": row["is_malicious"],
        "risk_level": row["risk_level"],
        "risk_score": row["risk_score"],
        "category": row["category"],
        "recommended_action": row["recommended_action"],
        "contains_sensitive_data": (
            row["contains_sensitive_data"]
        ),
        "matched_patterns": row["matched_patterns"],
        "sensitive_data_types": row["sensitive_data_types"],
        "prompt_length": row["prompt_length"],
    }


def test_first_event_uses_genesis_hash(tmp_path):
    database_path = tmp_path / "audit-test.db"

    save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=28,
        database_path=database_path,
    )

    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM security_events
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()

    assert row["previous_hash"] == GENESIS_HASH
    assert len(row["event_hash"]) == 64


def test_consecutive_events_are_linked(tmp_path):
    database_path = tmp_path / "audit-test.db"

    save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=28,
        database_path=database_path,
    )

    save_security_event(
        analysis_result={
            **SAMPLE_ANALYSIS,
            "risk_score": 100,
        },
        prompt_length=35,
        database_path=database_path,
    )

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM security_events
            ORDER BY id ASC
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[1]["previous_hash"] == rows[0]["event_hash"]


def test_modified_database_event_fails_verification(tmp_path):
    database_path = tmp_path / "audit-test.db"

    event_id = save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=28,
        database_path=database_path,
    )

    with get_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE security_events
            SET risk_score = ?
            WHERE id = ?
            """,
            (5, event_id),
        )

        modified_row = connection.execute(
            """
            SELECT *
            FROM security_events
            WHERE id = ?
            """,
            (event_id,),
        ).fetchone()

    assert not verify_event_hash(
        event_data=build_event_data(modified_row),
        stored_hash=modified_row["event_hash"],
        previous_hash=modified_row["previous_hash"],
    )


def test_complete_audit_chain_is_valid(tmp_path):
    database_path = tmp_path / "audit-test.db"

    save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=28,
        database_path=database_path,
    )

    save_security_event(
        analysis_result={
            **SAMPLE_ANALYSIS,
            "risk_score": 100,
        },
        prompt_length=35,
        database_path=database_path,
    )

    result = verify_audit_chain(
        database_path=database_path,
    )

    assert result["valid"] is True
    assert result["checked_events"] == 2
    assert result["broken_event_id"] is None


def test_complete_audit_chain_reports_broken_event(tmp_path):
    database_path = tmp_path / "audit-test.db"

    first_event_id = save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=28,
        database_path=database_path,
    )

    save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=35,
        database_path=database_path,
    )

    with get_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE security_events
            SET category = ?
            WHERE id = ?
            """,
            ("safe", first_event_id),
        )

    result = verify_audit_chain(
        database_path=database_path,
    )

    assert result["valid"] is False
    assert result["broken_event_id"] == first_event_id
    