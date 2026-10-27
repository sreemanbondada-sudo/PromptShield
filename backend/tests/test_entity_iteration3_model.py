"""Tests for the frozen iteration-three entity model."""

from pathlib import Path

import joblib
import pytest

from research.entity_localizer import (
    boundary_decoder,
)

from research.entity_localizer.train_entity_candidates import (
    load_jsonl,
)

from research.entity_localizer.train_iteration3_candidates import (
    DATASET_PATHS,
    ITERATION3_MODEL_PATH,
    evaluate_candidate,
    predict_candidate,
)


VALID_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
    "O",
}


@pytest.fixture(scope="module")
def candidate() -> dict:
    """Load the frozen iteration-three artifact."""
    assert ITERATION3_MODEL_PATH.exists()

    artifact = joblib.load(
        ITERATION3_MODEL_PATH
    )

    assert isinstance(artifact, dict)

    return artifact


@pytest.fixture(scope="module")
def validation_records() -> list[dict]:
    """Load the iteration-three validation split."""
    return load_jsonl(
        DATASET_PATHS["validation"]
    )


@pytest.fixture(scope="module")
def challenge_records() -> list[dict]:
    """Load the iteration-three challenge split."""
    return load_jsonl(
        DATASET_PATHS["challenge"]
    )


def test_iteration_three_artifact_metadata(
    candidate,
):
    """Verify frozen model metadata and safeguards."""
    assert candidate["model_name"] == (
        "iteration3_crf_context_one"
    )

    assert candidate["model_type"] == (
        "contextual_sensitive_entity_"
        "localizer_iteration3"
    )

    assert candidate["model_kind"] == "crf"

    assert candidate["dataset"] == (
        "contextual_sensitive_entity_"
        "iteration3_development_v1"
    )

    assert candidate["feature_set"] == (
        "iteration3_structural_features"
    )

    assert candidate["context_window"] == 1

    assert candidate["label_scheme"] == [
        "B-SENSITIVE",
        "I-SENSITIVE",
        "O",
    ]

    assert candidate[
        "boundary_decoder_required"
    ] is True

    assert candidate[
        "historical_final_holdout_used"
    ] is False

    assert candidate[
        "iteration2_final_holdout_used"
    ] is False

    assert candidate[
        "production_ready"
    ] is False

    assert candidate[
        "production_changed"
    ] is False

    assert candidate["mode"] == "research"

    assert candidate["vectorizer"] is None

    assert candidate["classifier"] is not None


def test_iteration_three_predictions_are_valid(
    candidate,
    challenge_records,
):
    """Every prompt receives a valid BIO sequence."""
    predictions = predict_candidate(
        challenge_records,
        candidate,
    )

    assert len(predictions) == len(
        challenge_records
    )

    for record, labels in zip(
        challenge_records,
        predictions,
        strict=True,
    ):
        assert len(labels) == len(
            record["tokens"]
        )

        assert set(labels).issubset(
            VALID_LABELS
        )

        previous_label = "O"

        for label in labels:
            if label == "I-SENSITIVE":
                assert previous_label in {
                    "B-SENSITIVE",
                    "I-SENSITIVE",
                }

            previous_label = label


def test_decoded_spans_have_exact_offsets(
    candidate,
    challenge_records,
):
    """Decoded span text must match prompt offsets."""
    predictions = predict_candidate(
        challenge_records,
        candidate,
    )

    for record, labels in zip(
        challenge_records,
        predictions,
        strict=True,
    ):
        result = (
            boundary_decoder
            .decode_sensitive_spans(
                prompt=record["prompt"],
                tokens=record["tokens"],
                predicted_labels=labels,
            )
        )

        assert isinstance(result, dict)
        assert "labels" in result
        assert "spans" in result

        for span in result["spans"]:
            assert span["start"] >= 0
            assert span["end"] > span["start"]

            assert span["end"] <= len(
                record["prompt"]
            )

            assert span["text"] == (
                record["prompt"][
                    span["start"]:
                    span["end"]
                ]
            )


def test_iteration_three_validation_quality(
    candidate,
    validation_records,
):
    """Verify the frozen validation performance."""
    evaluation = evaluate_candidate(
        validation_records,
        candidate,
    )

    assert (
        evaluation["record_count"]
        == 300
    )

    assert (
        evaluation["exact_span_precision"]
        >= 0.98
    )

    assert (
        evaluation["exact_span_recall"]
        >= 0.98
    )

    assert (
        evaluation["exact_span_f1"]
        >= 0.98
    )

    assert (
        evaluation["sensitive_token_f1"]
        >= 0.99
    )

    assert (
        evaluation[
            "false_positive_records"
        ]
        == 0
    )

    assert (
        evaluation[
            "false_negative_records"
        ]
        == 0
    )

    assert (
        evaluation[
            "incorrect_record_count"
        ]
        <= 2
    )


def test_iteration_three_challenge_quality(
    candidate,
    challenge_records,
):
    """Verify frozen development challenge results."""
    evaluation = evaluate_candidate(
        challenge_records,
        candidate,
    )

    assert (
        evaluation["record_count"]
        == 300
    )

    assert (
        evaluation["exact_span_precision"]
        == pytest.approx(1.0)
    )

    assert (
        evaluation["exact_span_recall"]
        == pytest.approx(1.0)
    )

    assert (
        evaluation["exact_span_f1"]
        == pytest.approx(1.0)
    )

    assert (
        evaluation["sensitive_token_f1"]
        == pytest.approx(1.0)
    )

    assert (
        evaluation[
            "false_positive_records"
        ]
        == 0
    )

    assert (
        evaluation[
            "false_negative_records"
        ]
        == 0
    )

    assert (
        evaluation[
            "incorrect_record_count"
        ]
        == 0
    )


def test_protected_holdouts_are_not_loaded():
    """Development paths exclude frozen holdouts."""
    configured_paths = {
        path.resolve()
        for path in DATASET_PATHS.values()
    }

    script_directory = (
        ITERATION3_MODEL_PATH
        .parent
        .parent
    )

    protected_paths = {
        (
            script_directory
            / "data"
            / "final_holdout.jsonl"
        ).resolve(),
        (
            script_directory
            / "data_iteration2_final"
            / "final_holdout.jsonl"
        ).resolve(),
    }

    assert configured_paths.isdisjoint(
        protected_paths
    )


def test_training_script_has_no_final_holdout_path():
    """Training source cannot reference holdout data."""
    training_module_path = Path(
        __import__(
            (
                "research.entity_localizer."
                "train_iteration3_candidates"
            ),
            fromlist=["__file__"],
        ).__file__
    )

    source = training_module_path.read_text(
        encoding="utf-8"
    )

    assert (
        "data_iteration2_final"
        not in source
    )

    assert (
        "/final_holdout.jsonl"
        not in source.replace("\\", "/")
    )