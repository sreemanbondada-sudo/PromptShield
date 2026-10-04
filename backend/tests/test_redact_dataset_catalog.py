from research.action_classifier.allow_families import (
    NEUTRAL_WRAPPERS,
)
from research.action_classifier.generation_utils import (
    calculate_distribution,
    create_record,
    generate_variants,
)
from research.action_classifier.redact_families import (
    REDACT_FAMILIES,
)


EXPECTED_SPLIT_DISTRIBUTION = {
    "train": 150,
    "validation": 25,
    "test": 25,
}


def generate_redact_records():
    """Generate every Redact catalog record."""
    records = []
    next_identifier = 401

    for family in REDACT_FAMILIES:
        prompts = generate_variants(
            base_prompts=family["base_prompts"],
            wrappers=NEUTRAL_WRAPPERS,
            target_count=family["target_count"],
        )

        for prompt in prompts:
            record = create_record(
                record_number=next_identifier,
                prompt=prompt,
                action="redact",
                rationale=family["rationale"],
                template_group=family["name"],
                split=family["split"],
                sensitive_values=(
                    family["sensitive_values"]
                ),
            )

            records.append(record)
            next_identifier += 1

    return records


def test_redact_catalog_has_expected_family_count():
    assert len(REDACT_FAMILIES) == 25


def test_redact_catalog_has_unique_family_names():
    family_names = [
        family["name"]
        for family in REDACT_FAMILIES
    ]

    assert len(family_names) == len(
        set(family_names)
    )


def test_redact_catalog_has_expected_distribution():
    records = generate_redact_records()
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
            distribution[split]["actions"]["redact"]
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
            distribution[split]["actions"]["block"]
            == 0
        )


def test_redact_catalog_generates_unique_prompts():
    records = generate_redact_records()

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


def test_every_redact_record_has_sensitive_spans():
    records = generate_redact_records()

    for record in records:
        assert record["action"] == "redact"
        assert record["sensitive_spans"]


def test_sensitive_span_offsets_match_prompt_text():
    records = generate_redact_records()

    for record in records:
        prompt = record["prompt"]

        for span in record["sensitive_spans"]:
            assert span["start"] >= 0
            assert span["end"] > span["start"]
            assert span["end"] <= len(prompt)

            extracted_text = prompt[
                span["start"]:span["end"]
            ]

            assert extracted_text == span["text"]
            assert span["type"].strip()


def test_family_sensitive_values_exist_in_prompts():
    for family in REDACT_FAMILIES:
        for base_prompt in family["base_prompts"]:
            for value, value_type in (
                family["sensitive_values"]
            ):
                assert value in base_prompt, (
                    f"Sensitive value {value!r} from "
                    f"{family['name']} is missing from "
                    "one of its base prompts."
                )

                assert value_type.strip()


def test_redact_catalog_contains_multiple_entity_types():
    entity_types = {
        value_type
        for family in REDACT_FAMILIES
        for _, value_type in family[
            "sensitive_values"
        ]
    }

    assert len(entity_types) >= 10

    assert {
        "email_address",
        "phone_number",
        "password",
        "passport_number",
        "bearer_token",
    }.issubset(entity_types)


def test_redact_template_groups_do_not_cross_splits():
    records = generate_redact_records()
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


def test_redact_records_have_valid_schema_fields():
    records = generate_redact_records()

    for record in records:
        assert record["id"].startswith("psac_")
        assert record["prompt"].strip()
        assert record["action"] == "redact"
        assert record["rationale"].strip()
        assert record["template_group"].strip()
        assert record["source"] == "generated"

        assert record["split"] in {
            "train",
            "validation",
            "test",
        }