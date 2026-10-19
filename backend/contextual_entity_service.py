"""Research-only contextual sensitive-entity service."""

from pathlib import Path
from typing import Any

import joblib

from research.entity_localizer.boundary_decoder import (
    decode_sensitive_spans,
)
from research.entity_localizer.build_entity_dataset import (
    tokenize_prompt,
)
from research.entity_localizer.train_entity_candidates import (
    build_token_features,
)


DEFAULT_CONTEXTUAL_ENTITY_MODEL_PATH = (
    Path(__file__).resolve().parent
    / "research"
    / "entity_localizer"
    / "models_iteration2"
    / "contextual_entity_candidate_iteration2.joblib"
)

EXPECTED_MODEL_TYPE = (
    "contextual_sensitive_entity_localizer_iteration2"
)

SENSITIVE_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
}

_model_cache: dict[Path, dict] = {}


def clear_contextual_entity_model_cache() -> None:
    """Clear cached research model artifacts."""
    _model_cache.clear()


def validate_model_artifact(
    artifact: Any,
) -> dict:
    """Validate the contextual entity artifact."""
    if not isinstance(artifact, dict):
        raise RuntimeError(
            "The contextual entity model artifact "
            "must be a dictionary."
        )

    required_keys = {
        "model_name",
        "model_type",
        "model_kind",
        "dataset",
        "context_window",
        "label_scheme",
        "classifier",
        "boundary_decoder_required",
        "historical_final_holdout_used",
        "production_ready",
        "mode",
    }

    missing_keys = required_keys - artifact.keys()

    if missing_keys:
        formatted_keys = ", ".join(
            sorted(missing_keys)
        )

        raise RuntimeError(
            "The contextual entity model artifact "
            f"is missing: {formatted_keys}."
        )

    if artifact["model_type"] != EXPECTED_MODEL_TYPE:
        raise RuntimeError(
            "The contextual entity model has an "
            "unsupported model type."
        )

    if artifact["model_kind"] != "crf":
        raise RuntimeError(
            "The contextual entity model must use "
            "the CRF model kind."
        )

    if not isinstance(
        artifact["context_window"],
        int,
    ) or artifact["context_window"] < 0:
        raise RuntimeError(
            "The contextual entity model contains "
            "an invalid context window."
        )

    label_scheme = set(
        artifact["label_scheme"]
    )

    expected_labels = {
        "B-SENSITIVE",
        "I-SENSITIVE",
        "O",
    }

    if label_scheme != expected_labels:
        raise RuntimeError(
            "The contextual entity model contains "
            "an unsupported BIO label scheme."
        )

    if artifact["classifier"] is None:
        raise RuntimeError(
            "The contextual entity classifier "
            "is missing."
        )

    if (
        artifact["boundary_decoder_required"]
        is not True
    ):
        raise RuntimeError(
            "The contextual entity artifact must "
            "require boundary decoding."
        )

    if (
        artifact["historical_final_holdout_used"]
        is not False
    ):
        raise RuntimeError(
            "The contextual entity artifact must not "
            "use the historical final holdout."
        )

    if artifact["production_ready"] is not False:
        raise RuntimeError(
            "The contextual entity artifact must "
            "remain research-only."
        )

    if artifact["mode"] != "research":
        raise RuntimeError(
            "The contextual entity artifact must "
            "remain in research mode."
        )

    return artifact


def load_contextual_entity_model(
    model_path: Path = (
        DEFAULT_CONTEXTUAL_ENTITY_MODEL_PATH
    ),
) -> dict:
    """Load and validate the research model."""
    resolved_path = Path(model_path).resolve()

    if resolved_path in _model_cache:
        return _model_cache[resolved_path]

    if not resolved_path.exists():
        raise RuntimeError(
            "The contextual entity model was not "
            "found. Run the iteration-two training "
            "script first."
        )

    try:
        artifact = joblib.load(
            resolved_path
        )

    except Exception as error:
        raise RuntimeError(
            "The contextual entity model could not "
            "be loaded."
        ) from error

    validated_artifact = (
        validate_model_artifact(
            artifact
        )
    )

    _model_cache[resolved_path] = (
        validated_artifact
    )

    return validated_artifact


def build_prompt_features(
    tokens: list[dict],
    context_window: int,
) -> list[dict]:
    """Build CRF features for one prompt."""
    return [
        build_token_features(
            tokens,
            token_index,
            context_window,
        )
        for token_index in range(
            len(tokens)
        )
    ]


def calculate_prediction_confidence(
    classifier,
    feature_sequence: list[dict],
    labels: list[str],
) -> tuple[float | None, float | None]:
    """
    Calculate overall and sensitive-token confidence.

    Confidence is informational because this service
    remains in research shadow mode.
    """
    predict_marginals = getattr(
        classifier,
        "predict_marginals_single",
        None,
    )

    if predict_marginals is None:
        return None, None

    marginal_probabilities = (
        predict_marginals(
            feature_sequence
        )
    )

    selected_probabilities = []
    sensitive_probabilities = []

    for (
        label,
        probabilities,
    ) in zip(
        labels,
        marginal_probabilities,
        strict=True,
    ):
        selected_probability = float(
            probabilities.get(
                label,
                0.0,
            )
        )

        selected_probabilities.append(
            selected_probability
        )

        if label in SENSITIVE_LABELS:
            sensitive_probabilities.append(
                selected_probability
            )

    overall_confidence = (
        sum(selected_probabilities)
        / len(selected_probabilities)
        if selected_probabilities
        else None
    )

    sensitive_confidence = (
        sum(sensitive_probabilities)
        / len(sensitive_probabilities)
        if sensitive_probabilities
        else None
    )

    return (
        round(overall_confidence, 4)
        if overall_confidence is not None
        else None,
        round(sensitive_confidence, 4)
        if sensitive_confidence is not None
        else None,
    )


def redact_detected_spans(
    prompt: str,
    spans: list[dict],
) -> str:
    """Replace detected spans without changing offsets."""
    redacted_prompt = prompt

    ordered_spans = sorted(
        spans,
        key=lambda span: (
            span["start"],
            span["end"],
        ),
        reverse=True,
    )

    for span in ordered_spans:
        start = int(span["start"])
        end = int(span["end"])

        if not 0 <= start < end <= len(prompt):
            raise RuntimeError(
                "The contextual entity model returned "
                "an invalid character span."
            )

        if prompt[start:end] != span["text"]:
            raise RuntimeError(
                "The contextual entity span does not "
                "match its prompt offsets."
            )

        redacted_prompt = (
            redacted_prompt[:start]
            + "[REDACTED]"
            + redacted_prompt[end:]
        )

    return redacted_prompt


def analyze_contextual_entities(
    prompt: str,
    model_path: Path = (
        DEFAULT_CONTEXTUAL_ENTITY_MODEL_PATH
    ),
) -> dict:
    """
    Locate sensitive entities using the research model.

    This function does not change production actions.
    """
    if not isinstance(prompt, str):
        raise TypeError(
            "The prompt must be a string."
        )

    if not prompt.strip():
        raise ValueError(
            "The prompt must not be empty."
        )

    artifact = load_contextual_entity_model(
        model_path
    )

    tokens = tokenize_prompt(prompt)

    if not tokens:
        return {
            "available": True,
            "contains_sensitive_data": False,
            "spans": [],
            "redacted_prompt": prompt,
            "confidence": None,
            "sensitive_confidence": None,
            "model_name": artifact["model_name"],
            "dataset": artifact["dataset"],
            "mode": "shadow",
            "production_changed": False,
        }

    feature_sequence = build_prompt_features(
        tokens,
        artifact["context_window"],
    )

    classifier = artifact["classifier"]

    predicted_sequences = classifier.predict(
        [feature_sequence]
    )

    if len(predicted_sequences) != 1:
        raise RuntimeError(
            "The contextual entity model returned "
            "an invalid prediction count."
        )

    predicted_labels = [
        str(label)
        for label in predicted_sequences[0]
    ]

    if len(predicted_labels) != len(tokens):
        raise RuntimeError(
            "The contextual entity prediction count "
            "does not match the token count."
        )

    decoded = decode_sensitive_spans(
        prompt=prompt,
        tokens=tokens,
        predicted_labels=predicted_labels,
    )

    spans = decoded["spans"]
    repaired_labels = decoded["labels"]

    confidence, sensitive_confidence = (
        calculate_prediction_confidence(
            classifier,
            feature_sequence,
            repaired_labels,
        )
    )

    findings = [
        {
            "start": int(span["start"]),
            "end": int(span["end"]),
            "text": str(span["text"]),
            "type": "contextual_sensitive_entity",
            "detection_method": (
                "contextual_crf_shadow"
            ),
        }
        for span in spans
    ]

    return {
        "available": True,
        "contains_sensitive_data": bool(
            findings
        ),
        "spans": findings,
        "redacted_prompt": (
            redact_detected_spans(
                prompt,
                findings,
            )
        ),
        "confidence": confidence,
        "sensitive_confidence": (
            sensitive_confidence
        ),
        "model_name": artifact["model_name"],
        "dataset": artifact["dataset"],
        "mode": "shadow",
        "production_changed": False,
    }


def analyze_contextual_entities_safely(
    prompt: str,
    model_path: Path = (
        DEFAULT_CONTEXTUAL_ENTITY_MODEL_PATH
    ),
) -> dict:
    """
    Return an unavailable shadow result on model errors.

    Production processing can continue unchanged.
    """
    try:
        return analyze_contextual_entities(
            prompt=prompt,
            model_path=model_path,
        )

    except (
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        return {
            "available": False,
            "contains_sensitive_data": False,
            "spans": [],
            "redacted_prompt": prompt,
            "confidence": None,
            "sensitive_confidence": None,
            "model_name": None,
            "dataset": None,
            "mode": "shadow",
            "production_changed": False,
            "error": str(error),
        }