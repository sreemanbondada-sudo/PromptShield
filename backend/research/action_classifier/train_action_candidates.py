"""Train and compare four contextual action classifiers."""

import json
import time
from pathlib import Path

import joblib

from sklearn.calibration import (
    CalibratedClassifierCV,
)
from sklearn.feature_extraction.text import (
    TfidfVectorizer,
)
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import (
    FeatureUnion,
    Pipeline,
)
from sklearn.linear_model import (
    LogisticRegression,
)
from sklearn.svm import LinearSVC


BASE_DIRECTORY = Path(__file__).resolve().parent
DATA_DIRECTORY = BASE_DIRECTORY / "data"
REPORT_DIRECTORY = BASE_DIRECTORY / "reports"
MODEL_DIRECTORY = BASE_DIRECTORY / "models"

ACTION_ORDER = [
    "allow",
    "review",
    "redact",
    "block",
]

DATASET_PATHS = {
    "train": DATA_DIRECTORY / "train.jsonl",
    "validation": (
        DATA_DIRECTORY / "validation.jsonl"
    ),
    "test": DATA_DIRECTORY / "test.jsonl",
}

REPORT_PATH = (
    REPORT_DIRECTORY
    / "four_class_candidate_evaluation.json"
)

MODEL_PATH = (
    MODEL_DIRECTORY
    / "contextual_action_candidate.joblib"
)


def load_jsonl(path: Path) -> list[dict]:
    """Load one JSON Lines dataset."""
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


def split_features_and_labels(
    records: list[dict],
) -> tuple[list[str], list[str]]:
    """Extract prompts and action labels."""
    prompts = [
        record["prompt"]
        for record in records
    ]

    labels = [
        record["action"]
        for record in records
    ]

    return prompts, labels


def build_word_logistic() -> Pipeline:
    """Build word TF-IDF with Logistic Regression."""
    return Pipeline(
        [
            (
                "features",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.98,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=4.0,
                    class_weight="balanced",
                    max_iter=3000,
                    random_state=42,
                ),
            ),
        ]
    )


def build_character_logistic() -> Pipeline:
    """Build character TF-IDF with Logistic Regression."""
    return Pipeline(
        [
            (
                "features",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=1,
                    max_df=1.0,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=4.0,
                    class_weight="balanced",
                    max_iter=3000,
                    random_state=42,
                ),
            ),
        ]
    )


def build_combined_features() -> FeatureUnion:
    """Build combined word and character features."""
    return FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.98,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "character",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=1,
                    max_df=1.0,
                    sublinear_tf=True,
                ),
            ),
        ]
    )


def build_combined_logistic() -> Pipeline:
    """Build combined TF-IDF with Logistic Regression."""
    return Pipeline(
        [
            (
                "features",
                build_combined_features(),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=4.0,
                    class_weight="balanced",
                    max_iter=3000,
                    random_state=42,
                ),
            ),
        ]
    )


def build_combined_calibrated_svm() -> Pipeline:
    """Build combined TF-IDF with calibrated Linear SVM."""
    return Pipeline(
        [
            (
                "features",
                build_combined_features(),
            ),
            (
                "classifier",
                CalibratedClassifierCV(
                    estimator=LinearSVC(
                        C=1.5,
                        class_weight="balanced",
                        random_state=42,
                    ),
                    method="sigmoid",
                    cv=3,
                ),
            ),
        ]
    )


def evaluate_model(
    model,
    prompts: list[str],
    expected_labels: list[str],
) -> dict:
    """Evaluate one fitted classifier."""
    predictions = model.predict(prompts)

    report = classification_report(
        expected_labels,
        predictions,
        labels=ACTION_ORDER,
        target_names=ACTION_ORDER,
        output_dict=True,
        zero_division=0,
    )

    incorrect_decisions = []

    for index, (
        prompt,
        expected,
        predicted,
    ) in enumerate(
        zip(
            prompts,
            expected_labels,
            predictions,
            strict=True,
        ),
        start=1,
    ):
        if expected != predicted:
            incorrect_decisions.append(
                {
                    "record_position": index,
                    "expected_action": expected,
                    "predicted_action": (
                        str(predicted)
                    ),
                    "prompt": prompt,
                }
            )

    return {
        "record_count": len(expected_labels),
        "accuracy": float(
            accuracy_score(
                expected_labels,
                predictions,
            )
        ),
        "balanced_accuracy": float(
            balanced_accuracy_score(
                expected_labels,
                predictions,
            )
        ),
        "macro_f1": float(
            f1_score(
                expected_labels,
                predictions,
                labels=ACTION_ORDER,
                average="macro",
                zero_division=0,
            )
        ),
        "classification_report": report,
        "confusion_matrix": {
            "labels": ACTION_ORDER,
            "values": confusion_matrix(
                expected_labels,
                predictions,
                labels=ACTION_ORDER,
            ).tolist(),
        },
        "incorrect_decisions": (
            incorrect_decisions
        ),
    }


def selection_key(
    candidate_result: dict,
) -> tuple:
    """Return validation-focused model ranking values."""
    validation = candidate_result[
        "validation"
    ]

    report = validation[
        "classification_report"
    ]

    return (
        validation["macro_f1"],
        report["block"]["recall"],
        report["redact"]["recall"],
        validation["balanced_accuracy"],
        validation["accuracy"],
    )


def print_evaluation(
    label: str,
    evaluation: dict,
) -> None:
    """Print a compact evaluation summary."""
    report = evaluation[
        "classification_report"
    ]

    print(f"  {label}")
    print(
        "    Accuracy: "
        f"{evaluation['accuracy']:.2%}"
    )
    print(
        "    Balanced accuracy: "
        f"{evaluation['balanced_accuracy']:.2%}"
    )
    print(
        "    Macro F1: "
        f"{evaluation['macro_f1']:.2%}"
    )
    print(
        "    Allow recall: "
        f"{report['allow']['recall']:.2%}"
    )
    print(
        "    Review recall: "
        f"{report['review']['recall']:.2%}"
    )
    print(
        "    Redact recall: "
        f"{report['redact']['recall']:.2%}"
    )
    print(
        "    Block recall: "
        f"{report['block']['recall']:.2%}"
    )
    print(
        "    Incorrect decisions: "
        f"{len(evaluation['incorrect_decisions'])}"
    )


def main() -> None:
    """Train, select and evaluate candidate models."""
    print(
        "Loading contextual action datasets..."
    )

    datasets = {
        split: load_jsonl(path)
        for split, path in DATASET_PATHS.items()
    }

    train_prompts, train_labels = (
        split_features_and_labels(
            datasets["train"]
        )
    )

    validation_prompts, validation_labels = (
        split_features_and_labels(
            datasets["validation"]
        )
    )

    test_prompts, test_labels = (
        split_features_and_labels(
            datasets["test"]
        )
    )

    print(
        f"Training records: {len(train_prompts)}"
    )
    print(
        "Validation records: "
        f"{len(validation_prompts)}"
    )
    print(
        f"Test records: {len(test_prompts)}"
    )
    print()

    candidate_builders = {
        "word_logistic": (
            build_word_logistic
        ),
        "character_logistic": (
            build_character_logistic
        ),
        "combined_logistic": (
            build_combined_logistic
        ),
        "combined_calibrated_svm": (
            build_combined_calibrated_svm
        ),
    }

    fitted_models = {}
    candidate_results = {}

    for candidate_name, builder in (
        candidate_builders.items()
    ):
        print(
            f"Training {candidate_name}..."
        )

        started_at = time.perf_counter()
        model = builder()

        model.fit(
            train_prompts,
            train_labels,
        )

        training_seconds = (
            time.perf_counter() - started_at
        )

        train_evaluation = evaluate_model(
            model,
            train_prompts,
            train_labels,
        )

        validation_evaluation = evaluate_model(
            model,
            validation_prompts,
            validation_labels,
        )

        candidate_results[candidate_name] = {
            "training_seconds": (
                training_seconds
            ),
            "train": train_evaluation,
            "validation": (
                validation_evaluation
            ),
        }

        fitted_models[candidate_name] = model

        print(
            "  Training time: "
            f"{training_seconds:.2f} seconds"
        )

        print_evaluation(
            "Validation results",
            validation_evaluation,
        )

        print()

    selected_name = max(
        candidate_results,
        key=lambda name: selection_key(
            candidate_results[name]
        ),
    )

    selected_model = fitted_models[
        selected_name
    ]

    print(
        "Selected candidate using validation "
        f"metrics: {selected_name}"
    )
    print()

    test_evaluation = evaluate_model(
        selected_model,
        test_prompts,
        test_labels,
    )

    print_evaluation(
        "Held-out test results",
        test_evaluation,
    )

    selected_validation = (
        candidate_results[selected_name][
            "validation"
        ]
    )

    report = {
        "dataset": (
            "contextual_action_dataset_v1"
        ),
        "selection_policy": [
            "validation_macro_f1",
            "validation_block_recall",
            "validation_redact_recall",
            "validation_balanced_accuracy",
            "validation_accuracy",
        ],
        "action_order": ACTION_ORDER,
        "candidate_results": (
            candidate_results
        ),
        "selected_candidate": selected_name,
        "selected_validation": (
            selected_validation
        ),
        "selected_test": test_evaluation,
    }

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            report,
            output_file,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )

        output_file.write("\n")

    MODEL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        {
            "model": selected_model,
            "model_name": selected_name,
            "action_order": ACTION_ORDER,
            "dataset": (
                "contextual_action_dataset_v1"
            ),
            "validation_macro_f1": (
                selected_validation[
                    "macro_f1"
                ]
            ),
            "test_macro_f1": (
                test_evaluation["macro_f1"]
            ),
        },
        MODEL_PATH,
    )

    print()
    print(f"Report saved to: {REPORT_PATH}")
    print(f"Candidate saved to: {MODEL_PATH}")


if __name__ == "__main__":
    main()