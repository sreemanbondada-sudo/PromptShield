import hashlib
import json
import re
from pathlib import Path

from research.entity_localizer import (
    build_iteration2_final_holdout,
)


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]

ENTITY_DIRECTORY = (
    BACKEND_DIRECTORY
    / "research"
    / "entity_localizer"
)

HOLDOUT_PATH = (
    ENTITY_DIRECTORY
    / "data_iteration2_final"
    / "final_holdout.jsonl"
)

MANIFEST_PATH = (
    ENTITY_DIRECTORY
    / "iteration2_final_holdout_manifest.json"
)

POLICY_PATH = (
    ENTITY_DIRECTORY
    / "ITERATION2_PROMOTION_GATES.json"
)

MODEL_PATH = (
    ENTITY_DIRECTORY
    / "models_iteration2"
    / "contextual_entity_candidate_iteration2.joblib"
)

HISTORICAL_HOLDOUT_PATH = (
    ENTITY_DIRECTORY
    / "data"
    / "final_holdout.jsonl"
)


def sha256_file(path: Path) -> str:
    """Calculate a SHA-256 checksum."""
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


def normalize_prompt(prompt: str) -> str:
    """Normalize a prompt for overlap comparison."""
    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        prompt.casefold(),
    )

    return " ".join(
        normalized.split()
    )


def test_frozen_holdout_files_exist():
    """All frozen evaluation inputs must exist."""
    assert HOLDOUT_PATH.exists()
    assert MANIFEST_PATH.exists()
    assert POLICY_PATH.exists()
    assert MODEL_PATH.exists()


def test_holdout_checksum_matches_manifest():
    """The frozen dataset must not be modified."""
    manifest = load_json(MANIFEST_PATH)

    assert sha256_file(HOLDOUT_PATH) == (
        manifest["dataset_sha256"]
    )


def test_policy_and_model_checksums_match_manifest():
    """Policy and candidate must remain unchanged."""
    manifest = load_json(MANIFEST_PATH)

    assert sha256_file(POLICY_PATH) == (
        manifest["promotion_policy_sha256"]
    )

    assert sha256_file(MODEL_PATH) == (
        manifest["candidate_model_sha256"]
    )


def test_manifest_records_frozen_research_state():
    """The manifest must prohibit tuning and promotion."""
    manifest = load_json(MANIFEST_PATH)

    assert manifest["frozen"] is True

    assert (
        manifest["one_time_evaluation"]
        is True
    )

    assert manifest["used_for_training"] is False

    assert (
        manifest["used_for_model_selection"]
        is False
    )

    assert (
        manifest["used_for_threshold_tuning"]
        is False
    )

    assert (
        manifest["historical_holdout_read"]
        is False
    )

    assert (
        manifest["production_changed"]
        is False
    )


def test_holdout_has_required_distribution():
    """The holdout must satisfy frozen size gates."""
    records = load_jsonl(HOLDOUT_PATH)
    manifest = load_json(MANIFEST_PATH)
    policy = load_json(POLICY_PATH)

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

    requirements = policy[
        "minimum_holdout_requirements"
    ]

    assert len(records) >= (
        requirements["total_records"]
    )

    assert len(positive_records) >= (
        requirements["positive_records"]
    )

    assert len(negative_records) >= (
        requirements[
            "negative_control_records"
        ]
    )

    assert sensitive_span_count >= (
        requirements[
            "minimum_sensitive_spans"
        ]
    )

    assert len(records) == 100
    assert len(positive_records) == 50
    assert len(negative_records) == 50
    assert sensitive_span_count == 63

    validation = manifest["validation"]

    assert validation["total_records"] == 100
    assert validation["positive_records"] == 50

    assert (
        validation["negative_control_records"]
        == 50
    )

    assert validation["sensitive_spans"] == 63


def test_holdout_ids_and_prompts_are_unique():
    """No record or normalized prompt may repeat."""
    records = load_jsonl(HOLDOUT_PATH)

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


def test_gold_spans_match_exact_prompt_offsets():
    """Every gold span must match prompt text."""
    records = load_jsonl(HOLDOUT_PATH)

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


def test_token_labels_reconstruct_gold_spans():
    """BIO labels must reconstruct exact boundaries."""
    records = load_jsonl(HOLDOUT_PATH)

    for record in records:
        prompt = record["prompt"]
        tokens = record["tokens"]

        reconstructed = []
        current_start = None
        current_end = None

        for token in tokens:
            label = token["label"]

            assert label in {
                "B-SENSITIVE",
                "I-SENSITIVE",
                "O",
            }

            assert prompt[
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


def test_holdout_has_no_development_overlap():
    """The final holdout must remain independent."""
    holdout_records = load_jsonl(
        HOLDOUT_PATH
    )

    holdout_prompts = {
        record["prompt"]
        for record in holdout_records
    }

    holdout_normalized = {
        normalize_prompt(record["prompt"])
        for record in holdout_records
    }

    holdout_template_groups = {
        record["template_group"]
        for record in holdout_records
    }

    development_prompts = set()
    development_normalized = set()
    development_template_groups = set()

    for path in (
        build_iteration2_final_holdout
        .DEVELOPMENT_DATASET_PATHS
    ):
        assert path.resolve() != (
            HISTORICAL_HOLDOUT_PATH.resolve()
        )

        for record in load_jsonl(path):
            prompt = record["prompt"]

            development_prompts.add(prompt)

            development_normalized.add(
                normalize_prompt(prompt)
            )

            if record.get("template_group"):
                development_template_groups.add(
                    record["template_group"]
                )

    assert not (
        holdout_prompts
        & development_prompts
    )

    assert not (
        holdout_normalized
        & development_normalized
    )

    assert not (
        holdout_template_groups
        & development_template_groups
    )


def test_historical_holdout_is_excluded():
    """The old failed holdout must never be loaded."""
    development_paths = {
        path.resolve()
        for path in (
            build_iteration2_final_holdout
            .DEVELOPMENT_DATASET_PATHS
        )
    }

    assert (
        HISTORICAL_HOLDOUT_PATH.resolve()
        not in development_paths
    )

    assert (
        build_iteration2_final_holdout
        .HISTORICAL_HOLDOUT_PATH
        .resolve()
        == HISTORICAL_HOLDOUT_PATH.resolve()
    )