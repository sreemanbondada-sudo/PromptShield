import json
from pathlib import Path

import joblib
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from train_expanded_model import (
    DEEPSET_TEST_PATH,
    NEURALCHEMY_TEST_PATH,
    load_prompt_label_csv,
    malicious_probabilities,
)


BASE_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = BASE_DIRECTORY / "data"
EXTERNAL_DIRECTORY = DATA_DIRECTORY / "external"
MODEL_DIRECTORY = BASE_DIRECTORY / "models"

PRODUCTION_MODEL_PATH = (
    MODEL_DIRECTORY / "prompt_classifier.joblib"
)

SCAMBENCH_MODEL_PATH = (
    MODEL_DIRECTORY
    / "scambench_candidate_classifier.joblib"
)

SCAMBENCH_TEST_PATH = (
    EXTERNAL_DIRECTORY / "scambench_test.csv"
)

PROMPTSHIELD_CHALLENGE_PATH = (
    DATA_DIRECTORY / "challenge_prompts.csv"
)

OUTPUT_PATH = (
    MODEL_DIRECTORY
    / "ensemble_evaluation.json"
)

PRODUCTION_THRESHOLD = 0.55
SCAMBENCH_THRESHOLD = 0.60


def calculate_metrics(
    labels: list[int],
    predictions: list[int],
) -> dict:
    """Calculate binary classification metrics."""
    matrix = confusion_matrix(
        labels,
        predictions,
        labels=[0, 1],
    )

    true_negative = int(matrix[0][0])
    false_positive = int(matrix[0][1])
    false_negative = int(matrix[1][0])
    true_positive = int(matrix[1][1])

    safe_total = true_negative + false_positive

    false_positive_rate = (
        false_positive / safe_total
        if safe_total
        else 0.0
    )

    return {
        "accuracy": accuracy_score(
            labels,
            predictions,
        ),
        "precision": precision_score(
            labels,
            predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            labels,
            predictions,
            zero_division=0,
        ),
        "f1_score": f1_score(
            labels,
            predictions,
            zero_division=0,
        ),
        "false_positive_rate": (
            false_positive_rate
        ),
        "confusion_matrix": matrix.tolist(),
        "true_negatives": true_negative,
        "false_positives": false_positive,
        "false_negatives": false_negative,
        "true_positives": true_positive,
    }


def print_metrics(
    model_name: str,
    metrics: dict,
) -> None:
    """Print readable classification metrics."""
    print(f"  {model_name}")
    print(
        f"    Accuracy: "
        f"{metrics['accuracy']:.2%}"
    )
    print(
        f"    Precision: "
        f"{metrics['precision']:.2%}"
    )
    print(
        f"    Recall: "
        f"{metrics['recall']:.2%}"
    )
    print(
        f"    F1 score: "
        f"{metrics['f1_score']:.2%}"
    )
    print(
        f"    False-positive rate: "
        f"{metrics['false_positive_rate']:.2%}"
    )
    print(
        f"    Confusion matrix: "
        f"{metrics['confusion_matrix']}"
    )


def evaluate_ensemble() -> None:
    """Compare production, candidate and OR ensemble."""
    if not PRODUCTION_MODEL_PATH.exists():
        raise RuntimeError(
            "Production model was not found."
        )

    if not SCAMBENCH_MODEL_PATH.exists():
        raise RuntimeError(
            "ScamBench candidate model was not found."
        )

    production_model = joblib.load(
        PRODUCTION_MODEL_PATH
    )

    scambench_model = joblib.load(
        SCAMBENCH_MODEL_PATH
    )

    evaluation_sets = {
        "neuralchemy_test": (
            load_prompt_label_csv(
                NEURALCHEMY_TEST_PATH
            )
        ),
        "deepset_test": (
            load_prompt_label_csv(
                DEEPSET_TEST_PATH
            )
        ),
        "scambench_test": (
            load_prompt_label_csv(
                SCAMBENCH_TEST_PATH
            )
        ),
        "promptshield_challenge": (
            load_prompt_label_csv(
                PROMPTSHIELD_CHALLENGE_PATH
            )
        ),
    }

    evaluations = {}

    for dataset_name, (
        prompts,
        labels,
    ) in evaluation_sets.items():
        production_probabilities = (
            malicious_probabilities(
                production_model,
                prompts,
            )
        )

        scambench_probabilities = (
            malicious_probabilities(
                scambench_model,
                prompts,
            )
        )

        production_predictions = [
            int(
                probability
                >= PRODUCTION_THRESHOLD
            )
            for probability in (
                production_probabilities
            )
        ]

        scambench_predictions = [
            int(
                probability
                >= SCAMBENCH_THRESHOLD
            )
            for probability in (
                scambench_probabilities
            )
        ]

        ensemble_predictions = [
            int(
                production_prediction == 1
                or scambench_prediction == 1
            )
            for (
                production_prediction,
                scambench_prediction,
            ) in zip(
                production_predictions,
                scambench_predictions,
            )
        ]

        candidate_only_detections = [
            index
            for index, (
                production_prediction,
                scambench_prediction,
            ) in enumerate(
                zip(
                    production_predictions,
                    scambench_predictions,
                )
            )
            if (
                production_prediction == 0
                and scambench_prediction == 1
            )
        ]

        candidate_only_true_positives = sum(
            labels[index] == 1
            for index in candidate_only_detections
        )

        candidate_only_false_positives = sum(
            labels[index] == 0
            for index in candidate_only_detections
        )

        dataset_metrics = {
            "production": calculate_metrics(
                labels,
                production_predictions,
            ),
            "scambench_candidate": (
                calculate_metrics(
                    labels,
                    scambench_predictions,
                )
            ),
            "or_ensemble": calculate_metrics(
                labels,
                ensemble_predictions,
            ),
            "candidate_only_detections": len(
                candidate_only_detections
            ),
            "candidate_only_true_positives": (
                candidate_only_true_positives
            ),
            "candidate_only_false_positives": (
                candidate_only_false_positives
            ),
        }

        evaluations[dataset_name] = (
            dataset_metrics
        )

        print()
        print(dataset_name)

        print_metrics(
            "Production model",
            dataset_metrics["production"],
        )

        print_metrics(
            "ScamBench candidate",
            dataset_metrics[
                "scambench_candidate"
            ],
        )

        print_metrics(
            "OR ensemble",
            dataset_metrics["or_ensemble"],
        )

        print(
            "  Candidate-only detections: "
            f"{len(candidate_only_detections)} "
            "("
            f"{candidate_only_true_positives} true, "
            f"{candidate_only_false_positives} false"
            ")"
        )

    report = {
        "production_threshold": (
            PRODUCTION_THRESHOLD
        ),
        "scambench_threshold": (
            SCAMBENCH_THRESHOLD
        ),
        "ensemble_rule": (
            "Flag when either production model or "
            "ScamBench model exceeds its threshold."
        ),
        "evaluations": evaluations,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"Report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    evaluate_ensemble()