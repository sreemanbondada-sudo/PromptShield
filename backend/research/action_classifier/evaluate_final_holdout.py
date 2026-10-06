"""Run the one-time final contextual holdout evaluation."""

import json
from pathlib import Path

import joblib

from evaluate_challenge import (
    build_disagreements,
    evaluate_candidate,
    load_jsonl,
    print_summary,
)
from evaluate_production_baseline import (
    evaluate_records,
)


BASE_DIRECTORY = Path(__file__).resolve().parent

FINAL_HOLDOUT_PATH = (
    BASE_DIRECTORY
    / "data"
    / "final_holdout.jsonl"
)

MODEL_PATH = (
    BASE_DIRECTORY
    / "models"
    / "contextual_action_candidate_iteration2.joblib"
)

REPORT_PATH = (
    BASE_DIRECTORY
    / "reports"
    / "final_holdout_evaluation.json"
)


PROMOTION_THRESHOLDS = {
    "macro_f1": 0.80,
    "allow_recall": 0.80,
    "review_recall": 0.70,
    "redact_recall": 0.90,
    "block_recall": 0.85,
    "macro_f1_gain": 0.25,
    "maximum_false_blocks": 2,
}


def count_false_blocks(
    result: dict,
) -> int:
    """Count non-Block prompts predicted as Block."""
    return sum(
        decision["expected_action"] != "block"
        and decision["predicted_action"] == "block"
        for decision in result["decisions"]
    )


def evaluate_promotion_gates(
    production: dict,
    candidate: dict,
) -> dict:
    """Evaluate conservative integration gates."""
    candidate_report = candidate[
        "classification_report"
    ]

    macro_f1_gain = (
        candidate["macro_f1"]
        - production["macro_f1"]
    )

    false_blocks = count_false_blocks(
        candidate
    )

    checks = {
        "macro_f1": {
            "value": candidate["macro_f1"],
            "threshold": (
                PROMOTION_THRESHOLDS[
                    "macro_f1"
                ]
            ),
            "passed": (
                candidate["macro_f1"]
                >= PROMOTION_THRESHOLDS[
                    "macro_f1"
                ]
            ),
        },
        "allow_recall": {
            "value": (
                candidate_report["allow"][
                    "recall"
                ]
            ),
            "threshold": (
                PROMOTION_THRESHOLDS[
                    "allow_recall"
                ]
            ),
            "passed": (
                candidate_report["allow"][
                    "recall"
                ]
                >= PROMOTION_THRESHOLDS[
                    "allow_recall"
                ]
            ),
        },
        "review_recall": {
            "value": (
                candidate_report["review"][
                    "recall"
                ]
            ),
            "threshold": (
                PROMOTION_THRESHOLDS[
                    "review_recall"
                ]
            ),
            "passed": (
                candidate_report["review"][
                    "recall"
                ]
                >= PROMOTION_THRESHOLDS[
                    "review_recall"
                ]
            ),
        },
        "redact_recall": {
            "value": (
                candidate_report["redact"][
                    "recall"
                ]
            ),
            "threshold": (
                PROMOTION_THRESHOLDS[
                    "redact_recall"
                ]
            ),
            "passed": (
                candidate_report["redact"][
                    "recall"
                ]
                >= PROMOTION_THRESHOLDS[
                    "redact_recall"
                ]
            ),
        },
        "block_recall": {
            "value": (
                candidate_report["block"][
                    "recall"
                ]
            ),
            "threshold": (
                PROMOTION_THRESHOLDS[
                    "block_recall"
                ]
            ),
            "passed": (
                candidate_report["block"][
                    "recall"
                ]
                >= PROMOTION_THRESHOLDS[
                    "block_recall"
                ]
            ),
        },
        "macro_f1_gain": {
            "value": macro_f1_gain,
            "threshold": (
                PROMOTION_THRESHOLDS[
                    "macro_f1_gain"
                ]
            ),
            "passed": (
                macro_f1_gain
                >= PROMOTION_THRESHOLDS[
                    "macro_f1_gain"
                ]
            ),
        },
        "false_blocks": {
            "value": false_blocks,
            "threshold": (
                PROMOTION_THRESHOLDS[
                    "maximum_false_blocks"
                ]
            ),
            "passed": (
                false_blocks
                <= PROMOTION_THRESHOLDS[
                    "maximum_false_blocks"
                ]
            ),
        },
    }

    promotion_passed = all(
        check["passed"]
        for check in checks.values()
    )

    return {
        "passed": promotion_passed,
        "checks": checks,
    }


def print_promotion_result(
    promotion: dict,
) -> None:
    """Print each final promotion gate."""
    print("Promotion gates")
    print("---------------")

    for name, check in (
        promotion["checks"].items()
    ):
        status = (
            "PASS"
            if check["passed"]
            else "FAIL"
        )

        value = check["value"]
        threshold = check["threshold"]

        if name == "false_blocks":
            print(
                f"{name}: {value} "
                f"(maximum {threshold}) "
                f"[{status}]"
            )

        else:
            print(
                f"{name}: {value:.2%} "
                f"(minimum {threshold:.2%}) "
                f"[{status}]"
            )

    print()

    if promotion["passed"]:
        print(
            "FINAL RESULT: PASS FOR CONTROLLED "
            "INTEGRATION TESTING"
        )

    else:
        print(
            "FINAL RESULT: DO NOT INTEGRATE YET"
        )


def main() -> None:
    """Run the final evaluation exactly once."""
    if REPORT_PATH.exists():
        raise RuntimeError(
            "The final holdout report already exists. "
            "Do not rerun or overwrite the one-time "
            "evaluation."
        )

    print(
        "Loading untouched final holdout..."
    )

    records = load_jsonl(
        FINAL_HOLDOUT_PATH
    )

    if len(records) != 40:
        raise RuntimeError(
            "Expected 40 final holdout records, "
            f"received {len(records)}."
        )

    print(f"Loaded {len(records)} records.")
    print()

    print(
        "Evaluating production pipeline..."
    )

    production_result = evaluate_records(
        records
    )

    print()
    print(
        "Evaluating preserved iteration-two "
        "candidate..."
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

    promotion = evaluate_promotion_gates(
        production=production_result,
        candidate=candidate_result,
    )

    print_promotion_result(promotion)

    disagreements = build_disagreements(
        production_result,
        candidate_result,
    )

    report = {
        "dataset": (
            "final_contextual_holdout_v1"
        ),
        "record_count": len(records),
        "candidate_name": (
            artifact["model_name"]
        ),
        "model_path": str(MODEL_PATH),
        "production": production_result,
        "candidate": candidate_result,
        "candidate_macro_f1_gain": float(
            candidate_result["macro_f1"]
            - production_result["macro_f1"]
        ),
        "promotion": promotion,
        "disagreements": disagreements,
    }

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "x",
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

    print()
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()