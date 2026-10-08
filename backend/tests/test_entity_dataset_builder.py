import json
from pathlib import Path

import pytest

from research.entity_localizer import (
    build_entity_dataset,
)


ENTITY_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "entity_localizer"
)

ENTITY_DATA_DIRECTORY = (
    ENTITY_DIRECTORY
    / "data"
)

EXPECTED_SPLIT_COUNTS = {
    "train": 640,
    "validation": 100,
    "test": 100,
    "challenge": 40,
}

EXPECTED_POSITIVE_RECORD_COUNTS = {
    "train": 160,
    "validation": 25,
    "test": 25,
    "challenge": 10,
}

EXPECTED_SPAN_COUNTS = {
    "train": 170,
    "validation": 25,
    "test": 30,
    "challenge": 11,
}

VALID_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
    "O",
}


def load_jsonl(path: Path) -> list[dict]:
    """Load a generated entity JSONL dataset."""
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
                    f"Invalid JSON in {path.name} "
                    f"at line {line_number}: {error}"
                )

            records.append(record)

    return records


@pytest.mark.parametrize(
    (
        "split",
        "expected_records",
        "expected_positive_records",
        "expected_spans",
    ),
    [
        (
            "train",
            640,
            160,
            170,
        ),
        (
            "validation",
            100,
            25,
            25,
        ),
        (
            "test",
            100,
            25,
            30,
        ),
        (
            "challenge",
            40,
            10,
            11,
        ),
    ],
)
def test_generated_split_counts(
    split,
    expected_records,
    expected_positive_records,
    expected_spans,
):
    path = (
        ENTITY_DATA_DIRECTORY
        / f"{split}.jsonl"
    )

    assert path.exists()

    records = load_jsonl(path)

    assert len(records) == expected_records

    positive_records = [
        record
        for record in records
        if record["has_sensitive_entity"]
    ]

    assert (
        len(positive_records)
        == expected_positive_records
    )

    span_count = sum(
        len(record["gold_spans"])
        for record in records
    )

    assert span_count == expected_spans


def test_combined_dataset_counts():
    total_records = 0
    total_positive_records = 0
    total_spans = 0

    for split in EXPECTED_SPLIT_COUNTS:
        records = load_jsonl(
            ENTITY_DATA_DIRECTORY
            / f"{split}.jsonl"
        )

        total_records += len(records)

        total_positive_records += sum(
            record["has_sensitive_entity"]
            for record in records
        )

        total_spans += sum(
            len(record["gold_spans"])
            for record in records
        )

    assert total_records == 880
    assert total_positive_records == 220
    assert total_spans == 236


@pytest.mark.parametrize(
    "split",
    [
        "train",
        "validation",
        "test",
        "challenge",
    ],
)
def test_record_ids_are_unique(split):
    records = load_jsonl(
        ENTITY_DATA_DIRECTORY
        / f"{split}.jsonl"
    )

    record_ids = [
        record["id"]
        for record in records
    ]

    assert len(record_ids) == len(
        set(record_ids)
    )


@pytest.mark.parametrize(
    "split",
    [
        "train",
        "validation",
        "test",
        "challenge",
    ],
)
def test_token_offsets_match_prompt_text(split):
    records = load_jsonl(
        ENTITY_DATA_DIRECTORY
        / f"{split}.jsonl"
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


@pytest.mark.parametrize(
    "split",
    [
        "train",
        "validation",
        "test",
        "challenge",
    ],
)
def test_gold_span_offsets_match_prompt_text(split):
    records = load_jsonl(
        ENTITY_DATA_DIRECTORY
        / f"{split}.jsonl"
    )

    for record in records:
        prompt = record["prompt"]

        for span in record["gold_spans"]:
            start = span["start"]
            end = span["end"]

            assert 0 <= start < end
            assert end <= len(prompt)

            assert (
                prompt[start:end]
                == span["text"]
            )


@pytest.mark.parametrize(
    "split",
    [
        "train",
        "validation",
        "test",
        "challenge",
    ],
)
def test_bio_sequences_are_valid(split):
    records = load_jsonl(
        ENTITY_DATA_DIRECTORY
        / f"{split}.jsonl"
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


@pytest.mark.parametrize(
    "split",
    [
        "train",
        "validation",
        "test",
        "challenge",
    ],
)
def test_bio_labels_reconstruct_gold_spans(split):
    records = load_jsonl(
        ENTITY_DATA_DIRECTORY
        / f"{split}.jsonl"
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


@pytest.mark.parametrize(
    "split",
    [
        "train",
        "validation",
        "test",
        "challenge",
    ],
)
def test_sensitive_record_flag_matches_spans(split):
    records = load_jsonl(
        ENTITY_DATA_DIRECTORY
        / f"{split}.jsonl"
    )

    for record in records:
        assert record[
            "has_sensitive_entity"
        ] is bool(
            record["gold_spans"]
        )


def test_final_holdout_is_not_an_entity_split():
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

    assert not (
        ENTITY_DATA_DIRECTORY
        / "final_holdout.jsonl"
    ).exists()


def test_entity_dataset_report_is_valid():
    report_path = (
        ENTITY_DIRECTORY
        / "entity_dataset_report.json"
    )

    assert report_path.exists()

    with report_path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        report = json.load(input_file)

    assert report["valid"] is True
    assert report["validation_errors"] == []
    assert report["final_holdout_used"] is False

    assert report["label_scheme"] == [
        "B-SENSITIVE",
        "I-SENSITIVE",
        "O",
    ]

    assert (
        report["combined"]["record_count"]
        == 880
    )

    assert (
        report["combined"][
            "records_with_sensitive_entities"
        ]
        == 220
    )

    assert (
        report["combined"][
            "total_sensitive_spans"
        ]
        == 236
    )

    assert (
        report["combined"][
            "token_label_counts"
        ]["B-SENSITIVE"]
        == 236
    )