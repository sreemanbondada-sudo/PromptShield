import hashlib
import json
from pathlib import Path

import pytest

from research.entity_localizer import (
    build_entity_dataset,
)


BACKEND_DIRECTORY = (
    Path(__file__).resolve().parents[1]
)

ENTITY_DIRECTORY = (
    BACKEND_DIRECTORY
    / "research"
    / "entity_localizer"
)

DATA_DIRECTORY = (
    ENTITY_DIRECTORY
    / "data"
)

HOLDOUT_PATH = (
    DATA_DIRECTORY
    / "final_holdout.jsonl"
)

MANIFEST_PATH = (
    ENTITY_DIRECTORY
    / "final_holdout_manifest.json"
)

EXPECTED_SHA256 = (
    "b1ad2dcfb0f5d9ca02846109430d4219"
    "8a1def8c0171c1d979a815312e94b69f"
)

DEVELOPMENT_SPLITS = [
    "train",
    "validation",
    "test",
    "challenge",
]

VALID_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
    "O",
}


def load_jsonl(path: Path) -> list[dict]:
    """Load and validate a JSON Lines file."""
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
                pytest.fail(
                    f"Invalid JSON in {path} "
                    f"at line {line_number}: {error}"
                )

            records.append(record)

    return records


def calculate_sha256(path: Path) -> str:
    """Calculate a file's SHA-256 checksum."""
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        while True:
            block = input_file.read(
                64 * 1024
            )

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def load_manifest() -> dict:
    """Load the frozen holdout manifest."""
    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        return json.load(input_file)


def test_final_holdout_files_exist():
    assert HOLDOUT_PATH.exists()
    assert MANIFEST_PATH.exists()


def test_final_holdout_checksum_is_unchanged():
    manifest = load_manifest()

    actual_sha256 = calculate_sha256(
        HOLDOUT_PATH
    )

    assert actual_sha256 == EXPECTED_SHA256
    assert manifest["sha256"] == EXPECTED_SHA256


def test_final_holdout_manifest_is_frozen():
    manifest = load_manifest()

    assert manifest["frozen"] is True

    assert (
        manifest["derived_from_development_data"]
        is False
    )

    assert (
        manifest["used_for_training"]
        is False
    )

    assert (
        manifest["used_for_model_selection"]
        is False
    )

    assert (
        manifest["used_for_threshold_tuning"]
        is False
    )


def test_final_holdout_manifest_counts():
    manifest = load_manifest()

    assert manifest["record_count"] == 60

    assert (
        manifest["positive_record_count"]
        == 30
    )

    assert (
        manifest["negative_record_count"]
        == 30
    )

    assert (
        manifest["sensitive_span_count"]
        == 36
    )

    assert sum(
        manifest[
            "sensitive_span_types"
        ].values()
    ) == 36


def test_final_holdout_record_counts():
    records = load_jsonl(
        HOLDOUT_PATH
    )

    positive_records = [
        record
        for record in records
        if record["has_sensitive_entity"]
    ]

    negative_records = [
        record
        for record in records
        if not record["has_sensitive_entity"]
    ]

    sensitive_span_count = sum(
        len(record["gold_spans"])
        for record in records
    )

    assert len(records) == 60
    assert len(positive_records) == 30
    assert len(negative_records) == 30
    assert sensitive_span_count == 36


def test_final_holdout_ids_are_unique():
    records = load_jsonl(
        HOLDOUT_PATH
    )

    record_ids = [
        record["id"]
        for record in records
    ]

    assert len(record_ids) == len(
        set(record_ids)
    )


def test_final_holdout_prompts_are_unique():
    records = load_jsonl(
        HOLDOUT_PATH
    )

    normalized_prompts = [
        record["prompt"]
        .strip()
        .casefold()
        for record in records
    ]

    assert len(normalized_prompts) == len(
        set(normalized_prompts)
    )


def test_final_holdout_metadata_is_frozen():
    records = load_jsonl(
        HOLDOUT_PATH
    )

    for record in records:
        assert (
            record["source_split"]
            == "final_holdout"
        )

        assert (
            record["source"]
            == "manual_holdout"
        )

        assert (
            record["holdout_frozen"]
            is True
        )

        assert (
            record["has_sensitive_entity"]
            == bool(record["gold_spans"])
        )


def test_final_holdout_token_offsets_are_exact():
    records = load_jsonl(
        HOLDOUT_PATH
    )

    for record in records:
        prompt = record["prompt"]

        for token in record["tokens"]:
            start = token["start"]
            end = token["end"]

            assert 0 <= start < end
            assert end <= len(prompt)

            assert (
                prompt[start:end]
                == token["text"]
            )


def test_final_holdout_span_offsets_are_exact():
    records = load_jsonl(
        HOLDOUT_PATH
    )

    for record in records:
        prompt = record["prompt"]

        previous_end = -1

        for span in record["gold_spans"]:
            start = span["start"]
            end = span["end"]

            assert 0 <= start < end
            assert end <= len(prompt)
            assert start >= previous_end

            assert (
                prompt[start:end]
                == span["text"]
            )

            previous_end = end


def test_final_holdout_bio_sequences_are_valid():
    records = load_jsonl(
        HOLDOUT_PATH
    )

    for record in records:
        previous_label = "O"

        for token in record["tokens"]:
            label = token["label"]

            assert label in VALID_LABELS

            if label == "I-SENSITIVE":
                assert previous_label in {
                    "B-SENSITIVE",
                    "I-SENSITIVE",
                }

            previous_label = label


def test_final_holdout_bio_reconstructs_gold_spans():
    records = load_jsonl(
        HOLDOUT_PATH
    )

    for record in records:
        reconstructed_spans = (
            build_entity_dataset
            .reconstruct_sensitive_spans(
                record["prompt"],
                record["tokens"],
            )
        )

        reconstructed_boundaries = [
            (
                span["start"],
                span["end"],
                span["text"],
            )
            for span in reconstructed_spans
        ]

        gold_boundaries = [
            (
                span["start"],
                span["end"],
                span["text"],
            )
            for span in record[
                "gold_spans"
            ]
        ]

        assert (
            reconstructed_boundaries
            == gold_boundaries
        )


def test_final_holdout_does_not_overlap_development_data():
    holdout_records = load_jsonl(
        HOLDOUT_PATH
    )

    holdout_prompts = {
        record["prompt"]
        .strip()
        .casefold()
        for record in holdout_records
    }

    development_prompts = set()

    for split in DEVELOPMENT_SPLITS:
        split_path = (
            DATA_DIRECTORY
            / f"{split}.jsonl"
        )

        split_records = load_jsonl(
            split_path
        )

        development_prompts.update(
            record["prompt"]
            .strip()
            .casefold()
            for record in split_records
        )

    assert (
        holdout_prompts
        .isdisjoint(
            development_prompts
        )
    )


def test_final_holdout_is_not_a_training_split():
    assert (
        "final_holdout"
        not in build_entity_dataset
        .SOURCE_DATASET_PATHS
    )

    assert (
        "final_holdout"
        not in build_entity_dataset
        .OUTPUT_DATASET_PATHS
    )