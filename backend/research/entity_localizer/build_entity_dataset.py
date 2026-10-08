"""Build BIO-token datasets for contextual sensitive-entity research."""

import json
import re
from collections import Counter
from pathlib import Path


BASE_DIRECTORY = Path(__file__).resolve().parent

ACTION_CLASSIFIER_DIRECTORY = (
    BASE_DIRECTORY.parent
    / "action_classifier"
)

SOURCE_DATA_DIRECTORY = (
    ACTION_CLASSIFIER_DIRECTORY
    / "data"
)

OUTPUT_DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "data"
)

REPORT_PATH = (
    BASE_DIRECTORY
    / "entity_dataset_report.json"
)

SOURCE_DATASET_PATHS = {
    "train": (
        SOURCE_DATA_DIRECTORY
        / "train.jsonl"
    ),
    "validation": (
        SOURCE_DATA_DIRECTORY
        / "validation.jsonl"
    ),
    "test": (
        SOURCE_DATA_DIRECTORY
        / "test.jsonl"
    ),
    "challenge": (
        SOURCE_DATA_DIRECTORY
        / "challenge.jsonl"
    ),
}

OUTPUT_DATASET_PATHS = {
    split: OUTPUT_DATA_DIRECTORY / f"{split}.jsonl"
    for split in SOURCE_DATASET_PATHS
}

TOKEN_PATTERN = re.compile(
    r"\w+|[^\w\s]",
    flags=re.UNICODE,
)

VALID_BIO_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
    "O",
}


def load_jsonl(path: Path) -> list[dict]:
    """Load records from a JSON Lines file."""
    if not path.exists():
        raise RuntimeError(
            f"Source dataset was not found: {path}"
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

            if not isinstance(record, dict):
                raise RuntimeError(
                    f"Record {line_number} in {path} "
                    "must be a JSON object."
                )

            records.append(record)

    if not records:
        raise RuntimeError(
            f"No records were loaded from {path}."
        )

    return records


def validate_sensitive_spans(
    record: dict,
    split: str,
    record_position: int,
) -> list[dict]:
    """Validate sensitive spans and return them in order."""
    record_id = record.get(
        "id",
        f"{split}:{record_position}",
    )

    prompt = record.get("prompt")

    if not isinstance(prompt, str):
        raise RuntimeError(
            f"{record_id}: prompt must be a string."
        )

    if not prompt.strip():
        raise RuntimeError(
            f"{record_id}: prompt must not be empty."
        )

    sensitive_spans = record.get(
        "sensitive_spans",
        [],
    )

    if not isinstance(sensitive_spans, list):
        raise RuntimeError(
            f"{record_id}: sensitive_spans "
            "must be a list."
        )

    validated_spans = []

    for span_position, span in enumerate(
        sensitive_spans,
        start=1,
    ):
        if not isinstance(span, dict):
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span_position} must be an object."
            )

        start = span.get("start")
        end = span.get("end")
        text = span.get("text")
        entity_type = span.get("type")

        if (
            not isinstance(start, int)
            or isinstance(start, bool)
        ):
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span_position} has an invalid start."
            )

        if (
            not isinstance(end, int)
            or isinstance(end, bool)
        ):
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span_position} has an invalid end."
            )

        if not isinstance(text, str):
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span_position} has invalid text."
            )

        if (
            not isinstance(entity_type, str)
            or not entity_type.strip()
        ):
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span_position} has an invalid type."
            )

        if start < 0:
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span_position} starts before zero."
            )

        if end <= start:
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span_position} has invalid offsets."
            )

        if end > len(prompt):
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span_position} exceeds prompt length."
            )

        actual_text = prompt[start:end]

        if actual_text != text:
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span_position} text does not match "
                "its prompt offsets."
            )

        validated_spans.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "type": entity_type.strip(),
            }
        )

    validated_spans.sort(
        key=lambda item: (
            item["start"],
            item["end"],
        )
    )

    for previous_span, current_span in zip(
        validated_spans,
        validated_spans[1:],
    ):
        if (
            current_span["start"]
            < previous_span["end"]
        ):
            raise RuntimeError(
                f"{record_id}: sensitive spans "
                "must not overlap."
            )

    return validated_spans


def tokenize_prompt(prompt: str) -> list[dict]:
    """Tokenize a prompt while preserving exact offsets."""
    tokens = []

    for match in TOKEN_PATTERN.finditer(prompt):
        tokens.append(
            {
                "text": match.group(0),
                "start": match.start(),
                "end": match.end(),
                "label": "O",
            }
        )

    if not tokens:
        raise RuntimeError(
            "Tokenization produced no tokens."
        )

    return tokens


def token_overlaps_span(
    token: dict,
    span: dict,
) -> bool:
    """Return whether a token overlaps a sensitive span."""
    return (
        token["start"] < span["end"]
        and token["end"] > span["start"]
    )


def apply_bio_labels(
    tokens: list[dict],
    sensitive_spans: list[dict],
    record_id: str,
) -> None:
    """Apply generic sensitive-entity BIO labels."""
    for span in sensitive_spans:
        overlapping_token_indexes = [
            token_index
            for token_index, token in enumerate(
                tokens
            )
            if token_overlaps_span(
                token,
                span,
            )
        ]

        if not overlapping_token_indexes:
            raise RuntimeError(
                f"{record_id}: sensitive span "
                f"{span['text']!r} is not covered "
                "by any token."
            )

        first_token_index = (
            overlapping_token_indexes[0]
        )

        last_token_index = (
            overlapping_token_indexes[-1]
        )

        first_token = tokens[
            first_token_index
        ]

        last_token = tokens[
            last_token_index
        ]

        if first_token["start"] != span["start"]:
            raise RuntimeError(
                f"{record_id}: tokenization does not "
                "preserve the start boundary for "
                f"sensitive span {span['text']!r}."
            )

        if last_token["end"] != span["end"]:
            raise RuntimeError(
                f"{record_id}: tokenization does not "
                "preserve the end boundary for "
                f"sensitive span {span['text']!r}."
            )

        for relative_position, token_index in enumerate(
            overlapping_token_indexes
        ):
            token = tokens[token_index]

            if token["label"] != "O":
                raise RuntimeError(
                    f"{record_id}: token belongs to "
                    "multiple sensitive spans."
                )

            if relative_position == 0:
                token["label"] = "B-SENSITIVE"

            else:
                token["label"] = "I-SENSITIVE"


def validate_bio_sequence(
    tokens: list[dict],
    record_id: str,
) -> None:
    """Validate the generated BIO label sequence."""
    previous_label = "O"

    for token_position, token in enumerate(
        tokens,
        start=1,
    ):
        label = token.get("label")

        if label not in VALID_BIO_LABELS:
            raise RuntimeError(
                f"{record_id}: token "
                f"{token_position} has an invalid "
                f"BIO label: {label!r}."
            )

        if (
            label == "I-SENSITIVE"
            and previous_label not in {
                "B-SENSITIVE",
                "I-SENSITIVE",
            }
        ):
            raise RuntimeError(
                f"{record_id}: I-SENSITIVE token "
                "does not follow a sensitive token."
            )

        previous_label = label


def reconstruct_sensitive_spans(
    prompt: str,
    tokens: list[dict],
) -> list[dict]:
    """Reconstruct entity boundaries from BIO labels."""
    reconstructed_spans = []
    active_start = None
    active_end = None

    for token in tokens:
        label = token["label"]

        if label == "B-SENSITIVE":
            if active_start is not None:
                reconstructed_spans.append(
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
                raise RuntimeError(
                    "Cannot reconstruct an "
                    "I-SENSITIVE token without a "
                    "preceding B-SENSITIVE token."
                )

            active_end = token["end"]

        elif active_start is not None:
            reconstructed_spans.append(
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
        reconstructed_spans.append(
            {
                "start": active_start,
                "end": active_end,
                "text": prompt[
                    active_start:active_end
                ],
            }
        )

    return reconstructed_spans


def verify_reconstructed_boundaries(
    prompt: str,
    tokens: list[dict],
    sensitive_spans: list[dict],
    record_id: str,
) -> None:
    """Ensure BIO labels preserve every gold boundary."""
    reconstructed_spans = (
        reconstruct_sensitive_spans(
            prompt,
            tokens,
        )
    )

    expected_boundaries = [
        (
            span["start"],
            span["end"],
            span["text"],
        )
        for span in sensitive_spans
    ]

    reconstructed_boundaries = [
        (
            span["start"],
            span["end"],
            span["text"],
        )
        for span in reconstructed_spans
    ]

    if (
        reconstructed_boundaries
        != expected_boundaries
    ):
        raise RuntimeError(
            f"{record_id}: reconstructed BIO "
            "boundaries do not match the gold "
            "sensitive spans."
        )


def build_entity_record(
    record: dict,
    split: str,
    record_position: int,
) -> dict:
    """Convert one action record into a BIO record."""
    record_id = record.get(
        "id",
        f"{split}:{record_position}",
    )

    if not isinstance(record_id, str):
        raise RuntimeError(
            f"{split}:{record_position}: "
            "record id must be a string."
        )

    prompt = record["prompt"]

    sensitive_spans = (
        validate_sensitive_spans(
            record,
            split,
            record_position,
        )
    )

    tokens = tokenize_prompt(prompt)

    apply_bio_labels(
        tokens,
        sensitive_spans,
        record_id,
    )

    validate_bio_sequence(
        tokens,
        record_id,
    )

    verify_reconstructed_boundaries(
        prompt,
        tokens,
        sensitive_spans,
        record_id,
    )

    return {
        "id": record_id,
        "prompt": prompt,
        "tokens": tokens,
        "gold_spans": sensitive_spans,
        "has_sensitive_entity": bool(
            sensitive_spans
        ),
        "source_action": record.get("action"),
        "source": record.get("source"),
        "source_split": split,
        "template_group": record.get(
            "template_group"
        ),
    }


def build_split(
    split: str,
    source_path: Path,
) -> tuple[list[dict], dict]:
    """Build one derived entity-localization split."""
    source_records = load_jsonl(
        source_path
    )

    output_records = []

    token_label_counts = Counter()
    span_type_counts = Counter()
    records_with_sensitive_entities = 0
    total_sensitive_spans = 0

    seen_record_ids = set()

    for record_position, record in enumerate(
        source_records,
        start=1,
    ):
        entity_record = build_entity_record(
            record,
            split,
            record_position,
        )

        record_id = entity_record["id"]

        if record_id in seen_record_ids:
            raise RuntimeError(
                f"{split}: duplicate record id "
                f"{record_id!r}."
            )

        seen_record_ids.add(record_id)

        if entity_record[
            "has_sensitive_entity"
        ]:
            records_with_sensitive_entities += 1

        for token in entity_record["tokens"]:
            token_label_counts[
                token["label"]
            ] += 1

        for span in entity_record["gold_spans"]:
            span_type_counts[
                span["type"]
            ] += 1

            total_sensitive_spans += 1

        output_records.append(
            entity_record
        )

    split_report = {
        "record_count": len(
            output_records
        ),
        "records_with_sensitive_entities": (
            records_with_sensitive_entities
        ),
        "records_without_sensitive_entities": (
            len(output_records)
            - records_with_sensitive_entities
        ),
        "total_tokens": sum(
            token_label_counts.values()
        ),
        "token_label_counts": {
            label: token_label_counts.get(
                label,
                0,
            )
            for label in [
                "B-SENSITIVE",
                "I-SENSITIVE",
                "O",
            ]
        },
        "total_sensitive_spans": (
            total_sensitive_spans
        ),
        "sensitive_span_types": dict(
            sorted(
                span_type_counts.items()
            )
        ),
    }

    return output_records, split_report


def write_jsonl(
    path: Path,
    records: list[dict],
) -> None:
    """Write records as deterministic JSON Lines."""
    with path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        for record in records:
            serialized_record = json.dumps(
                record,
                ensure_ascii=False,
                sort_keys=True,
            )

            output_file.write(
                serialized_record + "\n"
            )


def combine_reports(
    split_reports: dict[str, dict],
) -> dict:
    """Create a combined dataset summary."""
    combined_label_counts = Counter()
    combined_span_types = Counter()

    for split_report in split_reports.values():
        combined_label_counts.update(
            split_report[
                "token_label_counts"
            ]
        )

        combined_span_types.update(
            split_report[
                "sensitive_span_types"
            ]
        )

    return {
        "record_count": sum(
            report["record_count"]
            for report in split_reports.values()
        ),
        "records_with_sensitive_entities": sum(
            report[
                "records_with_sensitive_entities"
            ]
            for report in split_reports.values()
        ),
        "records_without_sensitive_entities": sum(
            report[
                "records_without_sensitive_entities"
            ]
            for report in split_reports.values()
        ),
        "total_tokens": sum(
            report["total_tokens"]
            for report in split_reports.values()
        ),
        "token_label_counts": {
            label: combined_label_counts.get(
                label,
                0,
            )
            for label in [
                "B-SENSITIVE",
                "I-SENSITIVE",
                "O",
            ]
        },
        "total_sensitive_spans": sum(
            report[
                "total_sensitive_spans"
            ]
            for report in split_reports.values()
        ),
        "sensitive_span_types": dict(
            sorted(
                combined_span_types.items()
            )
        ),
    }


def main() -> None:
    """Build and validate all entity datasets."""
    print(
        "Building contextual sensitive-entity "
        "datasets..."
    )

    print(
        "The untouched final holdout is not used."
    )

    OUTPUT_DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    split_reports = {}

    for split, source_path in (
        SOURCE_DATASET_PATHS.items()
    ):
        print(
            f"\nBuilding {split} split..."
        )

        output_records, split_report = (
            build_split(
                split,
                source_path,
            )
        )

        output_path = (
            OUTPUT_DATASET_PATHS[split]
        )

        write_jsonl(
            output_path,
            output_records,
        )

        split_reports[split] = (
            split_report
        )

        print(
            "  Records: "
            f"{split_report['record_count']}"
        )

        print(
            "  Records with sensitive entities: "
            f"{split_report[
                'records_with_sensitive_entities'
            ]}"
        )

        print(
            "  Sensitive spans: "
            f"{split_report[
                'total_sensitive_spans'
            ]}"
        )

        print(
            "  Tokens: "
            f"{split_report['total_tokens']}"
        )

        print(
            f"  Saved to: {output_path}"
        )

    combined_report = combine_reports(
        split_reports
    )

    report = {
        "dataset": (
            "contextual_sensitive_entity_bio_v1"
        ),
        "label_scheme": [
            "B-SENSITIVE",
            "I-SENSITIVE",
            "O",
        ],
        "tokenizer": (
            "Unicode words and individual "
            "non-whitespace punctuation"
        ),
        "source_directory": str(
            SOURCE_DATA_DIRECTORY
        ),
        "final_holdout_used": False,
        "splits": split_reports,
        "combined": combined_report,
        "validation_errors": [],
        "valid": True,
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
        "\nEntity dataset build completed."
    )

    print(
        "Total records: "
        f"{combined_report['record_count']}"
    )

    print(
        "Records with sensitive entities: "
        f"{combined_report[
            'records_with_sensitive_entities'
        ]}"
    )

    print(
        "Total sensitive spans: "
        f"{combined_report[
            'total_sensitive_spans'
        ]}"
    )

    print(
        "BIO label counts: "
        f"{combined_report[
            'token_label_counts'
        ]}"
    )

    print(
        f"Report saved to: {REPORT_PATH}"
    )


if __name__ == "__main__":
    main()