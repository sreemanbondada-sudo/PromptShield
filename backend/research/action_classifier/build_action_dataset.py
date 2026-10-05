"""Build the complete contextual action dataset."""

from pathlib import Path

from allow_families import (
    ALLOW_FAMILIES,
    NEUTRAL_WRAPPERS,
)
from block_families import BLOCK_FAMILIES
from generation_utils import (
    assert_distribution,
    assert_template_isolation,
    assert_unique_records,
    calculate_distribution,
    create_record,
    generate_variants,
    write_jsonl,
)
from redact_families import REDACT_FAMILIES
from review_families import REVIEW_FAMILIES


BASE_DIRECTORY = Path(__file__).resolve().parent
DATA_DIRECTORY = BASE_DIRECTORY / "data"

DATASET_PATHS = {
    "train": DATA_DIRECTORY / "train.jsonl",
    "validation": (
        DATA_DIRECTORY / "validation.jsonl"
    ),
    "test": DATA_DIRECTORY / "test.jsonl",
}

EXPECTED_DISTRIBUTION = {
    "train": {
        "allow": 150,
        "review": 150,
        "redact": 150,
        "block": 150,
    },
    "validation": {
        "allow": 25,
        "review": 25,
        "redact": 25,
        "block": 25,
    },
    "test": {
        "allow": 25,
        "review": 25,
        "redact": 25,
        "block": 25,
    },
}

CATALOGS = [
    (
        "allow",
        ALLOW_FAMILIES,
    ),
    (
        "review",
        REVIEW_FAMILIES,
    ),
    (
        "redact",
        REDACT_FAMILIES,
    ),
    (
        "block",
        BLOCK_FAMILIES,
    ),
]


def generate_family_records(
    action: str,
    families: list[dict],
    starting_identifier: int,
) -> tuple[list[dict], int]:
    """Generate records for one action catalog."""
    records = []
    next_identifier = starting_identifier

    for family in families:
        prompts = generate_variants(
            base_prompts=family["base_prompts"],
            wrappers=NEUTRAL_WRAPPERS,
            target_count=family["target_count"],
        )

        sensitive_values = family.get(
            "sensitive_values"
        )

        for prompt in prompts:
            record = create_record(
                record_number=next_identifier,
                prompt=prompt,
                action=action,
                rationale=family["rationale"],
                template_group=family["name"],
                split=family["split"],
                sensitive_values=sensitive_values,
            )

            records.append(record)
            next_identifier += 1

    return records, next_identifier


def build_records() -> list[dict]:
    """Generate and validate all 800 records."""
    all_records = []
    next_identifier = 1

    for action, families in CATALOGS:
        print(
            f"Generating {action} records..."
        )

        action_records, next_identifier = (
            generate_family_records(
                action=action,
                families=families,
                starting_identifier=(
                    next_identifier
                ),
            )
        )

        print(
            f"  Generated "
            f"{len(action_records)} records."
        )

        all_records.extend(action_records)

    if len(all_records) != 800:
        raise ValueError(
            "Expected 800 total records, "
            f"received {len(all_records)}."
        )

    expected_last_identifier = "psac_000800"

    if all_records[-1]["id"] != (
        expected_last_identifier
    ):
        raise ValueError(
            "Unexpected final record identifier. "
            f"Expected {expected_last_identifier}, "
            f"received {all_records[-1]['id']}."
        )

    assert_unique_records(all_records)
    assert_template_isolation(all_records)

    assert_distribution(
        records=all_records,
        expected_per_split=(
            EXPECTED_DISTRIBUTION
        ),
    )

    for record in all_records:
        if record["action"] == "redact":
            if not record["sensitive_spans"]:
                raise ValueError(
                    "Redact record has no sensitive "
                    f"spans: {record['id']}."
                )

        elif record["sensitive_spans"]:
            raise ValueError(
                "Only Redact records may contain "
                "sensitive spans in this dataset: "
                f"{record['id']}."
            )

    return all_records


def write_dataset(records: list[dict]) -> None:
    """Write each dataset split to JSON Lines."""
    for split, destination in (
        DATASET_PATHS.items()
    ):
        split_records = [
            record
            for record in records
            if record["split"] == split
        ]

        write_jsonl(
            destination=destination,
            records=split_records,
        )

        print(
            f"Wrote {len(split_records)} "
            f"{split} records to: "
            f"{destination}"
        )


def print_distribution(
    records: list[dict],
) -> None:
    """Print a readable dataset summary."""
    distribution = calculate_distribution(
        records
    )

    print()
    print("Contextual action dataset summary")
    print("---------------------------------")

    total_records = 0

    for split in [
        "train",
        "validation",
        "test",
    ]:
        split_data = distribution[split]
        total_records += split_data["total"]

        print()
        print(
            f"{split}: "
            f"{split_data['total']} records"
        )

        for action in [
            "allow",
            "review",
            "redact",
            "block",
        ]:
            print(
                f"  {action}: "
                f"{split_data['actions'][action]}"
            )

    print()
    print(f"Total records: {total_records}")


def main() -> None:
    """Build, validate and write the dataset."""
    print(
        "Building the complete contextual "
        "action dataset..."
    )

    records = build_records()

    print(
        "Dataset uniqueness, distribution and "
        "template isolation checks passed."
    )

    write_dataset(records)
    print_distribution(records)

    print()
    print(
        "Complete contextual action dataset "
        "generated successfully."
    )


if __name__ == "__main__":
    main()