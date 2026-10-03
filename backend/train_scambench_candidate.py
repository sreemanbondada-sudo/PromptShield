import json
from pathlib import Path

import joblib
from sklearn.model_selection import train_test_split

from model_pipeline import create_pipeline
from train_expanded_model import (
    DEEPSET_TEST_PATH,
    DEEPSET_TRAIN_PATH,
    HARD_NEGATIVE_PATH,
    LOCAL_TRAINING_PATH,
    NEURALCHEMY_TEST_PATH,
    NEURALCHEMY_TRAIN_PATH,
    NEURALCHEMY_VALIDATION_PATH,
    deduplicate_training_data,
    evaluate_probabilities,
    load_prompt_label_csv,
    malicious_probabilities,
    print_evaluation,
    select_threshold,
    verify_no_evaluation_leakage,
)


BASE_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = BASE_DIRECTORY / "data"
EXTERNAL_DIRECTORY = DATA_DIRECTORY / "external"
MODEL_DIRECTORY = BASE_DIRECTORY / "models"

SCAMBENCH_TRAIN_PATH = (
    EXTERNAL_DIRECTORY / "scambench_train.csv"
)

SCAMBENCH_VALIDATION_PATH = (
    EXTERNAL_DIRECTORY / "scambench_validation.csv"
)

SCAMBENCH_TEST_PATH = (
    EXTERNAL_DIRECTORY / "scambench_test.csv"
)

PROMPTSHIELD_CHALLENGE_PATH = (
    DATA_DIRECTORY / "challenge_prompts.csv"
)

CANDIDATE_MODEL_PATH = (
    MODEL_DIRECTORY
    / "scambench_candidate_classifier.joblib"
)

CANDIDATE_METRICS_PATH = (
    MODEL_DIRECTORY
    / "scambench_candidate_metrics.json"
)


def train_scambench_candidate() -> None:
    """Train an isolated ScamBench candidate model."""
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

    scambench_training = (
        load_prompt_label_csv(
            SCAMBENCH_TRAIN_PATH
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
        "scambench_validation": (
            load_prompt_label_csv(
                SCAMBENCH_VALIDATION_PATH
            )
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
            scambench_training,
        ]
    )

    verify_no_evaluation_leakage(
        training_prompts,
        evaluation_sets,
    )

    model = create_pipeline()

    print(
        "Training isolated ScamBench candidate model..."
    )

    model.fit(
        training_prompts,
        training_labels,
    )

    validation_probability_sets = {}

    for dataset_name in [
        "neuralchemy_validation",
        "deepset_validation",
        "scambench_validation",
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
            "scambench-candidate-v1"
        ),
        "model_type": (
            "TF-IDF Logistic Regression"
        ),
        "production_model_replaced": False,
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
            "scambench_train": len(
                scambench_training[0]
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
            "scambench_validation": len(
                evaluation_sets[
                    "scambench_validation"
                ][0]
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
        CANDIDATE_MODEL_PATH,
    )

    CANDIDATE_METRICS_PATH.write_text(
        json.dumps(
            metrics,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()

    print(
        "Combined training samples: "
        f"{len(training_prompts)}"
    )

    print(
        "ScamBench training samples: "
        f"{len(scambench_training[0])}"
    )

    print(
        "Removed training duplicates: "
        f"{removed_duplicates}"
    )

    print(
        "Selected threshold: "
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
        "Candidate model saved to: "
        f"{CANDIDATE_MODEL_PATH}"
    )

    print(
        "Candidate metrics saved to: "
        f"{CANDIDATE_METRICS_PATH}"
    )


if __name__ == "__main__":
    train_scambench_candidate()