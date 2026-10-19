import json
from pathlib import Path

import pytest

import contextual_entity_service


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]

CHALLENGE_PATH = (
    BACKEND_DIRECTORY
    / "research"
    / "entity_localizer"
    / "data_iteration2"
    / "challenge.jsonl"
)


@pytest.fixture(autouse=True)
def clear_model_cache():
    """Prevent cached artifacts leaking between tests."""
    contextual_entity_service.clear_contextual_entity_model_cache()

    yield

    contextual_entity_service.clear_contextual_entity_model_cache()


def load_challenge_records() -> list[dict]:
    """Load the iteration-two challenge dataset."""
    records = []

    with CHALLENGE_PATH.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        for line in input_file:
            stripped_line = line.strip()

            if stripped_line:
                records.append(
                    json.loads(stripped_line)
                )

    return records


def test_contextual_entity_model_loads():
    """The service loads the research CRF artifact."""
    artifact = (
        contextual_entity_service
        .load_contextual_entity_model()
    )

    assert artifact["model_kind"] == "crf"

    assert (
        artifact["boundary_decoder_required"]
        is True
    )

    assert (
        artifact["historical_final_holdout_used"]
        is False
    )

    assert artifact["production_ready"] is False
    assert artifact["mode"] == "research"


def test_contextual_entity_service_detects_challenge_entity():
    """A known challenge entity is localized exactly."""
    records = load_challenge_records()

    record = next(
        challenge_record
        for challenge_record in records
        if challenge_record["gold_spans"]
    )

    result = (
        contextual_entity_service
        .analyze_contextual_entities(
            record["prompt"]
        )
    )

    predicted_spans = {
        (
            span["start"],
            span["end"],
            span["text"],
        )
        for span in result["spans"]
    }

    gold_spans = {
        (
            span["start"],
            span["end"],
            span["text"],
        )
        for span in record["gold_spans"]
    }

    assert result["available"] is True

    assert (
        result["contains_sensitive_data"]
        is True
    )

    assert gold_spans.issubset(
        predicted_spans
    )

    assert "[REDACTED]" in (
        result["redacted_prompt"]
    )

    assert result["mode"] == "shadow"

    assert (
        result["production_changed"]
        is False
    )


def test_contextual_entity_service_preserves_safe_prompt():
    """A negative control must remain unchanged."""
    records = load_challenge_records()

    record = next(
        challenge_record
        for challenge_record in records
        if not challenge_record["gold_spans"]
    )

    result = (
        contextual_entity_service
        .analyze_contextual_entities(
            record["prompt"]
        )
    )

    assert result["available"] is True

    assert (
        result["contains_sensitive_data"]
        is False
    )

    assert result["spans"] == []

    assert (
        result["redacted_prompt"]
        == record["prompt"]
    )

    assert result["mode"] == "shadow"

    assert (
        result["production_changed"]
        is False
    )


def test_redaction_handles_multiple_spans():
    """Multiple spans are replaced without offset drift."""
    prompt = (
        "Email alice@example.com and use "
        "token ABC123XYZ."
    )

    spans = [
        {
            "start": 6,
            "end": 23,
            "text": "alice@example.com",
        },
        {
            "start": 38,
            "end": 47,
            "text": "ABC123XYZ",
        },
    ]

    redacted = (
        contextual_entity_service
        .redact_detected_spans(
            prompt,
            spans,
        )
    )

    assert redacted == (
        "Email [REDACTED] and use "
        "token [REDACTED]."
    )


def test_invalid_redaction_span_is_rejected():
    """Incorrect offsets must never silently redact text."""
    with pytest.raises(
        RuntimeError,
        match="does not match",
    ):
        (
            contextual_entity_service
            .redact_detected_spans(
                "Email alice@example.com",
                [
                    {
                        "start": 6,
                        "end": 10,
                        "text": "wrong-value",
                    }
                ],
            )
        )


def test_empty_prompt_is_rejected():
    """Blank prompts are invalid."""
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        (
            contextual_entity_service
            .analyze_contextual_entities(
                "   "
            )
        )


def test_safe_wrapper_handles_missing_model(
    tmp_path,
):
    """Model failure must not interrupt production."""
    missing_model_path = (
        tmp_path
        / "missing-model.joblib"
    )

    prompt = "Explain secure token storage."

    result = (
        contextual_entity_service
        .analyze_contextual_entities_safely(
            prompt=prompt,
            model_path=missing_model_path,
        )
    )

    assert result["available"] is False

    assert (
        result["contains_sensitive_data"]
        is False
    )

    assert result["spans"] == []

    assert result["redacted_prompt"] == prompt
    assert result["mode"] == "shadow"

    assert (
        result["production_changed"]
        is False
    )

    assert "not found" in result["error"]


def test_model_cache_reuses_artifact():
    """Repeated loads should reuse one validated artifact."""
    first_artifact = (
        contextual_entity_service
        .load_contextual_entity_model()
    )

    second_artifact = (
        contextual_entity_service
        .load_contextual_entity_model()
    )

    assert first_artifact is second_artifact