import json
import sys
from pathlib import Path


BASE_DIRECTORY = Path(__file__).resolve().parent

BACKEND_DIRECTORY = (
    BASE_DIRECTORY.parents[1]
)

if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIRECTORY),
    )


from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

from detector import analyze_prompt
from ml_detector import analyze_prompt_with_ml
from sensitive_detector import detect_sensitive_data


DATA_DIRECTORY = BASE_DIRECTORY / "data"

REPORT_DIRECTORY = BASE_DIRECTORY / "reports"

REPORT_PATH = (
    REPORT_DIRECTORY
    / "production_seed_baseline.json"
)

ACTION_ORDER = [
    "allow",
    "review",
    "redact",
    "block",
]


def load_records(
    dataset_path: Path,
) -> list[dict]:
    """Load a validated JSON Lines dataset."""
    records = []

    with dataset_path.open(
        "r",
        encoding="utf-8",
    ) as dataset_file:
        for line_number, raw_line in enumerate(
            dataset_file,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                raise RuntimeError(
                    f"{dataset_path.name}:"
                    f"{line_number}: blank line."
                )

            records.append(
                json.loads(line)
            )

    return records


def predict_production_action(
    prompt: str,
) -> dict:
    """Apply the current production decision priority."""
    rule_result = analyze_prompt(prompt)

    sensitive_result = detect_sensitive_data(
        prompt
    )

    ml_result = analyze_prompt_with_ml(
        prompt
    )

    if rule_result["is_malicious"]:
        action = "block"

    elif sensitive_result[
        "contains_sensitive_data"
    ]:
        action = "redact"

    elif ml_result["is_malicious"]:
        action = "review"

    else:
        action = "allow"

    return {
        "action": action,
        "rule_detected": rule_result[
            "is_malicious"
        ],
        "sensitive_detected": sensitive_result[
            "contains_sensitive_data"
        ],
        "ml_detected": ml_result[
            "is_malicious"
        ],
        "ml_probability": ml_result[
            "malicious_probability"
        ],
    }


def evaluate_records(
    records: list[dict],
) -> dict:
    """Evaluate production actions for records."""
    expected_actions = []
    predicted_actions = []
    decisions = []

    for index, record in enumerate(
        records,
        start=1,
    ):
        prediction = predict_production_action(
            record["prompt"]
        )

        expected_action = record["action"]
        predicted_action = prediction["action"]

        expected_actions.append(
            expected_action
        )

        predicted_actions.append(
            predicted_action
        )

        decisions.append(
            {
                "id": record["id"],
                "expected_action": (
                    expected_action
                ),
                "predicted_action": (
                    predicted_action
                ),
                "correct": (
                    expected_action
                    == predicted_action
                ),
                "rule_detected": prediction[
                    "rule_detected"
                ],
                "sensitive_detected": prediction[
                    "sensitive_detected"
                ],
                "ml_detected": prediction[
                    "ml_detected"
                ],
                "ml_probability": round(
                    float(
                        prediction[
                            "ml_probability"
                        ]
                    ),
                    6,
                ),
            }
        )

        if (
            index % 8 == 0
            or index == len(records)
        ):
            print(
                f"  Evaluated {index}/"
                f"{len(records)} records",
                flush=True,
            )

    report = classification_report(
        expected_actions,
        predicted_actions,
        labels=ACTION_ORDER,
        output_dict=True,
        zero_division=0,
    )

    return {
        "record_count": len(records),
        "accuracy": accuracy_score(
            expected_actions,
            predicted_actions,
        ),
        "balanced_accuracy": (
            balanced_accuracy_score(
                expected_actions,
                predicted_actions,
            )
        ),
        "macro_f1": f1_score(
            expected_actions,
            predicted_actions,
            labels=ACTION_ORDER,
            average="macro",
            zero_division=0,
        ),
        "classification_report": report,
        "confusion_matrix": {
            "labels": ACTION_ORDER,
            "values": confusion_matrix(
                expected_actions,
                predicted_actions,
                labels=ACTION_ORDER,
            ).tolist(),
        },
        "incorrect_decisions": [
            decision
            for decision in decisions
            if not decision["correct"]
        ],
        "decisions": decisions,
    }


def print_evaluation(
    name: str,
    evaluation: dict,
) -> None:
    """Print a compact evaluation summary."""
    print(name)

    print(
        "  Records: "
        f"{evaluation['record_count']}"
    )

    print(
        "  Accuracy: "
        f"{evaluation['accuracy']:.2%}"
    )

    print(
        "  Balanced accuracy: "
        f"{evaluation['balanced_accuracy']:.2%}"
    )

    print(
        "  Macro F1: "
        f"{evaluation['macro_f1']:.2%}"
    )

    print(
        "  Confusion matrix labels: "
        f"{evaluation['confusion_matrix']['labels']}"
    )

    print(
        "  Confusion matrix: "
        f"{evaluation['confusion_matrix']['values']}"
    )

    print(
        "  Incorrect decisions: "
        f"{len(evaluation['incorrect_decisions'])}"
    )


def main() -> None:
    """Evaluate the unchanged production pipeline."""
    print(
        "Loading contextual action seed datasets...",
        flush=True,
    )

    split_records = {
        split: load_records(
            DATA_DIRECTORY / f"{split}.jsonl"
        )
        for split in [
            "train",
            "validation",
            "test",
        ]
    }

    evaluations = {}

    for split, records in split_records.items():
        print(
            f"Evaluating {split} split...",
            flush=True,
        )

        evaluations[split] = evaluate_records(
            records
        )

    combined_records = []

    for records in split_records.values():
        combined_records.extend(records)

    print(
        "Evaluating combined dataset...",
        flush=True,
    )

    evaluations["combined"] = (
        evaluate_records(
            combined_records
        )
    )

    report = {
        "model": (
            "current_production_hybrid_pipeline"
        ),
        "dataset": (
            "contextual_action_seed_v1"
        ),
        "action_order": ACTION_ORDER,
        "evaluations": evaluations,
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
    print(
        "Production baseline evaluation completed."
    )
    print()

    for split in [
        "train",
        "validation",
        "test",
        "combined",
    ]:
        print_evaluation(
            split,
            evaluations[split],
        )

        print()

    print(
        f"Report saved to: {REPORT_PATH}"
    )


if __name__ == "__main__":
    main()