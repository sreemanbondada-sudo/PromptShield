import json
from pathlib import Path

import joblib
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from train_expanded_model import (
    DEEPSET_TEST_PATH,
    DEEPSET_TRAIN_PATH,
    NEURALCHEMY_TEST_PATH,
    NEURALCHEMY_VALIDATION_PATH,
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

SCAMBENCH_VALIDATION_PATH = (
    EXTERNAL_DIRECTORY
    / "scambench_validation.csv"
)

SCAMBENCH_TEST_PATH = (
    EXTERNAL_DIRECTORY / "scambench_test.csv"
)

PROMPTSHIELD_CHALLENGE_PATH = (
    DATA_DIRECTORY / "challenge_prompts.csv"
)

OUTPUT_PATH = (
    MODEL_DIRECTORY
    / "weighted_ensemble_evaluation.json"
)

CANDIDATE_WEIGHTS = [
    0.0,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    1.0,
]

THRESHOLDS = [
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
]

MINIMUM_SOURCE_RECALL = 0.70


def combine_probabilities(
    production_probabilities: list[float],
    candidate_probabilities: list[float],
    candidate_weight: float,
) -> list[float]:
    """Calculate weighted malicious probabilities."""
    production_weight = 1.0 - candidate_weight

    return [
        (
            production_weight
            * production_probability
        )
        + (
            candidate_weight
            * candidate_probability
        )
        for (
            production_probability,
            candidate_probability,
        ) in zip(
            production_probabilities,
            candidate_probabilities,
        )
    ]


def calculate_metrics(
    labels: list[int],
    probabilities: list[float],
    threshold: float,
) -> dict:
    """Calculate classification metrics."""
    predictions = [
        int(probability >= threshold)
        for probability in probabilities
    ]

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
        "balanced_accuracy": (
            balanced_accuracy_score(
                labels,
                predictions,
            )
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
    dataset_name: str,
    metrics: dict,
) -> None:
    """Print one evaluation result."""
    print(dataset_name)
    print(
        f"  Accuracy: "
        f"{metrics['accuracy']:.2%}"
    )
    print(
        f"  Balanced accuracy: "
        f"{metrics['balanced_accuracy']:.2%}"
    )
    print(
        f"  Precision: "
        f"{metrics['precision']:.2%}"
    )
    print(
        f"  Recall: "
        f"{metrics['recall']:.2%}"
    )
    print(
        f"  F1 score: "
        f"{metrics['f1_score']:.2%}"
    )
    print(
        f"  False-positive rate: "
        f"{metrics['false_positive_rate']:.2%}"
    )
    print(
        f"  Confusion matrix: "
        f"{metrics['confusion_matrix']}"
    )


def load_validation_sets() -> dict:
    """Load validation-only datasets."""
    deepset_full_training = (
        load_prompt_label_csv(
            DEEPSET_TRAIN_PATH
        )
    )

    (
        _,
        deepset_validation_prompts,
        _,
        deepset_validation_labels,
    ) = train_test_split(
        deepset_full_training[0],
        deepset_full_training[1],
        test_size=0.20,
        random_state=42,
        stratify=deepset_full_training[1],
    )

    return {
        "neuralchemy_validation": (
            load_prompt_label_csv(
                NEURALCHEMY_VALIDATION_PATH
            )
        ),
        "deepset_validation": (
            deepset_validation_prompts,
            deepset_validation_labels,
        ),
        "scambench_validation": (
            load_prompt_label_csv(
                SCAMBENCH_VALIDATION_PATH
            )
        ),
    }


def select_configuration(
    production_model,
    candidate_model,
    validation_sets: dict,
) -> tuple[dict, list[dict]]:
    """Select weight and threshold on validation data."""
    probability_sets = {}

    for dataset_name, (
        prompts,
        labels,
    ) in validation_sets.items():
        probability_sets[dataset_name] = {
            "labels": labels,
            "production": (
                malicious_probabilities(
                    production_model,
                    prompts,
                )
            ),
            "candidate": (
                malicious_probabilities(
                    candidate_model,
                    prompts,
                )
            ),
        }

    results = []

    for candidate_weight in CANDIDATE_WEIGHTS:
        for threshold in THRESHOLDS:
            dataset_metrics = {}

            for dataset_name, values in (
                probability_sets.items()
            ):
                combined_probabilities = (
                    combine_probabilities(
                        values["production"],
                        values["candidate"],
                        candidate_weight,
                    )
                )

                dataset_metrics[dataset_name] = (
                    calculate_metrics(
                        values["labels"],
                        combined_probabilities,
                        threshold,
                    )
                )

            recalls = [
                metrics["recall"]
                for metrics in (
                    dataset_metrics.values()
                )
            ]

            average_balanced_accuracy = sum(
                metrics["balanced_accuracy"]
                for metrics in (
                    dataset_metrics.values()
                )
            ) / len(dataset_metrics)

            average_f1 = sum(
                metrics["f1_score"]
                for metrics in (
                    dataset_metrics.values()
                )
            ) / len(dataset_metrics)

            average_false_positive_rate = sum(
                metrics["false_positive_rate"]
                for metrics in (
                    dataset_metrics.values()
                )
            ) / len(dataset_metrics)

            results.append(
                {
                    "candidate_weight": (
                        candidate_weight
                    ),
                    "production_weight": (
                        1.0 - candidate_weight
                    ),
                    "threshold": threshold,
                    "minimum_recall": min(recalls),
                    "average_balanced_accuracy": (
                        average_balanced_accuracy
                    ),
                    "average_f1": average_f1,
                    "average_false_positive_rate": (
                        average_false_positive_rate
                    ),
                    "datasets": dataset_metrics,
                }
            )

    eligible_results = [
        result
        for result in results
        if (
            result["minimum_recall"]
            >= MINIMUM_SOURCE_RECALL
        )
    ]

    if not eligible_results:
        raise RuntimeError(
            "No weighted configuration met the "
            "minimum validation recall requirement."
        )

    selected = max(
        eligible_results,
        key=lambda result: (
            result["average_balanced_accuracy"],
            result["average_f1"],
            -result[
                "average_false_positive_rate"
            ],
        ),
    )

    return selected, results


def evaluate_weighted_ensemble() -> None:
    """Select and evaluate a weighted ensemble."""
    production_model = joblib.load(
        PRODUCTION_MODEL_PATH
    )

    candidate_model = joblib.load(
        SCAMBENCH_MODEL_PATH
    )

    validation_sets = load_validation_sets()

    selected, search_results = (
        select_configuration(
            production_model,
            candidate_model,
            validation_sets,
        )
    )

    candidate_weight = selected[
        "candidate_weight"
    ]

    threshold = selected["threshold"]

    print("Selected validation configuration")
    print(
        "  Production weight: "
        f"{selected['production_weight']:.2f}"
    )
    print(
        "  ScamBench weight: "
        f"{candidate_weight:.2f}"
    )
    print(
        f"  Threshold: {threshold:.2f}"
    )
    print(
        "  Average validation balanced accuracy: "
        f"{selected['average_balanced_accuracy']:.2%}"
    )
    print(
        "  Average validation F1: "
        f"{selected['average_f1']:.2%}"
    )
    print(
        "  Average validation false-positive rate: "
        f"{selected['average_false_positive_rate']:.2%}"
    )

    test_sets = {
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

    test_evaluations = {}

    for dataset_name, (
        prompts,
        labels,
    ) in test_sets.items():
        production_probabilities = (
            malicious_probabilities(
                production_model,
                prompts,
            )
        )

        candidate_probabilities = (
            malicious_probabilities(
                candidate_model,
                prompts,
            )
        )

        combined_probabilities = (
            combine_probabilities(
                production_probabilities,
                candidate_probabilities,
                candidate_weight,
            )
        )

        metrics = calculate_metrics(
            labels,
            combined_probabilities,
            threshold,
        )

        test_evaluations[dataset_name] = metrics

        print()
        print_metrics(
            dataset_name,
            metrics,
        )

    report = {
        "selection_policy": {
            "selection_data": [
                "neuralchemy_validation",
                "deepset_validation",
                "scambench_validation",
            ],
            "objective": (
                "maximum equal-source average "
                "balanced accuracy"
            ),
            "tie_breakers": [
                "higher average F1",
                "lower average false-positive rate",
            ],
            "minimum_source_recall": (
                MINIMUM_SOURCE_RECALL
            ),
        },
        "selected_configuration": selected,
        "test_evaluations": test_evaluations,
        "searched_configurations": (
            search_results
        ),
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
    evaluate_weighted_ensemble()