import csv
import json
from collections import Counter
from pathlib import Path

from prepare_external_datasets import (
    OUTPUT_FIELDS,
    calculate_prompt_hash,
)


BASE_DIRECTORY = Path(__file__).parent

EXTERNAL_DATA_DIRECTORY = (
    BASE_DIRECTORY / "data" / "external"
)

REPORT_PATH = (
    EXTERNAL_DATA_DIRECTORY
    / "validation_report.json"
)

DATASET_FILES = {
    "deepset_train": {
        "path": (
            EXTERNAL_DATA_DIRECTORY
            / "deepset_train.csv"
        ),
        "source": "deepset/prompt-injections",
        "split": "train",
    },
    "deepset_test": {
        "path": (
            EXTERNAL_DATA_DIRECTORY
            / "deepset_test.csv"
        ),
        "source": "deepset/prompt-injections",
        "split": "test",
    },
    "neuralchemy_train": {
        "path": (
            EXTERNAL_DATA_DIRECTORY
            / "neuralchemy_core_train.csv"
        ),
        "source": (
            "neuralchemy/Prompt-injection-dataset"
        ),
        "split": "train",
    },
    "neuralchemy_validation": {
        "path": (
            EXTERNAL_DATA_DIRECTORY
            / "neuralchemy_core_validation.csv"
        ),
        "source": (
            "neuralchemy/Prompt-injection-dataset"
        ),
        "split": "validation",
    },
    "neuralchemy_test": {
        "path": (
            EXTERNAL_DATA_DIRECTORY
            / "neuralchemy_core_test.csv"
        ),
        "source": (
            "neuralchemy/Prompt-injection-dataset"
        ),
        "split": "test",
    },
}


def read_and_validate_file(
    file_name: str,
    configuration: dict,
) -> dict:
    """Validate one normalized external CSV file."""
    file_path = configuration["path"]

    if not file_path.exists():
        raise RuntimeError(
            f"Required dataset file is missing: "
            f"{file_path}"
        )

    with file_path.open(
        encoding="utf-8",
        newline="",
    ) as input_file:
        reader = csv.DictReader(input_file)

        if reader.fieldnames is None:
            raise RuntimeError(
                f"{file_name} has no CSV header."
            )

        missing_fields = (
            set(OUTPUT_FIELDS)
            - set(reader.fieldnames)
        )

        if missing_fields:
            raise RuntimeError(
                f"{file_name} is missing fields: "
                f"{sorted(missing_fields)}"
            )

        records = list(reader)

    if not records:
        raise RuntimeError(
            f"{file_name} contains no records."
        )

    label_counts = Counter()
    category_counts = Counter()
    prompt_hashes = set()
    group_ids = set()

    for row_number, record in enumerate(
        records,
        start=2,
    ):
        prompt = record["prompt"].strip()

        if not prompt:
            raise RuntimeError(
                f"{file_name} contains an empty "
                f"prompt at row {row_number}."
            )

        try:
            label = int(record["label"])

        except ValueError as error:
            raise RuntimeError(
                f"{file_name} contains an invalid "
                f"label at row {row_number}."
            ) from error

        if label not in {0, 1}:
            raise RuntimeError(
                f"{file_name} contains a non-binary "
                f"label at row {row_number}."
            )

        if (
            record["source_dataset"]
            != configuration["source"]
        ):
            raise RuntimeError(
                f"{file_name} has an incorrect source "
                f"at row {row_number}."
            )

        if (
            record["original_split"]
            != configuration["split"]
        ):
            raise RuntimeError(
                f"{file_name} has an incorrect split "
                f"at row {row_number}."
            )

        calculated_hash = calculate_prompt_hash(
            prompt
        )

        if record["prompt_hash"] != calculated_hash:
            raise RuntimeError(
                f"{file_name} has an invalid prompt "
                f"hash at row {row_number}."
            )

        if calculated_hash in prompt_hashes:
            raise RuntimeError(
                f"{file_name} contains a duplicate "
                f"prompt at row {row_number}."
            )

        prompt_hashes.add(calculated_hash)

        group_id = record["group_id"].strip()

        if group_id:
            group_ids.add(group_id)

        label_counts[str(label)] += 1

        category = (
            record["category"].strip()
            or "unknown"
        )

        category_counts[category] += 1

    return {
        "record_count": len(records),
        "label_counts": dict(
            sorted(label_counts.items())
        ),
        "category_counts": dict(
            sorted(category_counts.items())
        ),
        "prompt_hashes": prompt_hashes,
        "group_ids": group_ids,
    }


def overlap_count(
    first_values: set[str],
    second_values: set[str],
) -> int:
    """Return the number of shared values."""
    return len(
        first_values & second_values
    )


def require_no_overlap(
    first_name: str,
    first_values: set[str],
    second_name: str,
    second_values: set[str],
    value_type: str,
) -> None:
    """Reject leakage between official splits."""
    count = overlap_count(
        first_values,
        second_values,
    )

    if count:
        raise RuntimeError(
            f"Detected {count} shared {value_type} "
            f"values between {first_name} and "
            f"{second_name}."
        )


def main() -> None:
    """Validate prepared external datasets."""
    results = {}

    for file_name, configuration in (
        DATASET_FILES.items()
    ):
        results[file_name] = (
            read_and_validate_file(
                file_name,
                configuration,
            )
        )

    require_no_overlap(
        "deepset_train",
        results["deepset_train"][
            "prompt_hashes"
        ],
        "deepset_test",
        results["deepset_test"][
            "prompt_hashes"
        ],
        "prompt",
    )

    neuralchemy_splits = [
        "neuralchemy_train",
        "neuralchemy_validation",
        "neuralchemy_test",
    ]

    for index, first_name in enumerate(
        neuralchemy_splits
    ):
        for second_name in neuralchemy_splits[
            index + 1:
        ]:
            require_no_overlap(
                first_name,
                results[first_name][
                    "prompt_hashes"
                ],
                second_name,
                results[second_name][
                    "prompt_hashes"
                ],
                "prompt",
            )

            require_no_overlap(
                first_name,
                results[first_name][
                    "group_ids"
                ],
                second_name,
                results[second_name][
                    "group_ids"
                ],
                "group",
            )

    cross_source_overlap = overlap_count(
        results["neuralchemy_train"][
            "prompt_hashes"
        ],
        results["deepset_test"][
            "prompt_hashes"
        ],
    )

    report = {
        "valid": True,
        "files": {
            file_name: {
                "record_count": result[
                    "record_count"
                ],
                "label_counts": result[
                    "label_counts"
                ],
                "category_counts": result[
                    "category_counts"
                ],
            }
            for file_name, result in results.items()
        },
        "leakage_checks": {
            "official_split_prompt_overlap": 0,
            "official_split_group_overlap": 0,
            (
                "neuralchemy_train_to_"
                "deepset_test_prompt_overlap"
            ): cross_source_overlap,
        },
    }

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as report_file:
        json.dump(
            report,
            report_file,
            indent=2,
            sort_keys=True,
        )

        report_file.write("\n")

    print("External dataset validation passed.")
    print(
        f"Validation report: {REPORT_PATH}"
    )

    for file_name, result in results.items():
        print(
            f"{file_name}: "
            f"{result['record_count']} records, "
            f"labels={result['label_counts']}"
        )

    print(
        "NeurAlchemy-train to deepset-test "
        f"overlap: {cross_source_overlap}"
    )


if __name__ == "__main__":
    main()