import csv
import json
import re
from pathlib import Path


BASE_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = BASE_DIRECTORY / "data"
EXTERNAL_DIRECTORY = DATA_DIRECTORY / "external"

SCAMBENCH_PATHS = {
    "train": (
        EXTERNAL_DIRECTORY / "scambench_train.csv"
    ),
    "validation": (
        EXTERNAL_DIRECTORY / "scambench_validation.csv"
    ),
    "test": (
        EXTERNAL_DIRECTORY / "scambench_test.csv"
    ),
}

EXPECTED_COUNTS = {
    "train": 8000,
    "validation": 1000,
    "test": 1500,
}

REQUIRED_COLUMNS = {
    "prompt",
    "label",
    "category",
    "source",
    "language",
    "conversation_turns",
}

MAX_PROMPT_LENGTH = 5000


def normalize_prompt(prompt: str) -> str:
    """Normalize a prompt for exact duplicate checks."""
    return re.sub(
        r"\s+",
        " ",
        prompt,
    ).strip().casefold()


def load_rows(path: Path) -> list[dict]:
    """Load CSV records."""
    with path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as input_file:
        return list(csv.DictReader(input_file))


def load_existing_fingerprints() -> dict[str, set[str]]:
    """Load fingerprints from non-ScamBench CSV files."""
    fingerprints_by_file = {}

    csv_paths = [
        DATA_DIRECTORY / "prompts.csv",
        DATA_DIRECTORY / "challenge_prompts.csv",
        DATA_DIRECTORY / "hard_negative_prompts.csv",
        EXTERNAL_DIRECTORY / "deepset_train.csv",
        EXTERNAL_DIRECTORY / "deepset_test.csv",
        EXTERNAL_DIRECTORY / "neuralchemy_core_train.csv",
        EXTERNAL_DIRECTORY / "neuralchemy_core_validation.csv",
        EXTERNAL_DIRECTORY / "neuralchemy_core_test.csv",
    ]

    for path in csv_paths:
        if not path.exists():
            continue

        rows = load_rows(path)
        fingerprints = set()

        for row in rows:
            prompt = row.get("prompt", "")
            fingerprint = normalize_prompt(prompt)

            if fingerprint:
                fingerprints.add(fingerprint)

        fingerprints_by_file[path.name] = fingerprints

    return fingerprints_by_file


def validate_split(
    split_name: str,
    path: Path,
) -> tuple[set[str], dict]:
    """Validate one normalized ScamBench split."""
    if not path.exists():
        raise RuntimeError(
            f"Missing ScamBench file: {path}"
        )

    rows = load_rows(path)

    if len(rows) != EXPECTED_COUNTS[split_name]:
        raise RuntimeError(
            f"{split_name} contains {len(rows)} rows; "
            f"expected {EXPECTED_COUNTS[split_name]}."
        )

    if not rows:
        raise RuntimeError(
            f"{split_name} is empty."
        )

    missing_columns = (
        REQUIRED_COLUMNS - set(rows[0].keys())
    )

    if missing_columns:
        raise RuntimeError(
            f"{split_name} is missing columns: "
            f"{sorted(missing_columns)}"
        )

    fingerprints = set()
    label_counts = {
        "0": 0,
        "1": 0,
    }

    category_counts = {}

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        prompt = row["prompt"].strip()
        label = row["label"]
        category = row["category"].strip()
        source = row["source"].strip()
        language = row["language"].strip()
        conversation_turns = row[
            "conversation_turns"
        ]

        if not prompt:
            raise RuntimeError(
                f"{split_name} row {row_number} "
                "contains an empty prompt."
            )

        if len(prompt) > MAX_PROMPT_LENGTH:
            raise RuntimeError(
                f"{split_name} row {row_number} "
                "exceeds the prompt-length limit."
            )

        if label not in {"0", "1"}:
            raise RuntimeError(
                f"{split_name} row {row_number} "
                f"has invalid label {label!r}."
            )

        if not category:
            raise RuntimeError(
                f"{split_name} row {row_number} "
                "has no category."
            )

        if source != "shaw/scambench-training":
            raise RuntimeError(
                f"{split_name} row {row_number} "
                "has an unexpected source."
            )

        if language != "en":
            raise RuntimeError(
                f"{split_name} row {row_number} "
                "is not marked as English."
            )

        try:
            parsed_turns = int(conversation_turns)
        except ValueError as error:
            raise RuntimeError(
                f"{split_name} row {row_number} "
                "has invalid conversation turns."
            ) from error

        if parsed_turns < 1:
            raise RuntimeError(
                f"{split_name} row {row_number} "
                "contains no user turns."
            )

        fingerprint = normalize_prompt(prompt)

        if fingerprint in fingerprints:
            raise RuntimeError(
                f"Duplicate prompt inside "
                f"{split_name}: {prompt[:100]!r}"
            )

        fingerprints.add(fingerprint)
        label_counts[label] += 1

        category_counts[category] = (
            category_counts.get(category, 0) + 1
        )

    return fingerprints, {
        "records": len(rows),
        "labels": label_counts,
        "categories": category_counts,
    }


def validate_scambench_dataset() -> None:
    """Validate ScamBench data and leakage boundaries."""
    split_fingerprints = {}
    split_reports = {}

    for split_name, path in SCAMBENCH_PATHS.items():
        fingerprints, report = validate_split(
            split_name,
            path,
        )

        split_fingerprints[split_name] = fingerprints
        split_reports[split_name] = report

    split_names = list(split_fingerprints)

    for first_index, first_name in enumerate(
        split_names
    ):
        for second_name in split_names[
            first_index + 1:
        ]:
            overlap = (
                split_fingerprints[first_name]
                & split_fingerprints[second_name]
            )

            if overlap:
                raise RuntimeError(
                    f"{first_name} and {second_name} "
                    f"contain {len(overlap)} overlapping "
                    "prompts."
                )

    existing_fingerprints = (
        load_existing_fingerprints()
    )

    external_overlaps = {}

    for split_name, fingerprints in (
        split_fingerprints.items()
    ):
        external_overlaps[split_name] = {}

        for file_name, existing_values in (
            existing_fingerprints.items()
        ):
            overlap_count = len(
                fingerprints & existing_values
            )

            external_overlaps[split_name][
                file_name
            ] = overlap_count

    report = {
        "valid": True,
        "splits": split_reports,
        "cross_split_overlap": 0,
        "existing_dataset_overlaps": (
            external_overlaps
        ),
    }

    report_path = (
        EXTERNAL_DIRECTORY
        / "scambench_validation_report.json"
    )

    report_path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )

    print("ScamBench dataset validation passed.")
    print(f"Validation report: {report_path}")

    for split_name, split_report in (
        split_reports.items()
    ):
        print(
            f"{split_name}: "
            f"{split_report['records']} records, "
            f"labels={split_report['labels']}, "
            f"categories="
            f"{len(split_report['categories'])}"
        )

    total_existing_overlap = sum(
        overlap_count
        for split_results in (
            external_overlaps.values()
        )
        for overlap_count in split_results.values()
    )

    print(
        "Exact overlaps with existing datasets: "
        f"{total_existing_overlap}"
    )


if __name__ == "__main__":
    validate_scambench_dataset()