import pytest

from research.entity_localizer import (
    boundary_decoder,
    build_entity_dataset,
)


def create_labels_for_values(
    prompt: str,
    tokens: list[dict],
    predicted_values: list[str],
) -> list[str]:
    """Create BIO labels for selected prompt substrings."""
    labels = [
        "O"
        for _ in tokens
    ]

    for predicted_value in predicted_values:
        value_start = prompt.index(
            predicted_value
        )

        value_end = (
            value_start
            + len(predicted_value)
        )

        overlapping_indexes = [
            token_index
            for token_index, token in enumerate(
                tokens
            )
            if (
                token["start"] < value_end
                and token["end"] > value_start
            )
        ]

        if not overlapping_indexes:
            raise AssertionError(
                "The selected value did not overlap "
                "any tokens."
            )

        for position, token_index in enumerate(
            overlapping_indexes
        ):
            labels[token_index] = (
                "B-SENSITIVE"
                if position == 0
                else "I-SENSITIVE"
            )

    return labels


def decode_values(
    prompt: str,
    predicted_values: list[str],
) -> dict:
    """Tokenize a prompt and decode selected values."""
    tokens = (
        build_entity_dataset
        .tokenize_prompt(prompt)
    )

    predicted_labels = (
        create_labels_for_values(
            prompt,
            tokens,
            predicted_values,
        )
    )

    return (
        boundary_decoder
        .decode_sensitive_spans(
            prompt,
            tokens,
            predicted_labels,
        )
    )


def extracted_texts(
    result: dict,
) -> list[str]:
    """Return only the reconstructed span text."""
    return [
        span["text"]
        for span in result["spans"]
    ]


def test_partial_email_prefix_is_expanded():
    prompt = (
        "Update the customer record for "
        "rohan.sen@example.net."
    )

    result = decode_values(
        prompt,
        [
            "sen@example.net",
        ],
    )

    assert extracted_texts(result) == [
        "rohan.sen@example.net",
    ]


def test_partial_email_with_leading_period_is_expanded():
    prompt = (
        "The applicant is reachable at "
        "isha.mehta@example.com and supplied "
        "passport LM0000077."
    )

    result = decode_values(
        prompt,
        [
            ".mehta@example.com",
        ],
    )

    assert extracted_texts(result) == [
        "isha.mehta@example.com",
    ]


def test_terminal_sentence_period_is_not_included():
    prompt = (
        "Send the update to "
        "student@example.com."
    )

    result = decode_values(
        prompt,
        [
            "student@example.com",
        ],
    )

    assert extracted_texts(result) == [
        "student@example.com",
    ]


def test_repeated_numeric_sequence_is_extended():
    prompt = (
        "Use fictional card number "
        "4111 1111 1111 1111 in the test."
    )

    result = decode_values(
        prompt,
        [
            "4111 1111 1111",
        ],
    )

    assert extracted_texts(result) == [
        "4111 1111 1111 1111",
    ]


def test_hyphen_separated_numeric_sequence_is_extended():
    prompt = (
        "The sample value is "
        "1234-5678-9012-3456 for testing."
    )

    result = decode_values(
        prompt,
        [
            "1234-5678-9012",
        ],
    )

    assert extracted_texts(result) == [
        "1234-5678-9012-3456",
    ]


@pytest.mark.parametrize(
    "prompt",
    [
        (
            "Why do regulated services perform "
            "identity-verification checks?"
        ),
        (
            "Who should be notified after a "
            "personal-data breach?"
        ),
    ],
)
def test_isolated_hyphen_prediction_is_removed(
    prompt,
):
    result = decode_values(
        prompt,
        [
            "-",
        ],
    )

    assert result["spans"] == []

    assert all(
        label == "O"
        for label in result["labels"]
    )


def test_normal_alphanumeric_prediction_is_preserved():
    prompt = (
        "The supplied passport is LM0000077."
    )

    result = decode_values(
        prompt,
        [
            "LM0000077",
        ],
    )

    assert extracted_texts(result) == [
        "LM0000077",
    ]


def test_multiple_separate_entities_are_preserved():
    prompt = (
        "The applicant is reachable at "
        "isha.mehta@example.com and supplied "
        "passport LM0000077."
    )

    result = decode_values(
        prompt,
        [
            "mehta@example.com",
            "LM0000077",
        ],
    )

    assert extracted_texts(result) == [
        "isha.mehta@example.com",
        "LM0000077",
    ]


def test_safe_prompt_with_no_predictions_stays_empty():
    prompt = (
        "Explain why organizations perform "
        "identity verification."
    )

    result = decode_values(
        prompt,
        [],
    )

    assert result["spans"] == []

    assert all(
        label == "O"
        for label in result["labels"]
    )


def test_invalid_i_label_is_normalized():
    prompt = "Reference value AB123456."

    tokens = (
        build_entity_dataset
        .tokenize_prompt(prompt)
    )

    labels = [
        "O"
        for _ in tokens
    ]

    target_index = next(
        token_index
        for token_index, token in enumerate(
            tokens
        )
        if token["text"] == "AB123456"
    )

    labels[target_index] = "I-SENSITIVE"

    result = (
        boundary_decoder
        .decode_sensitive_spans(
            prompt,
            tokens,
            labels,
        )
    )

    assert extracted_texts(result) == [
        "AB123456",
    ]

    assert (
        result["labels"][target_index]
        == "B-SENSITIVE"
    )


def test_mismatched_token_and_label_counts_are_rejected():
    prompt = "Example value AB123456."

    tokens = (
        build_entity_dataset
        .tokenize_prompt(prompt)
    )

    with pytest.raises(
        ValueError,
        match="counts must match",
    ):
        boundary_decoder.repair_bio_labels(
            prompt,
            tokens,
            ["O"],
        )


def test_unsupported_bio_label_is_rejected():
    prompt = "Example value AB123456."

    tokens = (
        build_entity_dataset
        .tokenize_prompt(prompt)
    )

    labels = [
        "O"
        for _ in tokens
    ]

    labels[0] = "SENSITIVE"

    with pytest.raises(
        ValueError,
        match="Unsupported BIO label",
    ):
        boundary_decoder.repair_bio_labels(
            prompt,
            tokens,
            labels,
        )