from research.entity_localizer.build_entity_dataset import (
    tokenize_prompt,
)

from research.entity_localizer.iteration3_features import (
    build_component_features,
    build_iteration3_sequence_features,
    build_iteration3_token_features,
    count_characters,
    is_connector_token,
    is_structured_token,
    length_bucket,
    ratio_bucket,
    token_gap,
)


def find_token_index(
    tokens: list[dict],
    token_text: str,
) -> int:
    """Find the first matching token."""
    return next(
        index
        for index, token in enumerate(tokens)
        if token["text"] == token_text
    )


def test_character_counts_are_calculated():
    """Character-class counts are deterministic."""
    assert count_characters(
        "Ab12-_"
    ) == {
        "digit_count": 2,
        "alpha_count": 2,
        "whitespace_count": 0,
        "special_count": 2,
    }


def test_ratio_buckets_are_stable():
    """Ratios use coarse non-memorizing categories."""
    assert ratio_bucket(0, 4) == "zero"
    assert ratio_bucket(1, 8) == "low"
    assert ratio_bucket(2, 4) == "mixed"
    assert ratio_bucket(3, 4) == "high"
    assert ratio_bucket(4, 4) == "all"
    assert ratio_bucket(0, 0) == "none"


def test_length_buckets_are_stable():
    """Lengths are grouped into coarse categories."""
    assert length_bucket(0) == "empty"
    assert length_bucket(1) == "one"
    assert length_bucket(3) == "short"
    assert length_bucket(6) == "medium"
    assert length_bucket(12) == "long"
    assert length_bucket(13) == "very_long"


def test_structural_token_classification():
    """Numeric and connector tokens are structural."""
    assert is_structured_token("89001") is True
    assert is_structured_token("+") is True
    assert is_structured_token("AB12") is True

    assert is_structured_token(
        "ordinary"
    ) is False

    assert is_connector_token("+") is True
    assert is_connector_token("-") is True
    assert is_connector_token("@") is True

    assert is_connector_token(
        "ordinary"
    ) is False


def test_token_gap_uses_character_offsets():
    """Token gaps preserve spacing information."""
    tokens = tokenize_prompt(
        "+91 89001 33037"
    )

    assert token_gap(
        tokens[0],
        tokens[1],
    ) == 0

    assert token_gap(
        tokens[1],
        tokens[2],
    ) == 1


def test_phone_component_is_recognized():
    """Separated phone groups form one component."""
    tokens = tokenize_prompt(
        "Contact +91 89001 33037 privately."
    )

    token_index = find_token_index(
        tokens,
        "89001",
    )

    features = build_component_features(
        tokens,
        token_index,
    )

    assert (
        features["component:is_structured"]
        is True
    )

    assert (
        features[
            "component:numeric_group_count"
        ]
        == 3
    )

    assert (
        features["component:digit_count"]
        == 12
    )

    assert (
        features["component:starts_with_plus"]
        is True
    )

    assert (
        features["component:ends_with_digit"]
        is True
    )


def test_card_component_is_recognized():
    """Separated card groups form one component."""
    tokens = tokenize_prompt(
        "Card 4929 6101 7201 8301."
    )

    token_index = find_token_index(
        tokens,
        "6101",
    )

    features = build_component_features(
        tokens,
        token_index,
    )

    assert (
        features[
            "component:numeric_group_count"
        ]
        == 4
    )

    assert (
        features["component:digit_count"]
        == 16
    )

    assert (
        features["component:token_count"]
        == 4
    )


def test_hyphenated_safe_word_has_no_digits():
    """A safe hyphen must not resemble a phone."""
    tokens = tokenize_prompt(
        "Explain identity-verification checks."
    )

    token_index = find_token_index(
        tokens,
        "-",
    )

    features = build_component_features(
        tokens,
        token_index,
    )

    assert (
        features["component:digit_count"]
        == 0
    )

    assert (
        features[
            "component:numeric_group_count"
        ]
        == 0
    )

    assert (
        features["component:starts_with_plus"]
        is False
    )


def test_phone_token_receives_context_features():
    """A phone group receives local context signals."""
    tokens = tokenize_prompt(
        "Remove +91 85025 85925 before sharing."
    )

    token_index = find_token_index(
        tokens,
        "91",
    )

    features = (
        build_iteration3_token_features(
            tokens,
            token_index,
            context_window=2,
        )
    )

    assert (
        features[
            "iteration3:current:"
            "is_short_numeric_group"
        ]
        is True
    )

    assert (
        features[
            "iteration3:numeric_after_plus"
        ]
        is True
    )

    assert (
        features[
            "component:numeric_group_count"
        ]
        == 3
    )


def test_plus_token_knows_numeric_neighbor():
    """A plus sign before digits receives a signal."""
    tokens = tokenize_prompt(
        "Call +91 70000 12345."
    )

    token_index = find_token_index(
        tokens,
        "+",
    )

    features = (
        build_iteration3_token_features(
            tokens,
            token_index,
            context_window=2,
        )
    )

    assert (
        features[
            "iteration3:plus_before_numeric"
        ]
        is True
    )


def test_sequence_features_match_token_counts():
    """Every token receives one feature mapping."""
    record = {
        "prompt": (
            "Protect +91 70000 12345."
        ),
        "tokens": tokenize_prompt(
            "Protect +91 70000 12345."
        ),
    }

    sequences = (
        build_iteration3_sequence_features(
            [record],
            context_window=2,
        )
    )

    assert len(sequences) == 1

    assert len(sequences[0]) == len(
        record["tokens"]
    )

    assert all(
        isinstance(features, dict)
        for features in sequences[0]
    )