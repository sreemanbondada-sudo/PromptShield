"""Build iteration-three contextual entity development datasets."""

import hashlib
import json
import re
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent

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


BACKEND_DIRECTORY = (
    SCRIPT_DIRECTORY.parents[1]
)

if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIRECTORY),
    )


DATA_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "data_iteration3"
)

REPORT_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "reports_iteration3"
)

REPORT_PATH = (
    REPORT_DIRECTORY
    / "iteration3_dataset_report.json"
)

OUTPUT_PATHS = {
    "train": (
        DATA_DIRECTORY
        / "train.jsonl"
    ),
    "validation": (
        DATA_DIRECTORY
        / "validation.jsonl"
    ),
    "challenge": (
        DATA_DIRECTORY
        / "challenge.jsonl"
    ),
}

SPLIT_TARGETS = {
    "train": {
        "positive": 600,
        "negative": 600,
    },
    "validation": {
        "positive": 150,
        "negative": 150,
    },
    "challenge": {
        "positive": 150,
        "negative": 150,
    },
}

SPLIT_OFFSETS = {
    "train": 10000,
    "validation": 30000,
    "challenge": 50000,
}

DEVELOPMENT_REFERENCE_PATHS = [
    SCRIPT_DIRECTORY
    / "data"
    / "train.jsonl",
    SCRIPT_DIRECTORY
    / "data"
    / "validation.jsonl",
    SCRIPT_DIRECTORY
    / "data"
    / "test.jsonl",
    SCRIPT_DIRECTORY
    / "data"
    / "challenge.jsonl",
    SCRIPT_DIRECTORY
    / "data_iteration2"
    / "train.jsonl",
    SCRIPT_DIRECTORY
    / "data_iteration2"
    / "validation.jsonl",
    SCRIPT_DIRECTORY
    / "data_iteration2"
    / "challenge.jsonl",
]

FORBIDDEN_HOLDOUT_PATHS = {
    (
        SCRIPT_DIRECTORY
        / "data"
        / "final_holdout.jsonl"
    ).resolve(),
    (
        SCRIPT_DIRECTORY
        / "data_iteration2_final"
        / "final_holdout.jsonl"
    ).resolve(),
}

SOURCE_NAME = "generated_iteration3"

POSITIVE_TEMPLATES = {
    "train": [
        (
            "Remove {first_value} before the "
            "internal note is redistributed."
        ),
        (
            "The protected workflow received "
            "{first_value}; conceal it."
        ),
        (
            "A private form contains "
            "{first_value}, which must be masked."
        ),
        (
            "Hide {first_value} in the sanitized "
            "copy of this record."
        ),
        (
            "The restricted message exposes "
            "{first_value}; redact the value."
        ),
        (
            "Before sharing the document, replace "
            "{first_value} with a placeholder."
        ),
    ],
    "validation": [
        (
            "The confidential case file includes "
            "{first_value}; protect it."
        ),
        (
            "Sanitize {first_value} from the "
            "reviewer's exported copy."
        ),
        (
            "A restricted attachment shows "
            "{first_value}, so mask it."
        ),
        (
            "Do not reveal {first_value} in the "
            "external response."
        ),
        (
            "The private intake message contains "
            "{first_value}; redact it."
        ),
        (
            "Remove the exposed value "
            "{first_value} before publication."
        ),
    ],
    "challenge": [
        (
            "The sealed evidence mentions "
            "{first_value}; conceal that value."
        ),
        (
            "Before release, sanitize "
            "{first_value} from the transcript."
        ),
        (
            "The protected submission contains "
            "{first_value}, which cannot be shared."
        ),
        (
            "Mask {first_value} in the version "
            "prepared for outside readers."
        ),
        (
            "A confidential export reveals "
            "{first_value}; remove it."
        ),
        (
            "Replace {first_value} before this "
            "record leaves the secure system."
        ),
    ],
}

MULTIPLE_TEMPLATES = {
    "train": [
        (
            "The record contains {first_value} and "
            "{second_value}; redact both values."
        ),
        (
            "Protect {first_value}, together with "
            "{second_value}, before sharing."
        ),
        (
            "The private export exposes "
            "{first_value} followed by "
            "{second_value}."
        ),
    ],
    "validation": [
        (
            "The review copy contains "
            "{first_value} and {second_value}; "
            "conceal both."
        ),
        (
            "Remove {first_value} as well as "
            "{second_value} from the attachment."
        ),
        (
            "The confidential submission combines "
            "{first_value} with {second_value}."
        ),
    ],
    "challenge": [
        (
            "Before publication, hide "
            "{first_value} and {second_value}."
        ),
        (
            "The protected evidence exposes "
            "{first_value}, then "
            "{second_value}."
        ),
        (
            "Sanitize both {first_value} and "
            "{second_value} from the message."
        ),
    ],
}

NEGATIVE_SUBJECTS = [
    "email-address privacy",
    "phone-number verification",
    "payment-card security",
    "bank-account protection",
    "strong-password policies",
    "access-token storage",
    "passport renewal",
    "birth-date collection",
    "residential-address privacy",
    "medical-record identifiers",
    "recovery-code handling",
    "service-secret rotation",
    "customer identity checks",
    "personal-data minimization",
    "confidential-field design",
    "redaction testing",
    "privacy incident response",
    "secure form design",
    "authentication guidance",
    "credential-management policy",
    "financial-data governance",
    "health-data access control",
    "travel-document security",
    "masked test fixtures",
    "placeholder-value documentation",
    "privacy impact assessments",
    "data-retention policies",
    "breach-notification procedures",
    "secure logging practices",
    "sensitive-field classification",
]

NEGATIVE_TEMPLATES = {
    "train": [
        "Explain the purpose of {subject}.",
        "Write general guidance about {subject}.",
        "Describe safe practices for {subject}.",
        "Why is {subject} important?",
        "Summarize a policy covering {subject}.",
    ],
    "validation": [
        "Provide an overview of {subject}.",
        "How should teams reason about {subject}?",
        "Draft a checklist for {subject}.",
        "Explain common controls for {subject}.",
        "Describe lawful use of {subject}.",
    ],
    "challenge": [
        "What risks are associated with {subject}?",
        "Teach new staff about {subject}.",
        "Give defensive advice concerning {subject}.",
        "Explain how auditors review {subject}.",
        "Describe responsible handling of {subject}.",
    ],
}

MASKED_NEGATIVES = [
    "The email field says [email removed].",
    "The phone field contains [number withheld].",
    "The card field displays XXXX XXXX XXXX XXXX.",
    "The account value is [account unavailable].",
    "The password field shows <password omitted>.",
    "The token entry is [token removed].",
    "The passport field is intentionally blank.",
    "The birth-date field contains DD Month YYYY.",
    "The address says [location removed].",
    "The patient ID is replaced with [masked ID].",
    "The recovery code is shown as XXXX-XXXX.",
    "The service secret field is [not provided].",
]


def stable_fragment(
    prefix: str,
    index: int,
    length: int,
) -> str:
    """Create a deterministic hexadecimal value."""
    source = (
        f"{prefix}:iteration-three:{index}"
    )

    return hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()[:length]


def normalize_prompt(prompt: str) -> str:
    """Normalize prompts for overlap checking."""
    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        prompt.casefold(),
    )

    return " ".join(
        normalized.split()
    )


def load_jsonl(path: Path) -> list[dict]:
    """Load one JSON Lines file."""
    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        for line_number, line in enumerate(
            input_file,
            start=1,
        ):
            stripped_line = line.strip()

            if not stripped_line:
                continue

            try:
                records.append(
                    json.loads(stripped_line)
                )

            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Invalid JSON in {path} "
                    f"at line {line_number}."
                ) from error

    return records


def build_email(
    index: int,
) -> tuple[str, str]:
    """Build an email value."""
    value = (
        f"secure.person{index}"
        f"+vault{index % 97}"
        "@protected.example"
    )

    return value, "email_address"


def build_phone(
    index: int,
) -> tuple[str, str]:
    """Build varied international phone formats."""
    local_first = (
        70000
        + index % 20000
    )

    local_second = (
        10000
        + (
            index * 37
        )
        % 80000
    )

    variant = index % 6

    if variant == 0:
        value = (
            f"+91 {local_first:05d} "
            f"{local_second:05d}"
        )

    elif variant == 1:
        value = (
            f"+91-{local_first:05d}-"
            f"{local_second:05d}"
        )

    elif variant == 2:
        value = (
            f"(+91) {local_first:05d} "
            f"{local_second:05d}"
        )

    elif variant == 3:
        value = (
            f"{local_first:05d}"
            f"{local_second:05d}"
        )

    elif variant == 4:
        value = (
            f"+44 7700 "
            f"{900000 + index % 99999:06d}"
        )

    else:
        value = (
            f"+1 (415) 555-"
            f"{1000 + index % 8000:04d}"
        )

    return value, "phone_number"


def build_card(
    index: int,
) -> tuple[str, str]:
    """Build a fictional payment-card value."""
    value = (
        f"4532 "
        f"{2000 + index % 7000:04d} "
        f"{3000 + index % 6000:04d} "
        f"{4000 + index % 5000:04d}"
    )

    return value, "payment_card_number"


def build_bank_account(
    index: int,
) -> tuple[str, str]:
    """Build a fictional account value."""
    fragment = stable_fragment(
        "bank-account",
        index,
        16,
    ).upper()

    return (
        f"ACCT-{fragment}",
        "bank_account_number",
    )


def build_password(
    index: int,
) -> tuple[str, str]:
    """Build a fictional password."""
    fragment = stable_fragment(
        "password",
        index,
        12,
    )

    return (
        f"Vm!Secure{fragment}7#",
        "password",
    )


def build_access_token(
    index: int,
) -> tuple[str, str]:
    """Build a fictional access token."""
    fragment = stable_fragment(
        "access-token",
        index,
        32,
    )

    return (
        f"ctx3_live_{fragment}",
        "access_token",
    )


def build_passport(
    index: int,
) -> tuple[str, str]:
    """Build a fictional passport number."""
    return (
        f"QX{6100000 + index % 3000000:07d}",
        "passport_number",
    )


def build_birth_date(
    index: int,
) -> tuple[str, str]:
    """Build a birth-date value."""
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    day = 1 + index % 28
    month = months[index % 12]
    year = 1950 + index % 55

    return (
        f"{day} {month} {year}",
        "date_of_birth",
    )


def build_address(
    index: int,
) -> tuple[str, str]:
    """Build a fictional address."""
    value = (
        f"Flat {10 + index % 900}, "
        f"Cedar Privacy Avenue, "
        f"Zone {1 + index % 80}"
    )

    return value, "residential_address"


def build_service_secret(
    index: int,
) -> tuple[str, str]:
    """Build a fictional service secret."""
    fragment = stable_fragment(
        "service-secret",
        index,
        28,
    )

    return (
        f"svc3_secret_{fragment}",
        "service_secret",
    )


def build_recovery_code(
    index: int,
) -> tuple[str, str]:
    """Build a fictional recovery code."""
    first = stable_fragment(
        "recovery-first",
        index,
        8,
    ).upper()

    second = stable_fragment(
        "recovery-second",
        index,
        8,
    ).upper()

    return (
        f"{first}-{second}",
        "recovery_code",
    )


def build_medical_id(
    index: int,
) -> tuple[str, str]:
    """Build a fictional medical identifier."""
    fragment = stable_fragment(
        "medical-id",
        index,
        12,
    ).upper()

    return (
        f"MED3-{fragment}",
        "medical_identifier",
    )


VALUE_BUILDERS = [
    build_email,
    build_phone,
    build_phone,
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
    build_phone,
]


def create_spans(
    prompt: str,
    values: list[tuple[str, str]],
    record_id: str,
) -> list[dict]:
    """Create exact non-overlapping spans."""
    spans = []
    occupied_ranges = []

    for value, entity_type in values:
        if prompt.count(value) != 1:
            raise RuntimeError(
                f"{record_id}: value {value!r} "
                "must appear exactly once."
            )

        start = prompt.index(value)
        end = start + len(value)

        overlaps = any(
            start < existing_end
            and end > existing_start
            for (
                existing_start,
                existing_end,
            )
            in occupied_ranges
        )

        if overlaps:
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
    """Build one positive development record."""
    value_index = (
        SPLIT_OFFSETS[split]
        + position
    )

    first_builder = VALUE_BUILDERS[
        position % len(VALUE_BUILDERS)
    ]

    first_value = first_builder(
        value_index
    )

    values = [
        first_value
    ]

    record_id = (
        f"psei3_{split}_positive_"
        f"{position:06d}"
    )

    if position % 5 == 0:
        second_builder = VALUE_BUILDERS[
            (
                position + 7
            )
            % len(VALUE_BUILDERS)
        ]

        second_value = second_builder(
            value_index + 700000
        )

        if second_value[0] == first_value[0]:
            raise RuntimeError(
                f"{record_id}: duplicate values."
            )

        values.append(
            second_value
        )

        templates = MULTIPLE_TEMPLATES[
            split
        ]

        template_index = (
            position
            % len(templates)
        )

        prompt = templates[
            template_index
        ].format(
            first_value=first_value[0],
            second_value=second_value[0],
        )

        template_group = (
            f"iteration3_{split}_multiple_"
            f"{template_index}"
        )

    else:
        templates = POSITIVE_TEMPLATES[
            split
        ]

        template_index = (
            position
            % len(templates)
        )

        prompt = templates[
            template_index
        ].format(
            first_value=first_value[0]
        )

        template_group = (
            f"iteration3_{split}_positive_"
            f"{template_index}_"
            f"{first_value[1]}"
        )

    source_record = {
        "id": record_id,
        "prompt": prompt,
        "action": "redact",
        "rationale": (
            "The prompt contains one or more "
            "fictional sensitive values."
        ),
        "sensitive_spans": create_spans(
            prompt,
            values,
            record_id,
        ),
        "source": SOURCE_NAME,
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
    """Build one difficult negative control."""
    record_id = (
        f"psei3_{split}_negative_"
        f"{position:06d}"
    )

    if position % 4 == 0:
        masked_prompt = MASKED_NEGATIVES[
            (
                position // 4
            )
            % len(MASKED_NEGATIVES)
        ]

        prompt = (
            f"{masked_prompt} "
            f"Safe fixture {split} "
            f"N-{position:04d}."
        )

        template_group = (
            f"iteration3_{split}_masked_"
            f"{(
                position // 4
            ) % len(MASKED_NEGATIVES)}"
        )

    else:
        subject = NEGATIVE_SUBJECTS[
            position
            % len(NEGATIVE_SUBJECTS)
        ]

        templates = NEGATIVE_TEMPLATES[
            split
        ]

        template_index = (
            (
                position
                // len(NEGATIVE_SUBJECTS)
            )
            % len(templates)
        )

        prompt = templates[
            template_index
        ].format(
            subject=subject
        )

        prompt = (
            f"{prompt} "
            f"Development example "
            f"{split} S-{position:04d}."
        )

        template_group = (
            f"iteration3_{split}_concept_"
            f"{template_index}"
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
        "source": SOURCE_NAME,
        "split": split,
        "template_group": template_group,
    }

    positive_count = SPLIT_TARGETS[
        split
    ]["positive"]

    return (
        build_entity_dataset
        .build_entity_record(
            source_record,
            split,
            positive_count + position + 1,
        )
    )


def build_split(
    split: str,
) -> list[dict]:
    """Build one balanced development split."""
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


def load_reference_metadata() -> tuple[
    set[str],
    set[str],
    set[str],
]:
    """Load development metadata without holdouts."""
    prompts = set()
    normalized_prompts = set()
    template_groups = set()

    for path in DEVELOPMENT_REFERENCE_PATHS:
        resolved_path = path.resolve()

        if resolved_path in FORBIDDEN_HOLDOUT_PATHS:
            raise RuntimeError(
                "A consumed final holdout must "
                "not be read."
            )

        if not path.exists():
            raise RuntimeError(
                "Required development dataset "
                f"was not found: {path}"
            )

        for record in load_jsonl(path):
            prompt = record["prompt"]

            prompts.add(prompt)

            normalized_prompts.add(
                normalize_prompt(prompt)
            )

            template_group = record.get(
                "template_group"
            )

            if template_group:
                template_groups.add(
                    template_group
                )

    return (
        prompts,
        normalized_prompts,
        template_groups,
    )


def validate_records(
    records_by_split: dict[str, list[dict]],
) -> dict:
    """Validate uniqueness, balance and isolation."""
    all_records = [
        record
        for records in records_by_split.values()
        for record in records
    ]

    ids = [
        record["id"]
        for record in all_records
    ]

    prompts = [
        record["prompt"]
        for record in all_records
    ]

    normalized_prompts = [
        normalize_prompt(record["prompt"])
        for record in all_records
    ]

    if len(ids) != len(set(ids)):
        raise RuntimeError(
            "Iteration-three IDs must be unique."
        )

    if len(prompts) != len(set(prompts)):
        raise RuntimeError(
            "Iteration-three prompts must be "
            "unique."
        )

    if len(normalized_prompts) != len(
        set(normalized_prompts)
    ):
        raise RuntimeError(
            "Normalized iteration-three prompts "
            "must be unique."
        )

    (
        reference_prompts,
        reference_normalized_prompts,
        reference_template_groups,
    ) = load_reference_metadata()

    prompt_overlap = (
        set(prompts)
        & reference_prompts
    )

    normalized_overlap = (
        set(normalized_prompts)
        & reference_normalized_prompts
    )

    template_groups = {
        record["template_group"]
        for record in all_records
    }

    template_overlap = (
        template_groups
        & reference_template_groups
    )

    if prompt_overlap:
        raise RuntimeError(
            "Iteration-three prompts overlap "
            "earlier development data."
        )

    if normalized_overlap:
        raise RuntimeError(
            "Iteration-three normalized prompts "
            "overlap earlier development data."
        )

    if template_overlap:
        raise RuntimeError(
            "Iteration-three template groups "
            "overlap earlier development data."
        )

    split_reports = {}

    for split, records in (
        records_by_split.items()
    ):
        positives = [
            record
            for record in records
            if record[
                "has_sensitive_entity"
            ]
        ]

        negatives = [
            record
            for record in records
            if not record[
                "has_sensitive_entity"
            ]
        ]

        span_count = sum(
            len(record["gold_spans"])
            for record in records
        )

        expected = SPLIT_TARGETS[split]

        if len(positives) != (
            expected["positive"]
        ):
            raise RuntimeError(
                f"{split}: invalid positive count."
            )

        if len(negatives) != (
            expected["negative"]
        ):
            raise RuntimeError(
                f"{split}: invalid negative count."
            )

        split_reports[split] = {
            "total_records": len(records),
            "positive_records": len(
                positives
            ),
            "negative_records": len(
                negatives
            ),
            "sensitive_spans": span_count,
            "token_count": sum(
                len(record["tokens"])
                for record in records
            ),
        }

    return {
        "dataset": (
            "contextual_sensitive_entity_"
            "iteration3_development_v1"
        ),
        "split_reports": split_reports,
        "total_records": len(all_records),
        "total_sensitive_spans": sum(
            len(record["gold_spans"])
            for record in all_records
        ),
        "unique_ids": True,
        "unique_prompts": True,
        "unique_normalized_prompts": True,
        "previous_development_prompt_overlap": 0,
        "previous_development_normalized_overlap": 0,
        "previous_template_group_overlap": 0,
        "historical_final_holdout_used": False,
        "iteration2_final_holdout_used": False,
        "production_changed": False,
    }


def write_jsonl(
    path: Path,
    records: list[dict],
) -> None:
    """Write deterministic JSON Lines data."""
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        for record in records:
            output_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )


def write_report(
    report: dict,
) -> None:
    """Write the dataset report."""
    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            report,
            output_file,
            indent=2,
            sort_keys=True,
        )

        output_file.write("\n")


def main() -> None:
    """Build all iteration-three development data."""
    print(
        "Building iteration-three entity datasets..."
    )

    print(
        "Consumed final holdouts are not read "
        "or used."
    )

    records_by_split = {}

    for split in [
        "train",
        "validation",
        "challenge",
    ]:
        print(
            f"\nBuilding {split} split..."
        )

        records = build_split(
            split
        )

        records_by_split[split] = records

    report = validate_records(
        records_by_split
    )

    for split, records in (
        records_by_split.items()
    ):
        output_path = OUTPUT_PATHS[
            split
        ]

        write_jsonl(
            output_path,
            records,
        )

        split_report = report[
            "split_reports"
        ][split]

        print(
            "  Records:",
            split_report[
                "total_records"
            ],
        )

        print(
            "  Positive:",
            split_report[
                "positive_records"
            ],
        )

        print(
            "  Negative:",
            split_report[
                "negative_records"
            ],
        )

        print(
            "  Sensitive spans:",
            split_report[
                "sensitive_spans"
            ],
        )

        print(
            "  Saved to:",
            output_path,
        )

    write_report(
        report
    )

    print(
        "\nIteration-three dataset build "
        "completed."
    )

    print(
        "Total records:",
        report["total_records"],
    )

    print(
        "Total sensitive spans:",
        report[
            "total_sensitive_spans"
        ],
    )

    print(
        "Historical final holdout used:",
        report[
            "historical_final_holdout_used"
        ],
    )

    print(
        "Iteration-two final holdout used:",
        report[
            "iteration2_final_holdout_used"
        ],
    )

    print(
        "Report saved to:",
        REPORT_PATH,
    )


if __name__ == "__main__":
    main()