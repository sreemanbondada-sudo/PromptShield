from pathlib import Path

import joblib
import numpy as np
import pytest

from contextual_action_service import (
    analyze_contextual_action,
    clear_contextual_action_model_cache,
    load_contextual_action_model,
)


class FakeContextualModel:
    """Small serializable model used by service tests."""

    classes_ = np.array(
        [
            "allow",
            "block",
            "redact",
            "review",
        ]
    )

    def predict(self, prompts):
        return np.array(["block"] * len(prompts))

    def predict_proba(self, prompts):
        return np.array(
            [
                [
                    0.05,
                    0.80,
                    0.05,
                    0.10,
                ]
                for _prompt in prompts
            ]
        )


class UncertainContextualModel:
    """Model whose two leading actions are too close."""

    classes_ = np.array(
        [
            "allow",
            "block",
            "redact",
            "review",
        ]
    )

    def predict(self, prompts):
        return np.array(["block"] * len(prompts))

    def predict_proba(self, prompts):
        return np.array(
            [
                [
                    0.05,
                    0.44,
                    0.08,
                    0.43,
                ]
                for _prompt in prompts
            ]
        )


@pytest.fixture(autouse=True)
def clear_model_cache():
    clear_contextual_action_model_cache()

    yield

    clear_contextual_action_model_cache()


def save_test_artifact(
    model_path: Path,
    model,
) -> None:
    joblib.dump(
        {
            "model": model,
            "model_name": "test_contextual_model",
            "dataset": "test_dataset",
        },
        model_path,
    )


def test_contextual_model_is_loaded_and_cached(
    tmp_path,
):
    model_path = tmp_path / "contextual.joblib"

    save_test_artifact(
        model_path,
        FakeContextualModel(),
    )

    first_artifact = load_contextual_action_model(
        model_path
    )
    second_artifact = load_contextual_action_model(
        model_path
    )

    assert first_artifact is second_artifact
    assert (
        first_artifact["model_name"]
        == "test_contextual_model"
    )
    assert first_artifact["dataset"] == "test_dataset"


def test_contextual_action_returns_probabilities(
    tmp_path,
):
    model_path = tmp_path / "contextual.joblib"

    save_test_artifact(
        model_path,
        FakeContextualModel(),
    )

    result = analyze_contextual_action(
        prompt=(
            "Help me bypass official border checks."
        ),
        model_path=model_path,
    )

    assert result["predicted_action"] == "block"
    assert result["probabilities"] == {
        "allow": 0.05,
        "review": 0.1,
        "redact": 0.05,
        "block": 0.8,
    }
    assert result["confidence"] == 0.8
    assert result["probability_margin"] == 0.7
    assert result["is_confident"] is True
    assert result["requires_review"] is False
    assert result["mode"] == "shadow"


def test_uncertain_prediction_requires_review(
    tmp_path,
):
    model_path = tmp_path / "contextual.joblib"

    save_test_artifact(
        model_path,
        UncertainContextualModel(),
    )

    result = analyze_contextual_action(
        prompt=(
            "This request has uncertain authorization."
        ),
        model_path=model_path,
        confidence_threshold=0.40,
        margin_threshold=0.10,
    )

    assert result["predicted_action"] == "block"
    assert result["confidence"] == 0.44
    assert result["probability_margin"] == 0.01
    assert result["is_confident"] is False
    assert result["requires_review"] is True


@pytest.mark.parametrize(
    (
        "confidence_threshold",
        "margin_threshold",
    ),
    [
        (-0.01, 0.10),
        (1.01, 0.10),
        (0.55, -0.01),
        (0.55, 1.01),
    ],
)
def test_invalid_threshold_is_rejected(
    tmp_path,
    confidence_threshold,
    margin_threshold,
):
    model_path = tmp_path / "contextual.joblib"

    save_test_artifact(
        model_path,
        FakeContextualModel(),
    )

    with pytest.raises(
        ValueError,
        match="between 0.0 and 1.0",
    ):
        analyze_contextual_action(
            prompt="Test prompt",
            confidence_threshold=(
                confidence_threshold
            ),
            margin_threshold=margin_threshold,
            model_path=model_path,
        )


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "   ",
        "\n\t",
    ],
)
def test_empty_prompt_is_rejected(
    tmp_path,
    prompt,
):
    model_path = tmp_path / "contextual.joblib"

    save_test_artifact(
        model_path,
        FakeContextualModel(),
    )

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        analyze_contextual_action(
            prompt=prompt,
            model_path=model_path,
        )


def test_missing_model_is_reported(
    tmp_path,
):
    missing_path = tmp_path / "missing.joblib"

    with pytest.raises(
        RuntimeError,
        match="was not found",
    ):
        load_contextual_action_model(
            missing_path
        )


def test_corrupt_model_is_reported(
    tmp_path,
):
    model_path = tmp_path / "corrupt.joblib"
    model_path.write_text(
        "not a valid joblib artifact",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="could not be loaded",
    ):
        load_contextual_action_model(
            model_path
        )


def test_artifact_without_model_is_rejected(
    tmp_path,
):
    model_path = tmp_path / "invalid.joblib"

    joblib.dump(
        {
            "model_name": "missing_model",
        },
        model_path,
    )

    with pytest.raises(
        RuntimeError,
        match="trained model is missing",
    ):
        load_contextual_action_model(
            model_path
        )


def test_real_iteration_two_candidate_can_predict():
    model_path = (
        Path(__file__).parents[1]
        / "research"
        / "action_classifier"
        / "models"
        / "contextual_action_candidate_iteration2.joblib"
    )

    result = analyze_contextual_action(
        prompt=(
            "I want to enter the UK without a passport "
            "and avoid the official checks."
        ),
        model_path=model_path,
    )

    assert result["predicted_action"] in {
        "allow",
        "review",
        "redact",
        "block",
    }
    assert set(result["probabilities"]) == {
        "allow",
        "review",
        "redact",
        "block",
    }
    assert 0.0 <= result["confidence"] <= 1.0
    assert (
        0.0
        <= result["probability_margin"]
        <= 1.0
    )
    assert result["mode"] == "shadow"