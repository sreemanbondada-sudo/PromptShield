"""Compare raw and boundary-repaired entity predictions."""

import json
import sys
from pathlib import Path


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


import joblib

from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
)

from research.entity_localizer import (
    boundary_decoder,
)

from research.entity_localizer.train_entity_candidates import (
    load_jsonl,
    predict_records,
)


BASE_DIRECTORY = SCRIPT_DIRECTORY

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "data"
)

MODEL_PATH = (
    BASE_DIRECTORY
    / "models"
    / "contextual_entity_candidate.joblib"
)

REPORT_DIRECTORY = (
    BASE_DIRECTORY
    / "reports"
)

REPORT_PATH = (
    REPORT_DIRECTORY
    / "boundary_decoder_comparison.json"
)

DATASET_PATHS = {
    "validation": (
        DATA_DIRECTORY
        / "validation.jsonl"
    ),
    "test": (
        DATA_DIRECTORY
        / "test.jsonl"
    ),
    "challenge": (
        DATA_DIRECTORY
        / "challenge.jsonl"
    ),
}

SENSITIVE_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
}


def get_gold_boundaries(
    record: dict,
) -> set[tuple[int, int]]:
    """Return exact gold character boundaries."""
    return {
        (
            span["start"],
            span["end"],
        )
        for span in record["gold_spans"]
    }


def evaluate_predictions(
    records: list[dict],
    predictions_by_record: list[list[str]],
    use_boundary_decoder: bool,
) -> dict:
    """Evaluate raw or repaired entity predictions."""
    true_positive_spans = 0
    false_positive_spans = 0
    false_negative_spans = 0

    safe_record_count = 0
    positive_record_count = 0

    false_positive_records = 0
    false_negative_records = 0

    gold_token_labels = []
    predicted_token_labels = []

    incorrect_records = []

    for record, raw_labels in zip(
        records,
        predictions_by_record,
        strict=True,
    ):
        if use_boundary_decoder:
            decoded_result = (
                boundary_decoder
                .decode_sensitive_spans(
                    record["prompt"],
                    record["tokens"],
                    raw_labels,
                )
            )

            final_labels = (
                decoded_result["labels"]
            )

            predicted_spans = (
                decoded_result["spans"]
            )

        else:
            final_labels = (
                boundary_decoder
                .normalize_bio_labels(
                    raw_labels
                )
            )

            predicted_spans = (
                boundary_decoder
                .reconstruct_spans(
                    record["prompt"],
                    record["tokens"],
                    final_labels,
                )
            )

        gold_boundaries = (
            get_gold_boundaries(record)
        )

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

        record_gold_labels = [
            token["label"]
            for token in record["tokens"]
        ]

        gold_token_labels.extend(
            record_gold_labels
        )

        predicted_token_labels.extend(
            final_labels
        )

        if (
            predicted_boundaries
            != gold_boundaries
        ):
            incorrect_records.append(
                {
                    "id": record["id"],
                    "prompt": record["prompt"],
                    "source_action": (
                        record.get(
                            "source_action"
                        )
                    ),
                    "template_group": (
                        record.get(
                            "template_group"
                        )
                    ),
                    "gold_spans": (
                        record["gold_spans"]
                    ),
                    "predicted_spans": (
                        predicted_spans
                    ),
                }
            )

    precision_denominator = (
        true_positive_spans
        + false_positive_spans
    )

    recall_denominator = (
        true_positive_spans
        + false_negative_spans
    )

    exact_span_precision = (
        true_positive_spans
        / precision_denominator
        if precision_denominator
        else 0.0
    )

    exact_span_recall = (
        true_positive_spans
        / recall_denominator
        if recall_denominator
        else 0.0
    )

    exact_span_f1 = (
        2
        * exact_span_precision
        * exact_span_recall
        / (
            exact_span_precision
            + exact_span_recall
        )
        if (
            exact_span_precision
            + exact_span_recall
        )
        else 0.0
    )

    gold_sensitive_tokens = [
        label in SENSITIVE_LABELS
        for label in gold_token_labels
    ]

    predicted_sensitive_tokens = [
        label in SENSITIVE_LABELS
        for label in predicted_token_labels
    ]

    (
        token_precision,
        token_recall,
        token_f1,
        _,
    ) = precision_recall_fscore_support(
        gold_sensitive_tokens,
        predicted_sensitive_tokens,
        average="binary",
        zero_division=0,
    )

    token_accuracy = accuracy_score(
        gold_token_labels,
        predicted_token_labels,
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
        "record_count": len(records),
        "token_count": len(
            gold_token_labels
        ),
        "true_positive_spans": (
            true_positive_spans
        ),
        "false_positive_spans": (
            false_positive_spans
        ),
        "false_negative_spans": (
            false_negative_spans
        ),
        "exact_span_precision": (
            exact_span_precision
        ),
        "exact_span_recall": (
            exact_span_recall
        ),
        "exact_span_f1": exact_span_f1,
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


def calculate_change(
    raw_value: float,
    repaired_value: float,
) -> float:
    """Return the change from raw to repaired."""
    return repaired_value - raw_value


def evaluate_split(
    records: list[dict],
    artifact: dict,
) -> dict:
    """Evaluate one dataset split."""
    (
        _,
        predictions_by_record,
    ) = predict_records(
        records,
        artifact["vectorizer"],
        artifact["classifier"],
        artifact["context_window"],
    )

    raw_evaluation = evaluate_predictions(
        records,
        predictions_by_record,
        use_boundary_decoder=False,
    )

    repaired_evaluation = (
        evaluate_predictions(
            records,
            predictions_by_record,
            use_boundary_decoder=True,
        )
    )

    return {
        "raw": raw_evaluation,
        "repaired": repaired_evaluation,
        "changes": {
            "exact_span_precision": (
                calculate_change(
                    raw_evaluation[
                        "exact_span_precision"
                    ],
                    repaired_evaluation[
                        "exact_span_precision"
                    ],
                )
            ),
            "exact_span_recall": (
                calculate_change(
                    raw_evaluation[
                        "exact_span_recall"
                    ],
                    repaired_evaluation[
                        "exact_span_recall"
                    ],
                )
            ),
            "exact_span_f1": (
                calculate_change(
                    raw_evaluation[
                        "exact_span_f1"
                    ],
                    repaired_evaluation[
                        "exact_span_f1"
                    ],
                )
            ),
            "sensitive_token_f1": (
                calculate_change(
                    raw_evaluation[
                        "sensitive_token_f1"
                    ],
                    repaired_evaluation[
                        "sensitive_token_f1"
                    ],
                )
            ),
            "false_positive_record_rate": (
                calculate_change(
                    raw_evaluation[
                        "false_positive_record_rate"
                    ],
                    repaired_evaluation[
                        "false_positive_record_rate"
                    ],
                )
            ),
        },
    }


def print_evaluation(
    heading: str,
    evaluation: dict,
) -> None:
    """Print one evaluation result."""
    print(heading)

    print(
        "  Exact-span precision: "
        f"{evaluation[
            'exact_span_precision'
        ]:.2%}"
    )

    print(
        "  Exact-span recall: "
        f"{evaluation[
            'exact_span_recall'
        ]:.2%}"
    )

    print(
        "  Exact-span F1: "
        f"{evaluation[
            'exact_span_f1'
        ]:.2%}"
    )

    print(
        "  Sensitive-token F1: "
        f"{evaluation[
            'sensitive_token_f1'
        ]:.2%}"
    )

    print(
        "  False-positive safe records: "
        f"{evaluation[
            'false_positive_records'
        ]}"
    )

    print(
        "  False-positive record rate: "
        f"{evaluation[
            'false_positive_record_rate'
        ]:.2%}"
    )

    print(
        "  Completely missed positive records: "
        f"{evaluation[
            'false_negative_records'
        ]}"
    )

    print(
        "  Incorrect records: "
        f"{evaluation[
            'incorrect_record_count'
        ]}"
    )


def main() -> None:
    """Run raw-versus-repaired evaluation."""
    if not MODEL_PATH.exists():
        raise RuntimeError(
            "The contextual entity candidate "
            f"was not found: {MODEL_PATH}"
        )

    print(
        "Loading contextual entity candidate..."
    )

    artifact = joblib.load(
        MODEL_PATH
    )

    print(
        "Model: "
        f"{artifact['model_name']}"
    )

    print(
        "The final holdout is not used."
    )

    split_results = {}

    for split, dataset_path in (
        DATASET_PATHS.items()
    ):
        print(
            f"\nEvaluating {split} split..."
        )

        records = load_jsonl(
            dataset_path
        )

        split_result = evaluate_split(
            records,
            artifact,
        )

        split_results[split] = split_result

        print_evaluation(
            "\nRaw model",
            split_result["raw"],
        )

        print_evaluation(
            "\nBoundary-repaired model",
            split_result["repaired"],
        )

        print(
            "\n  Exact-span F1 change: "
            f"{split_result[
                'changes'
            ][
                'exact_span_f1'
            ]:+.2%}"
        )

        print(
            "  False-positive rate change: "
            f"{split_result[
                'changes'
            ][
                'false_positive_record_rate'
            ]:+.2%}"
        )

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "model_name": artifact[
            "model_name"
        ],
        "model_path": str(MODEL_PATH),
        "decoder": (
            "general_boundary_decoder_v1"
        ),
        "final_holdout_used": False,
        "splits": split_results,
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


if __name__ == "__main__":
    main()