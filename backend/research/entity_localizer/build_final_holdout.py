"""Build a frozen independent entity-localization holdout."""

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


ACTION_DATA_DIRECTORY = (
    SCRIPT_DIRECTORY.parent
    / "action_classifier"
    / "data"
)

OUTPUT_PATH = (
    SCRIPT_DIRECTORY
    / "data"
    / "final_holdout.jsonl"
)

MANIFEST_PATH = (
    SCRIPT_DIRECTORY
    / "final_holdout_manifest.json"
)

SOURCE_DATASET_PATHS = [
    ACTION_DATA_DIRECTORY / "train.jsonl",
    ACTION_DATA_DIRECTORY / "validation.jsonl",
    ACTION_DATA_DIRECTORY / "test.jsonl",
    ACTION_DATA_DIRECTORY / "challenge.jsonl",
]


def positive_record(
    record_id: int,
    prompt: str,
    sensitive_values: list[tuple[str, str]],
    group: str,
) -> dict:
    """Create one synthetic sensitive holdout record."""
    return {
        "id": f"pseh_{record_id:06d}",
        "prompt": prompt,
        "action": "redact",
        "rationale": (
            "The prompt contains one or more "
            "fictional sensitive values."
        ),
        "sensitive_values": sensitive_values,
        "source": "manual_holdout",
        "split": "final_holdout",
        "template_group": group,
    }


def negative_record(
    record_id: int,
    prompt: str,
    group: str,
) -> dict:
    """Create one safe negative-control record."""
    return {
        "id": f"pseh_{record_id:06d}",
        "prompt": prompt,
        "action": "allow",
        "rationale": (
            "The prompt discusses data or contains "
            "non-sensitive lookalikes without exposing "
            "an actual sensitive value."
        ),
        "sensitive_values": [],
        "source": "manual_holdout",
        "split": "final_holdout",
        "template_group": group,
    }


def get_holdout_definitions() -> list[dict]:
    """Return manually authored independent examples."""
    records = [
        positive_record(
            1,
            (
                "Please send the revised invoice to "
                "nora.kapoor+finance@samplemail.org "
                "before Friday."
            ),
            [
                (
                    "nora.kapoor+finance@samplemail.org",
                    "email_address",
                ),
            ],
            "unseen_email_plus_address",
        ),
        positive_record(
            2,
            (
                "The emergency contact written on the "
                "form is +44 7700 900821."
            ),
            [
                (
                    "+44 7700 900821",
                    "international_phone_number",
                ),
            ],
            "unseen_international_phone",
        ),
        positive_record(
            3,
            (
                "Charge the fictional training card "
                "5555-4444-3333-1111 for the demo."
            ),
            [
                (
                    "5555-4444-3333-1111",
                    "payment_card_number",
                ),
            ],
            "unseen_hyphenated_card",
        ),
        positive_record(
            4,
            (
                "The reimbursement account is "
                "GB29 NWBK 6016 1331 9268 19."
            ),
            [
                (
                    "GB29 NWBK 6016 1331 9268 19",
                    "iban",
                ),
            ],
            "unseen_iban",
        ),
        positive_record(
            5,
            (
                "Authenticate the sandbox request with "
                "Bearer q9Vz_7Lm-2RpX8Ka_4TdN6Yu."
            ),
            [
                (
                    "q9Vz_7Lm-2RpX8Ka_4TdN6Yu",
                    "bearer_token",
                ),
            ],
            "unseen_bearer_format",
        ),
        positive_record(
            6,
            (
                "The callback includes session_token="
                "Jk8Qp2_Wx7-Nm4Za6Tr9."
            ),
            [
                (
                    "Jk8Qp2_Wx7-Nm4Za6Tr9",
                    "session_token",
                ),
            ],
            "unseen_session_assignment",
        ),
        positive_record(
            7,
            (
                "Use database URL "
                "postgresql://demo_user:"
                "FictionalPass77@db.invalid/sample."
            ),
            [
                (
                    "postgresql://demo_user:"
                    "FictionalPass77@db.invalid/sample",
                    "database_connection_url",
                ),
            ],
            "unseen_connection_url",
        ),
        positive_record(
            8,
            (
                "The reset link contains recovery code "
                "R7KM-P2QX-V9DN."
            ),
            [
                (
                    "R7KM-P2QX-V9DN",
                    "recovery_code",
                ),
            ],
            "unseen_recovery_code",
        ),
        positive_record(
            9,
            (
                "The applicant entered passport number "
                "P<INDKUMAR<<ARUN<<<<<<<<<<<<123456789."
            ),
            [
                (
                    "P<INDKUMAR<<ARUN<<<<<<<<<<<<123456789",
                    "passport_machine_readable_value",
                ),
            ],
            "unseen_passport_mrz",
        ),
        positive_record(
            10,
            (
                "The tax form lists PAN BCDPK4821M."
            ),
            [
                (
                    "BCDPK4821M",
                    "pan_number",
                ),
            ],
            "unseen_pan_value",
        ),
        positive_record(
            11,
            (
                "The enrolment record contains UID "
                "4567 8901 2345."
            ),
            [
                (
                    "4567 8901 2345",
                    "aadhaar_number",
                ),
            ],
            "unseen_uid_value",
        ),
        positive_record(
            12,
            (
                "Transfer the fictional refund to "
                "account 009876543210 at the test bank."
            ),
            [
                (
                    "009876543210",
                    "bank_account_number",
                ),
            ],
            "unseen_bank_account",
        ),
        positive_record(
            13,
            (
                "The patient record identifier is "
                "MED-RX-908172."
            ),
            [
                (
                    "MED-RX-908172",
                    "medical_record_identifier",
                ),
            ],
            "unseen_medical_identifier",
        ),
        positive_record(
            14,
            (
                "The employee submitted national ID "
                "XZ-84-119027."
            ),
            [
                (
                    "XZ-84-119027",
                    "national_identifier",
                ),
            ],
            "unseen_national_identifier",
        ),
        positive_record(
            15,
            (
                "Her recorded date of birth is "
                "17 September 1998."
            ),
            [
                (
                    "17 September 1998",
                    "date_of_birth",
                ),
            ],
            "unseen_date_of_birth",
        ),
        positive_record(
            16,
            (
                "Deliver the replacement device to "
                "42 Lakeview Crescent, Mysuru 570001."
            ),
            [
                (
                    "42 Lakeview Crescent, Mysuru 570001",
                    "home_address",
                ),
            ],
            "unseen_postal_address",
        ),
        positive_record(
            17,
            (
                "The fictional US record uses SSN "
                "219-45-6789."
            ),
            [
                (
                    "219-45-6789",
                    "social_security_number",
                ),
            ],
            "unseen_ssn",
        ),
        positive_record(
            18,
            (
                "The driver record references licence "
                "KA09 20260001234."
            ),
            [
                (
                    "KA09 20260001234",
                    "driving_licence_number",
                ),
            ],
            "unseen_licence_number",
        ),
        positive_record(
            19,
            (
                "The webhook secret is "
                "whsec_Q7rT9mV2xK8pL4nD6sZ1."
            ),
            [
                (
                    "whsec_Q7rT9mV2xK8pL4nD6sZ1",
                    "webhook_secret",
                ),
            ],
            "unseen_webhook_secret",
        ),
        positive_record(
            20,
            (
                "Set client_secret to "
                "client-Z8p4N7q2R6m9T1v5."
            ),
            [
                (
                    "client-Z8p4N7q2R6m9T1v5",
                    "client_secret",
                ),
            ],
            "unseen_client_secret",
        ),
        positive_record(
            21,
            (
                "The signed test token is "
                "eyJhbGciOiJIUzI1NiJ9."
                "eyJzdWIiOiJkZW1vIn0."
                "Q7vN2mK8pR4tL9xS."
            ),
            [
                (
                    "eyJhbGciOiJIUzI1NiJ9."
                    "eyJzdWIiOiJkZW1vIn0."
                    "Q7vN2mK8pR4tL9xS",
                    "jwt",
                ),
            ],
            "unseen_jwt",
        ),
        positive_record(
            22,
            (
                "The query parameter is "
                "https://example.invalid/callback?"
                "access_token=Ax7Pq9Lm2Nv5Rt8K."
            ),
            [
                (
                    "Ax7Pq9Lm2Nv5Rt8K",
                    "url_access_token",
                ),
            ],
            "unseen_url_token",
        ),
        positive_record(
            23,
            (
                "Store this fictional password safely: "
                "Correct-Horse-72!River."
            ),
            [
                (
                    "Correct-Horse-72!River",
                    "password",
                ),
            ],
            "unseen_password_phrase",
        ),
        positive_record(
            24,
            (
                "The service credential is "
                "svc_live_R4m8K2p7T9x3N6q1."
            ),
            [
                (
                    "svc_live_R4m8K2p7T9x3N6q1",
                    "service_credential",
                ),
            ],
            "unseen_service_credential",
        ),
        positive_record(
            25,
            (
                "Contact amit.rao@demo.example using "
                "reference account 773300991122."
            ),
            [
                (
                    "amit.rao@demo.example",
                    "email_address",
                ),
                (
                    "773300991122",
                    "bank_account_number",
                ),
            ],
            "unseen_multiple_email_account",
        ),
        positive_record(
            26,
            (
                "The profile contains phone "
                "+91-91234-56789 and passport N9081726."
            ),
            [
                (
                    "+91-91234-56789",
                    "phone_number",
                ),
                (
                    "N9081726",
                    "passport_number",
                ),
            ],
            "unseen_multiple_phone_passport",
        ),
        positive_record(
            27,
            (
                "Use login name demo.operator with "
                "password Violet!Grid84."
            ),
            [
                (
                    "demo.operator",
                    "login_username",
                ),
                (
                    "Violet!Grid84",
                    "password",
                ),
            ],
            "unseen_username_password_pair",
        ),
        positive_record(
            28,
            (
                "The backup codes are "
                "BK7P-2LMQ and NZ4R-8VTX."
            ),
            [
                (
                    "BK7P-2LMQ",
                    "backup_code",
                ),
                (
                    "NZ4R-8VTX",
                    "backup_code",
                ),
            ],
            "unseen_multiple_backup_codes",
        ),
        positive_record(
            29,
            (
                "The support note includes customer ID "
                "CUS-709184 and birth date 03/11/1997."
            ),
            [
                (
                    "CUS-709184",
                    "customer_identifier",
                ),
                (
                    "03/11/1997",
                    "date_of_birth",
                ),
            ],
            "unseen_customer_birth_pair",
        ),
        positive_record(
            30,
            (
                "Connect using host 192.0.2.44 and "
                "private key fingerprint "
                "SHA256:Qm7R2pV9xK4tN8sL."
            ),
            [
                (
                    "192.0.2.44",
                    "private_host_address",
                ),
                (
                    "SHA256:Qm7R2pV9xK4tN8sL",
                    "private_key_fingerprint",
                ),
            ],
            "unseen_host_fingerprint_pair",
        ),
        negative_record(
            31,
            (
                "Explain why email addresses are "
                "considered personal information."
            ),
            "negative_email_concept",
        ),
        negative_record(
            32,
            (
                "What security controls protect "
                "international telephone records?"
            ),
            "negative_phone_concept",
        ),
        negative_record(
            33,
            (
                "Describe the standard structure of a "
                "payment card number without giving one."
            ),
            "negative_card_concept",
        ),
        negative_record(
            34,
            (
                "How should a company validate an IBAN "
                "before processing a transfer?"
            ),
            "negative_iban_concept",
        ),
        negative_record(
            35,
            (
                "Bearer authentication sends a token "
                "in the authorization header."
            ),
            "negative_bearer_concept",
        ),
        negative_record(
            36,
            (
                "The configuration field is named "
                "session_token but its value is empty."
            ),
            "negative_empty_assignment",
        ),
        negative_record(
            37,
            (
                "Give an overview of PostgreSQL "
                "connection-string security."
            ),
            "negative_connection_concept",
        ),
        negative_record(
            38,
            (
                "Recovery codes should be stored "
                "offline and used only once."
            ),
            "negative_recovery_concept",
        ),
        negative_record(
            39,
            (
                "What information is printed in the "
                "machine-readable area of a passport?"
            ),
            "negative_passport_concept",
        ),
        negative_record(
            40,
            (
                "PAN validation checks letters and "
                "digits in a defined arrangement."
            ),
            "negative_pan_concept",
        ),
        negative_record(
            41,
            (
                "The UID field should contain twelve "
                "digits, but this form is blank."
            ),
            "negative_uid_concept",
        ),
        negative_record(
            42,
            (
                "Bank account numbers must never be "
                "included in public support tickets."
            ),
            "negative_bank_concept",
        ),
        negative_record(
            43,
            (
                "Medical record identifiers require "
                "strict access controls."
            ),
            "negative_medical_concept",
        ),
        negative_record(
            44,
            (
                "National identification systems "
                "should follow privacy law."
            ),
            "negative_national_id_concept",
        ),
        negative_record(
            45,
            (
                "Ask the user for a date of birth only "
                "when it is legally necessary."
            ),
            "negative_birth_date_concept",
        ),
        negative_record(
            46,
            (
                "Explain how websites can avoid "
                "collecting unnecessary home addresses."
            ),
            "negative_address_concept",
        ),
        negative_record(
            47,
            (
                "A US social security number contains "
                "nine digits."
            ),
            "negative_ssn_concept",
        ),
        negative_record(
            48,
            (
                "Driver licence information should be "
                "encrypted at rest."
            ),
            "negative_licence_concept",
        ),
        negative_record(
            49,
            (
                "Webhook secrets should be rotated "
                "after accidental exposure."
            ),
            "negative_webhook_concept",
        ),
        negative_record(
            50,
            (
                "The client_secret setting is shown as "
                "[REDACTED] in the documentation."
            ),
            "negative_redacted_placeholder",
        ),
        negative_record(
            51,
            (
                "A JWT normally contains three "
                "base64url sections separated by dots."
            ),
            "negative_jwt_concept",
        ),
        negative_record(
            52,
            (
                "Remove access tokens from URL query "
                "parameters."
            ),
            "negative_url_token_concept",
        ),
        negative_record(
            53,
            (
                "A strong password should be unique "
                "and difficult to guess."
            ),
            "negative_password_concept",
        ),
        negative_record(
            54,
            (
                "The service credential was replaced "
                "with the placeholder EXAMPLE_VALUE."
            ),
            "negative_placeholder_value",
        ),
        negative_record(
            55,
            (
                "The order reference is 2026-10-08 and "
                "does not identify a person."
            ),
            "negative_date_like_reference",
        ),
        negative_record(
            56,
            (
                "Version 192.0.2 is used in this "
                "documentation heading."
            ),
            "negative_version_number",
        ),
        negative_record(
            57,
            (
                "The pattern XXXX-XXXX-XXXX-XXXX is a "
                "masked example, not a card number."
            ),
            "negative_masked_card",
        ),
        negative_record(
            58,
            (
                "Contact user@example.invalid is a "
                "reserved documentation address."
            ),
            "negative_reserved_email",
        ),
        negative_record(
            59,
            (
                "The identifier ABC-DEF-GHI is merely "
                "a section label."
            ),
            "negative_identifier_lookalike",
        ),
        negative_record(
            60,
            (
                "Discuss whether an organization should "
                "collect customer identifiers at all."
            ),
            "negative_customer_id_concept",
        ),
    ]

    return records


def build_sensitive_spans(
    prompt: str,
    sensitive_values: list[tuple[str, str]],
    record_id: str,
) -> list[dict]:
    """Find exact offsets for holdout values."""
    spans = []
    occupied_ranges = []

    for value, entity_type in sensitive_values:
        occurrence_count = prompt.count(value)

        if occurrence_count != 1:
            raise RuntimeError(
                f"{record_id}: sensitive value "
                f"{value!r} must occur exactly once; "
                f"found {occurrence_count} occurrences."
            )

        start = prompt.index(value)
        end = start + len(value)

        for existing_start, existing_end in (
            occupied_ranges
        ):
            if (
                start < existing_end
                and end > existing_start
            ):
                raise RuntimeError(
                    f"{record_id}: sensitive values "
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


def load_existing_prompts() -> set[str]:
    """Load prompts already used in development data."""
    prompts = set()

    for dataset_path in SOURCE_DATASET_PATHS:
        records = (
            build_entity_dataset
            .load_jsonl(dataset_path)
        )

        for record in records:
            prompts.add(
                record["prompt"].strip().casefold()
            )

    return prompts


def build_holdout_records() -> list[dict]:
    """Convert definitions into entity records."""
    definitions = get_holdout_definitions()
    existing_prompts = load_existing_prompts()

    holdout_records = []
    seen_ids = set()
    seen_prompts = set()

    for record_position, definition in enumerate(
        definitions,
        start=1,
    ):
        record_id = definition["id"]
        prompt = definition["prompt"].strip()

        normalized_prompt = prompt.casefold()

        if record_id in seen_ids:
            raise RuntimeError(
                f"Duplicate holdout ID: {record_id}"
            )

        if normalized_prompt in seen_prompts:
            raise RuntimeError(
                f"{record_id}: duplicate holdout prompt."
            )

        if normalized_prompt in existing_prompts:
            raise RuntimeError(
                f"{record_id}: prompt already exists "
                "in a development dataset."
            )

        seen_ids.add(record_id)
        seen_prompts.add(normalized_prompt)

        sensitive_spans = build_sensitive_spans(
            prompt,
            definition["sensitive_values"],
            record_id,
        )

        source_record = {
            "id": record_id,
            "prompt": prompt,
            "action": definition["action"],
            "rationale": (
                definition["rationale"]
            ),
            "sensitive_spans": sensitive_spans,
            "source": definition["source"],
            "split": definition["split"],
            "template_group": (
                definition["template_group"]
            ),
        }

        entity_record = (
            build_entity_dataset
            .build_entity_record(
                source_record,
                "final_holdout",
                record_position,
            )
        )

        entity_record["holdout_frozen"] = True

        holdout_records.append(
            entity_record
        )

    return holdout_records


def calculate_file_sha256(path: Path) -> str:
    """Calculate the SHA-256 digest of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        while True:
            block = input_file.read(
                64 * 1024
            )

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def main() -> None:
    """Build and freeze the final entity holdout."""
    print(
        "Building independent entity-localization "
        "holdout..."
    )

    records = build_holdout_records()

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

    span_types = Counter(
        span["type"]
        for record in records
        for span in record["gold_spans"]
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    build_entity_dataset.write_jsonl(
        OUTPUT_PATH,
        records,
    )

    file_sha256 = calculate_file_sha256(
        OUTPUT_PATH
    )

    manifest = {
        "dataset": (
            "contextual_sensitive_entity_"
            "final_holdout_v1"
        ),
        "frozen": True,
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
        "sensitive_span_types": dict(
            sorted(span_types.items())
        ),
        "source": "manual_synthetic_holdout",
        "derived_from_development_data": False,
        "used_for_training": False,
        "used_for_model_selection": False,
        "used_for_threshold_tuning": False,
        "sha256": file_sha256,
        "holdout_path": str(OUTPUT_PATH),
    }

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            manifest,
            output_file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        output_file.write("\n")

    print(
        "\nFinal holdout created and frozen."
    )

    print(
        f"Records: {len(records)}"
    )

    print(
        "Positive records: "
        f"{len(positive_records)}"
    )

    print(
        "Negative controls: "
        f"{len(negative_records)}"
    )

    print(
        "Sensitive spans: "
        f"{manifest['sensitive_span_count']}"
    )

    print(
        f"SHA-256: {file_sha256}"
    )

    print(
        f"Dataset saved to: {OUTPUT_PATH}"
    )

    print(
        f"Manifest saved to: {MANIFEST_PATH}"
    )

    print(
        "\nDo not train, select models or tune "
        "thresholds using this holdout."
    )


if __name__ == "__main__":
    main()