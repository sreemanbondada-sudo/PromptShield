import json
import sqlite3
from pathlib import Path


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
    """Create the security-events table if it does not exist."""
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
                prompt_length INTEGER NOT NULL
            )
            """
        )


def save_security_event(
    analysis_result: dict,
    prompt_length: int,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> int:
    """Save a security event and return its database ID."""
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

    with get_connection(database_path) as connection:
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
                prompt_length
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(analysis_result["is_malicious"]),
                analysis_result["risk_level"],
                analysis_result["risk_score"],
                analysis_result["category"],
                analysis_result["recommended_action"],
                int(
                    analysis_result[
                        "contains_sensitive_data"
                    ]
                ),
                json.dumps(matched_patterns),
                json.dumps(sensitive_data_types),
                prompt_length,
            ),
        )

        event_id = cursor.lastrowid

    if event_id is None:
        raise RuntimeError("The security event could not be saved.")

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
                SUM(contains_sensitive_data) AS sensitive_prompts
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
        "malicious_prompts": totals["malicious_prompts"] or 0,
        "sensitive_prompts": totals["sensitive_prompts"] or 0,
        "actions": {
            row["recommended_action"]: row["count"]
            for row in action_rows
        },
        "categories": {
            row["category"]: row["count"]
            for row in category_rows
        },
    }
