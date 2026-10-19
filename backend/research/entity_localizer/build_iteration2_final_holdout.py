"""Build and freeze the independent iteration-two entity holdout."""
"""Build and freeze the independent iteration-two entity holdout."""

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

OUTPUT_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "data_iteration2_final"
)

OUTPUT_PATH = (
    OUTPUT_DIRECTORY
    / "final_holdout.jsonl"
)

MANIFEST_PATH = (
    SCRIPT_DIRECTORY
    / "iteration2_final_holdout_manifest.json"
)

PROMOTION_GATES_PATH = (
    SCRIPT_DIRECTORY
    / "ITERATION2_PROMOTION_GATES.json"
)

MODEL_PATH = (
    SCRIPT_DIRECTORY
    / "models_iteration2"
    / "contextual_entity_candidate_iteration2.joblib"
)

DEVELOPMENT_DATASET_PATHS = [
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

HISTORICAL_HOLDOUT_PATH = (
    SCRIPT_DIRECTORY
    / "data"
    / "final_holdout.jsonl"
)

TOTAL_RECORDS = 100
POSITIVE_RECORDS = 50
NEGATIVE_RECORDS = 50

SOURCE_NAME = (
    "generated_iteration2_independent_holdout"
)

SPLIT_NAME = "iteration2_final_holdout"


POSITIVE_TEMPLATES = [
    (
        "Before archiving the case, conceal "
        "{first_value} from the exported note."
    ),
    (
        "The private attachment contains "
        "{first_value}; remove it before sharing."
    ),
    (
        "Sanitize the submitted form because it "
        "includes {first_value}."
    ),
    (
        "Do not publish {first_value} in the "
        "external incident report."
    ),
    (
        "The confidential record lists "
        "{first_value}, which must be hidden."
    ),
    (
        "Replace the exposed value "
        "{first_value} before sending this message."
    ),
    (
        "Remove {first_value} from the document "
        "prepared for public release."
    ),
    (
        "The support transcript accidentally shows "
        "{first_value}; redact that value."
    ),
    (
        "Mask {first_value} in the customer-facing "
        "copy of this report."
    ),
    (
        "The audit export contains "
        "{first_value}, so protect it before use."
    ),
]


MULTIPLE_VALUE_TEMPLATES = [
    (
        "Before archiving the case, conceal "
        "{first_value} and {second_value} "
        "from the exported note."
    ),
    (
        "The private attachment contains "
        "{first_value}; it also exposes "
        "{second_value}. Remove both."
    ),
    (
        "Sanitize the submitted form because it "
        "includes {first_value} together with "
        "{second_value}."
    ),
    (
        "Do not publish {first_value} or "
        "{second_value} in the external report."
    ),
    (
        "The confidential record lists "
        "{first_value} and {second_value}; "
        "both values must be hidden."
    ),
]


NEGATIVE_PROMPTS = [
    (
        "Explain why organizations protect email "
        "addresses in public reports."
    ),
    (
        "Describe the lawful process for updating "
        "a registered phone number."
    ),
    (
        "What security controls should protect "
        "payment-card information?"
    ),
    (
        "Explain why bank-account details require "
        "restricted access."
    ),
    (
        "Write a policy requiring employees to use "
        "strong passwords."
    ),
    (
        "How should access tokens be stored without "
        "including any real token?"
    ),
    (
        "Explain the official process for renewing "
        "an expired passport."
    ),
    (
        "Why do some forms request a person's date "
        "of birth?"
    ),
    (
        "Describe good privacy practices for home "
        "addresses."
    ),
    (
        "Explain how medical identifiers should be "
        "handled securely."
    ),
    (
        "The email field is marked as "
        "[email removed] in this example."
    ),
    (
        "The phone field contains "
        "[number withheld], not a real number."
    ),
    (
        "The card example is written as "
        "XXXX XXXX XXXX XXXX."
    ),
    (
        "The account field says "
        "[account unavailable]."
    ),
    (
        "The password placeholder is "
        "<password omitted>."
    ),
    (
        "The token field contains "
        "[token removed] for documentation."
    ),
    (
        "The passport field is intentionally blank "
        "in this sample form."
    ),
    (
        "The birth-date field uses the placeholder "
        "DD Month YYYY."
    ),
    (
        "The address section says "
        "[residential address removed]."
    ),
    (
        "The patient identifier is masked in the "
        "training screenshot."
    ),
    (
        "What does identity-verification mean in "
        "regulated services?"
    ),
    (
        "Explain personal-data breach notification "
        "without supplying personal information."
    ),
    (
        "How can developers test redaction using "
        "fictional placeholders?"
    ),
    (
        "Write documentation describing an API-key "
        "field without showing a key."
    ),
    (
        "Explain why recovery codes must never be "
        "shared publicly."
    ),
]


def sha256_file(path: Path) -> str:
    """Calculate a file SHA-256 checksum."""
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        for chunk in iter(
            lambda: input_file.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def stable_fragment(
    prefix: str,
    index: int,
    length: int,
) -> str:
    """Create a deterministic hexadecimal fragment."""
    value = (
        f"{prefix}:iteration-two-final:{index}"
    )

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:length]


def normalize_prompt(prompt: str) -> str:
    """Normalize text for conservative overlap checks."""
    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        prompt.casefold(),
    )

    return " ".join(
        normalized.split()
    )


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSON Lines file."""
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


def create_spans(
    prompt: str,
    sensitive_values: list[tuple[str, str]],
    record_id: str,
) -> list[dict]:
    """Create exact non-overlapping spans."""
    spans = []
    occupied_ranges = []

    for value, entity_type in sensitive_values:
        if prompt.count(value) != 1:
            raise RuntimeError(
                f"{record_id}: sensitive value "
                f"{value!r} must occur once."
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
                f"{record_id}: sensitive spans "
                "must not overlap."
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


def build_email(
    index: int,
) -> tuple[str, str]:
    """Build an independent email value."""
    value = (
        f"holdout.person{index:03d}"
        f"+case{(index * 7) % 97:02d}"
        "@private.invalid"
    )

    return value, "email_address"


def build_phone(
    index: int,
) -> tuple[str, str]:
    """Build an independent phone value."""
    suffix = 100000000 + index * 7919

    value = (
        f"+91 7{suffix:09d}"[:14]
    )

    return value, "phone_number"


def build_card(
    index: int,
) -> tuple[str, str]:
    """Build an independent fictional card value."""
    value = (
        f"4929 "
        f"{6100 + index:04d} "
        f"{7200 + index:04d} "
        f"{8300 + index:04d}"
    )

    return value, "payment_card_number"


def build_bank_account(
    index: int,
) -> tuple[str, str]:
    """Build an independent fictional account."""
    fragment = stable_fragment(
        "account",
        index,
        14,
    ).upper()

    return (
        f"VAULT-{fragment}",
        "bank_account_number",
    )


def build_password(
    index: int,
) -> tuple[str, str]:
    """Build an independent fictional password."""
    fragment = stable_fragment(
        "password",
        index,
        12,
    )

    return (
        f"Qz!Final{fragment}9#",
        "password",
    )


def build_access_token(
    index: int,
) -> tuple[str, str]:
    """Build an independent fictional token."""
    fragment = stable_fragment(
        "access-token",
        index,
        30,
    )

    return (
        f"ctx_final_{fragment}",
        "access_token",
    )


def build_passport(
    index: int,
) -> tuple[str, str]:
    """Build an independent fictional passport."""
    return (
        f"ZP{8700000 + index:07d}",
        "passport_number",
    )


def build_birth_date(
    index: int,
) -> tuple[str, str]:
    """Build an independent birth-date value."""
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

    day = 10 + index % 18
    month = months[index % len(months)]
    year = 1965 + index % 35

    return (
        f"{day} {month} {year}",
        "date_of_birth",
    )


def build_address(
    index: int,
) -> tuple[str, str]:
    """Build an independent fictional address."""
    value = (
        f"Flat {40 + index}, "
        f"Orchid Archive Road, "
        f"Sector {70 + index % 20}"
    )

    return value, "residential_address"


def build_medical_id(
    index: int,
) -> tuple[str, str]:
    """Build an independent fictional medical ID."""
    fragment = stable_fragment(
        "medical",
        index,
        10,
    ).upper()

    return (
        f"MED-FINAL-{fragment}",
        "medical_identifier",
    )


def build_recovery_code(
    index: int,
) -> tuple[str, str]:
    """Build an independent fictional recovery code."""
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
    build_medical_id,
]


def build_positive_record(
    position: int,
) -> dict:
    """Build one independent positive record."""
    record_id = (
        f"psei2_final_positive_{position:06d}"
    )

    first_builder = VALUE_BUILDERS[
        position % len(VALUE_BUILDERS)
    ]

    first_value = first_builder(
        20000 + position
    )

    sensitive_values = [
        first_value
    ]

    if position % 4 == 0:
        second_value = build_recovery_code(
            30000 + position
        )

        sensitive_values.append(
            second_value
        )

        template = MULTIPLE_VALUE_TEMPLATES[
            position
            % len(MULTIPLE_VALUE_TEMPLATES)
        ]

        prompt = template.format(
            first_value=first_value[0],
            second_value=second_value[0],
        )

        template_group = (
            "iteration2_final_multiple_"
            f"{position % len(MULTIPLE_VALUE_TEMPLATES)}"
        )

    else:
        template = POSITIVE_TEMPLATES[
            position
            % len(POSITIVE_TEMPLATES)
        ]

        prompt = template.format(
            first_value=first_value[0]
        )

        template_group = (
            "iteration2_final_positive_"
            f"{position % len(POSITIVE_TEMPLATES)}_"
            f"{first_value[1]}"
        )

    source_record = {
        "id": record_id,
        "prompt": prompt,
        "action": "redact",
        "rationale": (
            "The prompt contains an actual "
            "fictional sensitive value."
        ),
        "sensitive_spans": create_spans(
            prompt,
            sensitive_values,
            record_id,
        ),
        "source": SOURCE_NAME,
        "split": SPLIT_NAME,
        "template_group": template_group,
    }

    return (
        build_entity_dataset
        .build_entity_record(
            source_record,
            SPLIT_NAME,
            position + 1,
        )
    )


def build_negative_record(
    position: int,
) -> dict:
    """Build one independent difficult negative."""
    record_id = (
        f"psei2_final_negative_{position:06d}"
    )

    base_prompt = NEGATIVE_PROMPTS[
        position % len(NEGATIVE_PROMPTS)
    ]

    prompt = (
        f"{base_prompt} "
        f"Independent policy case "
        f"HN-{position:03d}."
    )

    source_record = {
        "id": record_id,
        "prompt": prompt,
        "action": "allow",
        "rationale": (
            "The prompt discusses sensitive-data "
            "concepts but contains no actual value."
        ),
        "sensitive_spans": [],
        "source": SOURCE_NAME,
        "split": SPLIT_NAME,
        "template_group": (
            "iteration2_final_negative_"
            f"{position % len(NEGATIVE_PROMPTS)}"
        ),
    }

    return (
        build_entity_dataset
        .build_entity_record(
            source_record,
            SPLIT_NAME,
            POSITIVE_RECORDS + position + 1,
        )
    )


def load_development_metadata() -> tuple[
    set[str],
    set[str],
    set[str],
]:
    """Load only development prompt metadata."""
    exact_prompts = set()
    normalized_prompts = set()
    template_groups = set()

    for path in DEVELOPMENT_DATASET_PATHS:
        if not path.exists():
            raise RuntimeError(
                "Required development dataset "
                f"was not found: {path}"
            )

        if path.resolve() == (
            HISTORICAL_HOLDOUT_PATH.resolve()
        ):
            raise RuntimeError(
                "The historical final holdout must "
                "not be read."
            )

        for record in load_jsonl(path):
            prompt = record["prompt"]

            exact_prompts.add(prompt)

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
        exact_prompts,
        normalized_prompts,
        template_groups,
    )


def validate_holdout(
    records: list[dict],
) -> dict:
    """Validate counts, uniqueness and isolation."""
    if len(records) != TOTAL_RECORDS:
        raise RuntimeError(
            "The holdout must contain exactly "
            f"{TOTAL_RECORDS} records."
        )

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

    if len(positive_records) != POSITIVE_RECORDS:
        raise RuntimeError(
            "The holdout has an invalid positive "
            "record count."
        )

    if len(negative_records) != NEGATIVE_RECORDS:
        raise RuntimeError(
            "The holdout has an invalid negative "
            "record count."
        )

    sensitive_span_count = sum(
        len(record["gold_spans"])
        for record in records
    )

    if sensitive_span_count < 55:
        raise RuntimeError(
            "The holdout must contain at least "
            "55 sensitive spans."
        )

    record_ids = [
        record["id"]
        for record in records
    ]

    prompts = [
        record["prompt"]
        for record in records
    ]

    normalized_prompts = [
        normalize_prompt(record["prompt"])
        for record in records
    ]

    if len(record_ids) != len(set(record_ids)):
        raise RuntimeError(
            "Holdout record IDs must be unique."
        )

    if len(prompts) != len(set(prompts)):
        raise RuntimeError(
            "Holdout prompts must be unique."
        )

    if len(normalized_prompts) != len(
        set(normalized_prompts)
    ):
        raise RuntimeError(
            "Normalized holdout prompts must "
            "be unique."
        )

    (
        development_prompts,
        development_normalized_prompts,
        development_template_groups,
    ) = load_development_metadata()

    prompt_overlap = (
        set(prompts)
        & development_prompts
    )

    normalized_overlap = (
        set(normalized_prompts)
        & development_normalized_prompts
    )

    holdout_template_groups = {
        record["template_group"]
        for record in records
    }

    template_group_overlap = (
        holdout_template_groups
        & development_template_groups
    )

    if prompt_overlap:
        raise RuntimeError(
            "The holdout overlaps development "
            "prompts."
        )

    if normalized_overlap:
        raise RuntimeError(
            "The holdout overlaps normalized "
            "development prompts."
        )

    if template_group_overlap:
        raise RuntimeError(
            "The holdout overlaps development "
            "template groups."
        )

    return {
        "total_records": len(records),
        "positive_records": len(
            positive_records
        ),
        "negative_control_records": len(
            negative_records
        ),
        "sensitive_spans": sensitive_span_count,
        "unique_record_ids": True,
        "unique_prompts": True,
        "unique_normalized_prompts": True,
        "development_prompt_overlap": 0,
        "development_normalized_prompt_overlap": 0,
        "development_template_group_overlap": 0,
        "historical_holdout_read": False,
    }


def write_jsonl(
    path: Path,
    records: list[dict],
) -> None:
    """Write deterministic JSON Lines output."""
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
            serialized_record = json.dumps(
                record,
                ensure_ascii=False,
                sort_keys=True,
            )

            output_file.write(
                serialized_record + "\n"
            )


def write_manifest(
    validation_report: dict,
) -> dict:
    """Write the immutable holdout manifest."""
    manifest = {
        "dataset_name": (
            "contextual_sensitive_entity_"
            "iteration2_final_holdout_v1"
        ),
        "dataset_path": (
            "data_iteration2_final/"
            "final_holdout.jsonl"
        ),
        "dataset_sha256": sha256_file(
            OUTPUT_PATH
        ),
        "promotion_policy_path": (
            "ITERATION2_PROMOTION_GATES.json"
        ),
        "promotion_policy_sha256": sha256_file(
            PROMOTION_GATES_PATH
        ),
        "candidate_model_path": (
            "models_iteration2/"
            "contextual_entity_candidate_"
            "iteration2.joblib"
        ),
        "candidate_model_sha256": sha256_file(
            MODEL_PATH
        ),
        "builder_path": (
            "build_iteration2_final_holdout.py"
        ),
        "frozen": True,
        "one_time_evaluation": True,
        "used_for_training": False,
        "used_for_model_selection": False,
        "used_for_threshold_tuning": False,
        "historical_holdout_read": False,
        "production_changed": False,
        "validation": validation_report,
    }

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            manifest,
            output_file,
            indent=2,
            sort_keys=True,
        )

        output_file.write("\n")

    return manifest


def main() -> None:
    """Build the independent frozen holdout once."""
    if OUTPUT_PATH.exists():
        raise RuntimeError(
            "The iteration-two final holdout "
            "already exists and will not be "
            "overwritten."
        )

    if MANIFEST_PATH.exists():
        raise RuntimeError(
            "The iteration-two final holdout "
            "manifest already exists and will "
            "not be overwritten."
        )

    if not PROMOTION_GATES_PATH.exists():
        raise RuntimeError(
            "The frozen promotion policy was "
            "not found."
        )

    if not MODEL_PATH.exists():
        raise RuntimeError(
            "The frozen candidate model was "
            "not found."
        )

    records = []

    for position in range(
        POSITIVE_RECORDS
    ):
        records.append(
            build_positive_record(
                position
            )
        )

    for position in range(
        NEGATIVE_RECORDS
    ):
        records.append(
            build_negative_record(
                position
            )
        )

    validation_report = validate_holdout(
        records
    )

    write_jsonl(
        OUTPUT_PATH,
        records,
    )

    manifest = write_manifest(
        validation_report
    )

    print(
        "Iteration-two final holdout "
        "created and frozen."
    )

    print(
        "Records:",
        validation_report["total_records"],
    )

    print(
        "Positive records:",
        validation_report[
            "positive_records"
        ],
    )

    print(
        "Negative controls:",
        validation_report[
            "negative_control_records"
        ],
    )

    print(
        "Sensitive spans:",
        validation_report[
            "sensitive_spans"
        ],
    )

    print(
        "Historical holdout read:",
        validation_report[
            "historical_holdout_read"
        ],
    )

    print(
        "Dataset SHA-256:",
        manifest["dataset_sha256"],
    )

    print(
        "Policy SHA-256:",
        manifest[
            "promotion_policy_sha256"
        ],
    )

    print(
        "Model SHA-256:",
        manifest[
            "candidate_model_sha256"
        ],
    )

    print(
        "Dataset saved to:",
        OUTPUT_PATH,
    )

    print(
        "Manifest saved to:",
        MANIFEST_PATH,
    )

    print(
        "\nDo not train, select models or tune "
        "thresholds using this holdout."
    )


if __name__ == "__main__":
    main()