"""Train and compare iteration-two entity localizers."""

import json
import sys
import time
from pathlib import Path

import joblib
import sklearn_crfsuite

from sklearn.feature_extraction import (
    DictVectorizer,
)

from sklearn.linear_model import (
    LogisticRegression,
)


SCRIPT_DIRECTORY = (
    Path(__file__).resolve().parent
)

BACKEND_DIRECTORY = (
    SCRIPT_DIRECTORY.parents[1]
)

if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIRECTORY),
    )


from research.entity_localizer.evaluate_boundary_decoder import (
    evaluate_predictions,
)

from research.entity_localizer.train_entity_candidates import (
    build_token_features,
    flatten_records,
    load_jsonl,
    predict_records,
)


DATA_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "data_iteration2"
)

MODEL_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "models_iteration2"
)

REPORT_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "reports_iteration2"
)

ITERATION1_MODEL_PATH = (
    SCRIPT_DIRECTORY
    / "models"
    / "contextual_entity_candidate.joblib"
)

ITERATION2_MODEL_PATH = (
    MODEL_DIRECTORY
    / "contextual_entity_candidate_iteration2.joblib"
)

REPORT_PATH = (
    REPORT_DIRECTORY
    / "iteration2_candidate_evaluation.json"
)

DATASET_PATHS = {
    "train": DATA_DIRECTORY / "train.jsonl",
    "validation": (
        DATA_DIRECTORY
        / "validation.jsonl"
    ),
    "challenge": (
        DATA_DIRECTORY
        / "challenge.jsonl"
    ),
}


def build_sequence_features(
    records: list[dict],
    context_window: int,
) -> list[list[dict]]:
    """Build one feature sequence per prompt."""
    return [
        [
            build_token_features(
                record["tokens"],
                token_index,
                context_window,
            )
            for token_index in range(
                len(record["tokens"])
            )
        ]
        for record in records
    ]


def build_sequence_labels(
    records: list[dict],
) -> list[list[str]]:
    """Build one BIO-label sequence per prompt."""
    return [
        [
            token["label"]
            for token in record["tokens"]
        ]
        for record in records
    ]


def predict_logistic_records(
    records: list[dict],
    vectorizer: DictVectorizer,
    classifier: LogisticRegression,
    context_window: int,
) -> list[list[str]]:
    """Predict BIO labels with a flat logistic model."""
    feature_rows, _ = flatten_records(
        records,
        context_window,
    )

    transformed_features = (
        vectorizer.transform(
            feature_rows
        )
    )

    flat_predictions = [
        str(label)
        for label in classifier.predict(
            transformed_features
        )
    ]

    predictions_by_record = []
    current_position = 0

    for record in records:
        token_count = len(
            record["tokens"]
        )

        predictions_by_record.append(
            flat_predictions[
                current_position:
                current_position + token_count
            ]
        )

        current_position += token_count

    if current_position != len(
        flat_predictions
    ):
        raise RuntimeError(
            "Logistic prediction count does not "
            "match the number of tokens."
        )

    return predictions_by_record


def predict_crf_records(
    records: list[dict],
    classifier,
    context_window: int,
) -> list[list[str]]:
    """Predict sequence labels using a CRF."""
    feature_sequences = (
        build_sequence_features(
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


def train_logistic_candidate(
    train_records: list[dict],
    context_window: int,
    regularization_strength: float,
) -> dict:
    """Train one balanced logistic candidate."""
    feature_rows, labels = flatten_records(
        train_records,
        context_window,
    )

    vectorizer = DictVectorizer(
        sparse=True
    )

    transformed_features = (
        vectorizer.fit_transform(
            feature_rows
        )
    )

    classifier = LogisticRegression(
        C=regularization_strength,
        class_weight="balanced",
        max_iter=2500,
        random_state=42,
    )

    classifier.fit(
        transformed_features,
        labels,
    )

    return {
        "model_kind": "logistic",
        "context_window": context_window,
        "vectorizer": vectorizer,
        "classifier": classifier,
        "feature_count": len(
            vectorizer.feature_names_
        ),
    }


def train_crf_candidate(
    train_records: list[dict],
    context_window: int,
    c1: float,
    c2: float,
) -> dict:
    """Train one sequence-aware CRF candidate."""
    feature_sequences = (
        build_sequence_features(
            train_records,
            context_window,
        )
    )

    label_sequences = (
        build_sequence_labels(
            train_records
        )
    )

    classifier = sklearn_crfsuite.CRF(
        algorithm="lbfgs",
        c1=c1,
        c2=c2,
        max_iterations=150,
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
        "c1": c1,
        "c2": c2,
        "feature_count": None,
    }


def predict_candidate(
    records: list[dict],
    candidate: dict,
) -> list[list[str]]:
    """Predict labels using either model family."""
    if candidate["model_kind"] == "logistic":
        return predict_logistic_records(
            records,
            candidate["vectorizer"],
            candidate["classifier"],
            candidate["context_window"],
        )

    if candidate["model_kind"] == "crf":
        return predict_crf_records(
            records,
            candidate["classifier"],
            candidate["context_window"],
        )

    raise RuntimeError(
        "Unsupported candidate model kind: "
        f"{candidate['model_kind']!r}."
    )


def evaluate_candidate(
    records: list[dict],
    candidate: dict,
) -> dict:
    """Evaluate one candidate with boundary repair."""
    predictions = predict_candidate(
        records,
        candidate,
    )

    return evaluate_predictions(
        records,
        predictions,
        use_boundary_decoder=True,
    )


def evaluate_iteration1_baseline(
    records: list[dict],
) -> dict:
    """Evaluate the preserved iteration-one model."""
    if not ITERATION1_MODEL_PATH.exists():
        raise RuntimeError(
            "Iteration-one entity model was not found: "
            f"{ITERATION1_MODEL_PATH}"
        )

    artifact = joblib.load(
        ITERATION1_MODEL_PATH
    )

    (
        _,
        predictions_by_record,
    ) = predict_records(
        records,
        artifact["vectorizer"],
        artifact["classifier"],
        artifact["context_window"],
    )

    evaluation = evaluate_predictions(
        records,
        predictions_by_record,
        use_boundary_decoder=True,
    )

    return {
        "model_name": artifact[
            "model_name"
        ],
        "model_kind": "iteration1_logistic",
        "context_window": artifact[
            "context_window"
        ],
        "evaluation": evaluation,
    }


def selection_score(
    result: dict,
) -> tuple:
    """Rank candidates using validation only."""
    evaluation = result[
        "validation"
    ]

    return (
        evaluation["exact_span_f1"],
        evaluation["exact_span_precision"],
        evaluation["exact_span_recall"],
        -evaluation[
            "false_positive_record_rate"
        ],
        evaluation["sensitive_token_f1"],
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
    """Print concise entity metrics."""
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
    """Create one serializable candidate result."""
    return {
        "name": name,
        "model_kind": candidate[
            "model_kind"
        ],
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
        "validation": validation,
    }


def main() -> None:
    """Train and compare iteration-two models."""
    print(
        "Loading iteration-two entity datasets..."
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
        "The historical final holdout is not "
        "loaded or used."
    )

    print(
        "\nEvaluating preserved iteration-one "
        "baseline on iteration-two validation..."
    )

    baseline_result = (
        evaluate_iteration1_baseline(
            validation_records
        )
    )

    print_evaluation(
        "Iteration-one baseline",
        baseline_result["evaluation"],
    )

    candidate_definitions = [
        {
            "name": "iteration2_logistic_context_one",
            "trainer": lambda: (
                train_logistic_candidate(
                    train_records,
                    context_window=1,
                    regularization_strength=1.0,
                )
            ),
        },
        {
            "name": "iteration2_logistic_context_two",
            "trainer": lambda: (
                train_logistic_candidate(
                    train_records,
                    context_window=2,
                    regularization_strength=1.0,
                )
            ),
        },
        {
            "name": "iteration2_crf_context_one",
            "trainer": lambda: (
                train_crf_candidate(
                    train_records,
                    context_window=1,
                    c1=0.10,
                    c2=0.10,
                )
            ),
        },
        {
            "name": "iteration2_crf_context_two",
            "trainer": lambda: (
                train_crf_candidate(
                    train_records,
                    context_window=2,
                    c1=0.05,
                    c2=0.10,
                )
            ),
        },
    ]

    trained_candidates = {}
    candidate_results = []

    for definition in candidate_definitions:
        name = definition["name"]

        print(f"\nTraining {name}...")

        started_at = time.perf_counter()

        candidate = definition[
            "trainer"
        ]()

        training_seconds = (
            time.perf_counter()
            - started_at
        )

        validation_evaluation = (
            evaluate_candidate(
                validation_records,
                candidate,
            )
        )

        result = candidate_report_entry(
            name,
            candidate,
            training_seconds,
            validation_evaluation,
        )

        trained_candidates[name] = candidate
        candidate_results.append(result)

        print(
            "  Training time: "
            f"{training_seconds:.2f} seconds"
        )

        print_evaluation(
            "Validation results",
            validation_evaluation,
        )

    selected_result = max(
        candidate_results,
        key=selection_score,
    )

    selected_name = selected_result[
        "name"
    ]

    selected_candidate = (
        trained_candidates[
            selected_name
        ]
    )

    print(
        "\nSelected using validation metrics: "
        f"{selected_name}"
    )

    challenge_evaluation = (
        evaluate_candidate(
            challenge_records,
            selected_candidate,
        )
    )

    print_evaluation(
        "Iteration-two challenge results",
        challenge_evaluation,
    )

    MODEL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_artifact = {
        "model_name": selected_name,
        "model_type": (
            "contextual_sensitive_entity_"
            "localizer_iteration2"
        ),
        "model_kind": selected_candidate[
            "model_kind"
        ],
        "dataset": (
            "contextual_sensitive_entity_"
            "iteration2_development_v1"
        ),
        "context_window": (
            selected_candidate[
                "context_window"
            ]
        ),
        "label_scheme": [
            "B-SENSITIVE",
            "I-SENSITIVE",
            "O",
        ],
        "classifier": (
            selected_candidate[
                "classifier"
            ]
        ),
        "vectorizer": (
            selected_candidate.get(
                "vectorizer"
            )
        ),
        "c1": selected_candidate.get("c1"),
        "c2": selected_candidate.get("c2"),
        "boundary_decoder_required": True,
        "historical_final_holdout_used": False,
        "production_ready": False,
        "mode": "research",
    }

    joblib.dump(
        model_artifact,
        ITERATION2_MODEL_PATH,
    )

    report = {
        "dataset": (
            "contextual_sensitive_entity_"
            "iteration2_development_v1"
        ),
        "historical_final_holdout_used": False,
        "selection_split": "validation",
        "challenge_used_for_selection": False,
        "iteration1_baseline": baseline_result,
        "candidate_results": candidate_results,
        "selected_candidate": selected_name,
        "selected_validation": (
            selected_result["validation"]
        ),
        "selected_challenge": (
            challenge_evaluation
        ),
        "model_path": str(
            ITERATION2_MODEL_PATH
        ),
    }

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            report,
            output_file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        output_file.write("\n")

    print(
        f"\nReport saved to: {REPORT_PATH}"
    )

    print(
        "Selected candidate saved to: "
        f"{ITERATION2_MODEL_PATH}"
    )

    print(
        "\nThe historical final holdout remains "
        "untouched."
    )

    print(
        "The selected candidate remains "
        "research-only."
    )


if __name__ == "__main__":
    main()