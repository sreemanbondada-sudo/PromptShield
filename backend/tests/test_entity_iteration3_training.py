"""Tests for iteration-three entity training safeguards."""
from research.entity_localizer import (
    train_iteration3_candidates,
)


def create_evaluation(
    exact_span_f1: float,
    exact_span_precision: float,
    exact_span_recall: float,
    sensitive_token_f1: float = 0.90,
    false_positive_record_rate: float = 0.0,
    false_negative_record_rate: float = 0.0,
    incorrect_record_count: int = 0,
) -> dict:
    """Create a minimal validation evaluation."""
    return {
        "exact_span_f1": exact_span_f1,
        "exact_span_precision": (
            exact_span_precision
        ),
        "exact_span_recall": (
            exact_span_recall
        ),
        "sensitive_token_f1": (
            sensitive_token_f1
        ),
        "false_positive_record_rate": (
            false_positive_record_rate
        ),
        "false_negative_record_rate": (
            false_negative_record_rate
        ),
        "incorrect_record_count": (
            incorrect_record_count
        ),
    }


def test_only_development_splits_are_configured():
    """Training exposes only development datasets."""
    assert set(
        train_iteration3_candidates
        .DATASET_PATHS
    ) == {
        "train",
        "validation",
        "challenge",
    }

    expected_directory = (
        train_iteration3_candidates
        .SCRIPT_DIRECTORY
        / "data_iteration3"
    )

    for dataset_path in (
        train_iteration3_candidates
        .DATASET_PATHS
        .values()
    ):
        assert dataset_path.parent == (
            expected_directory
        )


def test_protected_holdouts_are_not_dataset_paths():
    """Neither frozen holdout may be loaded."""
    script_directory = (
        train_iteration3_candidates
        .SCRIPT_DIRECTORY
    )

    protected_paths = {
        (
            script_directory
            / "data"
            / "final_holdout.jsonl"
        ).resolve(),
        (
            script_directory
            / "data_iteration2_final"
            / "final_holdout.jsonl"
        ).resolve(),
    }

    configured_paths = {
        path.resolve()
        for path in (
            train_iteration3_candidates
            .DATASET_PATHS
            .values()
        )
    }

    assert configured_paths.isdisjoint(
        protected_paths
    )


def test_report_and_model_use_iteration_three_paths():
    """Outputs remain isolated from older iterations."""
    assert (
        train_iteration3_candidates
        .MODEL_DIRECTORY
        .name
        == "models_iteration3"
    )

    assert (
        train_iteration3_candidates
        .REPORT_DIRECTORY
        .name
        == "reports_iteration3"
    )

    assert (
        train_iteration3_candidates
        .ITERATION3_MODEL_PATH
        .name
        == (
            "contextual_entity_candidate_"
            "iteration3.joblib"
        )
    )

    assert (
        train_iteration3_candidates
        .REPORT_PATH
        .name
        == (
            "iteration3_candidate_"
            "evaluation.json"
        )
    )


def test_model_artifact_remains_research_only():
    """A selected candidate cannot become production."""
    classifier = object()

    candidate = {
        "model_kind": "crf",
        "context_window": 2,
        "classifier": classifier,
        "c1": 0.05,
        "c2": 0.10,
        "max_iterations": 250,
    }

    artifact = (
        train_iteration3_candidates
        .build_model_artifact(
            "test_iteration3_candidate",
            candidate,
        )
    )

    assert artifact["classifier"] is classifier

    assert artifact["model_kind"] == "crf"

    assert artifact["feature_set"] == (
        "iteration3_structural_features"
    )

    assert (
        artifact[
            "boundary_decoder_required"
        ]
        is True
    )

    assert (
        artifact[
            "historical_final_holdout_used"
        ]
        is False
    )

    assert (
        artifact[
            "iteration2_final_holdout_used"
        ]
        is False
    )

    assert (
        artifact["production_ready"]
        is False
    )

    assert (
        artifact["production_changed"]
        is False
    )

    assert artifact["mode"] == "research"


def test_selection_uses_validation_metrics():
    """Candidate ranking uses validation only."""
    stronger_validation = {
        "validation": create_evaluation(
            exact_span_f1=0.92,
            exact_span_precision=0.93,
            exact_span_recall=0.91,
        ),
        "challenge": create_evaluation(
            exact_span_f1=0.10,
            exact_span_precision=0.10,
            exact_span_recall=0.10,
        ),
    }

    weaker_validation = {
        "validation": create_evaluation(
            exact_span_f1=0.80,
            exact_span_precision=0.81,
            exact_span_recall=0.79,
        ),
        "challenge": create_evaluation(
            exact_span_f1=1.0,
            exact_span_precision=1.0,
            exact_span_recall=1.0,
        ),
    }

    stronger_score = (
        train_iteration3_candidates
        .selection_score(
            stronger_validation
        )
    )

    weaker_score = (
        train_iteration3_candidates
        .selection_score(
            weaker_validation
        )
    )

    assert stronger_score > weaker_score


def test_selection_prefers_fewer_false_positives():
    """Safety metrics break otherwise equal scores."""
    safer_result = {
        "validation": create_evaluation(
            exact_span_f1=0.90,
            exact_span_precision=0.90,
            exact_span_recall=0.90,
            false_positive_record_rate=0.0,
        )
    }

    less_safe_result = {
        "validation": create_evaluation(
            exact_span_f1=0.90,
            exact_span_precision=0.90,
            exact_span_recall=0.90,
            false_positive_record_rate=0.10,
        )
    }

    safer_score = (
        train_iteration3_candidates
        .selection_score(
            safer_result
        )
    )

    less_safe_score = (
        train_iteration3_candidates
        .selection_score(
            less_safe_result
        )
    )

    assert safer_score > less_safe_score

def test_iteration_three_feature_builder_is_used():
    """New candidates use iteration-three features."""
    import inspect

    training_source = inspect.getsource(
        train_iteration3_candidates
        .train_crf_candidate
    )

    prediction_source = inspect.getsource(
        train_iteration3_candidates
        .predict_crf_records
    )

    assert (
        "build_iteration3_sequence_features"
        in training_source
    )

    assert (
        "build_iteration3_sequence_features"
        in prediction_source
    )

    assert (
        "build_sequence_features("
        not in training_source
    )

    assert (
        "build_sequence_features("
        not in prediction_source
    )
