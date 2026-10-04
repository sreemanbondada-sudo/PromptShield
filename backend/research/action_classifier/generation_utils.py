import json
from collections import Counter
from pathlib import Path
from typing import Iterable


VALID_ACTIONS = {
    "allow",
    "review",
    "redact",
    "block",
}

VALID_SPLITS = {
    "train",
    "validation",
    "test",
}

VALID_SOURCES = {
    "manual",
    "generated",
    "adapted",
}


def normalize_prompt(prompt: str) -> str:
    """Normalize a prompt for duplicate checking."""
    return " ".join(
        prompt.casefold().split()
    )


def build_sensitive_spans(
    prompt: str,
    sensitive_values: (
        list[tuple[str, str]]
        | None
    ) = None,
) -> list[dict]:
    """Calculate exact offsets for sensitive values."""
    spans = []
    occupied_ranges = []

    for value, value_type in (
        sensitive_values or []
    ):
        search_start = 0

        while True:
            start = prompt.find(
                value,
                search_start,
            )

            if start == -1:
                break

            end = start + len(value)

            candidate_range = (
                start,
                end,
            )

            overlaps = any(
                start < existing_end
                and end > existing_start
                for (
                    existing_start,
                    existing_end,
                )
                in occupied_ranges
            )

            if not overlaps:
                spans.append(
                    {
                        "start": start,
                        "end": end,
                        "text": value,
                        "type": value_type,
                    }
                )

                occupied_ranges.append(
                    candidate_range
                )

            search_start = end

        if not any(
            span["text"] == value
            and span["type"] == value_type
            for span in spans
        ):
            raise ValueError(
                f"Sensitive value {value!r} "
                "was not found in the prompt."
            )

    return sorted(
        spans,
        key=lambda span: (
            span["start"],
            span["end"],
        ),
    )


def create_record(
    record_number: int,
    prompt: str,
    action: str,
    rationale: str,
    template_group: str,
    split: str,
    sensitive_values: (
        list[tuple[str, str]]
        | None
    ) = None,
    source: str = "generated",
) -> dict:
    """Create one schema-compatible record."""
    if action not in VALID_ACTIONS:
        raise ValueError(
            f"Unsupported action: {action!r}."
        )

    if split not in VALID_SPLITS:
        raise ValueError(
            f"Unsupported split: {split!r}."
        )

    if source not in VALID_SOURCES:
        raise ValueError(
            f"Unsupported source: {source!r}."
        )

    cleaned_prompt = prompt.strip()

    if not cleaned_prompt:
        raise ValueError(
            "Prompt must not be empty."
        )

    spans = build_sensitive_spans(
        cleaned_prompt,
        sensitive_values,
    )

    if action == "redact" and not spans:
        raise ValueError(
            "Redact records require at least "
            "one sensitive span."
        )

    if (
        action in {"allow", "review"}
        and spans
    ):
        raise ValueError(
            f"{action} records cannot contain "
            "sensitive spans."
        )

    return {
        "id": f"psac_{record_number:06d}",
        "prompt": cleaned_prompt,
        "action": action,
        "sensitive_spans": spans,
        "rationale": rationale,
        "template_group": template_group,
        "source": source,
        "split": split,
    }


def generate_variants(
    base_prompts: Iterable[str],
    wrappers: Iterable[str],
    target_count: int,
) -> list[str]:
    """
    Generate deterministic wording variations.

    Every wrapper must contain the {content} field.
    """
    if target_count < 1:
        raise ValueError(
            "target_count must be positive."
        )

    variants = []
    normalized_variants = set()

    for base_prompt in base_prompts:
        cleaned_base = base_prompt.strip()

        if not cleaned_base:
            raise ValueError(
                "Base prompts must not be empty."
            )

        for wrapper in wrappers:
            if "{content}" not in wrapper:
                raise ValueError(
                    "Every wrapper must contain "
                    "{content}."
                )

            candidate = wrapper.format(
                content=cleaned_base
            ).strip()

            normalized_candidate = (
                normalize_prompt(candidate)
            )

            if (
                normalized_candidate
                in normalized_variants
            ):
                continue

            variants.append(candidate)

            normalized_variants.add(
                normalized_candidate
            )

            if len(variants) == target_count:
                return variants

    raise ValueError(
        "The supplied prompts and wrappers "
        f"generated only {len(variants)} unique "
        f"variants; {target_count} were required."
    )


def assert_unique_records(
    records: list[dict],
) -> None:
    """Reject duplicate IDs and prompts."""
    identifiers = [
        record["id"]
        for record in records
    ]

    duplicate_identifiers = [
        identifier
        for identifier, count
        in Counter(identifiers).items()
        if count > 1
    ]

    if duplicate_identifiers:
        raise ValueError(
            "Duplicate record identifiers: "
            f"{duplicate_identifiers}."
        )

    normalized_prompts = [
        normalize_prompt(
            record["prompt"]
        )
        for record in records
    ]

    duplicate_prompts = [
        prompt
        for prompt, count
        in Counter(
            normalized_prompts
        ).items()
        if count > 1
    ]

    if duplicate_prompts:
        raise ValueError(
            "Duplicate normalized prompts were "
            "generated."
        )


def assert_template_isolation(
    records: list[dict],
) -> None:
    """Ensure template groups do not cross splits."""
    group_splits = {}

    for record in records:
        template_group = record[
            "template_group"
        ]

        split = record["split"]

        group_splits.setdefault(
            template_group,
            set(),
        ).add(split)

    leaking_groups = {
        group: sorted(splits)
        for group, splits
        in group_splits.items()
        if len(splits) > 1
    }

    if leaking_groups:
        raise ValueError(
            "Template groups leak across splits: "
            f"{leaking_groups}."
        )


def calculate_distribution(
    records: list[dict],
) -> dict:
    """Calculate split and action counts."""
    distribution = {}

    for split in [
        "train",
        "validation",
        "test",
    ]:
        split_records = [
            record
            for record in records
            if record["split"] == split
        ]

        action_counts = Counter(
            record["action"]
            for record in split_records
        )

        distribution[split] = {
            "total": len(split_records),
            "actions": {
                action: action_counts.get(
                    action,
                    0,
                )
                for action in [
                    "allow",
                    "review",
                    "redact",
                    "block",
                ]
            },
        }

    return distribution


def assert_distribution(
    records: list[dict],
    expected_per_split: dict[
        str,
        dict[str, int],
    ],
) -> None:
    """Enforce the expected class distribution."""
    actual_distribution = (
        calculate_distribution(records)
    )

    for split, expected_actions in (
        expected_per_split.items()
    ):
        actual_actions = (
            actual_distribution[split][
                "actions"
            ]
        )

        if actual_actions != expected_actions:
            raise ValueError(
                f"Unexpected {split} action "
                "distribution. "
                f"Expected {expected_actions}, "
                f"received {actual_actions}."
            )


def write_jsonl(
    destination: Path,
    records: list[dict],
) -> None:
    """Write records as deterministic JSON Lines."""
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with destination.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        for record in records:
            output_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

            output_file.write("\n")