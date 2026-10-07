import database as sqlite_database
import postgres_database

from config import get_database_settings


def get_storage_backend_name() -> str:
    """Return the configured storage backend name."""
    return get_database_settings()["backend"]


def initialize_database() -> None:
    """Initialize the configured database backend."""
    settings = get_database_settings()

    if settings["backend"] == "postgresql":
        postgres_database.initialize_database(
            database_url=settings["database_url"],
        )
        return

    sqlite_database.initialize_database()


def save_security_event(
    analysis_result: dict,
    prompt_length: int,
) -> int:
    """Save an event using the configured backend."""
    settings = get_database_settings()

    if settings["backend"] == "postgresql":
        return postgres_database.save_security_event(
            analysis_result=analysis_result,
            prompt_length=prompt_length,
            database_url=settings["database_url"],
        )

    return sqlite_database.save_security_event(
        analysis_result=analysis_result,
        prompt_length=prompt_length,
    )

def get_contextual_action_shadow(
    event_id: int,
) -> dict | None:
    """Read contextual shadow metadata from configured storage."""
    settings = get_database_settings()

    if settings["backend"] == "postgresql":
        return (
            postgres_database
            .get_contextual_action_shadow(
                event_id=event_id,
                database_url=settings["database_url"],
            )
        )

    return (
        sqlite_database
        .get_contextual_action_shadow(
            event_id=event_id,
        )
    )

def get_contextual_shadow_statistics() -> dict:
    """Read contextual shadow statistics from configured storage."""
    settings = get_database_settings()

    if settings["backend"] == "postgresql":
        return (
            postgres_database
            .get_contextual_shadow_statistics(
                database_url=settings["database_url"],
            )
        )

    return (
        sqlite_database
        .get_contextual_shadow_statistics()
    )


def get_decrypted_event_preview(
    event_id: int,
) -> dict | None:
    """Read a preview using the configured backend."""
    settings = get_database_settings()

    if settings["backend"] == "postgresql":
        return (
            postgres_database
            .get_decrypted_event_preview(
                event_id=event_id,
                database_url=settings["database_url"],
            )
        )

    return (
        sqlite_database
        .get_decrypted_event_preview(
            event_id=event_id,
        )
    )


def get_recent_events(
    limit: int = 20,
) -> list[dict]:
    """Read recent events from the configured backend."""
    settings = get_database_settings()

    if settings["backend"] == "postgresql":
        return postgres_database.get_recent_events(
            limit=limit,
            database_url=settings["database_url"],
        )

    return sqlite_database.get_recent_events(
        limit=limit,
    )


def get_statistics() -> dict:
    """Read statistics from the configured backend."""
    settings = get_database_settings()

    if settings["backend"] == "postgresql":
        return postgres_database.get_statistics(
            database_url=settings["database_url"],
        )

    return sqlite_database.get_statistics()


def verify_audit_chain() -> dict:
    """Verify the configured backend audit chain."""
    settings = get_database_settings()

    if settings["backend"] == "postgresql":
        return postgres_database.verify_audit_chain(
            database_url=settings["database_url"],
        )

    return sqlite_database.verify_audit_chain()


def check_database_integrity() -> dict:
    """Check integrity of the configured backend."""
    settings = get_database_settings()

    if settings["backend"] == "postgresql":
        return (
            postgres_database
            .check_database_integrity(
                database_url=settings["database_url"],
            )
        )

    return sqlite_database.check_database_integrity()