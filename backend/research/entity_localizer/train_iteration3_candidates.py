"""Train and compare iteration-three entity localizers."""

import json
import sys
import time
from pathlib import Path

import joblib
import sklearn_crfsuite


SCRIPT_DIRECTORY = Path(__file__).resolve().parent

BACKEND_DIRECTORY = SCRIPT_DIRECTORY.parents[1]

if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIRECTORY),
    )


from research.entity_localizer.evaluate_boundary_decoder import (
    evaluate_predictions,
)

from research.entity_localizer.iteration3_features import (
    build_iteration3_sequence_features,
)

from research.entity_localizer.train_entity_candidates import (
    load_jsonl,
)


DATA_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "data_iteration3"
)

MODEL_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "models_iteration3"
)

REPORT_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "reports_iteration3"
)

ITERATION2_MODEL_PATH = (
    SCRIPT_DIRECTORY
    / "models_iteration2"
    / "contextual_entity_candidate_iteration2.joblib"
)

ITERATION3_MODEL_PATH = (
    MODEL_DIRECTORY
    / "contextual_entity_candidate_iteration3.joblib"
)

REPORT_PATH = (
    REPORT_DIRECTORY
    / "iteration3_candidate_evaluation.json"
)

DATASET_PATHS = {
    "train": (
        DATA_DIRECTORY
        / "train.jsonl"
    ),
    "validation": (
        DATA_DIRECTORY
        / "validation.jsonl"
    ),
    "challenge": (
        DATA_DIRECTORY
        / "challenge.jsonl"
    ),
}

LABEL_SCHEME = [
    "B-SENSITIVE",
    "I-SENSITIVE",
    "O",
]


def build_sequence_labels(
    records: list[dict],
) -> list[list[str]]:
    """Build one BIO-label sequence per prompt."""
    return [
        [
            str(token["label"])
            for token in record["tokens"]
        ]
        for record in records
    ]


def train_crf_candidate(
    train_records: list[dict],
    context_window: int,
    c1: float,
    c2: float,
    max_iterations: int,
) -> dict:
    """Train one CRF using iteration-three features."""
    feature_sequences = (
        build_iteration3_sequence_features(
            train_records,
            context_window,
        )
    )

    label_sequences = build_sequence_labels(
        train_records
    )

    classifier = sklearn_crfsuite.CRF(
        algorithm="lbfgs",
        c1=c1,
        c2=c2,
        max_iterations=max_iterations,
        all_possible_transitions=True,
        verbose=False,
    )

    classifier.fit(
        feature_sequences,
        label_sequences,
    )

    return {
        "model_kind": "crf",
        "context_window": context_window,
        "classifier": classifier,
        "vectorizer": None,
        "c1": c1,
        "c2": c2,
        "max_iterations": max_iterations,
        "feature_count": None,
    }


def predict_crf_records(
    records: list[dict],
    classifier,
    context_window: int,
) -> list[list[str]]:
    """Predict BIO labels with an iteration-three CRF."""
    feature_sequences = (
        build_iteration3_sequence_features(
            records,
            context_window,
        )
    )

    predictions = classifier.predict(
        feature_sequences
    )

    return [
        [
            str(label)
            for label in sequence
        ]
        for sequence in predictions
    ]


def predict_candidate(
    records: list[dict],
    candidate: dict,
) -> list[list[str]]:
    """Predict labels using an iteration-three candidate."""
    if candidate["model_kind"] != "crf":
        raise RuntimeError(
            "Iteration three currently supports only "
            "CRF candidates."
        )

    return predict_crf_records(
        records=records,
        classifier=candidate["classifier"],
        context_window=candidate[
            "context_window"
        ],
    )


def evaluate_candidate(
    records: list[dict],
    candidate: dict,
) -> dict:
    """Evaluate a candidate using boundary repair."""
    predictions = predict_candidate(
        records,
        candidate,
    )

    return evaluate_predictions(
        records,
        predictions,
        use_boundary_decoder=True,
    )


def evaluate_iteration2_baseline(
    records: list[dict],
) -> dict:
    """Evaluate the preserved iteration-two model."""
    if not ITERATION2_MODEL_PATH.exists():
        raise RuntimeError(
            "The preserved iteration-two model "
            "was not found: "
            f"{ITERATION2_MODEL_PATH}"
        )

    artifact = joblib.load(
        ITERATION2_MODEL_PATH
    )

    if artifact.get("model_kind") != "crf":
        raise RuntimeError(
            "The iteration-two baseline is not "
            "a CRF artifact."
        )

    feature_sequences = (
        build_iteration2_feature_sequences(
            records,
            artifact["context_window"],
        )
    )

    raw_predictions = artifact[
        "classifier"
    ].predict(
        feature_sequences
    )

    predictions = [
        [
            str(label)
            for label in sequence
        ]
        for sequence in raw_predictions
    ]

    evaluation = evaluate_predictions(
        records,
        predictions,
        use_boundary_decoder=True,
    )

    return {
        "model_name": artifact.get(
            "model_name",
            "iteration_two_candidate",
        ),
        "model_kind": artifact.get(
            "model_kind",
            "crf",
        ),
        "context_window": artifact[
            "context_window"
        ],
        "evaluation": evaluation,
    }


def build_iteration2_feature_sequences(
    records: list[dict],
    context_window: int,
) -> list[list[dict]]:
    """Build the original iteration-two features."""
    from research.entity_localizer.train_iteration2_candidates import (
        build_sequence_features,
    )

    return build_sequence_features(
        records,
        context_window,
    )


def selection_score(
    result: dict,
) -> tuple:
    """Rank candidates using validation only."""
    evaluation = result["validation"]

    return (
        evaluation["exact_span_f1"],
        evaluation["exact_span_precision"],
        evaluation["exact_span_recall"],
        evaluation["sensitive_token_f1"],
        -evaluation[
            "false_positive_record_rate"
        ],
        -evaluation[
            "false_negative_record_rate"
        ],
        -evaluation[
            "incorrect_record_count"
        ],
    )


def printable_percentage(
    value: float,
) -> str:
    """Format a decimal as a percentage."""
    return f"{value:.2%}"


def print_evaluation(
    heading: str,
    evaluation: dict,
) -> None:
    """Print the main entity metrics."""
    print(f"\n  {heading}")

    print(
        "    Exact-span precision: "
        + printable_percentage(
            evaluation[
                "exact_span_precision"
            ]
        )
    )

    print(
        "    Exact-span recall: "
        + printable_percentage(
            evaluation[
                "exact_span_recall"
            ]
        )
    )

    print(
        "    Exact-span F1: "
        + printable_percentage(
            evaluation[
                "exact_span_f1"
            ]
        )
    )

    print(
        "    Sensitive-token F1: "
        + printable_percentage(
            evaluation[
                "sensitive_token_f1"
            ]
        )
    )

    print(
        "    False-positive records: "
        f"{evaluation[
            'false_positive_records'
        ]}"
    )

    print(
        "    False-positive record rate: "
        + printable_percentage(
            evaluation[
                "false_positive_record_rate"
            ]
        )
    )

    print(
        "    False-negative records: "
        f"{evaluation[
            'false_negative_records'
        ]}"
    )

    print(
        "    False-negative record rate: "
        + printable_percentage(
            evaluation[
                "false_negative_record_rate"
            ]
        )
    )

    print(
        "    Incorrect records: "
        f"{evaluation[
            'incorrect_record_count'
        ]}"
    )


def candidate_report_entry(
    name: str,
    candidate: dict,
    training_seconds: float,
    validation: dict,
) -> dict:
    """Create a JSON-serializable result."""
    return {
        "name": name,
        "model_kind": candidate[
            "model_kind"
        ],
        "feature_set": (
            "iteration3_structural_features"
        ),
        "context_window": candidate[
            "context_window"
        ],
        "training_seconds": round(
            training_seconds,
            4,
        ),
        "feature_count": candidate.get(
            "feature_count"
        ),
        "c1": candidate.get("c1"),
        "c2": candidate.get("c2"),
        "max_iterations": candidate.get(
            "max_iterations"
        ),
        "validation": validation,
    }


def build_model_artifact(
    selected_name: str,
    selected_candidate: dict,
) -> dict:
    """Build the preserved research artifact."""
    return {
        "model_name": selected_name,
        "model_type": (
            "contextual_sensitive_entity_"
            "localizer_iteration3"
        ),
        "model_kind": selected_candidate[
            "model_kind"
        ],
        "dataset": (
            "contextual_sensitive_entity_"
            "iteration3_development_v1"
        ),
        "feature_set": (
            "iteration3_structural_features"
        ),
        "context_window": (
            selected_candidate[
                "context_window"
            ]
        ),
        "label_scheme": LABEL_SCHEME,
        "classifier": selected_candidate[
            "classifier"
        ],
        "vectorizer": None,
        "c1": selected_candidate["c1"],
        "c2": selected_candidate["c2"],
        "max_iterations": (
            selected_candidate[
                "max_iterations"
            ]
        ),
        "boundary_decoder_required": True,
        "historical_final_holdout_used": False,
        "iteration2_final_holdout_used": False,
        "production_ready": False,
        "production_changed": False,
        "mode": "research",
    }


def main() -> None:
    """Train and evaluate iteration-three candidates."""
    print(
        "Loading iteration-three entity datasets..."
    )

    for split, path in DATASET_PATHS.items():
        if not path.exists():
            raise RuntimeError(
                f"The {split} dataset is missing: "
                f"{path}"
            )

    train_records = load_jsonl(
        DATASET_PATHS["train"]
    )

    validation_records = load_jsonl(
        DATASET_PATHS["validation"]
    )

    challenge_records = load_jsonl(
        DATASET_PATHS["challenge"]
    )

    print(
        f"Training records: {len(train_records)}"
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
        "Historical and iteration-two final "
        "holdouts are not loaded or used."
    )

    print(
        "\nEvaluating preserved iteration-two "
        "baseline on iteration-three validation..."
    )

    baseline_result = (
        evaluate_iteration2_baseline(
            validation_records
        )
    )

    print_evaluation(
        "Iteration-two baseline",
        baseline_result["evaluation"],
    )

    candidate_definitions = [
        {
            "name": (
                "iteration3_crf_context_one"
            ),
            "context_window": 1,
            "c1": 0.10,
            "c2": 0.10,
            "max_iterations": 200,
        },
        {
            "name": (
                "iteration3_crf_context_two"
            ),
            "context_window": 2,
            "c1": 0.10,
            "c2": 0.10,
            "max_iterations": 200,
        },
        {
            "name": (
                "iteration3_crf_context_two_"
                "low_l1"
            ),
            "context_window": 2,
            "c1": 0.05,
            "c2": 0.10,
            "max_iterations": 250,
        },
        {
            "name": (
                "iteration3_crf_context_two_"
                "balanced"
            ),
            "context_window": 2,
            "c1": 0.05,
            "c2": 0.05,
            "max_iterations": 250,
        },
        {
            "name": (
                "iteration3_crf_context_three"
            ),
            "context_window": 3,
            "c1": 0.05,
            "c2": 0.10,
            "max_iterations": 250,
        },
    ]

    trained_candidates = {}
    candidate_results = []

    for definition in candidate_definitions:
        name = definition["name"]

        print(f"\nTraining {name}...")

        started_at = time.perf_counter()

        candidate = train_crf_candidate(
            train_records=train_records,
            context_window=definition[
                "context_window"
            ],
            c1=definition["c1"],
            c2=definition["c2"],
            max_iterations=definition[
                "max_iterations"
            ],
        )

        training_seconds = (
            time.perf_counter()
            - started_at
        )

        validation = evaluate_candidate(
            validation_records,
            candidate,
        )

        trained_candidates[name] = candidate

        candidate_results.append(
            candidate_report_entry(
                name=name,
                candidate=candidate,
                training_seconds=(
                    training_seconds
                ),
                validation=validation,
            )
        )

        print(
            "  Training time: "
            f"{training_seconds:.2f} seconds"
        )

        print_evaluation(
            "Validation results",
            validation,
        )

    selected_result = max(
        candidate_results,
        key=selection_score,
    )

    selected_name = selected_result["name"]

    selected_candidate = (
        trained_candidates[selected_name]
    )

    print(
        "\nSelected using validation metrics: "
        f"{selected_name}"
    )

    selected_challenge = evaluate_candidate(
        challenge_records,
        selected_candidate,
    )

    print_evaluation(
        "Iteration-three challenge results",
        selected_challenge,
    )

    MODEL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact = build_model_artifact(
        selected_name,
        selected_candidate,
    )

    joblib.dump(
        artifact,
        ITERATION3_MODEL_PATH,
    )

    report = {
        "dataset": (
            "contextual_sensitive_entity_"
            "iteration3_development_v1"
        ),
        "feature_set": (
            "iteration3_structural_features"
        ),
        "selection_split": "validation",
        "challenge_used_for_selection": False,
        "historical_final_holdout_used": False,
        "iteration2_final_holdout_used": False,
        "production_changed": False,
        "iteration2_baseline": (
            baseline_result
        ),
        "candidate_results": (
            candidate_results
        ),
        "selected_candidate": (
            selected_name
        ),
        "selected_validation": (
            selected_result["validation"]
        ),
        "selected_challenge": (
            selected_challenge
        ),
        "model_path": str(
            ITERATION3_MODEL_PATH
        ),
    }

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as report_file:
        json.dump(
            report,
            report_file,
            indent=2,
            ensure_ascii=False,
        )

        report_file.write("\n")

    print(
        "\nReport saved to: "
        f"{REPORT_PATH}"
    )

    print(
        "Selected candidate saved to: "
        f"{ITERATION3_MODEL_PATH}"
    )

    print(
        "\nHistorical and iteration-two final "
        "holdouts remain untouched."
    )

    print(
        "The selected candidate remains "
        "research-only."
    )


if __name__ == "__main__":
    main()