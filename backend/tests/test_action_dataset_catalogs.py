import pytest

from research.action_classifier.allow_families import (
    ALLOW_FAMILIES,
    NEUTRAL_WRAPPERS,
)
from research.action_classifier.generation_utils import (
    calculate_distribution,
    create_record,
    generate_variants,
)
from research.action_classifier.review_families import (
    REVIEW_FAMILIES,
)


EXPECTED_SPLIT_DISTRIBUTION = {
    "train": 150,
    "validation": 25,
    "test": 25,
}

CATALOGS = [
    (
        "allow",
        ALLOW_FAMILIES,
    ),
    (
        "review",
        REVIEW_FAMILIES,
    ),
]


def generate_catalog_records(
    action,
    families,
    starting_identifier=1,
):
    """Generate schema-compatible records for a catalog."""
    records = []
    next_identifier = starting_identifier

    for family in families:
        prompts = generate_variants(
            base_prompts=family["base_prompts"],
            wrappers=NEUTRAL_WRAPPERS,
            target_count=family["target_count"],
        )

        for prompt in prompts:
            record = create_record(
                record_number=next_identifier,
                prompt=prompt,
                action=action,
                rationale=family["rationale"],
                template_group=family["name"],
                split=family["split"],
            )

            records.append(record)
            next_identifier += 1

    return records


@pytest.mark.parametrize(
    ("action", "families"),
    CATALOGS,
)
def test_catalog_contains_expected_number_of_families(
    action,
    families,
):
    assert action in {
        "allow",
        "review",
    }

    assert len(families) == 25


@pytest.mark.parametrize(
    ("action", "families"),
    CATALOGS,
)
def test_catalog_family_names_are_unique(
    action,
    families,
):
    family_names = [
        family["name"]
        for family in families
    ]

    assert len(family_names) == len(
        set(family_names)
    ), (
        f"The {action} catalog contains duplicate "
        "family names."
    )


def test_family_names_are_unique_across_catalogs():
    all_family_names = [
        family["name"]
        for _, families in CATALOGS
        for family in families
    ]

    assert len(all_family_names) == len(
        set(all_family_names)
    )


@pytest.mark.parametrize(
    ("action", "families"),
    CATALOGS,
)
def test_catalog_has_expected_split_distribution(
    action,
    families,
):
    records = generate_catalog_records(
        action,
        families,
    )

    distribution = calculate_distribution(records)

    total_records = sum(
        split_data["total"]
        for split_data in distribution.values()
    )

    assert total_records == 200

    for split, expected_count in (
        EXPECTED_SPLIT_DISTRIBUTION.items()
    ):
        assert (
            distribution[split]["total"]
            == expected_count
        )

        assert (
            distribution[split]["actions"][action]
            == expected_count
        )

        for other_action in {
            "allow",
            "review",
            "redact",
            "block",
        } - {action}:
            assert (
                distribution[split]["actions"][
                    other_action
                ]
                == 0
            )


@pytest.mark.parametrize(
    ("action", "families"),
    CATALOGS,
)
def test_catalog_generates_unique_prompts(
    action,
    families,
):
    records = generate_catalog_records(
        action,
        families,
    )

    normalized_prompts = [
        " ".join(
            record["prompt"]
            .lower()
            .split()
        )
        for record in records
    ]

    assert len(normalized_prompts) == 200

    assert len(normalized_prompts) == len(
        set(normalized_prompts)
    ), (
        f"The {action} catalog generated duplicate "
        "prompts."
    )


def test_prompts_are_unique_across_all_catalogs():
    allow_records = generate_catalog_records(
        "allow",
        ALLOW_FAMILIES,
        starting_identifier=1,
    )

    review_records = generate_catalog_records(
        "review",
        REVIEW_FAMILIES,
        starting_identifier=201,
    )

    all_records = (
        allow_records
        + review_records
    )

    normalized_prompts = [
        " ".join(
            record["prompt"]
            .lower()
            .split()
        )
        for record in all_records
    ]

    assert len(all_records) == 400

    assert len(normalized_prompts) == len(
        set(normalized_prompts)
    )


@pytest.mark.parametrize(
    ("action", "families"),
    CATALOGS,
)
def test_generated_records_have_required_fields(
    action,
    families,
):
    records = generate_catalog_records(
        action,
        families,
    )

    for record in records:
        assert record["id"].startswith("psac_")
        assert record["prompt"].strip()
        assert record["action"] == action
        assert record["rationale"].strip()
        assert record["template_group"].strip()

        assert record["source"] == "generated"

        assert record["split"] in {
            "train",
            "validation",
            "test",
        }

        assert record["sensitive_spans"] == []


@pytest.mark.parametrize(
    ("action", "families"),
    CATALOGS,
)
def test_template_groups_do_not_cross_splits(
    action,
    families,
):
    records = generate_catalog_records(
        action,
        families,
    )

    template_group_splits = {}

    for record in records:
        template_group = record["template_group"]
        split = record["split"]

        template_group_splits.setdefault(
            template_group,
            set(),
        ).add(split)

    crossing_groups = {
        template_group: splits
        for template_group, splits
        in template_group_splits.items()
        if len(splits) > 1
    }

    assert crossing_groups == {}, (
        f"The {action} catalog contains template "
        f"groups shared across splits: "
        f"{crossing_groups}"
    )


@pytest.mark.parametrize(
    ("action", "families"),
    CATALOGS,
)
def test_catalog_family_targets_are_positive(
    action,
    families,
):
    for family in families:
        assert family["target_count"] > 0, (
            f"{action} family "
            f"{family['name']} has an invalid target."
        )


@pytest.mark.parametrize(
    ("action", "families"),
    CATALOGS,
)
def test_catalog_families_have_required_fields(
    action,
    families,
):
    for family in families:
        assert family["name"].strip()
        assert family["rationale"].strip()

        assert family["split"] in {
            "train",
            "validation",
            "test",
        }

        assert isinstance(
            family["base_prompts"],
            list,
        )

        assert family["base_prompts"]

        assert all(
            prompt.strip()
            for prompt in family["base_prompts"]
        ), (
            f"{action} family "
            f"{family['name']} contains an empty prompt."
        )


def test_review_catalog_contains_genuine_ambiguity():
    review_records = generate_catalog_records(
        "review",
        REVIEW_FAMILIES,
    )

    assert len(review_records) == 200

    assert all(
        record["action"] == "review"
        for record in review_records
    )

    assert all(
        record["sensitive_spans"] == []
        for record in review_records
    )

    ambiguity_terms = {
        "ambiguous",
        "unclear",
        "context",
        "authorization",
        "ownership",
        "intent",
    }

    assert any(
        any(
            term in record["rationale"].lower()
            for term in ambiguity_terms
        )
        for record in review_records
    )