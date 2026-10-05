"""Compare production and candidate action decisions."""

import json
from pathlib import Path

import joblib

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

from evaluate_production_baseline import (
    ACTION_ORDER,
    evaluate_records,
)


BASE_DIRECTORY = Path(__file__).resolve().parent

CHALLENGE_PATH = (
    BASE_DIRECTORY
    / "data"
    / "challenge.jsonl"
)

MODEL_PATH = (
    BASE_DIRECTORY
    / "models"
    / "contextual_action_candidate.joblib"
)

REPORT_PATH = (
    BASE_DIRECTORY
    / "reports"
    / "challenge_comparison.json"
)


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
                records.append(
                    json.loads(stripped_line)
                )

            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Invalid JSON in {path} "
                    f"at line {line_number}."
                ) from error

    if not records:
        raise RuntimeError(
            f"No records were loaded from {path}."
        )

    return records


def evaluate_candidate(
    model,
    records: list[dict],
) -> dict:
    """Evaluate the contextual candidate model."""
    prompts = [
        record["prompt"]
        for record in records
    ]

    expected_actions = [
        record["action"]
        for record in records
    ]

    predictions = model.predict(prompts)

    if hasattr(model, "predict_proba"):
        probability_rows = model.predict_proba(
            prompts
        )

        model_classes = [
            str(value)
            for value in model.classes_
        ]

    else:
        probability_rows = [
            None
            for _ in prompts
        ]

        model_classes = []

    decisions = []

    for (
        record,
        expected_action,
        predicted_action,
        probability_row,
    ) in zip(
        records,
        expected_actions,
        predictions,
        probability_rows,
        strict=True,
    ):
        predicted_action = str(
            predicted_action
        )

        probabilities = {}

        if probability_row is not None:
            probabilities = {
                action: round(
                    float(probability),
                    6,
                )
                for action, probability in zip(
                    model_classes,
                    probability_row,
                    strict=True,
                )
            }

        decisions.append(
            {
                "id": record["id"],
                "prompt": record["prompt"],
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
                "probabilities": probabilities,
            }
        )

    predicted_actions = [
        decision["predicted_action"]
        for decision in decisions
    ]

    report = classification_report(
        expected_actions,
        predicted_actions,
        labels=ACTION_ORDER,
        output_dict=True,
        zero_division=0,
    )

    return {
        "record_count": len(records),
        "accuracy": float(
            accuracy_score(
                expected_actions,
                predicted_actions,
            )
        ),
        "balanced_accuracy": float(
            balanced_accuracy_score(
                expected_actions,
                predicted_actions,
            )
        ),
        "macro_f1": float(
            f1_score(
                expected_actions,
                predicted_actions,
                labels=ACTION_ORDER,
                average="macro",
                zero_division=0,
            )
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


def print_summary(
    name: str,
    result: dict,
) -> None:
    """Print the most important metrics."""
    report = result[
        "classification_report"
    ]

    print(name)
    print("-" * len(name))

    print(
        f"Records: {result['record_count']}"
    )

    print(
        "Accuracy: "
        f"{result['accuracy']:.2%}"
    )

    print(
        "Balanced accuracy: "
        f"{result['balanced_accuracy']:.2%}"
    )

    print(
        "Macro F1: "
        f"{result['macro_f1']:.2%}"
    )

    for action in ACTION_ORDER:
        print(
            f"{action.title()} recall: "
            f"{report[action]['recall']:.2%}"
        )

    print(
        "Incorrect decisions: "
        f"{len(result['incorrect_decisions'])}"
    )

    print(
        "Confusion matrix: "
        f"{result['confusion_matrix']['values']}"
    )

    print()


def build_disagreements(
    production_result: dict,
    candidate_result: dict,
) -> list[dict]:
    """Record cases where the systems disagree."""
    production_by_id = {
        decision["id"]: decision
        for decision in production_result[
            "decisions"
        ]
    }

    candidate_by_id = {
        decision["id"]: decision
        for decision in candidate_result[
            "decisions"
        ]
    }

    disagreements = []

    for record_id, candidate_decision in (
        candidate_by_id.items()
    ):
        production_decision = (
            production_by_id[record_id]
        )

        if (
            production_decision[
                "predicted_action"
            ]
            == candidate_decision[
                "predicted_action"
            ]
        ):
            continue

        disagreements.append(
            {
                "id": record_id,
                "prompt": candidate_decision[
                    "prompt"
                ],
                "expected_action": (
                    candidate_decision[
                        "expected_action"
                    ]
                ),
                "production_action": (
                    production_decision[
                        "predicted_action"
                    ]
                ),
                "candidate_action": (
                    candidate_decision[
                        "predicted_action"
                    ]
                ),
                "production_correct": (
                    production_decision[
                        "correct"
                    ]
                ),
                "candidate_correct": (
                    candidate_decision[
                        "correct"
                    ]
                ),
                "candidate_probabilities": (
                    candidate_decision[
                        "probabilities"
                    ]
                ),
            }
        )

    return disagreements


def main() -> None:
    """Run the unseen challenge comparison."""
    print(
        "Loading manual challenge dataset..."
    )

    records = load_jsonl(
        CHALLENGE_PATH
    )

    print(
        f"Loaded {len(records)} records."
    )
    print()

    print(
        "Evaluating current production pipeline..."
    )

    production_result = evaluate_records(
        records
    )

    print()
    print(
        "Loading selected contextual candidate..."
    )

    artifact = joblib.load(MODEL_PATH)
    model = artifact["model"]

    candidate_result = evaluate_candidate(
        model,
        records,
    )

    print()
    print_summary(
        "Current production pipeline",
        production_result,
    )

    print_summary(
        (
            "Contextual candidate "
            f"({artifact['model_name']})"
        ),
        candidate_result,
    )

    disagreements = build_disagreements(
        production_result,
        candidate_result,
    )

    production_macro_f1_gain = (
        candidate_result["macro_f1"]
        - production_result["macro_f1"]
    )

    report = {
        "dataset": (
            "manual_contextual_challenge_v1"
        ),
        "record_count": len(records),
        "candidate_name": (
            artifact["model_name"]
        ),
        "production": production_result,
        "candidate": candidate_result,
        "candidate_macro_f1_gain": float(
            production_macro_f1_gain
        ),
        "disagreements": disagreements,
    }

    REPORT_PATH.parent.mkdir(
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

    print(
        "Candidate macro-F1 change: "
        f"{production_macro_f1_gain:+.2%}"
    )

    print(
        "System disagreements: "
        f"{len(disagreements)}"
    )

    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()