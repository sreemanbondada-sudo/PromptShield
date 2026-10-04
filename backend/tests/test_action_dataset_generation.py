import json

import pytest

from research.action_classifier.generation_utils import (
    assert_distribution,
    assert_template_isolation,
    assert_unique_records,
    build_sensitive_spans,
    create_record,
    generate_variants,
    write_jsonl,
)


def test_sensitive_spans_use_exact_offsets():
    prompt = (
        "Passport Z1234567 and "
        "email student@example.com"
    )

    spans = build_sensitive_spans(
        prompt,
        [
            (
                "Z1234567",
                "passport_number",
            ),
            (
                "student@example.com",
                "email_address",
            ),
        ],
    )

    assert len(spans) == 2

    for span in spans:
        assert (
            prompt[
                span["start"]:span["end"]
            ]
            == span["text"]
        )


def test_missing_sensitive_value_is_rejected():
    with pytest.raises(
        ValueError,
        match="was not found",
    ):
        build_sensitive_spans(
            "This prompt contains no identifier.",
            [
                (
                    "Z1234567",
                    "passport_number",
                ),
            ],
        )


def test_redact_record_requires_sensitive_span():
    with pytest.raises(
        ValueError,
        match="require at least one",
    ):
        create_record(
            record_number=1,
            prompt="This contains no value.",
            action="redact",
            rationale=(
                "This intentionally invalid record "
                "is used for testing."
            ),
            template_group="invalid_redact",
            split="train",
        )


def test_allow_record_rejects_sensitive_span():
    with pytest.raises(
        ValueError,
        match="cannot contain sensitive spans",
    ):
        create_record(
            record_number=2,
            prompt=(
                "My passport is Z1234567."
            ),
            action="allow",
            rationale=(
                "This intentionally invalid record "
                "is used for testing."
            ),
            template_group="invalid_allow",
            split="train",
            sensitive_values=[
                (
                    "Z1234567",
                    "passport_number",
                ),
            ],
        )


def test_variants_are_unique_and_deterministic():
    base_prompts = [
        "Explain secure password storage.",
        "Describe token protection.",
    ]

    wrappers = [
        "{content}",
        "For a security class, {content}",
        "In simple terms, {content}",
    ]

    first_result = generate_variants(
        base_prompts,
        wrappers,
        target_count=5,
    )

    second_result = generate_variants(
        base_prompts,
        wrappers,
        target_count=5,
    )

    assert first_result == second_result
    assert len(first_result) == 5

    assert len(
        {
            prompt.casefold()
            for prompt in first_result
        }
    ) == 5


def test_wrapper_requires_content_field():
    with pytest.raises(
        ValueError,
        match="must contain",
    ):
        generate_variants(
            ["Explain secure storage."],
            ["This wrapper has no field."],
            target_count=1,
        )


def test_duplicate_records_are_rejected():
    first_record = create_record(
        record_number=3,
        prompt="Explain safe authentication.",
        action="allow",
        rationale=(
            "The prompt requests defensive "
            "security information."
        ),
        template_group="safe_authentication",
        split="train",
    )

    duplicate_prompt_record = (
        create_record(
            record_number=4,
            prompt=(
                "  EXPLAIN   SAFE "
                "AUTHENTICATION. "
            ),
            action="allow",
            rationale=(
                "The prompt requests defensive "
                "security information."
            ),
            template_group=(
                "safe_authentication"
            ),
            split="train",
        )
    )

    with pytest.raises(
        ValueError,
        match="Duplicate normalized prompts",
    ):
        assert_unique_records(
            [
                first_record,
                duplicate_prompt_record,
            ]
        )


def test_template_leakage_is_rejected():
    training_record = create_record(
        record_number=5,
        prompt="Explain passport renewal.",
        action="allow",
        rationale=(
            "The prompt requests a legal "
            "administrative procedure."
        ),
        template_group="passport_help",
        split="train",
    )

    test_record = create_record(
        record_number=6,
        prompt="How does passport renewal work?",
        action="allow",
        rationale=(
            "The prompt requests a legal "
            "administrative procedure."
        ),
        template_group="passport_help",
        split="test",
    )

    with pytest.raises(
        ValueError,
        match="leak across splits",
    ):
        assert_template_isolation(
            [
                training_record,
                test_record,
            ]
        )


def test_expected_distribution_is_enforced():
    records = [
        create_record(
            record_number=7,
            prompt="Explain defensive security.",
            action="allow",
            rationale=(
                "The prompt requests defensive "
                "security education."
            ),
            template_group="defensive_security",
            split="train",
        ),
        create_record(
            record_number=8,
            prompt="This access request is unclear.",
            action="review",
            rationale=(
                "The request lacks sufficient "
                "authorization context."
            ),
            template_group="unclear_access",
            split="train",
        ),
    ]

    assert_distribution(
        records,
        {
            "train": {
                "allow": 1,
                "review": 1,
                "redact": 0,
                "block": 0,
            },
        },
    )

    with pytest.raises(
        ValueError,
        match="Unexpected train",
    ):
        assert_distribution(
            records,
            {
                "train": {
                    "allow": 2,
                    "review": 0,
                    "redact": 0,
                    "block": 0,
                },
            },
        )


def test_jsonl_writer_creates_valid_records(
    tmp_path,
):
    record = create_record(
        record_number=9,
        prompt="Explain safe token storage.",
        action="allow",
        rationale=(
            "The prompt requests defensive "
            "token-storage guidance."
        ),
        template_group="safe_token_storage",
        split="validation",
    )

    destination = (
        tmp_path / "validation.jsonl"
    )

    write_jsonl(
        destination,
        [record],
    )

    lines = destination.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(lines) == 1
    assert json.loads(lines[0]) == record