"""Tests for the frozen iteration-three promotion policy."""

import hashlib
import json
from pathlib import Path


ENTITY_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "entity_localizer"
)

POLICY_PATH = (
    ENTITY_DIRECTORY
    / "iteration3_promotion_gates.json"
)

EXPECTED_POLICY_SHA256 = (
    "13145fb8359e8e5b4fcbde9910331d92"
    "cc1ee0d608da0aeaa300789e42597ddb"
)


def load_policy() -> dict:
    """Load the frozen promotion policy."""
    with POLICY_PATH.open(
        "r",
        encoding="utf-8",
    ) as policy_file:
        return json.load(policy_file)


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


def test_promotion_policy_exists_and_is_valid():
    """The frozen policy must exist as JSON."""
    assert POLICY_PATH.exists()

    policy = load_policy()

    assert isinstance(policy, dict)

    assert policy["policy_name"] == (
        "entity_iteration3_final_"
        "promotion_policy"
    )

    assert policy["policy_version"] == 1

    assert policy["frozen_on"] == (
        "2026-10-28"
    )


def test_promotion_policy_checksum_is_frozen():
    """The policy cannot change after freezing."""
    assert calculate_sha256(
        POLICY_PATH
    ) == EXPECTED_POLICY_SHA256


def test_candidate_identity_is_frozen():
    """The policy targets the selected candidate."""
    candidate = load_policy()["candidate"]

    assert candidate == {
        "model_name": (
            "iteration3_crf_context_one"
        ),
        "model_type": (
            "contextual_sensitive_entity_"
            "localizer_iteration3"
        ),
        "model_kind": "crf",
        "feature_set": (
            "iteration3_structural_features"
        ),
        "context_window": 1,
    }


def test_final_holdout_cannot_influence_model():
    """The final holdout is evaluation-only."""
    protocol = load_policy()[
        "evaluation_protocol"
    ]

    assert (
        protocol[
            "final_holdout_is_independent"
        ]
        is True
    )

    assert (
        protocol[
            "final_holdout_may_be_"
            "evaluated_once"
        ]
        is True
    )

    assert (
        protocol[
            "final_holdout_may_be_"
            "used_for_training"
        ]
        is False
    )

    assert (
        protocol[
            "final_holdout_may_be_"
            "used_for_model_selection"
        ]
        is False
    )

    assert (
        protocol[
            "final_holdout_may_be_"
            "used_for_threshold_tuning"
        ]
        is False
    )

    assert (
        protocol[
            "historical_holdout_may_be_loaded"
        ]
        is False
    )

    assert (
        protocol[
            "iteration2_holdout_may_be_loaded"
        ]
        is False
    )

    assert (
        protocol["boundary_decoder_required"]
        is True
    )


def test_holdout_structure_is_frozen():
    """The holdout size and isolation are fixed."""
    requirements = load_policy()[
        "holdout_requirements"
    ]

    assert requirements == {
        "record_count": 120,
        "minimum_positive_records": 60,
        "minimum_negative_control_records": 60,
        "minimum_sensitive_spans": 72,
        "maximum_exact_prompt_overlap": 0,
        "maximum_normalized_prompt_overlap": 0,
        "maximum_template_group_overlap": 0,
    }


def test_minimum_quality_gates_are_frozen():
    """Required model-quality thresholds are fixed."""
    gates = load_policy()[
        "minimum_quality_gates"
    ]

    assert gates == {
        "exact_span_precision": 0.9,
        "exact_span_recall": 0.9,
        "exact_span_f1": 0.9,
        "sensitive_token_f1": 0.95,
    }


def test_maximum_safety_gates_are_frozen():
    """Allowed error limits are fixed."""
    gates = load_policy()[
        "maximum_safety_gates"
    ]

    assert gates == {
        "false_positive_record_rate": 0.05,
        "false_negative_record_rate": 0.05,
        "false_positive_records": 3,
        "false_negative_records": 3,
    }


def test_integrity_conditions_are_complete():
    """Every mandatory isolation check is required."""
    conditions = set(
        load_policy()[
            "mandatory_integrity_conditions"
        ]
    )

    assert conditions == {
        "holdout_checksum_matches_manifest",
        (
            "promotion_policy_checksum_"
            "matches_manifest"
        ),
        (
            "candidate_artifact_checksum_"
            "matches_manifest"
        ),
        "holdout_manifest_is_valid",
        "boundary_decoder_is_used",
        "historical_holdout_is_not_read",
        "iteration2_holdout_is_not_read",
        "holdout_is_not_used_for_training",
        (
            "holdout_is_not_used_for_"
            "model_selection"
        ),
        (
            "holdout_is_not_used_for_"
            "threshold_tuning"
        ),
        "holdout_has_no_exact_prompt_overlap",
        (
            "holdout_has_no_normalized_"
            "prompt_overlap"
        ),
        (
            "holdout_has_no_template_"
            "group_overlap"
        ),
        (
            "production_is_not_changed_"
            "by_evaluation"
        ),
    }


def test_promotion_requires_every_gate():
    """Partial gate success cannot promote a model."""
    rule = load_policy()["promotion_rule"]

    assert rule == {
        "require_all_quality_gates": True,
        "require_all_integrity_conditions": True,
        "failure_action": "do_not_promote",
        "success_action": (
            "approve_for_controlled_"
            "shadow_integration"
        ),
    }