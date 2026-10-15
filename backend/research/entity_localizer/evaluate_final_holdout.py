"""Perform the one-time final entity holdout evaluation."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib


SCRIPT_DIRECTORY = (
    Path(__file__).resolve().parent
)

BACKEND_DIRECTORY = (
    SCRIPT_DIRECTORY.parents[1]
)

if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIRECTORY),
    )


from research.entity_localizer.evaluate_boundary_decoder import (
    evaluate_predictions,
)

from research.entity_localizer.train_entity_candidates import (
    load_jsonl,
    predict_records,
)


HOLDOUT_PATH = (
    SCRIPT_DIRECTORY
    / "data"
    / "final_holdout.jsonl"
)

MANIFEST_PATH = (
    SCRIPT_DIRECTORY
    / "final_holdout_manifest.json"
)

PROMOTION_GATES_PATH = (
    SCRIPT_DIRECTORY
    / "promotion_gates.json"
)

MODEL_PATH = (
    SCRIPT_DIRECTORY
    / "models"
    / "contextual_entity_candidate.joblib"
)

BOUNDARY_DECODER_PATH = (
    SCRIPT_DIRECTORY
    / "boundary_decoder.py"
)

REPORT_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "reports"
)

REPORT_PATH = (
    REPORT_DIRECTORY
    / "final_holdout_evaluation.json"
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


def calculate_sha256(path: Path) -> str:
    """Calculate a file SHA-256 checksum."""
    if not path.exists():
        raise RuntimeError(
            f"Required file was not found: {path}"
        )

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


def verify_holdout(
    manifest: dict,
) -> dict:
    """Verify that the frozen holdout is unchanged."""
    actual_sha256 = calculate_sha256(
        HOLDOUT_PATH
    )

    expected_sha256 = manifest.get(
        "sha256"
    )

    checksum_matches = (
        actual_sha256
        == expected_sha256
    )

    required_manifest_conditions = {
        "frozen": (
            manifest.get("frozen")
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
        "not_derived_from_development_data": (
            manifest.get(
                "derived_from_development_data"
            )
            is False
        ),
    }

    manifest_is_valid = all(
        required_manifest_conditions.values()
    )

    return {
        "expected_sha256": expected_sha256,
        "actual_sha256": actual_sha256,
        "checksum_matches": (
            checksum_matches
        ),
        "manifest_conditions": (
            required_manifest_conditions
        ),
        "manifest_is_valid": (
            manifest_is_valid
        ),
        "valid": (
            checksum_matches
            and manifest_is_valid
        ),
    }


def evaluate_minimum_gate(
    metric_name: str,
    actual_value: float,
    minimum_value: float,
) -> dict:
    """Evaluate one minimum performance gate."""
    return {
        "metric": metric_name,
        "comparison": "minimum",
        "required": minimum_value,
        "actual": actual_value,
        "passed": (
            actual_value
            >= minimum_value
        ),
    }


def evaluate_maximum_gate(
    metric_name: str,
    actual_value: float,
    maximum_value: float,
) -> dict:
    """Evaluate one maximum performance gate."""
    return {
        "metric": metric_name,
        "comparison": "maximum",
        "required": maximum_value,
        "actual": actual_value,
        "passed": (
            actual_value
            <= maximum_value
        ),
    }


def evaluate_promotion_gates(
    evaluation: dict,
    promotion_policy: dict,
    holdout_verification: dict,
) -> dict:
    """Apply every frozen promotion gate."""
    metric_gates = []

    for metric_name, minimum_value in (
        promotion_policy[
            "minimum_metrics"
        ].items()
    ):
        if metric_name not in evaluation:
            raise RuntimeError(
                "Evaluation result does not contain "
                f"required metric {metric_name!r}."
            )

        metric_gates.append(
            evaluate_minimum_gate(
                metric_name,
                evaluation[metric_name],
                minimum_value,
            )
        )

    for metric_name, maximum_value in (
        promotion_policy[
            "maximum_metrics"
        ].items()
    ):
        if metric_name not in evaluation:
            raise RuntimeError(
                "Evaluation result does not contain "
                f"required metric {metric_name!r}."
            )

        metric_gates.append(
            evaluate_maximum_gate(
                metric_name,
                evaluation[metric_name],
                maximum_value,
            )
        )

    mandatory_conditions = {
        "holdout_checksum_matches": (
            holdout_verification[
                "checksum_matches"
            ]
        ),
        "holdout_manifest_is_valid": (
            holdout_verification[
                "manifest_is_valid"
            ]
        ),
        "boundary_decoder_used": True,
        "holdout_not_used_for_training": (
            holdout_verification[
                "manifest_conditions"
            ][
                "not_used_for_training"
            ]
        ),
        "holdout_not_used_for_model_selection": (
            holdout_verification[
                "manifest_conditions"
            ][
                "not_used_for_model_selection"
            ]
        ),
        "holdout_not_used_for_threshold_tuning": (
            holdout_verification[
                "manifest_conditions"
            ][
                "not_used_for_threshold_tuning"
            ]
        ),
    }

    metric_gates_passed = all(
        gate["passed"]
        for gate in metric_gates
    )

    mandatory_conditions_passed = all(
        mandatory_conditions.values()
    )

    all_gates_passed = (
        metric_gates_passed
        and mandatory_conditions_passed
    )

    return {
        "metric_gates": metric_gates,
        "mandatory_conditions": (
            mandatory_conditions
        ),
        "metric_gates_passed": (
            metric_gates_passed
        ),
        "mandatory_conditions_passed": (
            mandatory_conditions_passed
        ),
        "all_gates_passed": (
            all_gates_passed
        ),
    }


def print_metric(
    label: str,
    value: float,
) -> None:
    """Print a percentage metric."""
    print(
        f"{label}: {value:.2%}"
    )


def print_gate_result(gate: dict) -> None:
    """Print one promotion-gate result."""
    result = (
        "PASS"
        if gate["passed"]
        else "FAIL"
    )

    if gate["metric"].endswith(
        "_records"
    ):
        actual_text = str(
            gate["actual"]
        )

        required_text = str(
            gate["required"]
        )

    else:
        actual_text = (
            f"{gate['actual']:.2%}"
        )

        required_text = (
            f"{gate['required']:.2%}"
        )

    comparison_text = (
        "minimum"
        if gate["comparison"] == "minimum"
        else "maximum"
    )

    print(
        f"{gate['metric']}: "
        f"{actual_text} "
        f"({comparison_text} "
        f"{required_text}) "
        f"[{result}]"
    )


def main() -> None:
    """Run the protected one-time evaluation."""
    if REPORT_PATH.exists():
        raise RuntimeError(
            "The final holdout has already been "
            "evaluated. Refusing to overwrite the "
            f"existing report: {REPORT_PATH}"
        )

    required_paths = [
        HOLDOUT_PATH,
        MANIFEST_PATH,
        PROMOTION_GATES_PATH,
        MODEL_PATH,
        BOUNDARY_DECODER_PATH,
    ]

    for required_path in required_paths:
        if not required_path.exists():
            raise RuntimeError(
                "Required evaluation file was not "
                f"found: {required_path}"
            )

    print(
        "Loading frozen entity holdout..."
    )

    manifest = load_json(
        MANIFEST_PATH
    )

    promotion_policy = load_json(
        PROMOTION_GATES_PATH
    )

    holdout_verification = (
        verify_holdout(manifest)
    )

    print(
        "Expected SHA-256: "
        f"{holdout_verification[
            'expected_sha256'
        ]}"
    )

    print(
        "Actual SHA-256:   "
        f"{holdout_verification[
            'actual_sha256'
        ]}"
    )

    print(
        "Checksum valid: "
        f"{holdout_verification[
            'checksum_matches'
        ]}"
    )

    if not holdout_verification["valid"]:
        raise RuntimeError(
            "The frozen holdout verification failed. "
            "Evaluation has been stopped."
        )

    records = load_jsonl(
        HOLDOUT_PATH
    )

    if len(records) != manifest[
        "record_count"
    ]:
        raise RuntimeError(
            "Holdout record count does not match "
            "the frozen manifest."
        )

    print(
        f"Loaded records: {len(records)}"
    )

    print(
        "\nLoading preserved entity candidate..."
    )

    artifact = joblib.load(
        MODEL_PATH
    )

    print(
        "Model: "
        f"{artifact['model_name']}"
    )

    print(
        "Context window: "
        f"{artifact['context_window']}"
    )

    (
        _,
        predictions_by_record,
    ) = predict_records(
        records,
        artifact["vectorizer"],
        artifact["classifier"],
        artifact["context_window"],
    )

    print(
        "\nApplying frozen boundary decoder..."
    )

    evaluation = evaluate_predictions(
        records,
        predictions_by_record,
        use_boundary_decoder=True,
    )

    print(
        "\nFinal holdout performance"
    )

    print(
        "-------------------------"
    )

    print(
        "Records: "
        f"{evaluation['record_count']}"
    )

    print_metric(
        "Exact-span precision",
        evaluation[
            "exact_span_precision"
        ],
    )

    print_metric(
        "Exact-span recall",
        evaluation[
            "exact_span_recall"
        ],
    )

    print_metric(
        "Exact-span F1",
        evaluation[
            "exact_span_f1"
        ],
    )

    print_metric(
        "Sensitive-token F1",
        evaluation[
            "sensitive_token_f1"
        ],
    )

    print(
        "False-positive records: "
        f"{evaluation[
            'false_positive_records'
        ]}"
    )

    print_metric(
        "False-positive record rate",
        evaluation[
            "false_positive_record_rate"
        ],
    )

    print(
        "False-negative records: "
        f"{evaluation[
            'false_negative_records'
        ]}"
    )

    print_metric(
        "False-negative record rate",
        evaluation[
            "false_negative_record_rate"
        ],
    )

    print(
        "Incorrect records: "
        f"{evaluation[
            'incorrect_record_count'
        ]}"
    )

    gate_results = (
        evaluate_promotion_gates(
            evaluation,
            promotion_policy,
            holdout_verification,
        )
    )

    print(
        "\nFrozen promotion gates"
    )

    print(
        "----------------------"
    )

    for gate in gate_results[
        "metric_gates"
    ]:
        print_gate_result(gate)

    print(
        "\nMandatory conditions"
    )

    for condition_name, passed in (
        gate_results[
            "mandatory_conditions"
        ].items()
    ):
        result = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{condition_name}: [{result}]"
        )

    all_gates_passed = (
        gate_results[
            "all_gates_passed"
        ]
    )

    if all_gates_passed:
        final_decision = (
            "PASS FOR CONTROLLED SHADOW "
            "INTEGRATION"
        )

    else:
        final_decision = (
            "FAIL - DO NOT PROMOTE"
        )

    report = {
        "evaluation": (
            "contextual_sensitive_entity_"
            "final_holdout_v1"
        ),
        "evaluated_at_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "model": {
            "name": artifact[
                "model_name"
            ],
            "path": str(MODEL_PATH),
            "sha256": calculate_sha256(
                MODEL_PATH
            ),
            "context_window": artifact[
                "context_window"
            ],
            "production_ready_before_evaluation": (
                artifact.get(
                    "production_ready"
                )
            ),
        },
        "boundary_decoder": {
            "path": str(
                BOUNDARY_DECODER_PATH
            ),
            "sha256": calculate_sha256(
                BOUNDARY_DECODER_PATH
            ),
            "used": True,
        },
        "holdout": {
            "path": str(HOLDOUT_PATH),
            "manifest_path": str(
                MANIFEST_PATH
            ),
            "verification": (
                holdout_verification
            ),
        },
        "promotion_policy": (
            promotion_policy
        ),
        "performance": evaluation,
        "gate_results": gate_results,
        "final_decision": final_decision,
        "production_changed": False,
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
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        output_file.write("\n")

    print(
        "\nFINAL RESULT: "
        f"{final_decision}"
    )

    print(
        "\nProduction changed: False"
    )

    print(
        f"Report saved to: {REPORT_PATH}"
    )


if __name__ == "__main__":
    main()