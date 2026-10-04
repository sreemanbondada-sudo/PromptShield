import json
import re
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIRECTORY = Path(__file__).parent

DATA_DIRECTORY = BASE_DIRECTORY / "data"

DATASET_FILES = {
    "train": DATA_DIRECTORY / "train.jsonl",
    "validation": DATA_DIRECTORY / "validation.jsonl",
    "test": DATA_DIRECTORY / "test.jsonl",
}

VALID_ACTIONS = {
    "allow",
    "review",
    "redact",
    "block",
}

VALID_SOURCES = {
    "manual",
    "generated",
    "adapted",
}

REQUIRED_FIELDS = {
    "id",
    "prompt",
    "action",
    "sensitive_spans",
    "rationale",
    "template_group",
    "source",
    "split",
}

ID_PATTERN = re.compile(
    r"^psac_[0-9]{6}$"
)

GROUP_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*$"
)


def normalize_prompt(prompt: str) -> str:
    """Normalize prompts for exact duplicate detection."""
    return " ".join(
        prompt.casefold().split()
    )


def read_jsonl(
    dataset_path: Path,
) -> tuple[list[dict], list[str]]:
    """Read records from a JSON Lines file."""
    records = []
    errors = []

    if not dataset_path.exists():
        return [], [
            f"Missing dataset file: {dataset_path}"
        ]

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
                errors.append(
                    f"{dataset_path.name}:{line_number}: "
                    "blank lines are not permitted."
                )
                continue

            try:
                record = json.loads(line)

            except json.JSONDecodeError as error:
                errors.append(
                    f"{dataset_path.name}:{line_number}: "
                    f"invalid JSON: {error.msg}."
                )
                continue

            if not isinstance(record, dict):
                errors.append(
                    f"{dataset_path.name}:{line_number}: "
                    "each record must be a JSON object."
                )
                continue

            record["_line_number"] = line_number
            records.append(record)

    return records, errors


def validate_sensitive_span(
    span: object,
    prompt: str,
    record_location: str,
    span_index: int,
) -> list[str]:
    """Validate one sensitive-data span."""
    errors = []

    if not isinstance(span, dict):
        return [
            f"{record_location}: sensitive span "
            f"{span_index} must be an object."
        ]

    required_span_fields = {
        "start",
        "end",
        "text",
        "type",
    }

    span_fields = set(span)

    missing_fields = (
        required_span_fields - span_fields
    )

    unexpected_fields = (
        span_fields - required_span_fields
    )

    if missing_fields:
        errors.append(
            f"{record_location}: sensitive span "
            f"{span_index} is missing fields: "
            f"{sorted(missing_fields)}."
        )

    if unexpected_fields:
        errors.append(
            f"{record_location}: sensitive span "
            f"{span_index} has unexpected fields: "
            f"{sorted(unexpected_fields)}."
        )

    if missing_fields:
        return errors

    start = span["start"]
    end = span["end"]
    span_text = span["text"]
    span_type = span["type"]

    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or start < 0
    ):
        errors.append(
            f"{record_location}: sensitive span "
            f"{span_index} has an invalid start."
        )

    if (
        not isinstance(end, int)
        or isinstance(end, bool)
        or end < 1
    ):
        errors.append(
            f"{record_location}: sensitive span "
            f"{span_index} has an invalid end."
        )

    if (
        not isinstance(span_text, str)
        or not span_text
    ):
        errors.append(
            f"{record_location}: sensitive span "
            f"{span_index} must contain text."
        )

    if (
        not isinstance(span_type, str)
        or not GROUP_PATTERN.fullmatch(span_type)
    ):
        errors.append(
            f"{record_location}: sensitive span "
            f"{span_index} has an invalid type."
        )

    offsets_are_integers = (
        isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
    )

    if offsets_are_integers:
        if start >= end:
            errors.append(
                f"{record_location}: sensitive span "
                f"{span_index} must have start < end."
            )

        elif end > len(prompt):
            errors.append(
                f"{record_location}: sensitive span "
                f"{span_index} exceeds prompt length."
            )

        elif (
            isinstance(span_text, str)
            and prompt[start:end] != span_text
        ):
            errors.append(
                f"{record_location}: sensitive span "
                f"{span_index} text does not match "
                "the specified offsets."
            )

    return errors


def validate_record(
    record: dict,
    expected_split: str,
    dataset_name: str,
) -> list[str]:
    """Validate one action-classification record."""
    errors = []

    line_number = record.get(
        "_line_number",
        "?",
    )

    location = (
        f"{dataset_name}:{line_number}"
    )

    record_fields = (
        set(record) - {"_line_number"}
    )

    missing_fields = (
        REQUIRED_FIELDS - record_fields
    )

    unexpected_fields = (
        record_fields - REQUIRED_FIELDS
    )

    if missing_fields:
        errors.append(
            f"{location}: missing fields: "
            f"{sorted(missing_fields)}."
        )

    if unexpected_fields:
        errors.append(
            f"{location}: unexpected fields: "
            f"{sorted(unexpected_fields)}."
        )

    if missing_fields:
        return errors

    record_id = record["id"]
    prompt = record["prompt"]
    action = record["action"]
    sensitive_spans = record[
        "sensitive_spans"
    ]
    rationale = record["rationale"]
    template_group = record[
        "template_group"
    ]
    source = record["source"]
    split = record["split"]

    if (
        not isinstance(record_id, str)
        or not ID_PATTERN.fullmatch(record_id)
    ):
        errors.append(
            f"{location}: invalid record id."
        )

    if (
        not isinstance(prompt, str)
        or not 1 <= len(prompt) <= 5000
    ):
        errors.append(
            f"{location}: prompt length must be "
            "between 1 and 5000 characters."
        )

        prompt = (
            prompt
            if isinstance(prompt, str)
            else ""
        )

    if action not in VALID_ACTIONS:
        errors.append(
            f"{location}: invalid action "
            f"{action!r}."
        )

    if not isinstance(sensitive_spans, list):
        errors.append(
            f"{location}: sensitive_spans "
            "must be a list."
        )

        sensitive_spans = []

    if (
        action == "redact"
        and not sensitive_spans
    ):
        errors.append(
            f"{location}: redact records must "
            "contain at least one sensitive span."
        )

    if (
        action in {"allow", "review"}
        and sensitive_spans
    ):
        errors.append(
            f"{location}: {action} records must "
            "not contain sensitive spans."
        )

    validated_ranges = []

    for span_index, span in enumerate(
        sensitive_spans,
        start=1,
    ):
        errors.extend(
            validate_sensitive_span(
                span=span,
                prompt=prompt,
                record_location=location,
                span_index=span_index,
            )
        )

        if (
            isinstance(span, dict)
            and isinstance(
                span.get("start"),
                int,
            )
            and isinstance(
                span.get("end"),
                int,
            )
        ):
            validated_ranges.append(
                (
                    span["start"],
                    span["end"],
                )
            )

    sorted_ranges = sorted(validated_ranges)

    for previous_range, current_range in zip(
        sorted_ranges,
        sorted_ranges[1:],
    ):
        if current_range[0] < previous_range[1]:
            errors.append(
                f"{location}: sensitive spans "
                "must not overlap."
            )
            break

    if (
        not isinstance(rationale, str)
        or not 10 <= len(rationale) <= 500
    ):
        errors.append(
            f"{location}: rationale length must "
            "be between 10 and 500 characters."
        )

    if (
        not isinstance(template_group, str)
        or not GROUP_PATTERN.fullmatch(
            template_group
        )
    ):
        errors.append(
            f"{location}: invalid template_group."
        )

    if source not in VALID_SOURCES:
        errors.append(
            f"{location}: invalid source "
            f"{source!r}."
        )

    if split != expected_split:
        errors.append(
            f"{location}: split must be "
            f"{expected_split!r}, not {split!r}."
        )

    return errors


def validate_datasets() -> dict:
    """Validate all research dataset splits."""
    all_records = []
    errors = []
    split_counts = {}
    action_counts = {}

    for split, dataset_path in (
        DATASET_FILES.items()
    ):
        records, read_errors = read_jsonl(
            dataset_path
        )

        errors.extend(read_errors)

        split_counts[split] = len(records)

        split_action_counts = Counter()

        for record in records:
            errors.extend(
                validate_record(
                    record=record,
                    expected_split=split,
                    dataset_name=(
                        dataset_path.name
                    ),
                )
            )

            if record.get("action") in (
                VALID_ACTIONS
            ):
                split_action_counts[
                    record["action"]
                ] += 1

            all_records.append(
                {
                    **record,
                    "_split_name": split,
                    "_dataset_name": (
                        dataset_path.name
                    ),
                }
            )

        action_counts[split] = dict(
            sorted(
                split_action_counts.items()
            )
        )

    id_locations = defaultdict(list)
    prompt_locations = defaultdict(list)
    group_splits = defaultdict(set)

    for record in all_records:
        location = (
            f"{record['_dataset_name']}:"
            f"{record.get('_line_number', '?')}"
        )

        record_id = record.get("id")

        if isinstance(record_id, str):
            id_locations[record_id].append(
                location
            )

        prompt = record.get("prompt")

        if isinstance(prompt, str) and prompt:
            normalized_prompt = (
                normalize_prompt(prompt)
            )

            prompt_locations[
                normalized_prompt
            ].append(location)

        template_group = record.get(
            "template_group"
        )

        if isinstance(template_group, str):
            group_splits[
                template_group
            ].add(
                record["_split_name"]
            )

    for record_id, locations in (
        id_locations.items()
    ):
        if len(locations) > 1:
            errors.append(
                f"Duplicate id {record_id!r}: "
                f"{locations}."
            )

    for locations in prompt_locations.values():
        if len(locations) > 1:
            errors.append(
                "Duplicate normalized prompt: "
                f"{locations}."
            )

    for template_group, splits in (
        group_splits.items()
    ):
        if len(splits) > 1:
            errors.append(
                f"Template group "
                f"{template_group!r} leaks across "
                f"splits: {sorted(splits)}."
            )

    return {
        "valid": not errors,
        "errors": errors,
        "total_records": len(all_records),
        "split_counts": split_counts,
        "action_counts": action_counts,
    }


def main() -> None:
    """Run validation and print a summary."""
    report = validate_datasets()

    print(
        "PromptShield contextual action "
        "dataset validation"
    )

    print(
        f"Total records: "
        f"{report['total_records']}"
    )

    for split in DATASET_FILES:
        print(
            f"{split}: "
            f"{report['split_counts'][split]} "
            "records, actions="
            f"{report['action_counts'][split]}"
        )

    if not report["valid"]:
        print()
        print("Validation failed:")

        for error in report["errors"]:
            print(f"- {error}")

        raise SystemExit(1)

    print()
    print("Dataset validation passed.")


if __name__ == "__main__":
    main()