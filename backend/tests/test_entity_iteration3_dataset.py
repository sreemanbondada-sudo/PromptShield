import json
import re
from pathlib import Path

import pytest

from research.entity_localizer import (
    build_iteration3_dataset,
)


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]

ENTITY_DIRECTORY = (
    BACKEND_DIRECTORY
    / "research"
    / "entity_localizer"
)

DATA_DIRECTORY = (
    ENTITY_DIRECTORY
    / "data_iteration3"
)

REPORT_PATH = (
    ENTITY_DIRECTORY
    / "reports_iteration3"
    / "iteration3_dataset_report.json"
)

EXPECTED_COUNTS = {
    "train": {
        "total": 1200,
        "positive": 600,
        "negative": 600,
        "spans": 720,
    },
    "validation": {
        "total": 300,
        "positive": 150,
        "negative": 150,
        "spans": 180,
    },
    "challenge": {
        "total": 300,
        "positive": 150,
        "negative": 150,
        "spans": 180,
    },
}


def load_jsonl(path: Path) -> list[dict]:
    """Load one JSON Lines file."""
    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        for line in input_file:
            stripped_line = line.strip()

            if stripped_line:
                records.append(
                    json.loads(stripped_line)
                )

    return records


def normalize_prompt(prompt: str) -> str:
    """Normalize prompts for overlap checks."""
    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        prompt.casefold(),
    )

    return " ".join(
        normalized.split()
    )


@pytest.fixture(scope="module")
def records_by_split() -> dict[str, list[dict]]:
    """Load all iteration-three development data."""
    return {
        split: load_jsonl(
            DATA_DIRECTORY
            / f"{split}.jsonl"
        )
        for split in EXPECTED_COUNTS
    }


def test_iteration_three_files_exist():
    """Every generated development file must exist."""
    for split in EXPECTED_COUNTS:
        assert (
            DATA_DIRECTORY
            / f"{split}.jsonl"
        ).exists()

    assert REPORT_PATH.exists()


@pytest.mark.parametrize(
    "split",
    [
        "train",
        "validation",
        "challenge",
    ],
)
def test_split_distribution(
    records_by_split,
    split,
):
    """Each split must be balanced and complete."""
    records = records_by_split[split]
    expected = EXPECTED_COUNTS[split]

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

    span_count = sum(
        len(record["gold_spans"])
        for record in records
    )

    assert len(records) == expected["total"]

    assert len(positive_records) == (
        expected["positive"]
    )

    assert len(negative_records) == (
        expected["negative"]
    )

    assert span_count == expected["spans"]


def test_all_ids_and_prompts_are_unique(
    records_by_split,
):
    """No record may repeat across splits."""
    records = [
        record
        for split_records in (
            records_by_split.values()
        )
        for record in split_records
    ]

    record_ids = [
        record["id"]
        for record in records
    ]

    prompts = [
        record["prompt"]
        for record in records
    ]

    normalized_prompts = [
        normalize_prompt(record["prompt"])
        for record in records
    ]

    assert len(record_ids) == len(
        set(record_ids)
    )

    assert len(prompts) == len(
        set(prompts)
    )

    assert len(normalized_prompts) == len(
        set(normalized_prompts)
    )


def test_split_prompt_sets_are_disjoint(
    records_by_split,
):
    """Train, validation and challenge must not overlap."""
    prompt_sets = {
        split: {
            normalize_prompt(
                record["prompt"]
            )
            for record in records
        }
        for split, records in (
            records_by_split.items()
        )
    }

    assert not (
        prompt_sets["train"]
        & prompt_sets["validation"]
    )

    assert not (
        prompt_sets["train"]
        & prompt_sets["challenge"]
    )

    assert not (
        prompt_sets["validation"]
        & prompt_sets["challenge"]
    )


def test_gold_spans_match_prompt_offsets(
    records_by_split,
):
    """Gold spans must exactly match prompt text."""
    for records in records_by_split.values():
        for record in records:
            prompt = record["prompt"]
            previous_end = -1

            for span in record["gold_spans"]:
                start = span["start"]
                end = span["end"]

                assert 0 <= start < end
                assert end <= len(prompt)
                assert start >= previous_end

                assert prompt[start:end] == (
                    span["text"]
                )

                previous_end = end

            assert record[
                "has_sensitive_entity"
            ] is bool(record["gold_spans"])


def test_bio_labels_reconstruct_boundaries(
    records_by_split,
):
    """BIO sequences must reconstruct gold spans."""
    for records in records_by_split.values():
        for record in records:
            reconstructed = []
            current_start = None
            current_end = None

            for token in record["tokens"]:
                label = token["label"]

                assert label in {
                    "B-SENSITIVE",
                    "I-SENSITIVE",
                    "O",
                }

                assert record["prompt"][
                    token["start"]:
                    token["end"]
                ] == token["text"]

                if label == "B-SENSITIVE":
                    if current_start is not None:
                        reconstructed.append(
                            (
                                current_start,
                                current_end,
                            )
                        )

                    current_start = token["start"]
                    current_end = token["end"]

                elif label == "I-SENSITIVE":
                    assert current_start is not None
                    current_end = token["end"]

                elif current_start is not None:
                    reconstructed.append(
                        (
                            current_start,
                            current_end,
                        )
                    )

                    current_start = None
                    current_end = None

            if current_start is not None:
                reconstructed.append(
                    (
                        current_start,
                        current_end,
                    )
                )

            expected = [
                (
                    span["start"],
                    span["end"],
                )
                for span in record["gold_spans"]
            ]

            assert reconstructed == expected


def test_negative_controls_have_only_o_labels(
    records_by_split,
):
    """Safe negative controls must have no entities."""
    for records in records_by_split.values():
        negative_records = [
            record
            for record in records
            if not record[
                "has_sensitive_entity"
            ]
        ]

        for record in negative_records:
            assert record["gold_spans"] == []

            assert all(
                token["label"] == "O"
                for token in record["tokens"]
            )


def test_phone_formats_are_diverse(
    records_by_split,
):
    """Development data must cover varied phones."""
    phone_values = [
        span["text"]
        for records in records_by_split.values()
        for record in records
        for span in record["gold_spans"]
        if span["type"] == "phone_number"
    ]

    assert len(phone_values) >= 200

    assert any(
        value.startswith("+91 ")
        for value in phone_values
    )

    assert any(
        value.startswith("+91-")
        for value in phone_values
    )

    assert any(
        value.startswith("(+91)")
        for value in phone_values
    )

    assert any(
        value.isdigit()
        for value in phone_values
    )

    assert any(
        value.startswith("+44 ")
        for value in phone_values
    )

    assert any(
        value.startswith("+1 ")
        for value in phone_values
    )


def test_multi_entity_records_are_present(
    records_by_split,
):
    """Each split must contain multi-entity records."""
    for records in records_by_split.values():
        multi_entity_records = [
            record
            for record in records
            if len(record["gold_spans"]) > 1
        ]

        assert multi_entity_records


def test_previous_development_data_does_not_overlap(
    records_by_split,
):
    """Iteration three must be new development data."""
    iteration_three_prompts = {
        record["prompt"]
        for records in records_by_split.values()
        for record in records
    }

    iteration_three_normalized = {
        normalize_prompt(record["prompt"])
        for records in records_by_split.values()
        for record in records
    }

    reference_prompts = set()
    reference_normalized = set()

    for path in (
        build_iteration3_dataset
        .DEVELOPMENT_REFERENCE_PATHS
    ):
        assert path.resolve() not in (
            build_iteration3_dataset
            .FORBIDDEN_HOLDOUT_PATHS
        )

        for record in load_jsonl(path):
            reference_prompts.add(
                record["prompt"]
            )

            reference_normalized.add(
                normalize_prompt(
                    record["prompt"]
                )
            )

    assert not (
        iteration_three_prompts
        & reference_prompts
    )

    assert not (
        iteration_three_normalized
        & reference_normalized
    )


def test_consumed_holdouts_are_excluded():
    """Neither consumed final holdout may be read."""
    development_paths = {
        path.resolve()
        for path in (
            build_iteration3_dataset
            .DEVELOPMENT_REFERENCE_PATHS
        )
    }

    assert not (
        development_paths
        & build_iteration3_dataset
        .FORBIDDEN_HOLDOUT_PATHS
    )


def test_dataset_report_matches_files(
    records_by_split,
):
    """The generated report must match the data."""
    with REPORT_PATH.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        report = json.load(input_file)

    assert report["total_records"] == 1800

    assert (
        report["total_sensitive_spans"]
        == 1080
    )

    assert (
        report["historical_final_holdout_used"]
        is False
    )

    assert (
        report["iteration2_final_holdout_used"]
        is False
    )

    assert (
        report["production_changed"]
        is False
    )

    for split, expected in (
        EXPECTED_COUNTS.items()
    ):
        split_report = report[
            "split_reports"
        ][split]

        assert (
            split_report["total_records"]
            == expected["total"]
        )

        assert (
            split_report["positive_records"]
            == expected["positive"]
        )

        assert (
            split_report["negative_records"]
            == expected["negative"]
        )

        assert (
            split_report["sensitive_spans"]
            == expected["spans"]
        )