"""Build the independent iteration-two entity dataset."""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


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


from research.entity_localizer import (
    build_entity_dataset,
)


OUTPUT_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "data_iteration2"
)

REPORT_PATH = (
    SCRIPT_DIRECTORY
    / "reports_iteration2"
    / "iteration2_dataset_report.json"
)

SPLIT_TARGETS = {
    "train": {
        "positive": 400,
        "negative": 400,
    },
    "validation": {
        "positive": 100,
        "negative": 100,
    },
    "challenge": {
        "positive": 100,
        "negative": 100,
    },
}

POSITIVE_TEMPLATES = {
    "train": [
        "Please update the protected record with {value}.",
        "The submitted form contains {value}.",
        "Store {value} in the restricted customer profile.",
        "The private support note includes {value}.",
        "The applicant supplied {value} during verification.",
        "Replace the old confidential value with {value}.",
        "The internal record currently lists {value}.",
        "Send the protected document using {value}.",
        "The onboarding form records {value}.",
        "The confidential case file contains {value}.",
    ],
    "validation": [
        "A private attachment exposes {value}.",
        "The restricted application shows {value}.",
        "Remove {value} before sharing this record.",
        "The confidential export contains {value}.",
        "An internal operator entered {value}.",
    ],
    "challenge": [
        "Before publication, conceal {value}.",
        "The protected evidence contains {value}.",
        "A customer pasted {value} into the conversation.",
        "The private workflow received {value}.",
        "Do not expose the recorded value {value}.",
    ],
}

MULTIPLE_TEMPLATES = {
    "train": [
        (
            "The private profile contains {value1} "
            "and {value2}."
        ),
        (
            "Remove both {value1} and {value2} "
            "before sharing the file."
        ),
        (
            "The restricted form lists {value1}; "
            "it also includes {value2}."
        ),
    ],
    "validation": [
        (
            "Two protected values appear here: "
            "{value1} and {value2}."
        ),
        (
            "The confidential export combines "
            "{value1} with {value2}."
        ),
    ],
    "challenge": [
        (
            "Sanitize the message containing "
            "{value1}, followed by {value2}."
        ),
        (
            "The evidence reveals {value1} as well "
            "as {value2}."
        ),
    ],
}

NEGATIVE_TEMPLATES = {
    "train": [
        "Explain {subject}.",
        "Write a short policy about {subject}.",
        "Why should organizations understand {subject}?",
        "Give defensive guidance concerning {subject}.",
        "Summarize the privacy risks of {subject}.",
        "Describe lawful handling of {subject}.",
        "Create employee training about {subject}.",
        "What safeguards apply to {subject}?",
        "Discuss secure storage of {subject}.",
        "How should developers document {subject}?",
        "Give a general overview of {subject}.",
        "Explain safe deletion of {subject}.",
        "Why is access control important for {subject}?",
        "Describe encryption practices for {subject}.",
        "How should an audit cover {subject}?",
        "Explain data minimization for {subject}.",
        "What retention rules apply to {subject}?",
        "Describe consent requirements for {subject}.",
        "How should incidents involving {subject} be reported?",
        "Explain responsible testing involving {subject}.",
    ],
    "validation": [
        "Provide an educational note about {subject}.",
        "What legal concerns surround {subject}?",
        "Outline safe processing of {subject}.",
        "How can teams avoid exposing {subject}?",
        "Describe privacy-by-design for {subject}.",
        "What is the purpose of protecting {subject}?",
        "Give compliance advice regarding {subject}.",
        "How should access to {subject} be reviewed?",
        "Explain secure transmission of {subject}.",
        "Discuss breach response involving {subject}.",
    ],
    "challenge": [
        "Without showing a real value, explain {subject}.",
        "Teach new developers how to protect {subject}.",
        "What mistakes commonly expose {subject}?",
        "Give a conceptual definition of {subject}.",
        "How can logs avoid recording {subject}?",
        "Explain anonymization of {subject}.",
        "What controls prevent misuse of {subject}?",
        "Describe secure validation of {subject}.",
        "How should a privacy notice mention {subject}?",
        "Explain why public examples should mask {subject}.",
    ],
}

NEGATIVE_SUBJECTS = [
    "email addresses",
    "telephone numbers",
    "payment card numbers",
    "bank account numbers",
    "passwords",
    "access tokens",
    "passport numbers",
    "dates of birth",
    "home addresses",
    "medical record identifiers",
    "national identity numbers",
    "API credentials",
    "recovery codes",
    "session identifiers",
    "database connection strings",
    "employee identifiers",
    "customer account references",
    "authentication headers",
    "private-key material",
    "webhook secrets",
    "driver licence numbers",
    "tax identification values",
    "international bank identifiers",
    "usernames",
    "backup codes",
    "identity-verification documents",
    "personal-data breach reports",
    "redacted placeholders",
    "masked test values",
    "documentation-only examples",
    "security configuration fields",
    "privacy classification labels",
    "data-retention schedules",
    "authorization concepts",
    "encryption-key rotation",
    "synthetic test accounts",
    "reserved example domains",
    "software version numbers",
    "non-personal order references",
    "public product identifiers",
]

MASKED_NEGATIVE_PROMPTS = {
    "train": [
        "The card field displays XXXX-XXXX-XXXX-XXXX.",
        "The secret is shown only as [REDACTED].",
        "The password field contains ********.",
        "The account value is replaced by PLACEHOLDER.",
        "The token example is TOKEN_GOES_HERE.",
        "The phone field displays +XX XXXXX XXXXX.",
        "The email field contains user@example.invalid.",
        "The passport example is AA0000000.",
        "The date field uses DD/MM/YYYY.",
        "The identifier pattern is ABC-DEF-GHI.",
    ],
    "validation": [
        "The document shows account number [MASKED].",
        "The example credential is NOT_A_REAL_SECRET.",
        "The sample email uses person@example.invalid.",
        "The card number is hidden as **** **** **** ****.",
        "The backup code is represented by XXXX-XXXX.",
    ],
    "challenge": [
        "Only the placeholder YOUR_API_KEY appears here.",
        "The form preview shows phone number [REMOVED].",
        "The guide uses test@example.invalid as reserved text.",
        "The identifier is masked as ID-XXXXXX.",
        "The connection string has password=[HIDDEN].",
    ],
}


def stable_fragment(
    prefix: str,
    index: int,
    length: int = 20,
) -> str:
    """Create a deterministic fictional fragment."""
    source = (
        f"{prefix}:{index}:promptshield-iteration-two"
    )

    return hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()[:length]


def build_email(index: int) -> tuple[str, str]:
    value = (
        f"person{index}.case"
        f"+secure{index % 17}"
        "@mail.example"
    )

    return value, "email_address"


def build_phone(index: int) -> tuple[str, str]:
    value = (
        f"+91 8{index % 10000:04d} "
        f"{(index * 37) % 100000:05d}"
    )

    return value, "phone_number"


def build_card(index: int) -> tuple[str, str]:
    value = (
        f"4000-{index % 10000:04d}-"
        f"{(index * 7) % 10000:04d}-"
        f"{(index * 13) % 10000:04d}"
    )

    return value, "payment_card_number"


def build_bank_account(
    index: int,
) -> tuple[str, str]:
    value = (
        f"{700000000000 + index * 19:012d}"
    )

    return value, "bank_account_number"


def build_password(index: int) -> tuple[str, str]:
    value = (
        f"Nova!River{index:04d}#Q"
    )

    return value, "password"


def build_access_token(
    index: int,
) -> tuple[str, str]:
    value = (
        "tok_live_"
        + stable_fragment(
            "access-token",
            index,
            24,
        )
    )

    return value, "access_token"


def build_passport(index: int) -> tuple[str, str]:
    value = (
        f"K{(index * 97) % 10000000:07d}"
    )

    return value, "passport_number"


def build_birth_date(
    index: int,
) -> tuple[str, str]:
    months = [
        "January",
        "March",
        "May",
        "July",
        "September",
        "November",
    ]

    day = (
        index % 27
    ) + 1

    month = months[
        index % len(months)
    ]

    year = (
        1980
        + index % 25
    )

    value = (
        f"{day} {month} {year}"
    )

    return value, "date_of_birth"


def build_address(index: int) -> tuple[str, str]:
    streets = [
        "Lake Road",
        "Garden Avenue",
        "Temple Street",
        "River View",
        "Market Lane",
        "Station Road",
    ]

    cities = [
        "Mysuru",
        "Bengaluru",
        "Chennai",
        "Hyderabad",
        "Pune",
        "Kochi",
    ]

    number = (
        index % 180
    ) + 1

    street = streets[
        index % len(streets)
    ]

    city = cities[
        (index * 3) % len(cities)
    ]

    pin_code = (
        560000
        + index % 10000
    )

    value = (
        f"{number} {street}, "
        f"{city} {pin_code:06d}"
    )

    return value, "postal_address"


def build_service_secret(
    index: int,
) -> tuple[str, str]:
    value = (
        "svc_test_"
        + stable_fragment(
            "service-secret",
            index,
            22,
        )
    )

    return value, "service_secret"


def build_recovery_code(
    index: int,
) -> tuple[str, str]:
    fragment = stable_fragment(
        "recovery-code",
        index,
        12,
    ).upper()

    value = (
        f"{fragment[:4]}-"
        f"{fragment[4:8]}-"
        f"{fragment[8:12]}"
    )

    return value, "recovery_code"


def build_medical_id(
    index: int,
) -> tuple[str, str]:
    value = (
        f"MED-{(index * 41) % 1000000:06d}-RX"
    )

    return value, "medical_record_identifier"


VALUE_BUILDERS = [
    build_email,
    build_phone,
    build_card,
    build_bank_account,
    build_password,
    build_access_token,
    build_passport,
    build_birth_date,
    build_address,
    build_service_secret,
    build_recovery_code,
    build_medical_id,
]


def create_spans(
    prompt: str,
    sensitive_values: list[tuple[str, str]],
    record_id: str,
) -> list[dict]:
    """Create exact, non-overlapping character spans."""
    spans = []
    occupied_ranges = []

    for value, entity_type in sensitive_values:
        occurrence_count = prompt.count(
            value
        )

        if occurrence_count != 1:
            raise RuntimeError(
                f"{record_id}: value {value!r} "
                "must appear exactly once."
            )

        start = prompt.index(value)
        end = start + len(value)

        if any(
            start < existing_end
            and end > existing_start
            for (
                existing_start,
                existing_end,
            )
            in occupied_ranges
        ):
            raise RuntimeError(
                f"{record_id}: overlapping spans."
            )

        spans.append(
            {
                "start": start,
                "end": end,
                "text": value,
                "type": entity_type,
            }
        )

        occupied_ranges.append(
            (
                start,
                end,
            )
        )

    return sorted(
        spans,
        key=lambda span: (
            span["start"],
            span["end"],
        ),
    )


def build_positive_record(
    split: str,
    position: int,
) -> dict:
    """Build one positive entity record."""
    first_builder_index = (
        position
        % len(VALUE_BUILDERS)
    )

    first_builder = VALUE_BUILDERS[
        first_builder_index
    ]

    first_value = first_builder(
        position
        + {
            "train": 1000,
            "validation": 5000,
            "challenge": 9000,
        }[split]
    )

    record_id = (
        f"psei2_{split}_{position:06d}"
    )

    create_multiple = (
        position % 7 == 0
    )

    if create_multiple:
        second_builder = VALUE_BUILDERS[
            (
                first_builder_index
                + 5
            )
            % len(VALUE_BUILDERS)
        ]

        second_value = second_builder(
            position
            + {
                "train": 20000,
                "validation": 30000,
                "challenge": 40000,
            }[split]
        )

        template = MULTIPLE_TEMPLATES[
            split
        ][
            position
            % len(
                MULTIPLE_TEMPLATES[split]
            )
        ]

        prompt = template.format(
            value1=first_value[0],
            value2=second_value[0],
        )

        sensitive_values = [
            first_value,
            second_value,
        ]

        template_group = (
            f"{split}_multiple_"
            f"{first_builder_index}"
        )

    else:
        template = POSITIVE_TEMPLATES[
            split
        ][
            position
            % len(
                POSITIVE_TEMPLATES[split]
            )
        ]

        prompt = template.format(
            value=first_value[0]
        )

        sensitive_values = [
            first_value
        ]

        template_group = (
            f"{split}_positive_"
            f"{first_builder_index}"
        )

    spans = create_spans(
        prompt,
        sensitive_values,
        record_id,
    )

    source_record = {
        "id": record_id,
        "prompt": prompt,
        "action": "redact",
        "rationale": (
            "The prompt contains fictional "
            "sensitive values."
        ),
        "sensitive_spans": spans,
        "source": "generated_iteration2",
        "split": split,
        "template_group": template_group,
    }

    return (
        build_entity_dataset
        .build_entity_record(
            source_record,
            split,
            position + 1,
        )
    )


def build_negative_record(
    split: str,
    position: int,
) -> dict:
    """Build one difficult safe negative record."""
    record_id = (
        f"psei2_{split}_safe_{position:06d}"
    )

    masked_examples = (
        MASKED_NEGATIVE_PROMPTS[split]
    )

    if position % 5 == 0:
        masked_index = (
            position // 5
        ) % len(masked_examples)

        prompt = masked_examples[
            masked_index
        ]

        prompt = (
            f"{prompt} "
            f"Documentation case "
            f"{split}-{position:04d}."
        )

        template_group = (
            f"{split}_masked_negative"
        )

    else:
        subject_offset = {
            "train": 0,
            "validation": 20,
            "challenge": 30,
        }[split]

        available_subject_count = {
            "train": 20,
            "validation": 10,
            "challenge": 10,
        }[split]

        subject = NEGATIVE_SUBJECTS[
            subject_offset
            + (
                position
                % available_subject_count
            )
        ]

        templates = NEGATIVE_TEMPLATES[
            split
        ]

        template = templates[
            (
                position
                // available_subject_count
            )
            % len(templates)
        ]

        prompt = template.format(
            subject=subject
        )

        prompt = (
            f"{prompt} "
            f"Policy example "
            f"{split}-{position:04d}."
        )

        template_group = (
            f"{split}_concept_negative"
        )

    source_record = {
        "id": record_id,
        "prompt": prompt,
        "action": "allow",
        "rationale": (
            "The prompt contains no actual "
            "sensitive value."
        ),
        "sensitive_spans": [],
        "source": "generated_iteration2",
        "split": split,
        "template_group": template_group,
    }

    return (
        build_entity_dataset
        .build_entity_record(
            source_record,
            split,
            position + 1,
        )
    )


def build_split(split: str) -> list[dict]:
    """Build one balanced iteration-two split."""
    target = SPLIT_TARGETS[split]

    records = []

    for position in range(
        target["positive"]
    ):
        records.append(
            build_positive_record(
                split,
                position,
            )
        )

    for position in range(
        target["negative"]
    ):
        records.append(
            build_negative_record(
                split,
                position,
            )
        )

    return records


def validate_unique_records(
    split_records: dict[str, list[dict]],
) -> None:
    """Validate IDs and prompts across all splits."""
    seen_ids = set()
    seen_prompts = set()

    for split, records in (
        split_records.items()
    ):
        for record in records:
            record_id = record["id"]

            normalized_prompt = (
                record["prompt"]
                .strip()
                .casefold()
            )

            if record_id in seen_ids:
                raise RuntimeError(
                    f"Duplicate ID: {record_id}"
                )

            if normalized_prompt in seen_prompts:
                raise RuntimeError(
                    "Duplicate prompt across "
                    f"iteration-two splits: {record_id}"
                )

            if (
                record["source_split"]
                != split
            ):
                raise RuntimeError(
                    f"{record_id}: split mismatch."
                )

            seen_ids.add(record_id)
            seen_prompts.add(
                normalized_prompt
            )


def calculate_split_report(
    records: list[dict],
) -> dict:
    """Calculate dataset statistics."""
    positive_records = [
        record
        for record in records
        if record["has_sensitive_entity"]
    ]

    negative_records = [
        record
        for record in records
        if not record["has_sensitive_entity"]
    ]

    label_counts = Counter(
        token["label"]
        for record in records
        for token in record["tokens"]
    )

    span_types = Counter(
        span["type"]
        for record in records
        for span in record["gold_spans"]
    )

    return {
        "record_count": len(records),
        "positive_record_count": len(
            positive_records
        ),
        "negative_record_count": len(
            negative_records
        ),
        "sensitive_span_count": sum(
            len(record["gold_spans"])
            for record in records
        ),
        "token_count": sum(
            len(record["tokens"])
            for record in records
        ),
        "token_label_counts": {
            label: label_counts.get(
                label,
                0,
            )
            for label in [
                "B-SENSITIVE",
                "I-SENSITIVE",
                "O",
            ]
        },
        "sensitive_span_types": dict(
            sorted(span_types.items())
        ),
    }


def main() -> None:
    """Build the iteration-two development data."""
    print(
        "Building iteration-two entity datasets..."
    )

    print(
        "The historical final holdout is not read "
        "or used."
    )

    split_records = {
        split: build_split(split)
        for split in SPLIT_TARGETS
    }

    validate_unique_records(
        split_records
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    split_reports = {}

    for split, records in (
        split_records.items()
    ):
        output_path = (
            OUTPUT_DIRECTORY
            / f"{split}.jsonl"
        )

        build_entity_dataset.write_jsonl(
            output_path,
            records,
        )

        split_report = (
            calculate_split_report(
                records
            )
        )

        split_reports[split] = (
            split_report
        )

        print(f"\n{split}")
        print(
            "  Records: "
            f"{split_report['record_count']}"
        )
        print(
            "  Positive: "
            f"{split_report[
                'positive_record_count'
            ]}"
        )
        print(
            "  Negative: "
            f"{split_report[
                'negative_record_count'
            ]}"
        )
        print(
            "  Sensitive spans: "
            f"{split_report[
                'sensitive_span_count'
            ]}"
        )
        print(
            f"  Saved to: {output_path}"
        )

    report = {
        "dataset": (
            "contextual_sensitive_entity_"
            "iteration2_development_v1"
        ),
        "historical_final_holdout_used": False,
        "group_isolated_splits": True,
        "split_targets": SPLIT_TARGETS,
        "splits": split_reports,
        "combined_record_count": sum(
            report["record_count"]
            for report in split_reports.values()
        ),
        "valid": True,
        "validation_errors": [],
    }

    with REPORT_PATH.open(
        "w",
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
        "\nIteration-two dataset build completed."
    )

    print(
        "Total records: "
        f"{report['combined_record_count']}"
    )

    print(
        "Historical final holdout used: False"
    )

    print(
        f"Report saved to: {REPORT_PATH}"
    )


if __name__ == "__main__":
    main()