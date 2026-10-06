"""Calibrate contextual-action confidence thresholds."""

import json
from pathlib import Path

import joblib

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    recall_score,
)


BASE_DIRECTORY = Path(__file__).resolve().parent
DATA_DIRECTORY = BASE_DIRECTORY / "data"
MODEL_DIRECTORY = BASE_DIRECTORY / "models"
REPORT_DIRECTORY = BASE_DIRECTORY / "reports"

VALIDATION_PATH = (
    DATA_DIRECTORY / "validation.jsonl"
)

CHALLENGE_PATH = (
    DATA_DIRECTORY / "challenge.jsonl"
)

MODEL_PATH = (
    MODEL_DIRECTORY
    / "contextual_action_candidate_iteration2.joblib"
)

REPORT_PATH = (
    REPORT_DIRECTORY
    / "contextual_action_threshold_calibration.json"
)

ACTION_ORDER = [
    "allow",
    "review",
    "redact",
    "block",
]

CONFIDENCE_THRESHOLDS = [
    round(value / 100, 2)
    for value in range(0, 76, 5)
]

MARGIN_THRESHOLDS = [
    round(value / 100, 2)
    for value in range(0, 31, 5)
]

MINIMUM_CHALLENGE_RECALL = {
    "allow": 0.80,
    "review": 0.70,
    "redact": 0.90,
    "block": 0.85,
}

MAXIMUM_CHALLENGE_FALSE_BLOCKS = 2


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
                record = json.loads(
                    stripped_line
                )

            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Invalid JSON in {path} "
                    f"at line {line_number}."
                ) from error

            records.append(record)

    if not records:
        raise RuntimeError(
            f"No records were loaded from {path}."
        )

    return records


def load_candidate() -> tuple[object, dict]:
    """Load the preserved iteration-two candidate."""
    if not MODEL_PATH.exists():
        raise RuntimeError(
            "The preserved iteration-two candidate "
            f"was not found at {MODEL_PATH}."
        )

    try:
        artifact = joblib.load(MODEL_PATH)

    except Exception as error:
        raise RuntimeError(
            "The iteration-two candidate could "
            "not be loaded."
        ) from error

    if not isinstance(artifact, dict):
        raise RuntimeError(
            "The candidate artifact must be "
            "a dictionary."
        )

    model = artifact.get("model")

    if model is None:
        raise RuntimeError(
            "The candidate artifact does not "
            "contain a model."
        )

    model_classes = {
        str(action)
        for action in model.classes_
    }

    if model_classes != set(ACTION_ORDER):
        raise RuntimeError(
            "The candidate classes do not match "
            "the four PromptShield actions."
        )

    return model, artifact


def predict_records(
    model,
    records: list[dict],
) -> list[dict]:
    """Calculate raw predictions and probabilities."""
    prompts = [
        record["prompt"]
        for record in records
    ]

    raw_predictions = model.predict(prompts)
    raw_probabilities = model.predict_proba(prompts)

    predictions = []

    for (
        record,
        predicted_action,
        probability_values,
    ) in zip(
        records,
        raw_predictions,
        raw_probabilities,
        strict=True,
    ):
        probabilities = {
            str(action): float(probability)
            for action, probability in zip(
                model.classes_,
                probability_values,
                strict=True,
            )
        }

        ordered_probabilities = sorted(
            probabilities.values(),
            reverse=True,
        )

        confidence = ordered_probabilities[0]
        probability_margin = (
            ordered_probabilities[0]
            - ordered_probabilities[1]
        )

        predictions.append(
            {
                "id": record["id"],
                "prompt": record["prompt"],
                "expected_action": (
                    record["action"]
                ),
                "raw_action": str(
                    predicted_action
                ),
                "probabilities": {
                    action: round(
                        probabilities.get(
                            action,
                            0.0,
                        ),
                        6,
                    )
                    for action in ACTION_ORDER
                },
                "confidence": confidence,
                "probability_margin": (
                    probability_margin
                ),
            }
        )

    return predictions


def apply_thresholds(
    predictions: list[dict],
    confidence_threshold: float,
    margin_threshold: float,
) -> list[dict]:
    """
    Convert uncertain non-review predictions to review.

    A raw Review decision remains Review because it already
    represents uncertainty or a need for human assessment.
    """
    resolved_predictions = []

    for prediction in predictions:
        raw_action = prediction["raw_action"]

        is_confident = (
            prediction["confidence"]
            >= confidence_threshold
            and prediction["probability_margin"]
            >= margin_threshold
        )

        if raw_action == "review":
            resolved_action = "review"

        elif is_confident:
            resolved_action = raw_action

        else:
            resolved_action = "review"

        resolved_predictions.append(
            {
                **prediction,
                "resolved_action": resolved_action,
                "is_confident": is_confident,
            }
        )

    return resolved_predictions


def evaluate_predictions(
    predictions: list[dict],
) -> dict:
    """Calculate four-action evaluation metrics."""
    expected_actions = [
        prediction["expected_action"]
        for prediction in predictions
    ]

    resolved_actions = [
        prediction["resolved_action"]
        for prediction in predictions
    ]

    per_action_recall_values = recall_score(
        expected_actions,
        resolved_actions,
        labels=ACTION_ORDER,
        average=None,
        zero_division=0,
    )

    per_action_recall = {
        action: float(recall)
        for action, recall in zip(
            ACTION_ORDER,
            per_action_recall_values,
            strict=True,
        )
    }

    false_blocks = sum(
        expected_action != "block"
        and predicted_action == "block"
        for expected_action, predicted_action in zip(
            expected_actions,
            resolved_actions,
            strict=True,
        )
    )

    incorrect_decisions = [
        {
            "id": prediction["id"],
            "prompt": prediction["prompt"],
            "expected_action": (
                prediction["expected_action"]
            ),
            "raw_action": prediction["raw_action"],
            "resolved_action": (
                prediction["resolved_action"]
            ),
            "confidence": round(
                prediction["confidence"],
                6,
            ),
            "probability_margin": round(
                prediction["probability_margin"],
                6,
            ),
            "probabilities": (
                prediction["probabilities"]
            ),
        }
        for prediction in predictions
        if (
            prediction["expected_action"]
            != prediction["resolved_action"]
        )
    ]

    confident_non_review_count = sum(
        prediction["raw_action"] == "review"
        or prediction["is_confident"]
        for prediction in predictions
    )

    return {
        "record_count": len(predictions),
        "accuracy": float(
            accuracy_score(
                expected_actions,
                resolved_actions,
            )
        ),
        "balanced_accuracy": float(
            balanced_accuracy_score(
                expected_actions,
                resolved_actions,
            )
        ),
        "macro_f1": float(
            f1_score(
                expected_actions,
                resolved_actions,
                labels=ACTION_ORDER,
                average="macro",
                zero_division=0,
            )
        ),
        "per_action_recall": (
            per_action_recall
        ),
        "false_blocks": false_blocks,
        "trusted_prediction_rate": (
            confident_non_review_count
            / len(predictions)
        ),
        "confusion_matrix": {
            "labels": ACTION_ORDER,
            "values": confusion_matrix(
                expected_actions,
                resolved_actions,
                labels=ACTION_ORDER,
            ).tolist(),
        },
        "incorrect_decisions": (
            incorrect_decisions
        ),
    }


def passes_safety_gates(
    challenge_metrics: dict,
) -> bool:
    """Check the challenge-set calibration gates."""
    recalls = (
        challenge_metrics[
            "per_action_recall"
        ]
    )

    recalls_pass = all(
        recalls[action] >= minimum
        for action, minimum
        in MINIMUM_CHALLENGE_RECALL.items()
    )

    false_blocks_pass = (
        challenge_metrics["false_blocks"]
        <= MAXIMUM_CHALLENGE_FALSE_BLOCKS
    )

    return recalls_pass and false_blocks_pass


def build_calibration_results(
    validation_predictions: list[dict],
    challenge_predictions: list[dict],
) -> list[dict]:
    """Evaluate every threshold combination."""
    calibration_results = []

    combined_predictions = (
        validation_predictions
        + challenge_predictions
    )

    for confidence_threshold in (
        CONFIDENCE_THRESHOLDS
    ):
        for margin_threshold in (
            MARGIN_THRESHOLDS
        ):
            validation_resolved = apply_thresholds(
                validation_predictions,
                confidence_threshold,
                margin_threshold,
            )

            challenge_resolved = apply_thresholds(
                challenge_predictions,
                confidence_threshold,
                margin_threshold,
            )

            combined_resolved = apply_thresholds(
                combined_predictions,
                confidence_threshold,
                margin_threshold,
            )

            validation_metrics = evaluate_predictions(
                validation_resolved
            )
            challenge_metrics = evaluate_predictions(
                challenge_resolved
            )
            combined_metrics = evaluate_predictions(
                combined_resolved
            )

            calibration_results.append(
                {
                    "confidence_threshold": (
                        confidence_threshold
                    ),
                    "margin_threshold": (
                        margin_threshold
                    ),
                    "passes_safety_gates": (
                        passes_safety_gates(
                            challenge_metrics
                        )
                    ),
                    "validation": (
                        validation_metrics
                    ),
                    "challenge": challenge_metrics,
                    "combined": combined_metrics,
                }
            )

    return calibration_results


def select_thresholds(
    calibration_results: list[dict],
) -> dict:
    """
    Select thresholds using challenge performance first.

    The final holdout is intentionally excluded from threshold
    selection.
    """
    passing_results = [
        result
        for result in calibration_results
        if result["passes_safety_gates"]
    ]

    candidates = (
        passing_results
        if passing_results
        else calibration_results
    )

    return max(
        candidates,
        key=lambda result: (
            result["passes_safety_gates"],
            result["challenge"]["macro_f1"],
            result["challenge"][
                "balanced_accuracy"
            ],
            result["combined"]["macro_f1"],
            result["validation"]["macro_f1"],
            result["challenge"][
                "trusted_prediction_rate"
            ],
            -result["confidence_threshold"],
            -result["margin_threshold"],
        ),
    )


def print_metrics(
    heading: str,
    metrics: dict,
) -> None:
    """Print a compact metrics summary."""
    recalls = metrics["per_action_recall"]

    print()
    print(heading)
    print("-" * len(heading))
    print(
        f"Records: {metrics['record_count']}"
    )
    print(
        "Accuracy: "
        f"{metrics['accuracy']:.2%}"
    )
    print(
        "Balanced accuracy: "
        f"{metrics['balanced_accuracy']:.2%}"
    )
    print(
        "Macro F1: "
        f"{metrics['macro_f1']:.2%}"
    )

    for action in ACTION_ORDER:
        print(
            f"{action.title()} recall: "
            f"{recalls[action]:.2%}"
        )

    print(
        "False blocks: "
        f"{metrics['false_blocks']}"
    )
    print(
        "Trusted prediction rate: "
        f"{metrics['trusted_prediction_rate']:.2%}"
    )
    print(
        "Incorrect decisions: "
        f"{len(metrics['incorrect_decisions'])}"
    )


def main() -> None:
    """Run threshold calibration."""
    print(
        "Loading validation and challenge datasets..."
    )

    validation_records = load_jsonl(
        VALIDATION_PATH
    )
    challenge_records = load_jsonl(
        CHALLENGE_PATH
    )

    print(
        "Validation records: "
        f"{len(validation_records)}"
    )
    print(
        "Challenge records: "
        f"{len(challenge_records)}"
    )
    print(
        "The final holdout is not used."
    )

    model, artifact = load_candidate()

    print()
    print(
        "Candidate: "
        f"{artifact.get('model_name', 'unknown')}"
    )
    print("Calculating model probabilities...")

    validation_predictions = predict_records(
        model,
        validation_records,
    )
    challenge_predictions = predict_records(
        model,
        challenge_records,
    )

    calibration_results = (
        build_calibration_results(
            validation_predictions,
            challenge_predictions,
        )
    )

    selected = select_thresholds(
        calibration_results
    )

    passing_count = sum(
        result["passes_safety_gates"]
        for result in calibration_results
    )

    report = {
        "model_path": str(MODEL_PATH),
        "model_name": artifact.get(
            "model_name",
            "unknown",
        ),
        "calibration_sources": [
            "validation.jsonl",
            "challenge.jsonl",
        ],
        "excluded_sources": [
            "test.jsonl",
            "final_holdout.jsonl",
        ],
        "evaluated_combinations": len(
            calibration_results
        ),
        "passing_combinations": passing_count,
        "selection_gates": {
            "minimum_challenge_recall": (
                MINIMUM_CHALLENGE_RECALL
            ),
            "maximum_challenge_false_blocks": (
                MAXIMUM_CHALLENGE_FALSE_BLOCKS
            ),
        },
        "selected": selected,
        "all_results": calibration_results,
    }

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("Threshold calibration completed.")
    print(
        "Evaluated combinations: "
        f"{len(calibration_results)}"
    )
    print(
        "Combinations passing safety gates: "
        f"{passing_count}"
    )
    print()
    print(
        "Selected confidence threshold: "
        f"{selected['confidence_threshold']:.2f}"
    )
    print(
        "Selected probability-margin threshold: "
        f"{selected['margin_threshold']:.2f}"
    )
    print(
        "Safety gates passed: "
        f"{selected['passes_safety_gates']}"
    )

    print_metrics(
        "Validation performance",
        selected["validation"],
    )

    print_metrics(
        "Manual challenge performance",
        selected["challenge"],
    )

    print_metrics(
        "Combined calibration performance",
        selected["combined"],
    )

    print()
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()