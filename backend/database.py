import json
import sqlite3
from pathlib import Path
from audit_service import (
    GENESIS_HASH,
    create_event_hash,
    verify_event_hash,
)


DEFAULT_DATABASE_PATH = Path(__file__).parent / "promptshield.db"


def get_connection(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> sqlite3.Connection:
    """Create a connection to the PromptShield database."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> None:
    """Create or safely upgrade the security-events table."""
    with get_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_malicious INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                category TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                contains_sensitive_data INTEGER NOT NULL,
                matched_patterns TEXT NOT NULL,
                sensitive_data_types TEXT NOT NULL,
                prompt_length INTEGER NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL
            )
            """
        )

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(security_events)"
            ).fetchall()
        }

        if "previous_hash" not in existing_columns:
            connection.execute(
                f"""
                ALTER TABLE security_events
                ADD COLUMN previous_hash TEXT
                NOT NULL DEFAULT '{GENESIS_HASH}'
                """
            )

        if "event_hash" not in existing_columns:
            connection.execute(
                """
                ALTER TABLE security_events
                ADD COLUMN event_hash TEXT
                NOT NULL DEFAULT ''
                """
            )


def save_security_event(
    analysis_result: dict,
    prompt_length: int,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> int:
    """Save a privacy-safe, tamper-evident security event."""
    initialize_database(database_path)

    matched_patterns = analysis_result.get(
        "matched_patterns",
        [],
    )

    sensitive_data_types = [
        finding["type"]
        for finding in analysis_result.get(
            "sensitive_findings",
            [],
        )
    ]

    serialized_patterns = json.dumps(matched_patterns)
    serialized_sensitive_types = json.dumps(
        sensitive_data_types
    )

    event_data = {
        "is_malicious": int(
            analysis_result["is_malicious"]
        ),
        "risk_level": analysis_result["risk_level"],
        "risk_score": analysis_result["risk_score"],
        "category": analysis_result["category"],
        "recommended_action": (
            analysis_result["recommended_action"]
        ),
        "contains_sensitive_data": int(
            analysis_result["contains_sensitive_data"]
        ),
        "matched_patterns": serialized_patterns,
        "sensitive_data_types": (
            serialized_sensitive_types
        ),
        "prompt_length": prompt_length,
    }

    with get_connection(database_path) as connection:
        previous_row = connection.execute(
            """
            SELECT event_hash
            FROM security_events
            WHERE event_hash != ''
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        previous_hash = (
            previous_row["event_hash"]
            if previous_row is not None
            else GENESIS_HASH
        )

        event_hash = create_event_hash(
            event_data=event_data,
            previous_hash=previous_hash,
        )

        cursor = connection.execute(
            """
            INSERT INTO security_events (
                is_malicious,
                risk_level,
                risk_score,
                category,
                recommended_action,
                contains_sensitive_data,
                matched_patterns,
                sensitive_data_types,
                prompt_length,
                previous_hash,
                event_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_data["is_malicious"],
                event_data["risk_level"],
                event_data["risk_score"],
                event_data["category"],
                event_data["recommended_action"],
                event_data["contains_sensitive_data"],
                event_data["matched_patterns"],
                event_data["sensitive_data_types"],
                event_data["prompt_length"],
                previous_hash,
                event_hash,
            ),
        )

        event_id = cursor.lastrowid

        if event_id is None:
            raise RuntimeError(
                "The security event could not be saved."
            )

        return event_id


def get_recent_events(
    limit: int = 20,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> list[dict]:
    """Return the most recent security events."""
    initialize_database(database_path)

    safe_limit = max(1, min(limit, 100))

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM security_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    events = []

    for row in rows:
        event = dict(row)

        event["is_malicious"] = bool(
            event["is_malicious"]
        )

        event["contains_sensitive_data"] = bool(
            event["contains_sensitive_data"]
        )

        event["matched_patterns"] = json.loads(
            event["matched_patterns"]
        )

        event["sensitive_data_types"] = json.loads(
            event["sensitive_data_types"]
        )

        events.append(event)

    return events


def get_statistics(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> dict:
    """Calculate basic PromptShield security statistics."""
    initialize_database(database_path)

    with get_connection(database_path) as connection:
        totals = connection.execute(
            """
            SELECT
                COUNT(*) AS total_scans,
                SUM(is_malicious) AS malicious_prompts,
                SUM(contains_sensitive_data)
                    AS sensitive_prompts
            FROM security_events
            """
        ).fetchone()

        action_rows = connection.execute(
            """
            SELECT recommended_action, COUNT(*) AS count
            FROM security_events
            GROUP BY recommended_action
            """
        ).fetchall()

        category_rows = connection.execute(
            """
            SELECT category, COUNT(*) AS count
            FROM security_events
            GROUP BY category
            ORDER BY count DESC
            """
        ).fetchall()

    return {
        "total_scans": totals["total_scans"] or 0,
        "malicious_prompts": (
            totals["malicious_prompts"] or 0
        ),
        "sensitive_prompts": (
            totals["sensitive_prompts"] or 0
        ),
        "actions": {
            row["recommended_action"]: row["count"]
            for row in action_rows
        },
        "categories": {
            row["category"]: row["count"]
            for row in category_rows
        },
    }
def verify_audit_chain(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> dict:
    """Verify all cryptographically chained security events."""
    initialize_database(database_path)

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM security_events
            WHERE event_hash != ''
            ORDER BY id ASC
            """
        ).fetchall()

        legacy_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM security_events
            WHERE event_hash = ''
            """
        ).fetchone()["count"]

    expected_previous_hash = GENESIS_HASH

    for row in rows:
        event_data = {
            "is_malicious": row["is_malicious"],
            "risk_level": row["risk_level"],
            "risk_score": row["risk_score"],
            "category": row["category"],
            "recommended_action": (
                row["recommended_action"]
            ),
            "contains_sensitive_data": (
                row["contains_sensitive_data"]
            ),
            "matched_patterns": row["matched_patterns"],
            "sensitive_data_types": (
                row["sensitive_data_types"]
            ),
            "prompt_length": row["prompt_length"],
        }

        chain_link_is_valid = (
            row["previous_hash"]
            == expected_previous_hash
        )

        event_is_valid = verify_event_hash(
            event_data=event_data,
            stored_hash=row["event_hash"],
            previous_hash=row["previous_hash"],
        )

        if not chain_link_is_valid or not event_is_valid:
            return {
                "valid": False,
                "checked_events": 0,
                "legacy_events": legacy_count,
                "broken_event_id": row["id"],
            }

        expected_previous_hash = row["event_hash"]

    return {
        "valid": True,
        "checked_events": len(rows),
        "legacy_events": legacy_count,
        "broken_event_id": None,
    }