"""Structural tests for the frozen iteration-three holdout."""

import hashlib
import json
from pathlib import Path

from research.entity_localizer import (
    build_iteration3_final_holdout,
)


ENTITY_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "entity_localizer"
)

HOLDOUT_PATH = (
    ENTITY_DIRECTORY
    / "data_iteration3_final"
    / "final_holdout.jsonl"
)

MANIFEST_PATH = (
    ENTITY_DIRECTORY
    / "iteration3_final_holdout_manifest.json"
)

POLICY_PATH = (
    ENTITY_DIRECTORY
    / "iteration3_promotion_gates.json"
)

MODEL_PATH = (
    ENTITY_DIRECTORY
    / "models_iteration3"
    / "contextual_entity_candidate_iteration3.joblib"
)

EXPECTED_DATASET_SHA256 = (
    "1005629886ca3a5404c58129513fac496"
    "d0f0327b65b14332bf08abe75f642aa"
)

EXPECTED_MANIFEST_SHA256 = (
    "7909b20085ad6d33668659122cf3f2da"
    "53f4832ed2d1f9ba55498a9a4e9f5001"
)

EXPECTED_POLICY_SHA256 = (
    "13145fb8359e8e5b4fcbde9910331d92"
    "cc1ee0d608da0aeaa300789e42597ddb"
)

EXPECTED_MODEL_SHA256 = (
    "92c61b301025bc0d6e1b64370ed10696"
    "e6064b22c01e400e7cc4b514e6545a89"
)


def calculate_sha256(path: Path) -> str:
    """Calculate a file SHA-256 checksum."""
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        for chunk in iter(
            lambda: input_file.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict:
    """Load one JSON document."""
    with path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        return json.load(input_file)


def load_jsonl(path: Path) -> list[dict]:
    """Load one JSON Lines dataset."""
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


def test_frozen_files_exist():
    """Every frozen evaluation input must exist."""
    assert HOLDOUT_PATH.exists()
    assert MANIFEST_PATH.exists()
    assert POLICY_PATH.exists()
    assert MODEL_PATH.exists()


def test_frozen_checksums_match():
    """Frozen inputs cannot change silently."""
    assert calculate_sha256(
        HOLDOUT_PATH
    ) == EXPECTED_DATASET_SHA256

    assert calculate_sha256(
        MANIFEST_PATH
    ) == EXPECTED_MANIFEST_SHA256

    assert calculate_sha256(
        POLICY_PATH
    ) == EXPECTED_POLICY_SHA256

    assert calculate_sha256(
        MODEL_PATH
    ) == EXPECTED_MODEL_SHA256


def test_manifest_identifies_frozen_inputs():
    """Manifest checksums must identify exact inputs."""
    manifest = load_json(
        MANIFEST_PATH
    )

    assert manifest["dataset_sha256"] == (
        EXPECTED_DATASET_SHA256
    )

    assert (
        manifest["promotion_policy_sha256"]
        == EXPECTED_POLICY_SHA256
    )

    assert (
        manifest["candidate_model_sha256"]
        == EXPECTED_MODEL_SHA256
    )


def test_holdout_has_required_distribution():
    """The final holdout follows frozen structure."""
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

    assert len(records) == 120
    assert len(positive_records) == 60
    assert len(negative_records) == 60
    assert sensitive_span_count == 72


def test_holdout_records_are_unique():
    """IDs, prompts and normalized prompts are unique."""
    records = load_jsonl(
        HOLDOUT_PATH
    )

    record_ids = [
        record["id"]
        for record in records
    ]

    prompts = [
        record["prompt"]
        for record in records
    ]

    normalized_prompts = [
        build_iteration3_final_holdout
        .normalize_prompt(prompt)
        for prompt in prompts
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


def test_sensitive_span_offsets_are_exact():
    """Every gold span matches its prompt slice."""
    records = load_jsonl(
        HOLDOUT_PATH
    )

    for record in records:
        previous_end = -1

        for span in record["gold_spans"]:
            assert span["start"] >= 0
            assert span["end"] > span["start"]

            assert span["start"] >= previous_end

            assert span["end"] <= len(
                record["prompt"]
            )

            assert span["text"] == (
                record["prompt"][
                    span["start"]:
                    span["end"]
                ]
            )

            previous_end = span["end"]

        assert record[
            "has_sensitive_entity"
        ] is bool(record["gold_spans"])


def test_bio_labels_match_record_tokens():
    """BIO sequences are valid and span-aligned."""
    records = load_jsonl(
        HOLDOUT_PATH
    )

    valid_labels = {
        "B-SENSITIVE",
        "I-SENSITIVE",
        "O",
    }

    for record in records:
        labels = [
            token["label"]
            for token in record["tokens"]
        ]

        assert set(labels).issubset(
            valid_labels
        )

        previous_label = "O"

        for label in labels:
            if label == "I-SENSITIVE":
                assert previous_label in {
                    "B-SENSITIVE",
                    "I-SENSITIVE",
                }

            previous_label = label

        predicted_sensitive_tokens = [
            token
            for token in record["tokens"]
            if token["label"] != "O"
        ]

        assert bool(
            predicted_sensitive_tokens
        ) is record["has_sensitive_entity"]


def test_holdout_has_no_development_overlap():
    """Final prompts and templates are independent."""
    holdout_records = load_jsonl(
        HOLDOUT_PATH
    )

    development_records = []

    for path in (
        build_iteration3_final_holdout
        .DEVELOPMENT_PATHS
    ):
        development_records.extend(
            load_jsonl(path)
        )

    holdout_prompts = {
        record["prompt"]
        for record in holdout_records
    }

    development_prompts = {
        record["prompt"]
        for record in development_records
    }

    holdout_normalized = {
        build_iteration3_final_holdout
        .normalize_prompt(
            record["prompt"]
        )
        for record in holdout_records
    }

    development_normalized = {
        build_iteration3_final_holdout
        .normalize_prompt(
            record["prompt"]
        )
        for record in development_records
    }

    holdout_templates = {
        record["template_group"]
        for record in holdout_records
    }

    development_templates = {
        record["template_group"]
        for record in development_records
    }

    assert holdout_prompts.isdisjoint(
        development_prompts
    )

    assert holdout_normalized.isdisjoint(
        development_normalized
    )

    assert holdout_templates.isdisjoint(
        development_templates
    )


def test_manifest_records_no_prohibited_use():
    """The holdout remains evaluation-only."""
    manifest = load_json(
        MANIFEST_PATH
    )

    assert (
        manifest["historical_holdout_read"]
        is False
    )

    assert (
        manifest["iteration2_holdout_read"]
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
        manifest[
            "used_for_threshold_tuning"
        ]
        is False
    )

    assert (
        manifest["production_changed"]
        is False
    )

    assert manifest["validation"] == {
        "record_count": 120,
        "positive_records": 60,
        "negative_control_records": 60,
        "sensitive_spans": 72,
        "unique_ids": 120,
        "unique_prompts": 120,
        "unique_normalized_prompts": 120,
        "exact_prompt_overlap": 0,
        "normalized_prompt_overlap": 0,
        "template_group_overlap": 0,
    }