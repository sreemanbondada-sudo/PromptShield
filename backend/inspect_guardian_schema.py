import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download


BASE_DIRECTORY = Path(__file__).parent
REPORT_DIRECTORY = BASE_DIRECTORY / "data" / "external"
REPORT_PATH = (
    REPORT_DIRECTORY / "guardian_dataset_schema_report.json"
)

DATASET_ID = "Guardian0369/Prompt-injection-and-PII"
DATASET_REVISION = (
    "4fbd7338a757c6c6b61311a7eb997b3ef7edcae1"
)

DATA_FILES = [
    "dev_final.jsonl",
    "docs_final.jsonl",
    "hardNegatives_final.jsonl",
    "normal_final.jsonl",
    "promptInjection_final.jsonl",
    "test.jsonl",
    "test_raw.jsonl",
    "train.jsonl",
    "train_raw.jsonl",
]

CONTENT_FIELDS = {
    "text",
    "input",
    "output",
    "prompt",
    "content",
    "instruction",
    "response",
}

LABEL_FIELDS = {
    "label",
    "labels",
    "category",
    "_category",
    "class",
    "target",
}

SECRET_PATTERNS = {
    "email_address": re.compile(
        r"\b[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "slack_webhook": re.compile(
        r"https://hooks\.slack\.com/services/"
        r"[A-Za-z0-9/_-]+"
    ),
    "aws_access_key": re.compile(
        r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    ),
    "github_token": re.compile(
        r"\b(?:ghp|github_pat)_"
        r"[A-Za-z0-9_]{20,}\b"
    ),
    "private_key_marker": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?"
        r"PRIVATE KEY-----"
    ),
    "secret_assignment": re.compile(
        r"(?i)\b(?:password|passwd|secret|"
        r"api[_-]?key|token)\s*[:=]\s*"
        r"[^\s,;]{6,}"
    ),
}


def normalize_text(value: str) -> str:
    """Normalize content for privacy-safe duplicate checks."""
    return " ".join(
        value.casefold().split()
    )


def content_digest(value: str) -> str:
    """Return a one-way digest of normalized content."""
    normalized = normalize_text(value)

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def collect_strings(value: Any) -> list[str]:
    """Recursively collect strings without retaining them."""
    strings = []

    if isinstance(value, str):
        strings.append(value)

    elif isinstance(value, list):
        for item in value:
            strings.extend(collect_strings(item))

    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(collect_strings(item))

    return strings


def extract_content_strings(record: dict) -> list[str]:
    """Extract strings only from likely prompt-content fields."""
    strings = []

    for field_name, value in record.items():
        if field_name.casefold() in CONTENT_FIELDS:
            strings.extend(collect_strings(value))

    return strings


def safe_label_value(value: Any) -> str:
    """Convert a short label to a report-safe value."""
    if isinstance(value, (str, int, float, bool)):
        label = str(value).strip()

        if len(label) <= 100:
            return label

    return "<complex-or-long-value>"


def inspect_file(file_name: str) -> tuple[dict, list[str]]:
    """Inspect one JSONL file without reporting its content."""
    cached_path = Path(
        hf_hub_download(
            repo_id=DATASET_ID,
            filename=file_name,
            repo_type="dataset",
            revision=DATASET_REVISION,
        )
    )

    record_count = 0
    malformed_line_count = 0
    empty_line_count = 0
    records_with_content = 0
    records_without_content = 0
    records_with_secret_patterns = 0

    field_counts = Counter()
    schema_counts = Counter()
    label_value_counts = defaultdict(Counter)
    secret_pattern_counts = Counter()
    content_digests = []

    with cached_path.open(
        mode="r",
        encoding="utf-8",
    ) as dataset_file:
        for line in dataset_file:
            stripped_line = line.strip()

            if not stripped_line:
                empty_line_count += 1
                continue

            try:
                record = json.loads(stripped_line)

            except json.JSONDecodeError:
                malformed_line_count += 1
                continue

            if not isinstance(record, dict):
                malformed_line_count += 1
                continue

            record_count += 1

            record_fields = sorted(
                str(field_name)
                for field_name in record.keys()
            )

            schema_counts[
                "|".join(record_fields)
            ] += 1

            for field_name in record_fields:
                field_counts[field_name] += 1

            for field_name, value in record.items():
                if field_name.casefold() in LABEL_FIELDS:
                    label_value_counts[field_name][
                        safe_label_value(value)
                    ] += 1

            content_strings = extract_content_strings(
                record
            )

            nonempty_content = [
                value
                for value in content_strings
                if value.strip()
            ]

            if nonempty_content:
                records_with_content += 1
            else:
                records_without_content += 1

            record_secret_types = set()

            for content in nonempty_content:
                content_digests.append(
                    content_digest(content)
                )

                for (
                    pattern_name,
                    pattern,
                ) in SECRET_PATTERNS.items():
                    if pattern.search(content):
                        record_secret_types.add(
                            pattern_name
                        )

            if record_secret_types:
                records_with_secret_patterns += 1

                for pattern_name in record_secret_types:
                    secret_pattern_counts[
                        pattern_name
                    ] += 1

    duplicate_content_count = sum(
        count - 1
        for count in Counter(
            content_digests
        ).values()
        if count > 1
    )

    file_report = {
        "file": file_name,
        "record_count": record_count,
        "malformed_line_count": (
            malformed_line_count
        ),
        "empty_line_count": empty_line_count,
        "records_with_content": (
            records_with_content
        ),
        "records_without_content": (
            records_without_content
        ),
        "field_counts": dict(
            sorted(field_counts.items())
        ),
        "schemas": [
            {
                "fields": schema.split("|"),
                "record_count": count,
            }
            for schema, count in sorted(
                schema_counts.items()
            )
        ],
        "label_values": {
            field_name: dict(
                sorted(counter.items())
            )
            for field_name, counter in sorted(
                label_value_counts.items()
            )
        },
        "records_with_secret_patterns": (
            records_with_secret_patterns
        ),
        "secret_pattern_counts": dict(
            sorted(secret_pattern_counts.items())
        ),
        "duplicate_content_count": (
            duplicate_content_count
        ),
    }

    return file_report, content_digests


def inspect_dataset() -> dict:
    """Inspect all Guardian dataset JSONL schemas."""
    file_reports = []
    digest_files = defaultdict(set)
    total_records = 0
    total_malformed_lines = 0

    for file_name in DATA_FILES:
        print(f"Inspecting {file_name}...")

        file_report, digests = inspect_file(
            file_name
        )

        file_reports.append(file_report)

        total_records += file_report[
            "record_count"
        ]

        total_malformed_lines += file_report[
            "malformed_line_count"
        ]

        for digest in set(digests):
            digest_files[digest].add(file_name)

    cross_file_duplicate_groups = sum(
        1
        for files in digest_files.values()
        if len(files) > 1
    )

    schema_signatures = {
        tuple(schema["fields"])
        for file_report in file_reports
        for schema in file_report["schemas"]
    }

    files_with_secret_patterns = [
        file_report["file"]
        for file_report in file_reports
        if (
            file_report[
                "records_with_secret_patterns"
            ]
            > 0
        )
    ]

    review_reasons = []

    if len(schema_signatures) > 1:
        review_reasons.append(
            "Multiple record schemas were detected."
        )

    if total_malformed_lines > 0:
        review_reasons.append(
            "Malformed JSONL records were detected."
        )

    if files_with_secret_patterns:
        review_reasons.append(
            "Credential-like or PII-like patterns "
            "were detected in dataset content."
        )

    review_reasons.append(
        "The declared license remains `other` and "
        "requires clarification before production use."
    )

    return {
        "dataset_id": DATASET_ID,
        "dataset_revision": DATASET_REVISION,
        "inspection_policy": {
            "prompt_content_written_to_report": False,
            "matched_secret_values_written_to_report": False,
            "duplicate_detection_method": (
                "SHA-256 of normalized content"
            ),
            "production_model_modified": False,
        },
        "summary": {
            "files_inspected": len(file_reports),
            "total_records": total_records,
            "total_malformed_lines": (
                total_malformed_lines
            ),
            "distinct_schema_count": len(
                schema_signatures
            ),
            "cross_file_duplicate_groups": (
                cross_file_duplicate_groups
            ),
            "files_with_secret_patterns": (
                files_with_secret_patterns
            ),
        },
        "files": file_reports,
        "review_status": "under_review",
        "production_training_approved": False,
        "review_reasons": review_reasons,
    }


def main() -> None:
    """Run inspection and save a privacy-safe report."""
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

    summary = report["summary"]

    print()
    print("Guardian schema inspection completed.")
    print(
        "Files inspected:",
        summary["files_inspected"],
    )
    print(
        "Total records:",
        summary["total_records"],
    )
    print(
        "Malformed lines:",
        summary["total_malformed_lines"],
    )
    print(
        "Distinct schemas:",
        summary["distinct_schema_count"],
    )
    print(
        "Cross-file duplicate groups:",
        summary["cross_file_duplicate_groups"],
    )
    print(
        "Files with secret-like patterns:",
        len(
            summary[
                "files_with_secret_patterns"
            ]
        ),
    )
    print(
        "Production training approved:",
        report["production_training_approved"],
    )
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()