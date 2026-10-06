from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib


VALID_ACTIONS = {
    "allow",
    "review",
    "redact",
    "block",
}

DEFAULT_CONTEXTUAL_ACTION_MODEL_PATH = (
    Path(__file__).parent
    / "research"
    / "action_classifier"
    / "models"
    / "contextual_action_candidate_iteration2.joblib"
)

DEFAULT_CONFIDENCE_THRESHOLD = 0.55
DEFAULT_MARGIN_THRESHOLD = 0.10


def _validate_probability_threshold(
    value: float,
    setting_name: str,
) -> None:
    """Validate a probability or probability-margin threshold."""
    if not 0.0 <= value <= 1.0:
        raise ValueError(
            f"{setting_name} must be between 0.0 and 1.0."
        )


def _validate_artifact(
    artifact: Any,
    model_path: Path,
) -> dict:
    """Validate the structure of a contextual-model artifact."""
    if not isinstance(artifact, dict):
        raise RuntimeError(
            "The contextual action model artifact is invalid: "
            "the top-level value must be a dictionary."
        )

    model = artifact.get("model")

    if model is None:
        raise RuntimeError(
            "The contextual action model artifact is invalid: "
            "the trained model is missing."
        )

    if not callable(getattr(model, "predict", None)):
        raise RuntimeError(
            "The contextual action model artifact is invalid: "
            "the model does not support prediction."
        )

    if not callable(
        getattr(model, "predict_proba", None)
    ):
        raise RuntimeError(
            "The contextual action model artifact is invalid: "
            "the model does not provide class probabilities."
        )

    model_classes = {
        str(action)
        for action in getattr(
            model,
            "classes_",
            [],
        )
    }

    if model_classes != VALID_ACTIONS:
        raise RuntimeError(
            "The contextual action model artifact is invalid: "
            "its classes must be allow, review, redact and block."
        )

    return {
        "model": model,
        "model_name": str(
            artifact.get(
                "model_name",
                "contextual_action_classifier",
            )
        ),
        "dataset": str(
            artifact.get(
                "dataset",
                "contextual_action_dataset",
            )
        ),
        "model_path": str(model_path),
    }


@lru_cache(maxsize=4)
def load_contextual_action_model(
    model_path: Path = (
        DEFAULT_CONTEXTUAL_ACTION_MODEL_PATH
    ),
) -> dict:
    """Load and validate a trusted contextual action model."""
    resolved_path = Path(model_path).resolve()

    if not resolved_path.exists():
        raise RuntimeError(
            "The contextual action model was not found at "
            f"{resolved_path}."
        )

    if not resolved_path.is_file():
        raise RuntimeError(
            "The contextual action model path does not "
            "identify a file."
        )

    try:
        artifact = joblib.load(resolved_path)

    except Exception as error:
        raise RuntimeError(
            "The contextual action model could not be loaded."
        ) from error

    return _validate_artifact(
        artifact=artifact,
        model_path=resolved_path,
    )


def clear_contextual_action_model_cache() -> None:
    """Clear the cached contextual model for tests or reloads."""
    load_contextual_action_model.cache_clear()


def analyze_contextual_action(
    prompt: str,
    confidence_threshold: float = (
        DEFAULT_CONFIDENCE_THRESHOLD
    ),
    margin_threshold: float = DEFAULT_MARGIN_THRESHOLD,
    model_path: Path = (
        DEFAULT_CONTEXTUAL_ACTION_MODEL_PATH
    ),
) -> dict:
    """
    Predict an action without changing the production decision.

    This function is initially intended for shadow-mode
    evaluation. Production continues to use the existing hybrid
    decision pipeline until controlled integration is complete.
    """
    if not isinstance(prompt, str):
        raise TypeError("The prompt must be a string.")

    cleaned_prompt = prompt.strip()

    if not cleaned_prompt:
        raise ValueError("The prompt must not be empty.")

    _validate_probability_threshold(
        confidence_threshold,
        "confidence_threshold",
    )

    _validate_probability_threshold(
        margin_threshold,
        "margin_threshold",
    )

    artifact = load_contextual_action_model(
        Path(model_path)
    )
    model = artifact["model"]

    try:
        predicted_action = str(
            model.predict([cleaned_prompt])[0]
        )

        raw_probabilities = model.predict_proba(
            [cleaned_prompt]
        )[0]

    except Exception as error:
        raise RuntimeError(
            "The contextual action model could not analyze "
            "the prompt."
        ) from error

    probabilities = {
        str(action): float(probability)
        for action, probability in zip(
            model.classes_,
            raw_probabilities,
            strict=True,
        )
    }

    if predicted_action not in VALID_ACTIONS:
        raise RuntimeError(
            "The contextual action model returned an "
            "unsupported action."
        )

    ordered_probabilities = sorted(
        probabilities.values(),
        reverse=True,
    )

    confidence = ordered_probabilities[0]
    probability_margin = (
        ordered_probabilities[0]
        - ordered_probabilities[1]
    )

    is_confident = (
        confidence >= confidence_threshold
        and probability_margin >= margin_threshold
    )

    return {
        "predicted_action": predicted_action,
        "probabilities": {
            action: round(
                probabilities.get(action, 0.0),
                4,
            )
            for action in [
                "allow",
                "review",
                "redact",
                "block",
            ]
        },
        "confidence": round(confidence, 4),
        "probability_margin": round(
            probability_margin,
            4,
        ),
        "confidence_threshold": (
            confidence_threshold
        ),
        "margin_threshold": margin_threshold,
        "is_confident": is_confident,
        "requires_review": not is_confident,
        "model_name": artifact["model_name"],
        "dataset": artifact["dataset"],
        "mode": "shadow",
    }