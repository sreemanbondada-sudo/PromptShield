import json
from pathlib import Path

import joblib

from train_expanded_model import (
    DEEPSET_TEST_PATH,
    NEURALCHEMY_TEST_PATH,
    evaluate_probabilities,
    load_prompt_label_csv,
    malicious_probabilities,
    print_evaluation,
)


BASE_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = BASE_DIRECTORY / "data"
EXTERNAL_DIRECTORY = DATA_DIRECTORY / "external"
MODEL_DIRECTORY = BASE_DIRECTORY / "models"

MODEL_PATH = (
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
    / "scambench_candidate_threshold_060_metrics.json"
)

SELECTED_THRESHOLD = 0.60


def evaluate_candidate() -> None:
    """Evaluate the candidate at the validation-selected threshold."""
    if not MODEL_PATH.exists():
        raise RuntimeError(
            "ScamBench candidate model not found. "
            "Run python train_scambench_candidate.py first."
        )

    model = joblib.load(MODEL_PATH)

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

    print(
        "Evaluating ScamBench candidate at "
        f"threshold {SELECTED_THRESHOLD:.2f}..."
    )

    for dataset_name, (
        prompts,
        labels,
    ) in evaluation_sets.items():
        probabilities = malicious_probabilities(
            model,
            prompts,
        )

        metrics = evaluate_probabilities(
            labels,
            probabilities,
            SELECTED_THRESHOLD,
        )

        evaluations[dataset_name] = metrics

        print_evaluation(
            dataset_name,
            metrics,
        )

    report = {
        "model": MODEL_PATH.name,
        "threshold": SELECTED_THRESHOLD,
        "threshold_selection_basis": (
            "Highest average validation accuracy "
            "among evaluated thresholds"
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
    print(f"Metrics saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    evaluate_candidate()