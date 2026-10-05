from research.action_classifier.allow_families import (
    NEUTRAL_WRAPPERS,
)
from research.action_classifier.block_families import (
    BLOCK_FAMILIES,
)
from research.action_classifier.generation_utils import (
    calculate_distribution,
    create_record,
    generate_variants,
)


EXPECTED_SPLIT_DISTRIBUTION = {
    "train": 150,
    "validation": 25,
    "test": 25,
}


def generate_block_records():
    """Generate every Block catalog record."""
    records = []
    next_identifier = 601

    for family in BLOCK_FAMILIES:
        prompts = generate_variants(
            base_prompts=family["base_prompts"],
            wrappers=NEUTRAL_WRAPPERS,
            target_count=family["target_count"],
        )

        for prompt in prompts:
            record = create_record(
                record_number=next_identifier,
                prompt=prompt,
                action="block",
                rationale=family["rationale"],
                template_group=family["name"],
                split=family["split"],
            )

            records.append(record)
            next_identifier += 1

    return records


def test_block_catalog_has_expected_family_count():
    assert len(BLOCK_FAMILIES) == 25


def test_block_catalog_has_unique_family_names():
    family_names = [
        family["name"]
        for family in BLOCK_FAMILIES
    ]

    assert len(family_names) == len(
        set(family_names)
    )


def test_block_catalog_has_expected_distribution():
    records = generate_block_records()
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
            distribution[split]["actions"]["block"]
            == expected_count
        )

        assert (
            distribution[split]["actions"]["allow"]
            == 0
        )

        assert (
            distribution[split]["actions"]["review"]
            == 0
        )

        assert (
            distribution[split]["actions"]["redact"]
            == 0
        )


def test_block_catalog_generates_unique_prompts():
    records = generate_block_records()

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
    )


def test_block_records_have_no_sensitive_spans():
    records = generate_block_records()

    for record in records:
        assert record["action"] == "block"
        assert record["sensitive_spans"] == []


def test_block_template_groups_do_not_cross_splits():
    records = generate_block_records()
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

    assert crossing_groups == {}


def test_block_records_have_valid_schema_fields():
    records = generate_block_records()

    for record in records:
        assert record["id"].startswith("psac_")
        assert record["prompt"].strip()
        assert record["action"] == "block"
        assert record["rationale"].strip()
        assert record["template_group"].strip()
        assert record["source"] == "generated"

        assert record["split"] in {
            "train",
            "validation",
            "test",
        }


def test_block_catalog_contains_major_harm_families():
    family_names = {
        family["name"]
        for family in BLOCK_FAMILIES
    }

    expected_families = {
        "block_instruction_override",
        "block_system_prompt_extraction",
        "block_safety_bypass",
        "block_credential_theft",
        "block_unauthorized_account_access",
        "block_identity_document_fraud",
        "block_immigration_evasion",
        "block_private_data_exfiltration",
        "block_destructive_system_action",
        "block_exploit_for_intrusion",
    }

    assert expected_families.issubset(family_names)


def test_user_border_evasion_example_is_held_out():
    matching_families = [
        family
        for family in BLOCK_FAMILIES
        if family["name"] == (
            "block_test_border_evasion"
        )
    ]

    assert len(matching_families) == 1

    family = matching_families[0]

    assert family["split"] == "test"

    assert family["target_count"] == 5

    assert any(
        "UK without a passport" in prompt
        for prompt in family["base_prompts"]
    )


def test_block_family_fields_are_valid():
    for family in BLOCK_FAMILIES:
        assert family["name"].strip()
        assert family["rationale"].strip()
        assert family["target_count"] > 0

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
        )