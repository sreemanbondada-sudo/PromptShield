"""General BIO boundary repair for sensitive-entity predictions."""

from dataclasses import dataclass


SENSITIVE_LABELS = {
    "B-SENSITIVE",
    "I-SENSITIVE",
}

STRUCTURAL_CONNECTORS = {
    ".",
    "@",
    "_",
    "-",
    "+",
    ":",
    "/",
    "\\",
}

NUMERIC_SEPARATORS = {
    " ",
    "-",
}


@dataclass
class TokenGroup:
    """Inclusive token-index boundaries for one entity."""

    start: int
    end: int


def normalize_bio_labels(
    predicted_labels: list[str],
) -> list[str]:
    """Convert invalid standalone I labels into B labels."""
    normalized_labels = []
    previous_label = "O"

    for predicted_label in predicted_labels:
        label = predicted_label

        if label not in {
            "B-SENSITIVE",
            "I-SENSITIVE",
            "O",
        }:
            raise ValueError(
                f"Unsupported BIO label: {label!r}."
            )

        if (
            label == "I-SENSITIVE"
            and previous_label not in {
                "B-SENSITIVE",
                "I-SENSITIVE",
            }
        ):
            label = "B-SENSITIVE"

        normalized_labels.append(label)
        previous_label = label

    return normalized_labels


def labels_to_groups(
    labels: list[str],
) -> list[TokenGroup]:
    """Convert BIO labels into token-index groups."""
    groups = []
    active_start = None

    for token_index, label in enumerate(labels):
        if label == "B-SENSITIVE":
            if active_start is not None:
                groups.append(
                    TokenGroup(
                        start=active_start,
                        end=token_index - 1,
                    )
                )

            active_start = token_index

        elif label == "I-SENSITIVE":
            if active_start is None:
                active_start = token_index

        elif active_start is not None:
            groups.append(
                TokenGroup(
                    start=active_start,
                    end=token_index - 1,
                )
            )

            active_start = None

    if active_start is not None:
        groups.append(
            TokenGroup(
                start=active_start,
                end=len(labels) - 1,
            )
        )

    return groups


def token_has_alphanumeric_character(
    token: dict,
) -> bool:
    """Return whether a token contains a letter or digit."""
    return any(
        character.isalnum()
        for character in token["text"]
    )


def group_has_alphanumeric_content(
    tokens: list[dict],
    group: TokenGroup,
) -> bool:
    """Return whether an entity contains real content."""
    return any(
        token_has_alphanumeric_character(
            tokens[token_index]
        )
        for token_index in range(
            group.start,
            group.end + 1,
        )
    )


def remove_punctuation_only_groups(
    tokens: list[dict],
    groups: list[TokenGroup],
) -> list[TokenGroup]:
    """Remove predictions made entirely of punctuation."""
    return [
        group
        for group in groups
        if group_has_alphanumeric_content(
            tokens,
            group,
        )
    ]


def tokens_are_character_connected(
    prompt: str,
    left_token: dict,
    right_token: dict,
) -> bool:
    """Return whether no whitespace separates two tokens."""
    gap = prompt[
        left_token["end"]:
        right_token["start"]
    ]

    return gap == ""


def is_structural_connector(
    token: dict,
) -> bool:
    """Return whether a token joins structured values."""
    return (
        token["text"]
        in STRUCTURAL_CONNECTORS
    )


def group_contains_structured_sequence(
    tokens: list[dict],
    group: TokenGroup,
) -> bool:
    """Detect a predicted structured token sequence."""
    group_tokens = tokens[
        group.start:
        group.end + 1
    ]

    alphanumeric_token_count = sum(
        token_has_alphanumeric_character(token)
        for token in group_tokens
    )

    connector_count = sum(
        is_structural_connector(token)
        for token in group_tokens
    )

    return (
        alphanumeric_token_count >= 2
        and connector_count >= 1
    )


def find_connected_component_start(
    prompt: str,
    tokens: list[dict],
    start_index: int,
) -> int:
    """Find the start of a connected structured value."""
    component_start = start_index

    while component_start > 0:
        previous_token = tokens[
            component_start - 1
        ]

        current_token = tokens[
            component_start
        ]

        if not tokens_are_character_connected(
            prompt,
            previous_token,
            current_token,
        ):
            break

        if not (
            token_has_alphanumeric_character(
                previous_token
            )
            or is_structural_connector(
                previous_token
            )
        ):
            break

        component_start -= 1

    return component_start


def find_connected_component_end(
    prompt: str,
    tokens: list[dict],
    end_index: int,
) -> int:
    """Find the end of a connected structured value."""
    component_end = end_index

    while component_end + 1 < len(tokens):
        current_token = tokens[
            component_end
        ]

        next_token = tokens[
            component_end + 1
        ]

        if not tokens_are_character_connected(
            prompt,
            current_token,
            next_token,
        ):
            break

        if not (
            token_has_alphanumeric_character(
                next_token
            )
            or is_structural_connector(
                next_token
            )
        ):
            break

        component_end += 1

    return component_end


def trim_edge_connectors(
    tokens: list[dict],
    group: TokenGroup,
) -> TokenGroup | None:
    """Remove punctuation from entity boundaries."""
    start = group.start
    end = group.end

    while (
        start <= end
        and not token_has_alphanumeric_character(
            tokens[start]
        )
    ):
        start += 1

    while (
        end >= start
        and not token_has_alphanumeric_character(
            tokens[end]
        )
    ):
        end -= 1

    if start > end:
        return None

    return TokenGroup(
        start=start,
        end=end,
    )


def expand_structured_groups(
    prompt: str,
    tokens: list[dict],
    groups: list[TokenGroup],
) -> list[TokenGroup]:
    """Repair partial boundaries of connected values."""
    expanded_groups = []

    for group in groups:
        if not group_contains_structured_sequence(
            tokens,
            group,
        ):
            expanded_groups.append(group)
            continue

        expanded_group = TokenGroup(
            start=find_connected_component_start(
                prompt,
                tokens,
                group.start,
            ),
            end=find_connected_component_end(
                prompt,
                tokens,
                group.end,
            ),
        )

        trimmed_group = trim_edge_connectors(
            tokens,
            expanded_group,
        )

        if trimmed_group is not None:
            expanded_groups.append(
                trimmed_group
            )

    return expanded_groups


def is_digit_token(token: dict) -> bool:
    """Return whether the complete token is numeric."""
    return token["text"].isdigit()


def gap_is_numeric_separator(
    prompt: str,
    left_token: dict,
    right_token: dict,
) -> bool:
    """Return whether a small gap joins numeric groups."""
    gap = prompt[
        left_token["end"]:
        right_token["start"]
    ]

    return (
        0 < len(gap) <= 3
        and all(
            character in NUMERIC_SEPARATORS
            for character in gap
        )
    )


def get_numeric_indexes(
    tokens: list[dict],
    group: TokenGroup,
) -> list[int]:
    """Return numeric token indexes inside a group."""
    return [
        token_index
        for token_index in range(
            group.start,
            group.end + 1,
        )
        if is_digit_token(
            tokens[token_index]
        )
    ]


def expand_repeated_numeric_groups(
    prompt: str,
    tokens: list[dict],
    groups: list[TokenGroup],
) -> list[TokenGroup]:
    """Extend multi-part numeric values across separators."""
    expanded_groups = []

    for group in groups:
        numeric_indexes = get_numeric_indexes(
            tokens,
            group,
        )

        if len(numeric_indexes) < 2:
            expanded_groups.append(group)
            continue

        numeric_lengths = [
            len(tokens[index]["text"])
            for index in numeric_indexes
        ]

        most_common_length = max(
            set(numeric_lengths),
            key=numeric_lengths.count,
        )

        start = group.start
        end = group.end

        while start > 0:
            previous_token = tokens[start - 1]
            current_token = tokens[start]

            if not (
                is_digit_token(previous_token)
                and len(
                    previous_token["text"]
                )
                == most_common_length
                and gap_is_numeric_separator(
                    prompt,
                    previous_token,
                    current_token,
                )
            ):
                break

            start -= 1

        while end + 1 < len(tokens):
            current_token = tokens[end]
            next_token = tokens[end + 1]

            if not (
                is_digit_token(next_token)
                and len(next_token["text"])
                == most_common_length
                and gap_is_numeric_separator(
                    prompt,
                    current_token,
                    next_token,
                )
            ):
                break

            end += 1

        expanded_groups.append(
            TokenGroup(
                start=start,
                end=end,
            )
        )

    return expanded_groups


def merge_overlapping_groups(
    groups: list[TokenGroup],
) -> list[TokenGroup]:
    """Merge token groups that overlap after expansion."""
    if not groups:
        return []

    sorted_groups = sorted(
        groups,
        key=lambda group: (
            group.start,
            group.end,
        ),
    )

    merged_groups = [
        TokenGroup(
            start=sorted_groups[0].start,
            end=sorted_groups[0].end,
        )
    ]

    for group in sorted_groups[1:]:
        previous_group = merged_groups[-1]

        if group.start <= previous_group.end:
            previous_group.end = max(
                previous_group.end,
                group.end,
            )

        else:
            merged_groups.append(
                TokenGroup(
                    start=group.start,
                    end=group.end,
                )
            )

    return merged_groups


def groups_to_bio_labels(
    token_count: int,
    groups: list[TokenGroup],
) -> list[str]:
    """Convert repaired groups back to BIO labels."""
    labels = [
        "O"
        for _ in range(token_count)
    ]

    for group in groups:
        labels[group.start] = "B-SENSITIVE"

        for token_index in range(
            group.start + 1,
            group.end + 1,
        ):
            labels[token_index] = "I-SENSITIVE"

    return labels


def repair_bio_labels(
    prompt: str,
    tokens: list[dict],
    predicted_labels: list[str],
) -> list[str]:
    """Apply all general boundary-repair operations."""
    if len(tokens) != len(predicted_labels):
        raise ValueError(
            "Token and prediction counts must match."
        )

    normalized_labels = normalize_bio_labels(
        predicted_labels
    )

    groups = labels_to_groups(
        normalized_labels
    )

    groups = remove_punctuation_only_groups(
        tokens,
        groups,
    )

    groups = expand_structured_groups(
        prompt,
        tokens,
        groups,
    )

    groups = expand_repeated_numeric_groups(
        prompt,
        tokens,
        groups,
    )

    groups = merge_overlapping_groups(
        groups
    )

    return groups_to_bio_labels(
        len(tokens),
        groups,
    )


def reconstruct_spans(
    prompt: str,
    tokens: list[dict],
    labels: list[str],
) -> list[dict]:
    """Reconstruct character spans from BIO labels."""
    normalized_labels = normalize_bio_labels(
        labels
    )

    groups = labels_to_groups(
        normalized_labels
    )

    spans = []

    for group in groups:
        start = tokens[group.start]["start"]
        end = tokens[group.end]["end"]

        spans.append(
            {
                "start": start,
                "end": end,
                "text": prompt[start:end],
            }
        )

    return spans


def decode_sensitive_spans(
    prompt: str,
    tokens: list[dict],
    predicted_labels: list[str],
) -> dict:
    """Repair predictions and return exact spans."""
    repaired_labels = repair_bio_labels(
        prompt,
        tokens,
        predicted_labels,
    )

    spans = reconstruct_spans(
        prompt,
        tokens,
        repaired_labels,
    )

    return {
        "labels": repaired_labels,
        "spans": spans,
    }