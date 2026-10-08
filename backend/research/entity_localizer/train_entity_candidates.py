"""Train and compare contextual sensitive-entity localizers."""

import json
import time
from collections import Counter
from pathlib import Path

import joblib

from sklearn.calibration import (
    CalibratedClassifierCV,
)
from sklearn.feature_extraction import (
    DictVectorizer,
)
from sklearn.linear_model import (
    LogisticRegression,
)
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
)
from sklearn.svm import (
    LinearSVC,
)


BASE_DIRECTORY = Path(__file__).resolve().parent

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "data"
)

REPORT_DIRECTORY = (
    BASE_DIRECTORY
    / "reports"
)

MODEL_DIRECTORY = (
    BASE_DIRECTORY
    / "models"
)

DATASET_PATHS = {
    "train": DATA_DIRECTORY / "train.jsonl",
    "validation": (
        DATA_DIRECTORY
        / "validation.jsonl"
    ),
    "test": DATA_DIRECTORY / "test.jsonl",
}

REPORT_PATH = (
    REPORT_DIRECTORY
    / "entity_candidate_evaluation.json"
)

MODEL_PATH = (
    MODEL_DIRECTORY
    / "contextual_entity_candidate.joblib"
)

BIO_LABELS = [
    "B-SENSITIVE",
    "I-SENSITIVE",
    "O",
]

SENSITIVE_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
}


def load_jsonl(path: Path) -> list[dict]:
    """Load one generated JSON Lines dataset."""
    if not path.exists():
        raise RuntimeError(
            f"Entity dataset was not found: {path}"
        )

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


def token_shape(value: str) -> str:
    """Return a compact character-shape representation."""
    shape_characters = []

    for character in value:
        if character.isupper():
            shape_character = "X"

        elif character.islower():
            shape_character = "x"

        elif character.isdigit():
            shape_character = "d"

        elif character.isspace():
            shape_character = "s"

        else:
            shape_character = character

        if (
            not shape_characters
            or shape_characters[-1]
            != shape_character
        ):
            shape_characters.append(
                shape_character
            )

    return "".join(shape_characters)[:30]


def add_token_features(
    features: dict,
    prefix: str,
    token_text: str,
) -> None:
    """Add lexical and structural features for one token."""
    lowered_token = token_text.lower()

    features[f"{prefix}:lower"] = lowered_token
    features[f"{prefix}:shape"] = token_shape(
        token_text
    )
    features[f"{prefix}:length"] = min(
        len(token_text),
        40,
    )

    features[f"{prefix}:is_alpha"] = (
        token_text.isalpha()
    )

    features[f"{prefix}:is_digit"] = (
        token_text.isdigit()
    )

    features[f"{prefix}:is_alphanumeric"] = (
        token_text.isalnum()
    )

    features[f"{prefix}:is_upper"] = (
        token_text.isupper()
    )

    features[f"{prefix}:is_lower"] = (
        token_text.islower()
    )

    features[f"{prefix}:is_title"] = (
        token_text.istitle()
    )

    features[f"{prefix}:contains_digit"] = any(
        character.isdigit()
        for character in token_text
    )

    features[f"{prefix}:contains_alpha"] = any(
        character.isalpha()
        for character in token_text
    )

    features[f"{prefix}:contains_upper"] = any(
        character.isupper()
        for character in token_text
    )

    features[f"{prefix}:contains_lower"] = any(
        character.islower()
        for character in token_text
    )

    features[f"{prefix}:contains_hyphen"] = (
        "-" in token_text
    )

    features[f"{prefix}:contains_underscore"] = (
        "_" in token_text
    )

    features[f"{prefix}:contains_at"] = (
        "@" in token_text
    )

    features[f"{prefix}:contains_period"] = (
        "." in token_text
    )

    features[f"{prefix}:contains_colon"] = (
        ":" in token_text
    )

    features[f"{prefix}:prefix1"] = (
        lowered_token[:1]
    )

    features[f"{prefix}:prefix2"] = (
        lowered_token[:2]
    )

    features[f"{prefix}:prefix3"] = (
        lowered_token[:3]
    )

    features[f"{prefix}:prefix4"] = (
        lowered_token[:4]
    )

    features[f"{prefix}:suffix1"] = (
        lowered_token[-1:]
    )

    features[f"{prefix}:suffix2"] = (
        lowered_token[-2:]
    )

    features[f"{prefix}:suffix3"] = (
        lowered_token[-3:]
    )

    features[f"{prefix}:suffix4"] = (
        lowered_token[-4:]
    )


def build_token_features(
    tokens: list[dict],
    token_index: int,
    context_window: int,
) -> dict:
    """Build contextual features for one token."""
    current_token = tokens[token_index]

    features = {
        "bias": 1.0,
        "position_is_first": token_index == 0,
        "position_is_last": (
            token_index == len(tokens) - 1
        ),
        "relative_position": round(
            token_index
            / max(len(tokens) - 1, 1),
            3,
        ),
    }

    add_token_features(
        features,
        "current",
        current_token["text"],
    )

    for distance in range(
        1,
        context_window + 1,
    ):
        previous_index = token_index - distance
        next_index = token_index + distance

        if previous_index >= 0:
            add_token_features(
                features,
                f"previous_{distance}",
                tokens[previous_index]["text"],
            )

        else:
            features[
                f"previous_{distance}:BOS"
            ] = True

        if next_index < len(tokens):
            add_token_features(
                features,
                f"next_{distance}",
                tokens[next_index]["text"],
            )

        else:
            features[
                f"next_{distance}:EOS"
            ] = True

    return features


def flatten_records(
    records: list[dict],
    context_window: int,
) -> tuple[list[dict], list[str]]:
    """Convert prompt records into token samples."""
    feature_rows = []
    labels = []

    for record in records:
        tokens = record["tokens"]

        for token_index, token in enumerate(
            tokens
        ):
            feature_rows.append(
                build_token_features(
                    tokens,
                    token_index,
                    context_window,
                )
            )

            labels.append(
                token["label"]
            )

    return feature_rows, labels


def normalize_bio_labels(
    predicted_labels: list[str],
) -> list[str]:
    """Repair invalid I labels produced independently."""
    normalized_labels = []
    previous_label = "O"

    for predicted_label in predicted_labels:
        label = predicted_label

        if (
            label == "I-SENSITIVE"
            and previous_label not in {
                "B-SENSITIVE",
                "I-SENSITIVE",
            }
        ):
            label = "B-SENSITIVE"

        normalized_labels.append(label)
        previous_label = label

    return normalized_labels


def reconstruct_spans(
    prompt: str,
    tokens: list[dict],
    labels: list[str],
) -> list[dict]:
    """Convert token BIO predictions into character spans."""
    spans = []

    active_start = None
    active_end = None

    for token, label in zip(
        tokens,
        labels,
        strict=True,
    ):
        if label == "B-SENSITIVE":
            if active_start is not None:
                spans.append(
                    {
                        "start": active_start,
                        "end": active_end,
                        "text": prompt[
                            active_start:active_end
                        ],
                    }
                )

            active_start = token["start"]
            active_end = token["end"]

        elif label == "I-SENSITIVE":
            if active_start is None:
                active_start = token["start"]

            active_end = token["end"]

        elif active_start is not None:
            spans.append(
                {
                    "start": active_start,
                    "end": active_end,
                    "text": prompt[
                        active_start:active_end
                    ],
                }
            )

            active_start = None
            active_end = None

    if active_start is not None:
        spans.append(
            {
                "start": active_start,
                "end": active_end,
                "text": prompt[
                    active_start:active_end
                ],
            }
        )

    return spans


def calculate_span_metrics(
    records: list[dict],
    predictions_by_record: list[list[str]],
) -> dict:
    """Calculate exact-span and record-level metrics."""
    true_positive_spans = 0
    false_positive_spans = 0
    false_negative_spans = 0

    safe_record_count = 0
    positive_record_count = 0

    false_positive_records = 0
    false_negative_records = 0

    incorrect_records = []

    for record, predicted_labels in zip(
        records,
        predictions_by_record,
        strict=True,
    ):
        normalized_labels = normalize_bio_labels(
            predicted_labels
        )

        predicted_spans = reconstruct_spans(
            record["prompt"],
            record["tokens"],
            normalized_labels,
        )

        gold_boundaries = {
            (
                span["start"],
                span["end"],
            )
            for span in record["gold_spans"]
        }

        predicted_boundaries = {
            (
                span["start"],
                span["end"],
            )
            for span in predicted_spans
        }

        matched_boundaries = (
            gold_boundaries
            & predicted_boundaries
        )

        true_positive_spans += len(
            matched_boundaries
        )

        false_positive_spans += len(
            predicted_boundaries
            - gold_boundaries
        )

        false_negative_spans += len(
            gold_boundaries
            - predicted_boundaries
        )

        if gold_boundaries:
            positive_record_count += 1

            if not predicted_boundaries:
                false_negative_records += 1

        else:
            safe_record_count += 1

            if predicted_boundaries:
                false_positive_records += 1

        if predicted_boundaries != gold_boundaries:
            incorrect_records.append(
                {
                    "id": record["id"],
                    "prompt": record["prompt"],
                    "gold_spans": (
                        record["gold_spans"]
                    ),
                    "predicted_spans": (
                        predicted_spans
                    ),
                    "source_action": record.get(
                        "source_action"
                    ),
                    "template_group": record.get(
                        "template_group"
                    ),
                }
            )

    span_precision_denominator = (
        true_positive_spans
        + false_positive_spans
    )

    span_recall_denominator = (
        true_positive_spans
        + false_negative_spans
    )

    span_precision = (
        true_positive_spans
        / span_precision_denominator
        if span_precision_denominator
        else 0.0
    )

    span_recall = (
        true_positive_spans
        / span_recall_denominator
        if span_recall_denominator
        else 0.0
    )

    span_f1 = (
        2
        * span_precision
        * span_recall
        / (
            span_precision
            + span_recall
        )
        if (
            span_precision
            + span_recall
        )
        else 0.0
    )

    false_positive_record_rate = (
        false_positive_records
        / safe_record_count
        if safe_record_count
        else 0.0
    )

    false_negative_record_rate = (
        false_negative_records
        / positive_record_count
        if positive_record_count
        else 0.0
    )

    return {
        "true_positive_spans": (
            true_positive_spans
        ),
        "false_positive_spans": (
            false_positive_spans
        ),
        "false_negative_spans": (
            false_negative_spans
        ),
        "exact_span_precision": span_precision,
        "exact_span_recall": span_recall,
        "exact_span_f1": span_f1,
        "safe_record_count": safe_record_count,
        "positive_record_count": (
            positive_record_count
        ),
        "false_positive_records": (
            false_positive_records
        ),
        "false_negative_records": (
            false_negative_records
        ),
        "false_positive_record_rate": (
            false_positive_record_rate
        ),
        "false_negative_record_rate": (
            false_negative_record_rate
        ),
        "incorrect_record_count": len(
            incorrect_records
        ),
        "incorrect_records": (
            incorrect_records
        ),
    }


def predict_records(
    records: list[dict],
    vectorizer: DictVectorizer,
    classifier,
    context_window: int,
) -> tuple[list[str], list[list[str]]]:
    """Predict flattened and record-grouped labels."""
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

        record_predictions = (
            flat_predictions[
                current_position:
                current_position + token_count
            ]
        )

        predictions_by_record.append(
            record_predictions
        )

        current_position += token_count

    if current_position != len(
        flat_predictions
    ):
        raise RuntimeError(
            "Prediction count does not match "
            "the number of dataset tokens."
        )

    return (
        flat_predictions,
        predictions_by_record,
    )


def evaluate_model(
    records: list[dict],
    vectorizer: DictVectorizer,
    classifier,
    context_window: int,
) -> dict:
    """Evaluate one entity model."""
    flat_gold_labels = [
        token["label"]
        for record in records
        for token in record["tokens"]
    ]

    (
        flat_predictions,
        predictions_by_record,
    ) = predict_records(
        records,
        vectorizer,
        classifier,
        context_window,
    )

    sensitive_gold = [
        label in SENSITIVE_LABELS
        for label in flat_gold_labels
    ]

    sensitive_predictions = [
        label in SENSITIVE_LABELS
        for label in flat_predictions
    ]

    (
        token_precision,
        token_recall,
        token_f1,
        _,
    ) = precision_recall_fscore_support(
        sensitive_gold,
        sensitive_predictions,
        average="binary",
        zero_division=0,
    )

    token_accuracy = accuracy_score(
        flat_gold_labels,
        flat_predictions,
    )

    span_metrics = calculate_span_metrics(
        records,
        predictions_by_record,
    )

    return {
        "record_count": len(records),
        "token_count": len(
            flat_gold_labels
        ),
        "token_accuracy": float(
            token_accuracy
        ),
        "sensitive_token_precision": float(
            token_precision
        ),
        "sensitive_token_recall": float(
            token_recall
        ),
        "sensitive_token_f1": float(
            token_f1
        ),
        **span_metrics,
    }


def build_logistic_classifier(
    regularization_strength: float,
):
    """Create a balanced logistic classifier."""
    return LogisticRegression(
        C=regularization_strength,
        class_weight="balanced",
        max_iter=2000,
        random_state=42,
    )


def build_calibrated_svm():
    """Create a calibrated balanced linear SVM."""
    return CalibratedClassifierCV(
        estimator=LinearSVC(
            C=1.0,
            class_weight="balanced",
            random_state=42,
        ),
        cv=3,
        method="sigmoid",
    )


def print_evaluation(
    heading: str,
    evaluation: dict,
) -> None:
    """Print concise evaluation metrics."""
    print(f"\n  {heading}")

    print(
        "    Exact-span precision: "
        f"{evaluation[
            'exact_span_precision'
        ]:.2%}"
    )

    print(
        "    Exact-span recall: "
        f"{evaluation[
            'exact_span_recall'
        ]:.2%}"
    )

    print(
        "    Exact-span F1: "
        f"{evaluation[
            'exact_span_f1'
        ]:.2%}"
    )

    print(
        "    Sensitive-token F1: "
        f"{evaluation[
            'sensitive_token_f1'
        ]:.2%}"
    )

    print(
        "    False-positive safe records: "
        f"{evaluation[
            'false_positive_records'
        ]}"
    )

    print(
        "    False-positive record rate: "
        f"{evaluation[
            'false_positive_record_rate'
        ]:.2%}"
    )

    print(
        "    False-negative positive records: "
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


def selection_score(
    candidate_result: dict,
) -> tuple:
    """Return the validation model-selection score."""
    validation = candidate_result[
        "validation"
    ]

    return (
        validation["exact_span_f1"],
        validation["exact_span_recall"],
        -validation[
            "false_positive_record_rate"
        ],
        validation["sensitive_token_f1"],
        validation["exact_span_precision"],
    )


def main() -> None:
    """Train, compare and preserve the best candidate."""
    print(
        "Loading contextual entity datasets..."
    )

    train_records = load_jsonl(
        DATASET_PATHS["train"]
    )

    validation_records = load_jsonl(
        DATASET_PATHS["validation"]
    )

    test_records = load_jsonl(
        DATASET_PATHS["test"]
    )

    print(
        f"Training records: {len(train_records)}"
    )

    print(
        "Validation records: "
        f"{len(validation_records)}"
    )

    print(
        f"Test records: {len(test_records)}"
    )

    print(
        "The challenge dataset and final holdout "
        "are not used for model selection."
    )

    candidate_definitions = [
        {
            "name": "logistic_local",
            "context_window": 0,
            "classifier_factory": (
                lambda: build_logistic_classifier(
                    1.0
                )
            ),
        },
        {
            "name": "logistic_context_one",
            "context_window": 1,
            "classifier_factory": (
                lambda: build_logistic_classifier(
                    1.0
                )
            ),
        },
        {
            "name": "logistic_context_two",
            "context_window": 2,
            "classifier_factory": (
                lambda: build_logistic_classifier(
                    1.0
                )
            ),
        },
        {
            "name": "calibrated_svm_context_two",
            "context_window": 2,
            "classifier_factory": (
                build_calibrated_svm
            ),
        },
    ]

    candidate_results = []
    trained_candidates = {}

    for candidate_definition in (
        candidate_definitions
    ):
        candidate_name = (
            candidate_definition["name"]
        )

        context_window = (
            candidate_definition[
                "context_window"
            ]
        )

        print(
            f"\nTraining {candidate_name}..."
        )

        training_features, training_labels = (
            flatten_records(
                train_records,
                context_window,
            )
        )

        training_label_counts = Counter(
            training_labels
        )

        vectorizer = DictVectorizer(
            sparse=True
        )

        transformed_training_features = (
            vectorizer.fit_transform(
                training_features
            )
        )

        classifier = (
            candidate_definition[
                "classifier_factory"
            ]()
        )

        training_started = (
            time.perf_counter()
        )

        classifier.fit(
            transformed_training_features,
            training_labels,
        )

        training_seconds = (
            time.perf_counter()
            - training_started
        )

        validation_evaluation = (
            evaluate_model(
                validation_records,
                vectorizer,
                classifier,
                context_window,
            )
        )

        candidate_result = {
            "name": candidate_name,
            "context_window": (
                context_window
            ),
            "training_seconds": round(
                training_seconds,
                4,
            ),
            "feature_count": len(
                vectorizer.feature_names_
            ),
            "training_token_count": len(
                training_labels
            ),
            "training_label_counts": {
                label: (
                    training_label_counts.get(
                        label,
                        0,
                    )
                )
                for label in BIO_LABELS
            },
            "validation": (
                validation_evaluation
            ),
        }

        candidate_results.append(
            candidate_result
        )

        trained_candidates[
            candidate_name
        ] = {
            "vectorizer": vectorizer,
            "classifier": classifier,
            "context_window": (
                context_window
            ),
        }

        print(
            "  Training time: "
            f"{training_seconds:.2f} seconds"
        )

        print(
            "  Features: "
            f"{len(vectorizer.feature_names_)}"
        )

        print_evaluation(
            "Validation results",
            validation_evaluation,
        )

    selected_result = max(
        candidate_results,
        key=selection_score,
    )

    selected_name = (
        selected_result["name"]
    )

    selected_candidate = (
        trained_candidates[
            selected_name
        ]
    )

    print(
        "\nSelected candidate using validation "
        f"metrics: {selected_name}"
    )

    test_evaluation = evaluate_model(
        test_records,
        selected_candidate[
            "vectorizer"
        ],
        selected_candidate[
            "classifier"
        ],
        selected_candidate[
            "context_window"
        ],
    )

    print_evaluation(
        "Held-out test results",
        test_evaluation,
    )

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    MODEL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "dataset": (
            "contextual_sensitive_entity_bio_v1"
        ),
        "label_scheme": BIO_LABELS,
        "selection_split": "validation",
        "challenge_used_for_selection": False,
        "final_holdout_used": False,
        "candidate_results": (
            candidate_results
        ),
        "selected_candidate": (
            selected_name
        ),
        "selected_validation": (
            selected_result[
                "validation"
            ]
        ),
        "selected_test": test_evaluation,
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

    model_artifact = {
        "model_name": selected_name,
        "model_type": (
            "contextual_sensitive_entity_localizer"
        ),
        "dataset": (
            "contextual_sensitive_entity_bio_v1"
        ),
        "label_scheme": BIO_LABELS,
        "context_window": (
            selected_candidate[
                "context_window"
            ]
        ),
        "vectorizer": (
            selected_candidate[
                "vectorizer"
            ]
        ),
        "classifier": (
            selected_candidate[
                "classifier"
            ]
        ),
        "feature_builder_version": 1,
        "production_ready": False,
        "mode": "research",
    }

    joblib.dump(
        model_artifact,
        MODEL_PATH,
    )

    print(
        f"\nReport saved to: {REPORT_PATH}"
    )

    print(
        f"Candidate saved to: {MODEL_PATH}"
    )

    print(
        "\nThe candidate remains research-only."
    )


if __name__ == "__main__":
    main()