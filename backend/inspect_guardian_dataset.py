import json
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi


BASE_DIRECTORY = Path(__file__).parent
REPORT_DIRECTORY = BASE_DIRECTORY / "data" / "external"
REPORT_PATH = (
    REPORT_DIRECTORY / "guardian_dataset_metadata_report.json"
)

DATASET_ID = "Guardian0369/Prompt-injection-and-PII"

EXPECTED_DATA_FILES = {
    "dev_final.jsonl",
    "docs_final.jsonl",
    "hardNegatives_final.jsonl",
    "normal_final.jsonl",
    "promptInjection_final.jsonl",
    "test.jsonl",
    "test_raw.jsonl",
    "train.jsonl",
    "train_raw.jsonl",
}


def serialize_card_data(card_data) -> dict:
    """Return selected dataset-card metadata as JSON-safe data."""
    if card_data is None:
        return {}

    return {
        "license": getattr(card_data, "license", None),
        "language": getattr(card_data, "language", None),
        "task_categories": getattr(
            card_data,
            "task_categories",
            None,
        ),
        "tags": getattr(card_data, "tags", None),
        "size_categories": getattr(
            card_data,
            "size_categories",
            None,
        ),
    }


def inspect_dataset() -> dict:
    """
    Inspect repository metadata without importing the dataset
    into PromptShield training.
    """
    api = HfApi()

    print(f"Inspecting dataset metadata: {DATASET_ID}")

    dataset_info = api.dataset_info(
        repo_id=DATASET_ID,
        files_metadata=True,
    )

    repository_files = sorted(
        sibling.rfilename
        for sibling in dataset_info.siblings
    )

    file_metadata = []

    for sibling in dataset_info.siblings:
        file_metadata.append(
            {
                "path": sibling.rfilename,
                "size_bytes": getattr(
                    sibling,
                    "size",
                    None,
                ),
                "blob_id": getattr(
                    sibling,
                    "blob_id",
                    None,
                ),
            }
        )

    available_expected_files = sorted(
        file_name
        for file_name in EXPECTED_DATA_FILES
        if file_name in repository_files
    )

    missing_expected_files = sorted(
        EXPECTED_DATA_FILES
        - set(available_expected_files)
    )

    card_metadata = serialize_card_data(
        dataset_info.card_data
    )

    license_name = card_metadata.get("license")

    review_reasons = []

    if license_name in {
        None,
        "",
        "other",
        "unknown",
    }:
        review_reasons.append(
            "The dataset does not declare a clear "
            "standard redistribution license."
        )

    if missing_expected_files:
        review_reasons.append(
            "Some expected dataset files were not found."
        )

    review_reasons.append(
        "Dataset files may use different schemas and require "
        "field-level inspection before label mapping."
    )

    review_reasons.append(
        "Examples may contain synthetic credentials, PII or "
        "reasoning traces and must be sanitized before use."
    )

    return {
        "dataset_id": DATASET_ID,
        "inspected_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "repository_revision": dataset_info.sha,
        "private": dataset_info.private,
        "gated": dataset_info.gated,
        "downloads": dataset_info.downloads,
        "likes": dataset_info.likes,
        "card_metadata": card_metadata,
        "repository_file_count": len(
            repository_files
        ),
        "repository_files": repository_files,
        "file_metadata": file_metadata,
        "expected_data_files": sorted(
            EXPECTED_DATA_FILES
        ),
        "available_expected_files": (
            available_expected_files
        ),
        "missing_expected_files": (
            missing_expected_files
        ),
        "production_training_approved": False,
        "review_status": "under_review",
        "review_reasons": review_reasons,
        "next_review_steps": [
            (
                "Clarify the dataset license and "
                "redistribution permissions."
            ),
            (
                "Inspect each data file using a "
                "privacy-safe schema scanner."
            ),
            (
                "Define explicit mappings for safe, "
                "malicious and sensitive-data labels."
            ),
            (
                "Remove exact and normalized duplicates "
                "across training and evaluation splits."
            ),
            (
                "Scan for credential-like strings before "
                "saving or committing prepared records."
            ),
            (
                "Train an isolated candidate model without "
                "overwriting the production model."
            ),
        ],
    }


def main() -> None:
    """Generate the Guardian dataset metadata report."""
    report = inspect_dataset()

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("Guardian dataset metadata inspection completed.")
    print(
        "Revision:",
        report["repository_revision"],
    )
    print(
        "Declared license:",
        report["card_metadata"].get("license"),
    )
    print(
        "Repository files:",
        report["repository_file_count"],
    )
    print(
        "Expected files available:",
        len(report["available_expected_files"]),
    )
    print(
        "Production training approved:",
        report["production_training_approved"],
    )
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()