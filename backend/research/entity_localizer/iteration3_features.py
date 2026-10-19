"""General structural token features for entity iteration three."""

from research.entity_localizer.train_entity_candidates import (
    build_token_features,
)


STRUCTURAL_CONNECTORS = {
    "+",
    "-",
    "_",
    ".",
    "/",
    ":",
    "@",
    "#",
    "(",
    ")",
}

NUMERIC_SEPARATORS = {
    "-",
    "/",
    ".",
    "(",
    ")",
}

MAX_COMPONENT_GAP = 1


def count_characters(
    token_text: str,
) -> dict:
    """Count general character classes."""
    digit_count = sum(
        character.isdigit()
        for character in token_text
    )

    alpha_count = sum(
        character.isalpha()
        for character in token_text
    )

    whitespace_count = sum(
        character.isspace()
        for character in token_text
    )

    special_count = (
        len(token_text)
        - digit_count
        - alpha_count
        - whitespace_count
    )

    return {
        "digit_count": digit_count,
        "alpha_count": alpha_count,
        "whitespace_count": whitespace_count,
        "special_count": special_count,
    }


def ratio_bucket(
    numerator: int,
    denominator: int,
) -> str:
    """Convert a ratio into a stable category."""
    if denominator <= 0:
        return "none"

    ratio = numerator / denominator

    if ratio == 0:
        return "zero"

    if ratio < 0.25:
        return "low"

    if ratio < 0.75:
        return "mixed"

    if ratio < 1.0:
        return "high"

    return "all"


def length_bucket(length: int) -> str:
    """Return a coarse token-length category."""
    if length == 0:
        return "empty"

    if length == 1:
        return "one"

    if length <= 3:
        return "short"

    if length <= 6:
        return "medium"

    if length <= 12:
        return "long"

    return "very_long"


def is_connector_token(
    token_text: str,
) -> bool:
    """Return whether a token joins structured values."""
    return token_text in STRUCTURAL_CONNECTORS


def is_numeric_separator(
    token_text: str,
) -> bool:
    """Return whether a token separates numeric groups."""
    return token_text in NUMERIC_SEPARATORS


def is_structured_token(
    token_text: str,
) -> bool:
    """Return whether a token can form a structured value."""
    return (
        token_text.isdigit()
        or is_connector_token(token_text)
        or (
            any(
                character.isdigit()
                for character in token_text
            )
            and any(
                character.isalpha()
                for character in token_text
            )
        )
    )


def token_gap(
    left_token: dict,
    right_token: dict,
) -> int:
    """Return the character gap between two tokens."""
    return max(
        0,
        int(right_token["start"])
        - int(left_token["end"]),
    )


def tokens_can_connect(
    left_token: dict,
    right_token: dict,
) -> bool:
    """Return whether adjacent tokens form one structure."""
    if token_gap(
        left_token,
        right_token,
    ) > MAX_COMPONENT_GAP:
        return False

    left_text = left_token["text"]
    right_text = right_token["text"]

    if not (
        is_structured_token(left_text)
        and is_structured_token(right_text)
    ):
        return False

    return (
        left_text.isdigit()
        or right_text.isdigit()
        or is_connector_token(left_text)
        or is_connector_token(right_text)
    )


def find_component_start(
    tokens: list[dict],
    token_index: int,
) -> int:
    """Find the start of a connected structure."""
    start = token_index

    while start > 0:
        if not tokens_can_connect(
            tokens[start - 1],
            tokens[start],
        ):
            break

        start -= 1

    return start


def find_component_end(
    tokens: list[dict],
    token_index: int,
) -> int:
    """Find the end of a connected structure."""
    end = token_index

    while end + 1 < len(tokens):
        if not tokens_can_connect(
            tokens[end],
            tokens[end + 1],
        ):
            break

        end += 1

    return end


def build_component_features(
    tokens: list[dict],
    token_index: int,
) -> dict:
    """Describe the connected structured component."""
    current_text = tokens[token_index][
        "text"
    ]

    if not is_structured_token(current_text):
        return {
            "component:is_structured": False,
            "component:token_count": 0,
            "component:numeric_group_count": 0,
            "component:digit_count": 0,
            "component:connector_count": 0,
            "component:starts_with_plus": False,
            "component:ends_with_digit": False,
            "component:current_is_first": False,
            "component:current_is_last": False,
        }

    start = find_component_start(
        tokens,
        token_index,
    )

    end = find_component_end(
        tokens,
        token_index,
    )

    while (
        end > start
        and is_connector_token(
            tokens[end]["text"]
        )
    ):
        end -= 1

    while (
        start < end
        and is_connector_token(
            tokens[start]["text"]
        )
        and tokens[start]["text"]
        not in {
            "+",
            "(",
        }
    ):
        start += 1

    component_tokens = tokens[
        start:
        end + 1
    ]

    component_texts = [
        token["text"]
        for token in component_tokens
    ]

    numeric_groups = [
        token_text
        for token_text in component_texts
        if token_text.isdigit()
    ]

    digit_count = sum(
        sum(
            character.isdigit()
            for character in token_text
        )
        for token_text in component_texts
    )

    connector_count = sum(
        is_connector_token(token_text)
        for token_text in component_texts
    )

    numeric_group_lengths = [
        len(group)
        for group in numeric_groups
    ]

    return {
        "component:is_structured": True,
        "component:token_count": min(
            len(component_tokens),
            20,
        ),
        "component:numeric_group_count": min(
            len(numeric_groups),
            10,
        ),
        "component:digit_count": min(
            digit_count,
            40,
        ),
        "component:digit_count_bucket": (
            length_bucket(digit_count)
        ),
        "component:connector_count": min(
            connector_count,
            10,
        ),
        "component:starts_with_plus": (
            component_texts[0] == "+"
        ),
        "component:ends_with_digit": (
            component_texts[-1].isdigit()
        ),
        "component:has_numeric_separator": any(
            is_numeric_separator(token_text)
            for token_text in component_texts
        ),
        "component:has_at": (
            "@" in component_texts
        ),
        "component:has_period": (
            "." in component_texts
        ),
        "component:has_hyphen": (
            "-" in component_texts
        ),
        "component:has_underscore": (
            "_" in component_texts
        ),
        "component:current_is_first": (
            token_index == start
        ),
        "component:current_is_last": (
            token_index == end
        ),
        "component:current_position": (
            token_index - start
        ),
        "component:max_numeric_group_length": (
            max(numeric_group_lengths)
            if numeric_group_lengths
            else 0
        ),
        "component:min_numeric_group_length": (
            min(numeric_group_lengths)
            if numeric_group_lengths
            else 0
        ),
    }

def add_iteration3_token_features(
    features: dict,
    prefix: str,
    token_text: str,
) -> None:
    """Add richer general token-shape features."""
    counts = count_characters(
        token_text
    )

    token_length = len(token_text)

    features[
        f"{prefix}:length_bucket"
    ] = length_bucket(token_length)

    features[
        f"{prefix}:digit_count"
    ] = min(
        counts["digit_count"],
        40,
    )

    features[
        f"{prefix}:alpha_count"
    ] = min(
        counts["alpha_count"],
        40,
    )

    features[
        f"{prefix}:special_count"
    ] = min(
        counts["special_count"],
        20,
    )

    features[
        f"{prefix}:digit_ratio"
    ] = ratio_bucket(
        counts["digit_count"],
        token_length,
    )

    features[
        f"{prefix}:alpha_ratio"
    ] = ratio_bucket(
        counts["alpha_count"],
        token_length,
    )

    features[
        f"{prefix}:is_connector"
    ] = is_connector_token(
        token_text
    )

    features[
        f"{prefix}:is_numeric_separator"
    ] = is_numeric_separator(
        token_text
    )

    features[
        f"{prefix}:is_structured"
    ] = is_structured_token(
        token_text
    )

    features[
        f"{prefix}:is_short_numeric_group"
    ] = (
        token_text.isdigit()
        and 1 <= len(token_text) <= 3
    )

    features[
        f"{prefix}:is_medium_numeric_group"
    ] = (
        token_text.isdigit()
        and 4 <= len(token_text) <= 6
    )

    features[
        f"{prefix}:is_long_numeric_group"
    ] = (
        token_text.isdigit()
        and len(token_text) >= 7
    )


def build_iteration3_token_features(
    tokens: list[dict],
    token_index: int,
    context_window: int,
) -> dict:
    """Build base and iteration-three features."""
    features = build_token_features(
        tokens,
        token_index,
        context_window,
    )

    current_token = tokens[token_index]

    add_iteration3_token_features(
        features,
        "iteration3:current",
        current_token["text"],
    )

    features.update(
        build_component_features(
            tokens,
            token_index,
        )
    )

    for distance in range(
        1,
        context_window + 1,
    ):
        previous_index = token_index - distance
        next_index = token_index + distance

        if previous_index >= 0:
            previous_token = tokens[
                previous_index
            ]

            add_iteration3_token_features(
                features,
                (
                    "iteration3:"
                    f"previous_{distance}"
                ),
                previous_token["text"],
            )

            features[
                (
                    "iteration3:"
                    f"previous_{distance}:gap"
                )
            ] = token_gap(
                previous_token,
                current_token,
            )

        if next_index < len(tokens):
            next_token = tokens[
                next_index
            ]

            add_iteration3_token_features(
                features,
                (
                    "iteration3:"
                    f"next_{distance}"
                ),
                next_token["text"],
            )

            features[
                (
                    "iteration3:"
                    f"next_{distance}:gap"
                )
            ] = token_gap(
                current_token,
                next_token,
            )

    previous_is_numeric = (
        token_index > 0
        and tokens[
            token_index - 1
        ]["text"].isdigit()
    )

    next_is_numeric = (
        token_index + 1 < len(tokens)
        and tokens[
            token_index + 1
        ]["text"].isdigit()
    )

    features[
        "iteration3:previous_is_numeric"
    ] = previous_is_numeric

    features[
        "iteration3:next_is_numeric"
    ] = next_is_numeric

    features[
        "iteration3:between_numeric_groups"
    ] = (
        is_connector_token(
            current_token["text"]
        )
        and previous_is_numeric
        and next_is_numeric
    )

    features[
        "iteration3:plus_before_numeric"
    ] = (
        current_token["text"] == "+"
        and next_is_numeric
    )

    features[
        "iteration3:numeric_after_plus"
    ] = (
        current_token["text"].isdigit()
        and token_index > 0
        and tokens[
            token_index - 1
        ]["text"] == "+"
    )

    return features


def build_iteration3_sequence_features(
    records: list[dict],
    context_window: int,
) -> list[list[dict]]:
    """Build iteration-three CRF feature sequences."""
    return [
        [
            build_iteration3_token_features(
                record["tokens"],
                token_index,
                context_window,
            )
            for token_index in range(
                len(record["tokens"])
            )
        ]
        for record in records
    ]