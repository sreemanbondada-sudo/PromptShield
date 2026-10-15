import json
from pathlib import Path

import joblib
import pytest

from research.entity_localizer.boundary_decoder import (
    decode_sensitive_spans,
)
from research.entity_localizer.train_iteration2_candidates import (
    predict_candidate,
)


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]

ENTITY_DIRECTORY = (
    BACKEND_DIRECTORY
    / "research"
    / "entity_localizer"
)

MODEL_PATH = (
    ENTITY_DIRECTORY
    / "models_iteration2"
    / "contextual_entity_candidate_iteration2.joblib"
)

CHALLENGE_PATH = (
    ENTITY_DIRECTORY
    / "data_iteration2"
    / "challenge.jsonl"
)

HISTORICAL_HOLDOUT_PATH = (
    ENTITY_DIRECTORY
    / "data"
    / "final_holdout.jsonl"
)

VALID_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
    "O",
}


def load_jsonl(path: Path) -> list[dict]:
    """Load records from a JSON Lines file."""
    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        for line_number, line in enumerate(
            input_file,
            start=1,
        ):
            stripped_line = line.strip()

            if not stripped_line:
                continue

            try:
                records.append(
                    json.loads(stripped_line)
                )

            except json.JSONDecodeError as error:
                raise AssertionError(
                    f"Invalid JSON in {path} "
                    f"at line {line_number}."
                ) from error

    return records


@pytest.fixture(scope="module")
def candidate() -> dict:
    """Load the frozen iteration-two candidate."""
    assert MODEL_PATH.exists(), (
        "The iteration-two entity model is missing. "
        "Run train_iteration2_candidates.py first."
    )

    artifact = joblib.load(MODEL_PATH)

    assert isinstance(artifact, dict)

    return artifact


@pytest.fixture(scope="module")
def challenge_records() -> list[dict]:
    """Load the iteration-two challenge records."""
    assert CHALLENGE_PATH.exists()

    records = load_jsonl(CHALLENGE_PATH)

    assert records

    return records


def normalize_span(span: dict) -> tuple[int, int, str]:
    """Convert a span to an exact comparable value."""
    return (
        int(span["start"]),
        int(span["end"]),
        str(span["text"]),
    )

def decode_record_predictions(
    records: list[dict],
    predictions: list[list[str]],
) -> list[list[dict]]:
    """Decode predicted labels into exact spans."""
    decoded_records = []

    for record, predicted_labels in zip(
        records,
        predictions,
        strict=True,
    ):
        decoded = decode_sensitive_spans(
            prompt=record["prompt"],
            tokens=record["tokens"],
            predicted_labels=predicted_labels,
        )

        assert isinstance(decoded, dict)
        assert "spans" in decoded
        assert "labels" in decoded

        assert len(decoded["labels"]) == len(
            record["tokens"]
        )

        assert set(decoded["labels"]).issubset(
            VALID_LABELS
        )

        decoded_records.append(
            decoded["spans"]
        )

    return decoded_records


def test_iteration_two_artifact_metadata(
    candidate,
):
    """The saved artifact must remain research-only."""
    assert candidate["model_kind"] == "crf"
    assert candidate["classifier"] is not None
    assert candidate["vectorizer"] is None

    assert candidate["context_window"] == 2

    assert candidate["label_scheme"] == [
        "B-SENSITIVE",
        "I-SENSITIVE",
        "O",
    ]

    assert (
        candidate["boundary_decoder_required"]
        is True
    )

    assert (
        candidate["historical_final_holdout_used"]
        is False
    )

    assert candidate["production_ready"] is False
    assert candidate["mode"] == "research"


def test_iteration_two_artifact_predicts_valid_sequences(
    candidate,
    challenge_records,
):
    """The artifact must produce one valid label per token."""
    records = challenge_records[:20]

    predictions = predict_candidate(
        records,
        candidate,
    )

    assert len(predictions) == len(records)

    for record, predicted_labels in zip(
        records,
        predictions,
        strict=True,
    ):
        assert len(predicted_labels) == len(
            record["tokens"]
        )

        assert set(predicted_labels).issubset(
            VALID_LABELS
        )


def test_decoded_spans_have_exact_offsets(
    candidate,
    challenge_records,
):
    """Every decoded span must match its prompt offsets."""
    predictions = predict_candidate(
        challenge_records,
        candidate,
    )

    decoded_records = decode_record_predictions(
        challenge_records,
        predictions,
    )

    for record, spans in zip(
        challenge_records,
        decoded_records,
        strict=True,
    ):
        prompt = record["prompt"]

        for span in spans:
            assert 0 <= span["start"] < span["end"]
            assert span["end"] <= len(prompt)

            assert (
                prompt[
                    span["start"]:
                    span["end"]
                ]
                == span["text"]
            )


def test_iteration_two_challenge_quality(
    candidate,
    challenge_records,
):
    """
    Verify the frozen iteration-two challenge performance.

    This test does not load or evaluate the historical
    final holdout.
    """
    predictions = predict_candidate(
        challenge_records,
        candidate,
    )

    decoded_records = decode_record_predictions(
        challenge_records,
        predictions,
    )

    true_positive_spans = 0
    predicted_span_count = 0
    gold_span_count = 0

    false_positive_records = 0
    false_negative_records = 0

    negative_record_count = 0
    positive_record_count = 0

    for record, predicted_spans in zip(
        challenge_records,
        decoded_records,
        strict=True,
    ):
        gold_spans = record["gold_spans"]

        gold_values = {
            normalize_span(span)
            for span in gold_spans
        }

        predicted_values = {
            normalize_span(span)
            for span in predicted_spans
        }

        true_positive_spans += len(
            gold_values & predicted_values
        )

        gold_span_count += len(gold_values)

        predicted_span_count += len(
            predicted_values
        )

        if gold_values:
            positive_record_count += 1

            if not predicted_values:
                false_negative_records += 1

        else:
            negative_record_count += 1

            if predicted_values:
                false_positive_records += 1

    precision = (
        true_positive_spans
        / predicted_span_count
        if predicted_span_count
        else 0.0
    )

    recall = (
        true_positive_spans
        / gold_span_count
        if gold_span_count
        else 0.0
    )

    exact_span_f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall
        else 0.0
    )

    false_positive_record_rate = (
        false_positive_records
        / negative_record_count
        if negative_record_count
        else 0.0
    )

    false_negative_record_rate = (
        false_negative_records
        / positive_record_count
        if positive_record_count
        else 0.0
    )

    assert precision >= 0.90
    assert recall >= 0.90
    assert exact_span_f1 >= 0.90

    assert false_positive_records == 0
    assert false_negative_records == 0

    assert false_positive_record_rate == 0.0
    assert false_negative_record_rate == 0.0


def test_historical_holdout_is_not_loaded(
    monkeypatch,
    candidate,
    challenge_records,
):
    """Prediction must not access the historical holdout."""
    original_open = Path.open

    def protected_open(path, *args, **kwargs):
        resolved_path = Path(path).resolve()

        assert resolved_path != (
            HISTORICAL_HOLDOUT_PATH.resolve()
        ), (
            "The historical final holdout must not "
            "be loaded during iteration-two testing."
        )

        return original_open(
            path,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        Path,
        "open",
        protected_open,
    )

    predictions = predict_candidate(
        challenge_records[:5],
        candidate,
    )

    assert len(predictions) == 5