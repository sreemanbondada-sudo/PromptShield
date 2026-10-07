import json
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from audit_service import (
    GENESIS_HASH,
    create_event_hash,
    verify_event_hash,
)
from config import get_database_settings
from encryption_service import (
    decrypt_text,
    encrypt_text,
)


DATABASE_CONNECT_TIMEOUT_SECONDS = 5

# All audit-chain writers acquire this transaction-level lock.
# The value is an application-specific signed 64-bit integer.
AUDIT_CHAIN_ADVISORY_LOCK_ID = 578721238


def get_database_url(
    database_url: str | None = None,
) -> str:
    """Return a validated PostgreSQL connection URL."""
    if database_url is not None:
        selected_url = database_url
    else:
        database_settings = get_database_settings()

        if (
            database_settings["backend"]
            != "postgresql"
        ):
            raise RuntimeError(
                "PostgreSQL storage was selected without "
                "a configured PostgreSQL database URL."
            )

        selected_url = database_settings[
            "database_url"
        ]

    if selected_url is None:
        raise RuntimeError(
            "The PostgreSQL database URL is not configured."
        )

    if selected_url.startswith("postgres://"):
        selected_url = (
            "postgresql://"
            + selected_url[len("postgres://"):]
        )

    return selected_url


def get_connection(
    database_url: str | None = None,
) -> psycopg.Connection:
    """Create a PostgreSQL connection using dictionary rows."""
    return psycopg.connect(
        get_database_url(database_url),
        connect_timeout=(
            DATABASE_CONNECT_TIMEOUT_SECONDS
        ),
        row_factory=dict_row,
    )


def initialize_database(
    database_url: str | None = None,
) -> None:
    """Create the PostgreSQL PromptShield tables."""
    with get_connection(database_url) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS security_events (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                is_malicious SMALLINT NOT NULL
                    CHECK (is_malicious IN (0, 1)),
                risk_level TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                category TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                contains_sensitive_data SMALLINT NOT NULL
                    CHECK (
                        contains_sensitive_data IN (0, 1)
                    ),
                matched_patterns TEXT NOT NULL,
                sensitive_data_types TEXT NOT NULL,
                prompt_length INTEGER NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS
                encrypted_event_previews (
                    event_id BIGINT PRIMARY KEY,
                    event_reference TEXT NOT NULL UNIQUE,
                    encrypted_preview TEXT NOT NULL,
                    CONSTRAINT
                        encrypted_event_previews_event_fk
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
                    event_id BIGINT PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    production_action TEXT NOT NULL,
                    predicted_action TEXT,
                    probabilities TEXT NOT NULL
                        DEFAULT '{}',
                    confidence DOUBLE PRECISION,
                    probability_margin DOUBLE PRECISION,
                    is_confident SMALLINT
                        CHECK (
                            is_confident IS NULL
                            OR is_confident IN (0, 1)
                        ),
                    requires_review SMALLINT
                        CHECK (
                            requires_review IS NULL
                            OR requires_review IN (0, 1)
                        ),
                    agrees_with_production SMALLINT
                        CHECK (
                            agrees_with_production IS NULL
                            OR agrees_with_production IN (0, 1)
                        ),
                    model_name TEXT,
                    mode TEXT NOT NULL
                        DEFAULT 'shadow',
                    CONSTRAINT
                        contextual_action_shadows_event_fk
                    FOREIGN KEY (event_id)
                        REFERENCES security_events(id)
                        ON DELETE CASCADE
                )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                security_events_created_at_index
            ON security_events (created_at DESC)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                security_events_category_index
            ON security_events (category)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                security_events_action_index
            ON security_events (recommended_action)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                contextual_shadows_agreement_index
            ON contextual_action_shadows (
                agrees_with_production
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                contextual_shadows_prediction_index
            ON contextual_action_shadows (
                predicted_action
            )
            """
        )




def build_preview_associated_data(
    event_id: int,
    event_reference: str,
) -> str:
    """Build authenticated context for an encrypted preview."""
    return (
        "promptshield:event-preview:"
        f"{event_id}:{event_reference}"
    )


def save_security_event(
    analysis_result: dict,
    prompt_length: int,
    database_url: str | None = None,
) -> int:
    """
    Save a tamper-evident event, encrypted preview and shadow data.
    """
    initialize_database(database_url)

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

    with get_connection(database_url) as connection:
        connection.execute(
            """
            SELECT pg_advisory_xact_lock(%s)
            """,
            (AUDIT_CHAIN_ADVISORY_LOCK_ID,),
        )

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

        inserted_row = connection.execute(
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
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            RETURNING id
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
                event_data[
                    "sensitive_data_types"
                ],
                event_data["prompt_length"],
                previous_hash,
                event_hash,
            ),
        ).fetchone()

        if inserted_row is None:
            raise RuntimeError(
                "The security event could not be saved."
            )

        event_id = int(inserted_row["id"])
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
            VALUES (%s, %s, %s)
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
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
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
    database_url: str | None = None,
) -> dict | None:
    """Return privacy-safe contextual shadow metadata."""
    initialize_database(database_url)

    with get_connection(database_url) as connection:
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
            WHERE event_id = %s
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

    if result["created_at"] is not None:
        result["created_at"] = format_created_at(
            result["created_at"]
        )

    return result


def get_decrypted_event_preview(
    event_id: int,
    database_url: str | None = None,
) -> dict | None:
    """Decrypt an internally stored redacted preview."""
    initialize_database(database_url)

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
                event_id,
                event_reference,
                encrypted_preview
            FROM encrypted_event_previews
            WHERE event_id = %s
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


def format_created_at(value) -> str:
    """Return the timestamp format used by the dashboard."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(
                timezone.utc
            ).replace(tzinfo=None)

        return value.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    return str(value)


def get_recent_events(
    limit: int = 20,
    database_url: str | None = None,
) -> list[dict]:
    """Return the most recent PostgreSQL events."""
    initialize_database(database_url)

    safe_limit = max(
        1,
        min(limit, 100),
    )

    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM security_events
            ORDER BY id DESC
            LIMIT %s
            """,
            (safe_limit,),
        ).fetchall()

    events = []

    for row in rows:
        event = dict(row)

        event["created_at"] = format_created_at(
            event["created_at"]
        )

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
    database_url: str | None = None,
) -> dict:
    """Calculate PostgreSQL security statistics."""
    initialize_database(database_url)

    with get_connection(database_url) as connection:
        totals = connection.execute(
            """
            SELECT
                COUNT(*) AS total_scans,
                COALESCE(
                    SUM(is_malicious),
                    0
                ) AS malicious_prompts,
                COALESCE(
                    SUM(contains_sensitive_data),
                    0
                ) AS sensitive_prompts
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

    if totals is None:
        raise RuntimeError(
            "PostgreSQL statistics could not be calculated."
        )

    return {
        "total_scans": int(
            totals["total_scans"]
        ),
        "malicious_prompts": int(
            totals["malicious_prompts"]
        ),
        "sensitive_prompts": int(
            totals["sensitive_prompts"]
        ),
        "actions": {
            row["recommended_action"]: int(
                row["count"]
            )
            for row in action_rows
        },
        "categories": {
            row["category"]: int(row["count"])
            for row in category_rows
        },
    }


def verify_audit_chain(
    database_url: str | None = None,
) -> dict:
    """Verify all PostgreSQL audit-chain events."""
    initialize_database(database_url)

    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM security_events
            WHERE event_hash != ''
            ORDER BY id ASC
            """
        ).fetchall()

        legacy_row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM security_events
            WHERE event_hash = ''
            """
        ).fetchone()

    legacy_count = (
        int(legacy_row["count"])
        if legacy_row is not None
        else 0
    )

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
    database_url: str | None = None,
) -> dict:
    """Check PostgreSQL connectivity and required tables."""
    initialize_database(database_url)

    with get_connection(database_url) as connection:
        result = connection.execute(
            """
            SELECT
                to_regclass(
                    'public.security_events'
                ) IS NOT NULL
                    AS security_events_exists,
                to_regclass(
                    'public.encrypted_event_previews'
                ) IS NOT NULL
                    AS encrypted_previews_exists
            """
        ).fetchone()

    if result is None:
        return {
            "valid": False,
            "quick_check": [
                "PostgreSQL integrity query failed."
            ],
            "foreign_key_violations": 0,
            "backend": "postgresql",
        }

    tables_exist = (
        result["security_events_exists"]
        and result["encrypted_previews_exists"]
    )

    return {
        "valid": bool(tables_exist),
        "quick_check": (
            ["ok"]
            if tables_exist
            else ["Required PostgreSQL tables are missing."]
        ),
        "foreign_key_violations": 0,
        "backend": "postgresql",
    }