import base64

import pytest

from database import (
    get_connection,
    get_decrypted_event_preview,
    save_security_event,
)


SAMPLE_ANALYSIS = {
    "is_malicious": False,
    "risk_level": "medium",
    "risk_score": 60,
    "category": "sensitive_data_exposure",
    "recommended_action": "redact",
    "contains_sensitive_data": True,
    "matched_patterns": [],
    "sensitive_findings": [
        {
            "type": "email_address",
            "redacted_value": "[REDACTED]",
            "start": 20,
            "end": 39,
            "detection_method": "pattern",
        }
    ],
    "redacted_prompt": (
        "Send the report to [REDACTED]"
    ),
}


def test_redacted_preview_is_encrypted_in_database(
    tmp_path,
):
    database_path = tmp_path / "encrypted-test.db"

    event_id = save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=39,
        database_path=database_path,
    )

    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT encrypted_preview
            FROM encrypted_event_previews
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()

    assert row is not None

    assert (
        SAMPLE_ANALYSIS["redacted_prompt"]
        not in row["encrypted_preview"]
    )


def test_encrypted_preview_can_be_decrypted(
    tmp_path,
):
    database_path = tmp_path / "encrypted-test.db"

    event_id = save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=39,
        database_path=database_path,
    )

    result = get_decrypted_event_preview(
        event_id=event_id,
        database_path=database_path,
    )

    assert result is not None
    assert result["event_id"] == event_id

    assert (
        result["redacted_prompt"]
        == SAMPLE_ANALYSIS["redacted_prompt"]
    )


def test_identical_previews_have_different_ciphertexts(
    tmp_path,
):
    database_path = tmp_path / "encrypted-test.db"

    first_event_id = save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=39,
        database_path=database_path,
    )

    second_event_id = save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=39,
        database_path=database_path,
    )

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT event_id, encrypted_preview
            FROM encrypted_event_previews
            ORDER BY event_id ASC
            """
        ).fetchall()

    assert len(rows) == 2

    assert (
        rows[0]["event_id"]
        == first_event_id
    )

    assert (
        rows[1]["event_id"]
        == second_event_id
    )

    assert (
        rows[0]["encrypted_preview"]
        != rows[1]["encrypted_preview"]
    )


def test_modified_encrypted_preview_is_rejected(
    tmp_path,
):
    database_path = tmp_path / "encrypted-test.db"

    event_id = save_security_event(
        analysis_result=SAMPLE_ANALYSIS,
        prompt_length=39,
        database_path=database_path,
    )

    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT encrypted_preview
            FROM encrypted_event_previews
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()

        encrypted_bytes = bytearray(
            base64.urlsafe_b64decode(
                row["encrypted_preview"]
            )
        )

        encrypted_bytes[-1] ^= 1

        modified_preview = (
            base64.urlsafe_b64encode(
                encrypted_bytes
            ).decode("utf-8")
        )

        connection.execute(
            """
            UPDATE encrypted_event_previews
            SET encrypted_preview = ?
            WHERE event_id = ?
            """,
            (
                modified_preview,
                event_id,
            ),
        )

    with pytest.raises(
        ValueError,
        match="invalid or has been modified",
    ):
        get_decrypted_event_preview(
            event_id=event_id,
            database_path=database_path,
        )

def test_ciphertext_cannot_be_swapped_between_events(
    tmp_path,
):
    database_path = tmp_path / "encrypted-test.db"

    first_event_id = save_security_event(
        analysis_result={
            **SAMPLE_ANALYSIS,
            "redacted_prompt": "First protected preview",
        },
        prompt_length=23,
        database_path=database_path,
    )

    second_event_id = save_security_event(
        analysis_result={
            **SAMPLE_ANALYSIS,
            "redacted_prompt": "Second protected preview",
        },
        prompt_length=24,
        database_path=database_path,
    )

    with get_connection(database_path) as connection:
        second_row = connection.execute(
            """
            SELECT encrypted_preview
            FROM encrypted_event_previews
            WHERE event_id = ?
            """,
            (second_event_id,),
        ).fetchone()

        connection.execute(
            """
            UPDATE encrypted_event_previews
            SET encrypted_preview = ?
            WHERE event_id = ?
            """,
            (
                second_row["encrypted_preview"],
                first_event_id,
            ),
        )

    with pytest.raises(
        ValueError,
        match="invalid or has been modified",
    ):
        get_decrypted_event_preview(
            event_id=first_event_id,
            database_path=database_path,
        )