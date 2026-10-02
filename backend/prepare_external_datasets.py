import csv
import hashlib
import re
import unicodedata
from pathlib import Path

from datasets import load_dataset


OUTPUT_DIRECTORY = (
    Path(__file__).parent / "data" / "external"
)

DEEPSET_DATASET_NAME = (
    "deepset/prompt-injections"
)

NEURALCHEMY_DATASET_NAME = (
    "neuralchemy/Prompt-injection-dataset"
)

OUTPUT_FIELDS = [
    "prompt",
    "label",
    "category",
    "source_dataset",
    "source_detail",
    "original_split",
    "group_id",
    "is_augmented",
    "severity",
    "prompt_hash",
]


def normalize_for_hashing(prompt: str) -> str:
    """Normalize prompt text for duplicate detection."""
    normalized = unicodedata.normalize(
        "NFKC",
        prompt,
    )

    normalized = normalized.casefold()

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def calculate_prompt_hash(prompt: str) -> str:
    """Return a stable SHA-256 hash for a prompt."""
    normalized_prompt = normalize_for_hashing(
        prompt
    )

    return hashlib.sha256(
        normalized_prompt.encode("utf-8")
    ).hexdigest()


def normalize_boolean(value) -> bool:
    """Convert common values to a Boolean."""
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
        }

    return bool(value)


def validate_label(value) -> int:
    """Validate and normalize a binary label."""
    label = int(value)

    if label not in {0, 1}:
        raise ValueError(
            f"Unsupported dataset label: {value}"
        )

    return label


def normalize_deepset_record(
    record: dict,
    split_name: str,
) -> dict:
    """Normalize one deepset record."""
    prompt = str(record["text"]).strip()
    label = validate_label(record["label"])

    if not prompt:
        raise ValueError(
            "The deepset dataset contains an empty prompt."
        )

    category = (
        "prompt_injection"
        if label == 1
        else "benign"
    )

    return {
        "prompt": prompt,
        "label": label,
        "category": category,
        "source_dataset": DEEPSET_DATASET_NAME,
        "source_detail": "",
        "original_split": split_name,
        "group_id": "",
        "is_augmented": False,
        "severity": "",
        "prompt_hash": calculate_prompt_hash(prompt),
    }


def normalize_neuralchemy_record(
    record: dict,
    split_name: str,
) -> dict:
    """Normalize one NeurAlchemy core record."""
    prompt = str(record["text"]).strip()
    label = validate_label(record["label"])

    if not prompt:
        raise ValueError(
            "The NeurAlchemy dataset contains "
            "an empty prompt."
        )

    category = str(
        record.get(
            "category",
            "malicious" if label == 1 else "benign",
        )
    ).strip()

    return {
        "prompt": prompt,
        "label": label,
        "category": category,
        "source_dataset": (
            NEURALCHEMY_DATASET_NAME
        ),
        "source_detail": str(
            record.get("source", "")
        ).strip(),
        "original_split": split_name,
        "group_id": str(
            record.get("group_id", "")
        ).strip(),
        "is_augmented": normalize_boolean(
            record.get("augmented", False)
        ),
        "severity": str(
            record.get("severity", "")
        ).strip(),
        "prompt_hash": calculate_prompt_hash(prompt),
    }


def write_normalized_split(
    records,
    split_name: str,
    output_filename: str,
    normalizer,
) -> tuple[int, set[str], dict[str, str]]:
    """Normalize, deduplicate and write one split."""
    output_path = (
        OUTPUT_DIRECTORY / output_filename
    )

    normalized_records = []
    prompt_hashes = set()
    groups = {}

    for record in records:
        normalized_record = normalizer(
            record,
            split_name,
        )

        prompt_hash = normalized_record[
            "prompt_hash"
        ]

        if prompt_hash in prompt_hashes:
            continue

        prompt_hashes.add(prompt_hash)

        group_id = normalized_record[
            "group_id"
        ]

        if group_id:
            groups[group_id] = split_name

        normalized_records.append(
            normalized_record
        )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=OUTPUT_FIELDS,
        )

        writer.writeheader()
        writer.writerows(normalized_records)

    return (
        len(normalized_records),
        prompt_hashes,
        groups,
    )


def verify_split_separation(
    source_name: str,
    split_hashes: dict[str, set[str]],
    split_groups: dict[str, dict[str, str]],
) -> None:
    """Reject prompt or group overlap across splits."""
    split_names = list(split_hashes)

    for index, first_split in enumerate(
        split_names
    ):
        for second_split in split_names[
            index + 1:
        ]:
            prompt_overlap = (
                split_hashes[first_split]
                & split_hashes[second_split]
            )

            if prompt_overlap:
                raise RuntimeError(
                    f"{source_name} contains "
                    f"{len(prompt_overlap)} prompt overlaps "
                    f"between {first_split} and "
                    f"{second_split}."
                )

            first_groups = set(
                split_groups[first_split]
            )

            second_groups = set(
                split_groups[second_split]
            )

            group_overlap = (
                first_groups & second_groups
            )

            if group_overlap:
                raise RuntimeError(
                    f"{source_name} contains "
                    f"{len(group_overlap)} group overlaps "
                    f"between {first_split} and "
                    f"{second_split}."
                )


def prepare_source(
    dataset,
    source_name: str,
    filename_prefix: str,
    normalizer,
) -> dict[str, int]:
    """Prepare every published split for one source."""
    split_hashes = {}
    split_groups = {}
    split_counts = {}

    for split_name, records in dataset.items():
        output_filename = (
            f"{filename_prefix}_{split_name}.csv"
        )

        (
            record_count,
            prompt_hashes,
            groups,
        ) = write_normalized_split(
            records=records,
            split_name=split_name,
            output_filename=output_filename,
            normalizer=normalizer,
        )

        split_counts[split_name] = record_count
        split_hashes[split_name] = prompt_hashes
        split_groups[split_name] = groups

    verify_split_separation(
        source_name=source_name,
        split_hashes=split_hashes,
        split_groups=split_groups,
    )

    return split_counts


def main() -> None:
    """Download and prepare approved external datasets."""
    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Loading deepset prompt-injection dataset..."
    )

    deepset_dataset = load_dataset(
        DEEPSET_DATASET_NAME
    )

    deepset_counts = prepare_source(
        dataset=deepset_dataset,
        source_name=DEEPSET_DATASET_NAME,
        filename_prefix="deepset",
        normalizer=normalize_deepset_record,
    )

    print(
        "Loading NeurAlchemy core dataset..."
    )

    neuralchemy_dataset = load_dataset(
        NEURALCHEMY_DATASET_NAME,
        "core",
    )

    neuralchemy_counts = prepare_source(
        dataset=neuralchemy_dataset,
        source_name=NEURALCHEMY_DATASET_NAME,
        filename_prefix="neuralchemy_core",
        normalizer=normalize_neuralchemy_record,
    )

    print()
    print("Dataset preparation completed.")
    print(
        f"Output directory: {OUTPUT_DIRECTORY}"
    )
    print(
        f"deepset splits: {deepset_counts}"
    )
    print(
        "NeurAlchemy core splits: "
        f"{neuralchemy_counts}"
    )


if __name__ == "__main__":
    main()