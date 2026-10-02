import csv
import json
from pathlib import Path

import joblib
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from model_pipeline import create_pipeline
from prepare_external_datasets import (
    calculate_prompt_hash,
)


BASE_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = BASE_DIRECTORY / "data"
EXTERNAL_DIRECTORY = DATA_DIRECTORY / "external"
MODEL_DIRECTORY = BASE_DIRECTORY / "models"

LOCAL_TRAINING_PATH = (
    DATA_DIRECTORY / "prompts.csv"
)

HARD_NEGATIVE_PATH = (
    DATA_DIRECTORY / "hard_negative_prompts.csv"
)

NEURALCHEMY_TRAIN_PATH = (
    EXTERNAL_DIRECTORY
    / "neuralchemy_core_train.csv"
)

NEURALCHEMY_VALIDATION_PATH = (
    EXTERNAL_DIRECTORY
    / "neuralchemy_core_validation.csv"
)

NEURALCHEMY_TEST_PATH = (
    EXTERNAL_DIRECTORY
    / "neuralchemy_core_test.csv"
)

DEEPSET_TRAIN_PATH = (
    EXTERNAL_DIRECTORY / "deepset_train.csv"
)

DEEPSET_TEST_PATH = (
    EXTERNAL_DIRECTORY / "deepset_test.csv"
)

MODEL_PATH = (
    MODEL_DIRECTORY
    / "prompt_classifier.joblib"
)

METRICS_PATH = (
    MODEL_DIRECTORY / "metrics.json"
)

THRESHOLDS = [
    round(value / 100, 2)
    for value in range(30, 81, 5)
]


def load_prompt_label_csv(
    dataset_path: Path,
) -> tuple[list[str], list[int]]:
    """Load prompt text and binary labels."""
    prompts = []
    labels = []

    with dataset_path.open(
        encoding="utf-8",
        newline="",
    ) as dataset_file:
        reader = csv.DictReader(dataset_file)

        for row in reader:
            prompt = row["prompt"].strip()
            label = int(row["label"])

            if not prompt:
                raise RuntimeError(
                    f"{dataset_path.name} contains "
                    "an empty prompt."
                )

            if label not in {0, 1}:
                raise RuntimeError(
                    f"{dataset_path.name} contains "
                    "a non-binary label."
                )

            prompts.append(prompt)
            labels.append(label)

    return prompts, labels


def deduplicate_training_data(
    prompt_sets: list[
        tuple[list[str], list[int]]
    ],
) -> tuple[list[str], list[int], int]:
    """Combine and deduplicate training sources."""
    prompts = []
    labels = []
    seen_hashes = set()
    removed_duplicates = 0

    for source_prompts, source_labels in prompt_sets:
        for prompt, label in zip(
            source_prompts,
            source_labels,
            strict=True,
        ):
            prompt_hash = calculate_prompt_hash(
                prompt
            )

            if prompt_hash in seen_hashes:
                removed_duplicates += 1
                continue

            seen_hashes.add(prompt_hash)
            prompts.append(prompt)
            labels.append(label)

    return prompts, labels, removed_duplicates


def verify_no_evaluation_leakage(
    training_prompts: list[str],
    evaluation_sets: dict[
        str,
        tuple[list[str], list[int]],
    ],
) -> None:
    """Reject exact train/evaluation overlap."""
    training_hashes = {
        calculate_prompt_hash(prompt)
        for prompt in training_prompts
    }

    for dataset_name, (
        evaluation_prompts,
        _,
    ) in evaluation_sets.items():
        evaluation_hashes = {
            calculate_prompt_hash(prompt)
            for prompt in evaluation_prompts
        }

        overlap = (
            training_hashes
            & evaluation_hashes
        )

        if overlap:
            raise RuntimeError(
                f"Detected {len(overlap)} prompt "
                f"overlaps between training data "
                f"and {dataset_name}."
            )


def malicious_probabilities(
    model,
    prompts: list[str],
) -> list[float]:
    """Return malicious-class probabilities."""
    probabilities = model.predict_proba(
        prompts
    )

    malicious_class_index = list(
        model.classes_
    ).index(1)

    return [
        float(row[malicious_class_index])
        for row in probabilities
    ]


def evaluate_probabilities(
    labels: list[int],
    probabilities: list[float],
    threshold: float,
) -> dict:
    """Calculate metrics for one threshold."""
    predictions = [
        int(probability >= threshold)
        for probability in probabilities
    ]

    return {
        "threshold": threshold,
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
        "roc_auc": roc_auc_score(
            labels,
            probabilities,
        ),
        "confusion_matrix": confusion_matrix(
            labels,
            predictions,
        ).tolist(),
        "classification_report": (
            classification_report(
                labels,
                predictions,
                target_names=[
                    "safe",
                    "malicious",
                ],
                output_dict=True,
                zero_division=0,
            )
        ),
    }


def select_threshold(
    validation_sets: dict[
        str,
        tuple[list[int], list[float]],
    ],
) -> tuple[float, list[dict]]:
    """
    Select a threshold across validation sources.

    Each validation source contributes equally.
    """
    threshold_results = []

    for threshold in THRESHOLDS:
        dataset_results = {}

        for dataset_name, (
            labels,
            probabilities,
        ) in validation_sets.items():
            dataset_results[dataset_name] = (
                evaluate_probabilities(
                    labels,
                    probabilities,
                    threshold,
                )
            )

        average_f1 = sum(
            result["f1_score"]
            for result in dataset_results.values()
        ) / len(dataset_results)

        average_recall = sum(
            result["recall"]
            for result in dataset_results.values()
        ) / len(dataset_results)

        minimum_recall = min(
            result["recall"]
            for result in dataset_results.values()
        )

        average_accuracy = sum(
            result["accuracy"]
            for result in dataset_results.values()
        ) / len(dataset_results)

        threshold_results.append(
            {
                "threshold": threshold,
                "average_f1": average_f1,
                "average_recall": average_recall,
                "minimum_recall": minimum_recall,
                "average_accuracy": average_accuracy,
                "datasets": dataset_results,
            }
        )

    best_result = max(
        threshold_results,
        key=lambda result: (
            result["average_f1"],
            result["minimum_recall"],
            result["average_recall"],
            result["average_accuracy"],
        ),
    )

    return (
        best_result["threshold"],
        threshold_results,
    )


def print_evaluation(
    name: str,
    metrics: dict,
) -> None:
    """Print a compact evaluation summary."""
    print()
    print(name)

    print(
        f"  Accuracy: "
        f"{metrics['accuracy']:.2%}"
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
        f"  ROC-AUC: "
        f"{metrics['roc_auc']:.4f}"
    )

    print(
        "  Confusion matrix: "
        f"{metrics['confusion_matrix']}"
    )


def train_expanded_model() -> None:
    """Train and evaluate the expanded production model."""
    local_training = load_prompt_label_csv(
        LOCAL_TRAINING_PATH
    )

    hard_negative_training = (
        load_prompt_label_csv(
            HARD_NEGATIVE_PATH
        )
    )

    neuralchemy_training = (
        load_prompt_label_csv(
            NEURALCHEMY_TRAIN_PATH
        )
    )

    deepset_full_training = (
        load_prompt_label_csv(
            DEEPSET_TRAIN_PATH
        )
    )

    (
        deepset_training_prompts,
        deepset_validation_prompts,
        deepset_training_labels,
        deepset_validation_labels,
    ) = train_test_split(
        deepset_full_training[0],
        deepset_full_training[1],
        test_size=0.20,
        random_state=42,
        stratify=deepset_full_training[1],
    )

    deepset_training = (
        deepset_training_prompts,
        deepset_training_labels,
    )

    evaluation_sets = {
        "neuralchemy_validation": (
            load_prompt_label_csv(
                NEURALCHEMY_VALIDATION_PATH
            )
        ),
        "deepset_validation": (
            deepset_validation_prompts,
            deepset_validation_labels,
        ),
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
    }

    (
        training_prompts,
        training_labels,
        removed_duplicates,
    ) = deduplicate_training_data(
        [
            neuralchemy_training,
            deepset_training,
            local_training,
            hard_negative_training,
        ]
    )

    verify_no_evaluation_leakage(
        training_prompts,
        evaluation_sets,
    )

    model = create_pipeline()

    print(
        "Training expanded production model..."
    )

    model.fit(
        training_prompts,
        training_labels,
    )

    validation_probability_sets = {}

    for dataset_name in [
        "neuralchemy_validation",
        "deepset_validation",
    ]:
        prompts, labels = evaluation_sets[
            dataset_name
        ]

        probabilities = malicious_probabilities(
            model,
            prompts,
        )

        validation_probability_sets[
            dataset_name
        ] = (
            labels,
            probabilities,
        )

    (
        selected_threshold,
        threshold_results,
    ) = select_threshold(
        validation_probability_sets
    )

    evaluations = {}

    for dataset_name, (
        prompts,
        labels,
    ) in evaluation_sets.items():
        probabilities = malicious_probabilities(
            model,
            prompts,
        )

        evaluations[dataset_name] = (
            evaluate_probabilities(
                labels,
                probabilities,
                selected_threshold,
            )
        )

    metrics = {
        "model_version": (
            "expanded-v4-hard-negatives"
        ),
        "model_type": (
            "TF-IDF Logistic Regression"
        ),
        "training_sources": {
            "neuralchemy_train": len(
                neuralchemy_training[0]
            ),
            "deepset_train_partition": len(
                deepset_training_prompts
            ),
            "promptshield_baseline": len(
                local_training[0]
            ),
            "promptshield_hard_negatives": len(
                hard_negative_training[0]
            ),
        },
        "validation_sources": {
            "neuralchemy_validation": len(
                evaluation_sets[
                    "neuralchemy_validation"
                ][0]
            ),
            "deepset_validation_partition": len(
                deepset_validation_prompts
            ),
        },
        "combined_training_size": len(
            training_prompts
        ),
        "removed_training_duplicates": (
            removed_duplicates
        ),
        "selected_threshold": (
            selected_threshold
        ),
        "threshold_selection_method": (
            "equal-source average validation F1"
        ),
        "threshold_results": (
            threshold_results
        ),
        "evaluations": evaluations,
    }

    MODEL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    METRICS_PATH.write_text(
        json.dumps(
            metrics,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()

    print(
        f"Combined training samples: "
        f"{len(training_prompts)}"
    )

    print(
        f"Reserved deepset validation samples: "
        f"{len(deepset_validation_prompts)}"
    )

    print(
        f"Removed training duplicates: "
        f"{removed_duplicates}"
    )

    print(
        f"Selected threshold: "
        f"{selected_threshold:.2f}"
    )

    for dataset_name, evaluation in (
        evaluations.items()
    ):
        print_evaluation(
            dataset_name,
            evaluation,
        )

    print()

    print(
        f"Model saved to: {MODEL_PATH}"
    )

    print(
        f"Metrics saved to: {METRICS_PATH}"
    )


if __name__ == "__main__":
    train_expanded_model()
    