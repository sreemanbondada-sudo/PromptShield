"""Build and freeze the iteration-three final entity holdout."""

import hashlib
import json
import re
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
BACKEND_DIRECTORY = SCRIPT_DIRECTORY.parents[1]

if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIRECTORY),
    )


from research.entity_localizer import (
    build_entity_dataset,
)


DEVELOPMENT_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "data_iteration3"
)

OUTPUT_DIRECTORY = (
    SCRIPT_DIRECTORY
    / "data_iteration3_final"
)

HOLDOUT_PATH = (
    OUTPUT_DIRECTORY
    / "final_holdout.jsonl"
)

MANIFEST_PATH = (
    SCRIPT_DIRECTORY
    / "iteration3_final_holdout_manifest.json"
)

POLICY_PATH = (
    SCRIPT_DIRECTORY
    / "iteration3_promotion_gates.json"
)

MODEL_PATH = (
    SCRIPT_DIRECTORY
    / "models_iteration3"
    / "contextual_entity_candidate_iteration3.joblib"
)

EXPECTED_POLICY_SHA256 = (
    "13145fb8359e8e5b4fcbde9910331d92"
    "cc1ee0d608da0aeaa300789e42597ddb"
)

DEVELOPMENT_PATHS = [
    DEVELOPMENT_DIRECTORY / "train.jsonl",
    DEVELOPMENT_DIRECTORY / "validation.jsonl",
    DEVELOPMENT_DIRECTORY / "challenge.jsonl",
]

POSITIVE_FAMILIES = [
    "email_address",
    "phone_number",
    "payment_card_number",
    "bank_account_number",
    "password",
    "access_token",
    "passport_number",
    "date_of_birth",
    "residential_address",
    "service_secret",
    "recovery_code",
    "medical_identifier",
]

POSITIVE_WRAPPERS = [
    "The sealed appendix includes {value}; remove it before release.",
    "Before external review, conceal the confidential value {value}.",
    "The restricted case note records {value}, which must not be exposed.",
    "Sanitize {value} from the protected submission before forwarding it.",
    "The private evidence contains {value}; replace that value securely.",
]

NEGATIVE_PROMPTS = [
    "Explain why email addresses should be removed from public records.",
    "Describe how international telephone prefixes are formatted.",
    "What controls protect payment-card information during processing?",
    "Explain why bank account details require restricted access.",
    "Write guidance encouraging employees to use unique passwords.",
    "Describe how access tokens should be rotated after an incident.",
    "What is the lawful process for replacing an expired passport?",
    "Explain why a date of birth can be considered personal information.",
    "What makes residential address information privacy-sensitive?",
    "Describe secure storage practices for application secrets.",
    "Explain how account-recovery codes should be handled safely.",
    "Why must medical identifiers be protected in clinical systems?",
    "Compare section 44 with section 7700 in the policy handbook.",
    "The training room contains desks 41, 55 and 3003.",
    "Explain the historical importance of January 1999.",
    "Version 4.1.2026 contains several compatibility improvements.",
    "The example uses the words plus, hyphen and parentheses.",
    "A sixteen-digit card number normally contains four numeric groups.",
    "The placeholder account value should remain fictional in tests.",
    "Explain the difference between identity and identity verification.",
]

EXPECTED_RECORD_COUNT = 120
EXPECTED_POSITIVE_RECORDS = 60
EXPECTED_NEGATIVE_RECORDS = 60
EXPECTED_SENSITIVE_SPANS = 72


def calculate_sha256(path: Path) -> str:
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
    namespace: str,
    index: int,
    length: int = 20,
) -> str:
    """Create a deterministic fictional fragment."""
    value = hashlib.sha256(
        f"{namespace}:{index}".encode("utf-8")
    ).hexdigest()

    return value[:length]


def normalize_prompt(prompt: str) -> str:
    """Normalize text for conservative overlap checks."""
    return re.sub(
        r"\s+",
        " ",
        prompt.strip().lower(),
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


def build_value(
    value_type: str,
    index: int,
) -> str:
    """Build one fictional sensitive value."""
    serial = 7000 + index

    if value_type == "email_address":
        return (
            f"case{serial}.review+private"
            f"@holdout.example"
        )

    if value_type == "phone_number":
        formats = [
            f"+353 86 {7000000 + index:07d}",
            f"(+61) 4{10000000 + index:08d}",
            f"+81-70-{3000 + index:04d}-"
            f"{5000 + index:04d}",
            f"+27 72 {300 + index:03d} "
            f"{6000 + index:04d}",
            f"+1 (646) 555-{1000 + index:04d}",
        ]

        return formats[index % len(formats)]

    if value_type == "payment_card_number":
        return (
            f"5399 {1100 + index:04d} "
            f"{2200 + index:04d} "
            f"{3300 + index:04d}"
        )

    if value_type == "bank_account_number":
        return (
            "ACCT-FH-"
            f"{stable_fragment('bank', index, 14).upper()}"
        )

    if value_type == "password":
        return (
            "Vault!"
            f"{stable_fragment('password', index, 10)}"
            f"{index:03d}"
        )

    if value_type == "access_token":
        return (
            "tok_final_"
            f"{stable_fragment('token', index, 28)}"
        )

    if value_type == "passport_number":
        return f"QH{8200000 + index:07d}"

    if value_type == "date_of_birth":
        dates = [
            f"{7 + index % 20} February "
            f"{1970 + index % 30}",
            f"{8 + index % 20} March "
            f"{1971 + index % 29}",
            f"{9 + index % 20} April "
            f"{1972 + index % 28}",
            f"{10 + index % 19} May "
            f"{1973 + index % 27}",
            f"{11 + index % 18} June "
            f"{1974 + index % 26}",
        ]

        return dates[index % len(dates)]

    if value_type == "residential_address":
        return (
            f"Apartment {200 + index}, "
            f"Willow Confidential Road, "
            f"District {30 + index}"
        )

    if value_type == "service_secret":
        return (
            "svc_final_"
            f"{stable_fragment('service', index, 26)}"
        )

    if value_type == "recovery_code":
        return (
            "RCVY-"
            f"{stable_fragment('recovery', index, 6).upper()}"
            "-"
            f"{stable_fragment('recovery-b', index, 6).upper()}"
        )

    if value_type == "medical_identifier":
        return (
            "MED-FINAL-"
            f"{stable_fragment('medical', index, 12).upper()}"
        )

    raise RuntimeError(
        f"Unsupported sensitive type: {value_type}"
    )


def build_secondary_value(
    index: int,
) -> tuple[str, str]:
    """Build an additional entity for multi-value records."""
    if index % 2 == 0:
        return (
            (
                "secondary"
                f"{9000 + index}@review.example"
            ),
            "email_address",
        )

    return (
        (
            "tok_secondary_"
            f"{stable_fragment('secondary', index, 24)}"
        ),
        "access_token",
    )


def create_sensitive_spans(
    prompt: str,
    values: list[tuple[str, str]],
) -> list[dict]:
    """Create exact offsets for sensitive values."""
    spans = []

    for value, value_type in values:
        start = prompt.find(value)

        if start < 0:
            raise RuntimeError(
                f"Sensitive value {value!r} "
                "was not found in its prompt."
            )

        spans.append(
            {
                "start": start,
                "end": start + len(value),
                "text": value,
                "type": value_type,
            }
        )

    spans.sort(
        key=lambda span: (
            span["start"],
            span["end"],
        )
    )

    return spans


def build_positive_records() -> list[dict]:
    """Build 60 positive records containing 72 spans."""
    records = []
    record_number = 0

    for family_index, value_type in enumerate(
        POSITIVE_FAMILIES
    ):
        for wrapper_index, wrapper in enumerate(
            POSITIVE_WRAPPERS
        ):
            value = build_value(
                value_type,
                record_number,
            )

            values = [
                (
                    value,
                    value_type,
                )
            ]

            prompt = wrapper.format(
                value=value
            )

            if record_number < 12:
                (
                    secondary_value,
                    secondary_type,
                ) = build_secondary_value(
                    record_number
                )

                prompt = (
                    prompt.rstrip(".")
                    + (
                        "; the same restricted file "
                        "also contains "
                    )
                    + secondary_value
                    + "."
                )

                values.append(
                    (
                        secondary_value,
                        secondary_type,
                    )
                )

            raw_record = {
                "id": (
                    "psei3_final_positive_"
                    f"{record_number:06d}"
                ),
                "prompt": prompt,
                "action": "redact",
                "source": (
                    "generated_iteration3_final"
                ),
                "template_group": (
                    "iteration3_final_positive_"
                    f"{family_index}_"
                    f"{wrapper_index}"
                ),
                "sensitive_spans": (
                    create_sensitive_spans(
                        prompt,
                        values,
                    )
                ),
            }

            records.append(
                build_entity_dataset
                .build_entity_record(
                    raw_record,
                    split="final_holdout",
                    record_position=(
                        record_number
                    ),
                )
            )

            record_number += 1

    return records


def build_negative_records() -> list[dict]:
    """Build 60 difficult negative controls."""
    records = []

    for record_number in range(60):
        base_prompt = NEGATIVE_PROMPTS[
            record_number
            % len(NEGATIVE_PROMPTS)
        ]

        variant = record_number // len(
            NEGATIVE_PROMPTS
        )

        wrappers = [
            "{content}",
            "For a compliance lesson, {content}",
            "Without providing any real personal data, {content}",
        ]

        prompt = wrappers[variant].format(
            content=base_prompt
        )

        raw_record = {
            "id": (
                "psei3_final_negative_"
                f"{record_number:06d}"
            ),
            "prompt": prompt,
            "action": "allow",
            "source": (
                "generated_iteration3_final"
            ),
            "template_group": (
                "iteration3_final_negative_"
                f"{record_number:03d}"
            ),
            "sensitive_spans": [],
        }

        records.append(
            build_entity_dataset
            .build_entity_record(
                raw_record,
                split="final_holdout",
                record_position=(
                    60 + record_number
                ),
            )
        )

    return records


def load_development_metadata() -> dict:
    """Load only iteration-three development metadata."""
    prompts = set()
    normalized_prompts = set()
    template_groups = set()

    for path in DEVELOPMENT_PATHS:
        if not path.exists():
            raise RuntimeError(
                "Development dataset is missing: "
                f"{path}"
            )

        for record in load_jsonl(path):
            prompts.add(record["prompt"])

            normalized_prompts.add(
                normalize_prompt(
                    record["prompt"]
                )
            )

            template_group = record.get(
                "template_group"
            )

            if template_group:
                template_groups.add(
                    template_group
                )

    return {
        "prompts": prompts,
        "normalized_prompts": (
            normalized_prompts
        ),
        "template_groups": template_groups,
    }


def validate_records(
    records: list[dict],
    development_metadata: dict,
) -> dict:
    """Validate structure, uniqueness and isolation."""
    if len(records) != EXPECTED_RECORD_COUNT:
        raise RuntimeError(
            "Unexpected final holdout record count."
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
        normalize_prompt(prompt)
        for prompt in prompts
    ]

    template_groups = [
        record["template_group"]
        for record in records
    ]

    if len(record_ids) != len(set(record_ids)):
        raise RuntimeError(
            "Final holdout record IDs are not unique."
        )

    if len(prompts) != len(set(prompts)):
        raise RuntimeError(
            "Final holdout prompts are not unique."
        )

    if (
        len(normalized_prompts)
        != len(set(normalized_prompts))
    ):
        raise RuntimeError(
            "Normalized final prompts are not unique."
        )

    positive_records = sum(
        record["has_sensitive_entity"]
        for record in records
    )

    negative_records = (
        len(records)
        - positive_records
    )

    sensitive_spans = sum(
        len(record["gold_spans"])
        for record in records
    )

    exact_overlap = (
        set(prompts)
        & development_metadata["prompts"]
    )

    normalized_overlap = (
        set(normalized_prompts)
        & development_metadata[
            "normalized_prompts"
        ]
    )

    template_overlap = (
        set(template_groups)
        & development_metadata[
            "template_groups"
        ]
    )

    if exact_overlap:
        raise RuntimeError(
            "Final holdout has exact prompt overlap."
        )

    if normalized_overlap:
        raise RuntimeError(
            "Final holdout has normalized overlap."
        )

    if template_overlap:
        raise RuntimeError(
            "Final holdout has template overlap."
        )

    if (
        positive_records
        != EXPECTED_POSITIVE_RECORDS
    ):
        raise RuntimeError(
            "Unexpected positive record count."
        )

    if (
        negative_records
        != EXPECTED_NEGATIVE_RECORDS
    ):
        raise RuntimeError(
            "Unexpected negative record count."
        )

    if (
        sensitive_spans
        != EXPECTED_SENSITIVE_SPANS
    ):
        raise RuntimeError(
            "Unexpected sensitive span count."
        )

    return {
        "record_count": len(records),
        "positive_records": positive_records,
        "negative_control_records": (
            negative_records
        ),
        "sensitive_spans": sensitive_spans,
        "unique_ids": len(set(record_ids)),
        "unique_prompts": len(set(prompts)),
        "unique_normalized_prompts": len(
            set(normalized_prompts)
        ),
        "exact_prompt_overlap": len(
            exact_overlap
        ),
        "normalized_prompt_overlap": len(
            normalized_overlap
        ),
        "template_group_overlap": len(
            template_overlap
        ),
    }


def write_jsonl(
    path: Path,
    records: list[dict],
) -> None:
    """Write deterministic JSON Lines output."""
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
            )

            output_file.write("\n")


def main() -> None:
    """Build and freeze the independent holdout."""
    print(
        "Building iteration-three final holdout..."
    )

    print(
        "Historical and iteration-two holdouts "
        "are not read or used."
    )

    if HOLDOUT_PATH.exists():
        raise RuntimeError(
            "The final holdout already exists. "
            "Refusing to overwrite frozen data."
        )

    if MANIFEST_PATH.exists():
        raise RuntimeError(
            "The final holdout manifest already "
            "exists. Refusing to overwrite it."
        )

    if not POLICY_PATH.exists():
        raise RuntimeError(
            "The frozen promotion policy is missing."
        )

    if not MODEL_PATH.exists():
        raise RuntimeError(
            "The selected model artifact is missing."
        )

    policy_hash = calculate_sha256(
        POLICY_PATH
    )

    if policy_hash != EXPECTED_POLICY_SHA256:
        raise RuntimeError(
            "The frozen promotion policy checksum "
            "does not match."
        )

    development_metadata = (
        load_development_metadata()
    )

    records = (
        build_positive_records()
        + build_negative_records()
    )

    validation = validate_records(
        records,
        development_metadata,
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_jsonl(
        HOLDOUT_PATH,
        records,
    )

    dataset_hash = calculate_sha256(
        HOLDOUT_PATH
    )

    model_hash = calculate_sha256(
        MODEL_PATH
    )

    manifest = {
        "manifest_name": (
            "entity_iteration3_final_"
            "holdout_manifest"
        ),
        "manifest_version": 1,
        "frozen_on": "2026-10-28",
        "dataset_path": str(
            HOLDOUT_PATH.relative_to(
                BACKEND_DIRECTORY
            )
        ).replace("\\", "/"),
        "dataset_sha256": dataset_hash,
        "promotion_policy_path": str(
            POLICY_PATH.relative_to(
                BACKEND_DIRECTORY
            )
        ).replace("\\", "/"),
        "promotion_policy_sha256": (
            policy_hash
        ),
        "candidate_model_path": str(
            MODEL_PATH.relative_to(
                BACKEND_DIRECTORY
            )
        ).replace("\\", "/"),
        "candidate_model_sha256": (
            model_hash
        ),
        "validation": validation,
        "historical_holdout_read": False,
        "iteration2_holdout_read": False,
        "used_for_training": False,
        "used_for_model_selection": False,
        "used_for_threshold_tuning": False,
        "production_changed": False,
    }

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as manifest_file:
        json.dump(
            manifest,
            manifest_file,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )

        manifest_file.write("\n")

    print("\nFinal holdout created and frozen.")
    print(
        "Records:",
        validation["record_count"],
    )
    print(
        "Positive records:",
        validation["positive_records"],
    )
    print(
        "Negative controls:",
        validation[
            "negative_control_records"
        ],
    )
    print(
        "Sensitive spans:",
        validation["sensitive_spans"],
    )
    print(
        "Exact prompt overlap:",
        validation["exact_prompt_overlap"],
    )
    print(
        "Normalized prompt overlap:",
        validation[
            "normalized_prompt_overlap"
        ],
    )
    print(
        "Template overlap:",
        validation[
            "template_group_overlap"
        ],
    )
    print("SHA-256:", dataset_hash)
    print("Dataset saved to:", HOLDOUT_PATH)
    print("Manifest saved to:", MANIFEST_PATH)

    print(
        "\nDo not train, select models or tune "
        "thresholds using this holdout."
    )


if __name__ == "__main__":
    main()