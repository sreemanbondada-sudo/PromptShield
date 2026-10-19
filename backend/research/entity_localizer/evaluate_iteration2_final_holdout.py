"""Run the protected iteration-two entity holdout evaluation."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib


SCRIPT_DIRECTORY = Path(__file__).resolve().parent

BACKEND_DIRECTORY = (
    SCRIPT_DIRECTORY.parents[1]
)

if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIRECTORY),
    )


from research.entity_localizer import (
    build_iteration2_final_holdout,
)

from research.entity_localizer.evaluate_boundary_decoder import (
    evaluate_predictions,
)

from research.entity_localizer.train_iteration2_candidates import (
    predict_candidate,
)


HOLDOUT_PATH = (
    SCRIPT_DIRECTORY
    / "data_iteration2_final"
    / "final_holdout.jsonl"
)

MANIFEST_PATH = (
    SCRIPT_DIRECTORY
    / "iteration2_final_holdout_manifest.json"
)

PROMOTION_GATES_PATH = (
    SCRIPT_DIRECTORY
    / "ITERATION2_PROMOTION_GATES.json"
)

MODEL_PATH = (
    SCRIPT_DIRECTORY
    / "models_iteration2"
    / "contextual_entity_candidate_iteration2.joblib"
)

BOUNDARY_DECODER_PATH = (
    SCRIPT_DIRECTORY
    / "boundary_decoder.py"
)

HISTORICAL_HOLDOUT_PATH = (
    SCRIPT_DIRECTORY
    / "data"
    / "final_holdout.jsonl"
)

REPORT_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "reports_iteration2"
)

REPORT_PATH = (
    REPORT_DIRECTORY
    / "iteration2_final_holdout_evaluation.json"
)


def load_json(path: Path) -> dict:
    """Load one JSON object."""
    if not path.exists():
        raise RuntimeError(
            f"Required file was not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        value = json.load(input_file)

    if not isinstance(value, dict):
        raise RuntimeError(
            f"Expected a JSON object in {path}."
        )

    return value


def load_jsonl(path: Path) -> list[dict]:
    """Load one JSON Lines dataset."""
    if not path.exists():
        raise RuntimeError(
            f"Required file was not found: {path}"
        )

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
                raise RuntimeError(
                    f"Invalid JSON in {path} "
                    f"at line {line_number}."
                ) from error

            records.append(record)

    if not records:
        raise RuntimeError(
            f"No records were loaded from {path}."
        )

    return records


def calculate_sha256(path: Path) -> str:
    """Calculate a file SHA-256 checksum."""
    if not path.exists():
        raise RuntimeError(
            f"Required file was not found: {path}"
        )

    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        for block in iter(
            lambda: input_file.read(
                64 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def verify_frozen_inputs(
    manifest: dict,
    promotion_policy: dict,
) -> dict:
    """Verify every frozen evaluation input."""
    expected_dataset_hash = manifest.get(
        "dataset_sha256"
    )

    expected_policy_hash = manifest.get(
        "promotion_policy_sha256"
    )

    expected_model_hash = manifest.get(
        "candidate_model_sha256"
    )

    actual_dataset_hash = calculate_sha256(
        HOLDOUT_PATH
    )

    actual_policy_hash = calculate_sha256(
        PROMOTION_GATES_PATH
    )

    actual_model_hash = calculate_sha256(
        MODEL_PATH
    )

    development_paths = {
        path.resolve()
        for path in (
            build_iteration2_final_holdout
            .DEVELOPMENT_DATASET_PATHS
        )
    }

    historical_path_excluded = (
        HISTORICAL_HOLDOUT_PATH.resolve()
        not in development_paths
    )

    manifest_conditions = {
        "frozen": (
            manifest.get("frozen")
            is True
        ),
        "one_time_evaluation": (
            manifest.get(
                "one_time_evaluation"
            )
            is True
        ),
        "not_used_for_training": (
            manifest.get(
                "used_for_training"
            )
            is False
        ),
        "not_used_for_model_selection": (
            manifest.get(
                "used_for_model_selection"
            )
            is False
        ),
        "not_used_for_threshold_tuning": (
            manifest.get(
                "used_for_threshold_tuning"
            )
            is False
        ),
        "historical_holdout_not_read": (
            manifest.get(
                "historical_holdout_read"
            )
            is False
        ),
        "production_not_changed": (
            manifest.get(
                "production_changed"
            )
            is False
        ),
        "historical_path_excluded": (
            historical_path_excluded
        ),
    }

    dataset_checksum_matches = (
        actual_dataset_hash
        == expected_dataset_hash
    )

    policy_checksum_matches = (
        actual_policy_hash
        == expected_policy_hash
    )

    model_checksum_matches = (
        actual_model_hash
        == expected_model_hash
    )

    manifest_is_valid = all(
        manifest_conditions.values()
    )

    policy_is_valid = (
        promotion_policy.get(
            "evaluation_mode"
        )
        == "one_time_independent_holdout"
        and promotion_policy.get(
            "production_behavior_before_promotion"
        )
        == "unchanged"
    )

    valid = all(
        [
            dataset_checksum_matches,
            policy_checksum_matches,
            model_checksum_matches,
            manifest_is_valid,
            policy_is_valid,
        ]
    )

    return {
        "expected_dataset_sha256": (
            expected_dataset_hash
        ),
        "actual_dataset_sha256": (
            actual_dataset_hash
        ),
        "dataset_checksum_matches": (
            dataset_checksum_matches
        ),
        "expected_policy_sha256": (
            expected_policy_hash
        ),
        "actual_policy_sha256": (
            actual_policy_hash
        ),
        "policy_checksum_matches": (
            policy_checksum_matches
        ),
        "expected_model_sha256": (
            expected_model_hash
        ),
        "actual_model_sha256": (
            actual_model_hash
        ),
        "model_checksum_matches": (
            model_checksum_matches
        ),
        "manifest_conditions": (
            manifest_conditions
        ),
        "manifest_is_valid": (
            manifest_is_valid
        ),
        "policy_is_valid": (
            policy_is_valid
        ),
        "valid": valid,
    }


def verify_holdout_structure(
    records: list[dict],
    manifest: dict,
    promotion_policy: dict,
) -> dict:
    """Revalidate counts, spans and isolation."""
    validation = (
        build_iteration2_final_holdout
        .validate_holdout(records)
    )

    requirements = promotion_policy[
        "minimum_holdout_requirements"
    ]

    requirement_checks = {
        "total_records": (
            validation["total_records"]
            >= requirements["total_records"]
        ),
        "positive_records": (
            validation["positive_records"]
            >= requirements["positive_records"]
        ),
        "negative_control_records": (
            validation[
                "negative_control_records"
            ]
            >= requirements[
                "negative_control_records"
            ]
        ),
        "minimum_sensitive_spans": (
            validation["sensitive_spans"]
            >= requirements[
                "minimum_sensitive_spans"
            ]
        ),
    }

    manifest_validation_matches = (
        validation
        == manifest.get("validation")
    )

    valid = (
        all(requirement_checks.values())
        and manifest_validation_matches
    )

    return {
        "validation": validation,
        "requirement_checks": (
            requirement_checks
        ),
        "manifest_validation_matches": (
            manifest_validation_matches
        ),
        "valid": valid,
    }


def verify_model_artifact(
    artifact: dict,
) -> dict:
    """Verify that the preserved candidate is valid."""
    if not isinstance(artifact, dict):
        raise RuntimeError(
            "The candidate artifact must be "
            "a dictionary."
        )

    conditions = {
        "model_name_matches": (
            artifact.get("model_name")
            == "iteration2_crf_context_two"
        ),
        "model_kind_is_crf": (
            artifact.get("model_kind")
            == "crf"
        ),
        "boundary_decoder_required": (
            artifact.get(
                "boundary_decoder_required"
            )
            is True
        ),
        "historical_holdout_not_used": (
            artifact.get(
                "historical_final_holdout_used"
            )
            is False
        ),
        "research_only": (
            artifact.get("production_ready")
            is False
            and artifact.get("mode")
            == "research"
        ),
        "classifier_available": (
            artifact.get("classifier")
            is not None
        ),
    }

    return {
        "conditions": conditions,
        "valid": all(
            conditions.values()
        ),
    }


def minimum_gate(
    metric: str,
    actual: float,
    required: float,
) -> dict:
    """Evaluate one minimum metric gate."""
    return {
        "metric": metric,
        "comparison": "minimum",
        "actual": actual,
        "required": required,
        "passed": actual >= required,
    }


def maximum_gate(
    metric: str,
    actual: float,
    required: float,
) -> dict:
    """Evaluate one maximum metric gate."""
    return {
        "metric": metric,
        "comparison": "maximum",
        "actual": actual,
        "required": required,
        "passed": actual <= required,
    }


def evaluate_quality_gates(
    evaluation: dict,
    promotion_policy: dict,
) -> list[dict]:
    """Apply the frozen performance thresholds."""
    gates = promotion_policy[
        "quality_gates"
    ]

    return [
        minimum_gate(
            "exact_span_precision",
            evaluation[
                "exact_span_precision"
            ],
            gates[
                "exact_span_precision_minimum"
            ],
        ),
        minimum_gate(
            "exact_span_recall",
            evaluation[
                "exact_span_recall"
            ],
            gates[
                "exact_span_recall_minimum"
            ],
        ),
        minimum_gate(
            "exact_span_f1",
            evaluation[
                "exact_span_f1"
            ],
            gates[
                "exact_span_f1_minimum"
            ],
        ),
        minimum_gate(
            "sensitive_token_f1",
            evaluation[
                "sensitive_token_f1"
            ],
            gates[
                "sensitive_token_f1_minimum"
            ],
        ),
        maximum_gate(
            "false_positive_record_rate",
            evaluation[
                "false_positive_record_rate"
            ],
            gates[
                "false_positive_record_rate_maximum"
            ],
        ),
        maximum_gate(
            "false_negative_record_rate",
            evaluation[
                "false_negative_record_rate"
            ],
            gates[
                "false_negative_record_rate_maximum"
            ],
        ),
        maximum_gate(
            "false_positive_records",
            evaluation[
                "false_positive_records"
            ],
            gates[
                "false_positive_records_maximum"
            ],
        ),
        maximum_gate(
            "false_negative_records",
            evaluation[
                "false_negative_records"
            ],
            gates[
                "false_negative_records_maximum"
            ],
        ),
    ]


def evaluate_mandatory_conditions(
    frozen_inputs: dict,
    structure_verification: dict,
    model_verification: dict,
) -> dict:
    """Evaluate every non-performance condition."""
    validation = structure_verification[
        "validation"
    ]

    return {
        "holdout_checksum_matches_manifest": (
            frozen_inputs[
                "dataset_checksum_matches"
            ]
        ),
        "holdout_manifest_is_valid": (
            frozen_inputs["manifest_is_valid"]
            and structure_verification["valid"]
        ),
        "boundary_decoder_is_used": True,
        "candidate_artifact_checksum_matches": (
            frozen_inputs[
                "model_checksum_matches"
            ]
        ),
        "historical_holdout_is_not_read": (
            frozen_inputs[
                "manifest_conditions"
            ][
                "historical_holdout_not_read"
            ]
            and frozen_inputs[
                "manifest_conditions"
            ][
                "historical_path_excluded"
            ]
            and model_verification[
                "conditions"
            ][
                "historical_holdout_not_used"
            ]
        ),
        "holdout_is_not_used_for_training": (
            frozen_inputs[
                "manifest_conditions"
            ][
                "not_used_for_training"
            ]
        ),
        "holdout_is_not_used_for_model_selection": (
            frozen_inputs[
                "manifest_conditions"
            ][
                "not_used_for_model_selection"
            ]
        ),
        "holdout_is_not_used_for_threshold_tuning": (
            frozen_inputs[
                "manifest_conditions"
            ][
                "not_used_for_threshold_tuning"
            ]
        ),
        "holdout_has_no_prompt_overlap_with_development_data": (
            validation[
                "development_prompt_overlap"
            ]
            == 0
        ),
        "holdout_has_no_normalized_prompt_overlap_with_development_data": (
            validation[
                "development_normalized_prompt_overlap"
            ]
            == 0
        ),
        "holdout_has_no_template_group_overlap_with_development_data": (
            validation[
                "development_template_group_overlap"
            ]
            == 0
        ),
    }


def print_percentage_metric(
    label: str,
    value: float,
) -> None:
    """Print one percentage metric."""
    print(
        f"{label}: {value:.2%}"
    )


def print_quality_gate(gate: dict) -> None:
    """Print one frozen quality-gate result."""
    result = (
        "PASS"
        if gate["passed"]
        else "FAIL"
    )

    metric = gate["metric"]

    if metric.endswith(
        "_records"
    ):
        actual = str(
            gate["actual"]
        )

        required = str(
            gate["required"]
        )

    else:
        actual = (
            f"{gate['actual']:.2%}"
        )

        required = (
            f"{gate['required']:.2%}"
        )

    comparison = (
        "minimum"
        if gate["comparison"] == "minimum"
        else "maximum"
    )

    print(
        f"{metric}: {actual} "
        f"({comparison} {required}) "
        f"[{result}]"
    )


def main() -> None:
    """Run the protected evaluation exactly once."""
    if REPORT_PATH.exists():
        raise RuntimeError(
            "The iteration-two final holdout has "
            "already been evaluated. Refusing to "
            "overwrite the existing report: "
            f"{REPORT_PATH}"
        )

    required_paths = [
        HOLDOUT_PATH,
        MANIFEST_PATH,
        PROMOTION_GATES_PATH,
        MODEL_PATH,
        BOUNDARY_DECODER_PATH,
    ]

    for path in required_paths:
        if not path.exists():
            raise RuntimeError(
                "Required evaluation file was "
                f"not found: {path}"
            )

    manifest = load_json(
        MANIFEST_PATH
    )

    promotion_policy = load_json(
        PROMOTION_GATES_PATH
    )

    print(
        "Verifying frozen evaluation inputs..."
    )

    frozen_inputs = verify_frozen_inputs(
        manifest,
        promotion_policy,
    )

    print(
        "Dataset checksum valid:",
        frozen_inputs[
            "dataset_checksum_matches"
        ],
    )

    print(
        "Policy checksum valid:",
        frozen_inputs[
            "policy_checksum_matches"
        ],
    )

    print(
        "Model checksum valid:",
        frozen_inputs[
            "model_checksum_matches"
        ],
    )

    if not frozen_inputs["valid"]:
        raise RuntimeError(
            "Frozen input verification failed. "
            "The model was not evaluated."
        )

    print(
        "\nLoading independent final holdout..."
    )

    records = load_jsonl(
        HOLDOUT_PATH
    )

    structure_verification = (
        verify_holdout_structure(
            records,
            manifest,
            promotion_policy,
        )
    )

    if not structure_verification["valid"]:
        raise RuntimeError(
            "Holdout structure verification "
            "failed. The model was not evaluated."
        )

    print(
        "Loaded records:",
        len(records),
    )

    print(
        "Historical holdout loaded: False"
    )

    print(
        "\nLoading preserved iteration-two "
        "candidate..."
    )

    artifact = joblib.load(
        MODEL_PATH
    )

    model_verification = (
        verify_model_artifact(
            artifact
        )
    )

    if not model_verification["valid"]:
        raise RuntimeError(
            "Candidate artifact verification "
            "failed. The model was not evaluated."
        )

    print(
        "Model:",
        artifact["model_name"],
    )

    print(
        "Context window:",
        artifact["context_window"],
    )

    print(
        "\nGenerating predictions..."
    )

    predictions = predict_candidate(
        records,
        artifact,
    )

    print(
        "Applying frozen boundary decoder..."
    )

    evaluation = evaluate_predictions(
        records,
        predictions,
        use_boundary_decoder=True,
    )

    quality_gates = evaluate_quality_gates(
        evaluation,
        promotion_policy,
    )

    mandatory_conditions = (
        evaluate_mandatory_conditions(
            frozen_inputs,
            structure_verification,
            model_verification,
        )
    )

    expected_mandatory_conditions = set(
        promotion_policy[
            "mandatory_integrity_conditions"
        ]
    )

    if set(mandatory_conditions) != (
        expected_mandatory_conditions
    ):
        raise RuntimeError(
            "Evaluator mandatory conditions do "
            "not match the frozen policy."
        )

    quality_gates_passed = all(
        gate["passed"]
        for gate in quality_gates
    )

    mandatory_conditions_passed = all(
        mandatory_conditions.values()
    )

    passed = (
        quality_gates_passed
        and mandatory_conditions_passed
    )

    decision_rules = promotion_policy[
        "decision_rules"
    ]

    decision = (
        decision_rules["pass_result"]
        if passed
        else decision_rules["fail_result"]
    )

    report = {
        "evaluation_name": (
            "contextual_entity_iteration2_"
            "final_holdout_evaluation"
        ),
        "evaluated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "model_name": artifact["model_name"],
        "model_type": artifact["model_type"],
        "dataset_name": manifest[
            "dataset_name"
        ],
        "frozen_inputs": frozen_inputs,
        "structure_verification": (
            structure_verification
        ),
        "model_verification": (
            model_verification
        ),
        "boundary_decoder_used": True,
        "evaluation": evaluation,
        "quality_gates": quality_gates,
        "mandatory_conditions": (
            mandatory_conditions
        ),
        "quality_gates_passed": (
            quality_gates_passed
        ),
        "mandatory_conditions_passed": (
            mandatory_conditions_passed
        ),
        "passed": passed,
        "decision": decision,
        "production_changed": False,
        "next_mode": (
            "controlled_shadow"
            if passed
            else "research_only"
        ),
    }

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "x",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            report,
            output_file,
            indent=2,
            sort_keys=True,
        )

        output_file.write("\n")

    print(
        "\nFinal holdout performance"
    )

    print(
        "-------------------------"
    )

    print(
        "Records:",
        evaluation["record_count"],
    )

    print_percentage_metric(
        "Exact-span precision",
        evaluation[
            "exact_span_precision"
        ],
    )

    print_percentage_metric(
        "Exact-span recall",
        evaluation[
            "exact_span_recall"
        ],
    )

    print_percentage_metric(
        "Exact-span F1",
        evaluation[
            "exact_span_f1"
        ],
    )

    print_percentage_metric(
        "Sensitive-token F1",
        evaluation[
            "sensitive_token_f1"
        ],
    )

    print(
        "False-positive records:",
        evaluation[
            "false_positive_records"
        ],
    )

    print_percentage_metric(
        "False-positive record rate",
        evaluation[
            "false_positive_record_rate"
        ],
    )

    print(
        "False-negative records:",
        evaluation[
            "false_negative_records"
        ],
    )

    print_percentage_metric(
        "False-negative record rate",
        evaluation[
            "false_negative_record_rate"
        ],
    )

    print(
        "Incorrect records:",
        evaluation[
            "incorrect_record_count"
        ],
    )

    print(
        "\nFrozen quality gates"
    )

    print(
        "--------------------"
    )

    for gate in quality_gates:
        print_quality_gate(gate)

    print(
        "\nMandatory integrity conditions"
    )

    print(
        "------------------------------"
    )

    for name, condition_passed in (
        mandatory_conditions.items()
    ):
        result = (
            "PASS"
            if condition_passed
            else "FAIL"
        )

        print(
            f"{name}: [{result}]"
        )

    print(
        "\nFINAL RESULT:",
        decision,
    )

    print(
        "\nProduction changed: False"
    )

    print(
        "Report saved to:",
        REPORT_PATH,
    )


if __name__ == "__main__":
    main()