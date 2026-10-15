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

ITERATION1_DATA_DIRECTORY = (
    ENTITY_DIRECTORY
    / "data"
)

ITERATION2_DATA_DIRECTORY = (
    ENTITY_DIRECTORY
    / "data_iteration2"
)

ITERATION2_REPORT_PATH = (
    ENTITY_DIRECTORY
    / "reports_iteration2"
    / "iteration2_dataset_report.json"
)

EXPECTED_SPLITS = {
    "train": {
        "records": 800,
        "positive": 400,
        "negative": 400,
        "spans": 458,
    },
    "validation": {
        "records": 200,
        "positive": 100,
        "negative": 100,
        "spans": 115,
    },
    "challenge": {
        "records": 200,
        "positive": 100,
        "negative": 100,
        "spans": 115,
    },
}

VALID_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
    "O",
}


def load_jsonl(path: Path) -> list[dict]:
    """Load one JSON Lines dataset."""
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


def get_iteration2_records(
    split: str,
) -> list[dict]:
    """Load one iteration-two split."""
    return load_jsonl(
        ITERATION2_DATA_DIRECTORY
        / f"{split}.jsonl"
    )


@pytest.mark.parametrize(
    (
        "split",
        "expected",
    ),
    EXPECTED_SPLITS.items(),
)
def test_iteration2_split_counts(
    split,
    expected,
):
    records = get_iteration2_records(
        split
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

    assert len(records) == expected[
        "records"
    ]

    assert len(positive_records) == expected[
        "positive"
    ]

    assert len(negative_records) == expected[
        "negative"
    ]

    assert sensitive_span_count == expected[
        "spans"
    ]


def test_iteration2_combined_counts():
    all_records = [
        record
        for split in EXPECTED_SPLITS
        for record in get_iteration2_records(
            split
        )
    ]

    positive_count = sum(
        record["has_sensitive_entity"]
        for record in all_records
    )

    negative_count = sum(
        not record["has_sensitive_entity"]
        for record in all_records
    )

    sensitive_span_count = sum(
        len(record["gold_spans"])
        for record in all_records
    )

    assert len(all_records) == 1200
    assert positive_count == 600
    assert negative_count == 600
    assert sensitive_span_count == 688


def test_iteration2_ids_are_unique():
    record_ids = [
        record["id"]
        for split in EXPECTED_SPLITS
        for record in get_iteration2_records(
            split
        )
    ]

    assert len(record_ids) == len(
        set(record_ids)
    )


def test_iteration2_prompts_are_unique():
    normalized_prompts = [
        record["prompt"]
        .strip()
        .casefold()
        for split in EXPECTED_SPLITS
        for record in get_iteration2_records(
            split
        )
    ]

    assert len(normalized_prompts) == len(
        set(normalized_prompts)
    )


@pytest.mark.parametrize(
    "split",
    EXPECTED_SPLITS,
)
def test_iteration2_record_metadata(
    split,
):
    records = get_iteration2_records(
        split
    )

    for record in records:
        assert (
            record["source"]
            == "generated_iteration2"
        )

        assert (
            record["source_split"]
            == split
        )

        assert (
            record["has_sensitive_entity"]
            == bool(record["gold_spans"])
        )

        if record["has_sensitive_entity"]:
            assert (
                record["source_action"]
                == "redact"
            )

        else:
            assert (
                record["source_action"]
                == "allow"
            )


@pytest.mark.parametrize(
    "split",
    EXPECTED_SPLITS,
)
def test_iteration2_token_offsets_are_exact(
    split,
):
    records = get_iteration2_records(
        split
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
    EXPECTED_SPLITS,
)
def test_iteration2_span_offsets_are_exact(
    split,
):
    records = get_iteration2_records(
        split
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


@pytest.mark.parametrize(
    "split",
    EXPECTED_SPLITS,
)
def test_iteration2_bio_sequences_are_valid(
    split,
):
    records = get_iteration2_records(
        split
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
    EXPECTED_SPLITS,
)
def test_iteration2_bio_reconstructs_gold_spans(
    split,
):
    records = get_iteration2_records(
        split
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


def test_iteration2_splits_do_not_overlap():
    prompt_sets = {}

    for split in EXPECTED_SPLITS:
        prompt_sets[split] = {
            record["prompt"]
            .strip()
            .casefold()
            for record in get_iteration2_records(
                split
            )
        }

    assert prompt_sets[
        "train"
    ].isdisjoint(
        prompt_sets["validation"]
    )

    assert prompt_sets[
        "train"
    ].isdisjoint(
        prompt_sets["challenge"]
    )

    assert prompt_sets[
        "validation"
    ].isdisjoint(
        prompt_sets["challenge"]
    )


def test_iteration2_does_not_overlap_iteration1():
    iteration2_prompts = {
        record["prompt"]
        .strip()
        .casefold()
        for split in EXPECTED_SPLITS
        for record in get_iteration2_records(
            split
        )
    }

    iteration1_prompts = set()

    for split in [
        "train",
        "validation",
        "test",
        "challenge",
    ]:
        path = (
            ITERATION1_DATA_DIRECTORY
            / f"{split}.jsonl"
        )

        iteration1_prompts.update(
            record["prompt"]
            .strip()
            .casefold()
            for record in load_jsonl(path)
        )

    assert iteration2_prompts.isdisjoint(
        iteration1_prompts
    )


def test_iteration2_does_not_overlap_historical_holdout():
    holdout_path = (
        ITERATION1_DATA_DIRECTORY
        / "final_holdout.jsonl"
    )

    assert holdout_path.exists()

    holdout_prompts = {
        record["prompt"]
        .strip()
        .casefold()
        for record in load_jsonl(
            holdout_path
        )
    }

    iteration2_prompts = {
        record["prompt"]
        .strip()
        .casefold()
        for split in EXPECTED_SPLITS
        for record in get_iteration2_records(
            split
        )
    }

    assert iteration2_prompts.isdisjoint(
        holdout_prompts
    )


def test_iteration2_report_is_valid():
    assert ITERATION2_REPORT_PATH.exists()

    with ITERATION2_REPORT_PATH.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        report = json.load(input_file)

    assert report["valid"] is True
    assert report["validation_errors"] == []

    assert (
        report[
            "historical_final_holdout_used"
        ]
        is False
    )

    assert (
        report["group_isolated_splits"]
        is True
    )

    assert (
        report["combined_record_count"]
        == 1200
    )

    assert (
        report["splits"]["train"][
            "record_count"
        ]
        == 800
    )

    assert (
        report["splits"]["validation"][
            "record_count"
        ]
        == 200
    )

    assert (
        report["splits"]["challenge"][
            "record_count"
        ]
        == 200
    )