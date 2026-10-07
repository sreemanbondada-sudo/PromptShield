import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from audit_service import (
    GENESIS_HASH,
    create_event_hash,
    verify_event_hash,
)
from encryption_service import (
    decrypt_text,
    encrypt_text,
)


DEFAULT_DATABASE_PATH = (
    Path(__file__).parent / "promptshield.db"
)

DATABASE_TIMEOUT_SECONDS = 5.0
DATABASE_BUSY_TIMEOUT_MILLISECONDS = 5000


def get_connection(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> sqlite3.Connection:
    """Create and safely configure a database connection."""
    connection = sqlite3.connect(
        database_path,
        timeout=DATABASE_TIMEOUT_SECONDS,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "PRAGMA busy_timeout = "
        f"{DATABASE_BUSY_TIMEOUT_MILLISECONDS}"
    )

    connection.execute(
        "PRAGMA journal_mode = WAL"
    )

    connection.execute(
        "PRAGMA synchronous = NORMAL"
    )

    return connection


def initialize_database(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> None:
    """Create or safely upgrade the PromptShield database."""
    with get_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
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

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS
                encrypted_event_previews (
                    event_id INTEGER PRIMARY KEY,
                    event_reference TEXT NOT NULL UNIQUE,
                    encrypted_preview TEXT NOT NULL,
                    FOREIGN KEY (event_id)
                        REFERENCES security_events(id)
                        ON DELETE CASCADE
                )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS
                contextual_action_shadows (
                    event_id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    production_action TEXT NOT NULL,
                    predicted_action TEXT,
                    probabilities TEXT NOT NULL
                        DEFAULT '{}',
                    confidence REAL,
                    probability_margin REAL,
                    is_confident INTEGER,
                    requires_review INTEGER,
                    agrees_with_production INTEGER,
                    model_name TEXT,
                    mode TEXT NOT NULL
                        DEFAULT 'shadow',
                    FOREIGN KEY (event_id)
                        REFERENCES security_events(id)
                        ON DELETE CASCADE
                )
            """
        )

def build_preview_associated_data(
    event_id: int,
    event_reference: str,
) -> str:
    """Build authenticated context for an encrypted preview."""
    return (
        f"promptshield:event-preview:"
        f"{event_id}:{event_reference}"
    )

def save_security_event(
    analysis_result: dict,
    prompt_length: int,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> int:
    """
    Save a tamper-evident event, encrypted preview and shadow data.
    """
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

    serialized_patterns = json.dumps(
        matched_patterns
    )

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
            analysis_result[
                "contains_sensitive_data"
            ]
        ),
        "matched_patterns": serialized_patterns,
        "sensitive_data_types": (
            serialized_sensitive_types
        ),
        "prompt_length": prompt_length,
    }

    with get_connection(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")

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
                event_data[
                    "contains_sensitive_data"
                ],
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

        event_reference = uuid4().hex

        associated_data = (
            build_preview_associated_data(
                event_id=event_id,
                event_reference=event_reference,
            )
        )

        redacted_preview = analysis_result.get(
            "redacted_prompt",
            "",
        )

        encrypted_preview = encrypt_text(
            plaintext=redacted_preview,
            associated_data=associated_data,
        )

        connection.execute(
            """
            INSERT INTO encrypted_event_previews (
                event_id,
                event_reference,
                encrypted_preview
            )
            VALUES (?, ?, ?)
            """,
            (
                event_id,
                event_reference,
                encrypted_preview,
            ),
        )

        contextual_shadow = analysis_result.get(
            "contextual_shadow"
        )

        if contextual_shadow is not None:
            serialized_probabilities = json.dumps(
                contextual_shadow.get(
                    "probabilities",
                    {},
                )
            )

            def nullable_boolean(value):
                if value is None:
                    return None

                return int(bool(value))

            connection.execute(
                """
                INSERT INTO contextual_action_shadows (
                    event_id,
                    production_action,
                    predicted_action,
                    probabilities,
                    confidence,
                    probability_margin,
                    is_confident,
                    requires_review,
                    agrees_with_production,
                    model_name,
                    mode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    analysis_result[
                        "recommended_action"
                    ],
                    contextual_shadow.get(
                        "predicted_action"
                    ),
                    serialized_probabilities,
                    contextual_shadow.get(
                        "confidence"
                    ),
                    contextual_shadow.get(
                        "probability_margin"
                    ),
                    nullable_boolean(
                        contextual_shadow.get(
                            "is_confident"
                        )
                    ),
                    nullable_boolean(
                        contextual_shadow.get(
                            "requires_review"
                        )
                    ),
                    nullable_boolean(
                        contextual_shadow.get(
                            "agrees_with_production"
                        )
                    ),
                    contextual_shadow.get(
                        "model_name"
                    ),
                    contextual_shadow.get(
                        "mode",
                        "shadow",
                    ),
                ),
            )

        return event_id

def get_contextual_action_shadow(
    event_id: int,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> dict | None:
    """Return privacy-safe contextual shadow metadata."""
    initialize_database(database_path)

    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT
                event_id,
                created_at,
                production_action,
                predicted_action,
                probabilities,
                confidence,
                probability_margin,
                is_confident,
                requires_review,
                agrees_with_production,
                model_name,
                mode
            FROM contextual_action_shadows
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()

    if row is None:
        return None

    result = dict(row)

    result["probabilities"] = json.loads(
        result["probabilities"]
    )

    for field_name in [
        "is_confident",
        "requires_review",
        "agrees_with_production",
    ]:
        if result[field_name] is not None:
            result[field_name] = bool(
                result[field_name]
            )

    return result

    
def get_decrypted_event_preview(
    event_id: int,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> dict | None:
    """Decrypt an internally stored redacted preview."""
    initialize_database(database_path)

    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT
                event_id,
                event_reference,
                encrypted_preview
            FROM encrypted_event_previews
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()

    if row is None:
        return None

    associated_data = build_preview_associated_data(
        event_id=row["event_id"],
        event_reference=row["event_reference"],
    )

    redacted_preview = decrypt_text(
        encrypted_payload=row["encrypted_preview"],
        associated_data=associated_data,
    )

    return {
        "event_id": row["event_id"],
        "event_reference": row["event_reference"],
        "redacted_prompt": redacted_preview,
    }
    
def get_recent_events(
    limit: int = 20,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> list[dict]:
    """Return the most recent security events."""
    initialize_database(database_path)

    safe_limit = max(
        1,
        min(limit, 100),
    )

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
            SELECT
                recommended_action,
                COUNT(*) AS count
            FROM security_events
            GROUP BY recommended_action
            """
        ).fetchall()

        category_rows = connection.execute(
            """
            SELECT
                category,
                COUNT(*) AS count
            FROM security_events
            GROUP BY category
            ORDER BY count DESC
            """
        ).fetchall()

    return {
        "total_scans": (
            totals["total_scans"] or 0
        ),
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
    """Verify all cryptographically chained events."""
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

    for checked_events, row in enumerate(rows):
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
            "matched_patterns": (
                row["matched_patterns"]
            ),
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

        if (
            not chain_link_is_valid
            or not event_is_valid
        ):
            return {
                "valid": False,
                "checked_events": checked_events,
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
def check_database_integrity(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> dict:
    """Check SQLite data and foreign-key integrity."""
    initialize_database(database_path)

    with get_connection(database_path) as connection:
        quick_check_rows = connection.execute(
            "PRAGMA quick_check"
        ).fetchall()

        foreign_key_rows = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

    quick_check_messages = [
        row[0]
        for row in quick_check_rows
    ]

    database_is_valid = (
        quick_check_messages == ["ok"]
        and not foreign_key_rows
    )

    return {
        "valid": database_is_valid,
        "quick_check": quick_check_messages,
        "foreign_key_violations": len(
            foreign_key_rows
        ),
    }