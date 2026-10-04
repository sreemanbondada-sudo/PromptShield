"""
Contextual Redact dataset families.

Every sensitive value in this research catalog is fictional
and exists only for defensive classifier development.
"""


REDACT_FAMILIES = [
    {
        "name": "shared_personal_email",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes a specific personal email "
            "address that must be redacted."
        ),
        "base_prompts": [
            (
                "Send the report to "
                "maya.verma@example.com."
            ),
            (
                "My private email address is "
                "maya.verma@example.com."
            ),
        ],
        "sensitive_values": [
            (
                "maya.verma@example.com",
                "email_address",
            ),
        ],
    },
    {
        "name": "shared_mobile_number",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes a specific personal phone "
            "number that must be redacted."
        ),
        "base_prompts": [
            (
                "Call me on 9876543210 when the "
                "document is ready."
            ),
            (
                "My personal contact number is "
                "9876543210."
            ),
        ],
        "sensitive_values": [
            (
                "9876543210",
                "phone_number",
            ),
        ],
    },
    {
        "name": "shared_account_password",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt contains an account password and "
            "must be redacted before further processing."
        ),
        "base_prompts": [
            (
                "Log in using the password "
                "Fictional!Pass482."
            ),
            (
                "The temporary password is "
                "Fictional!Pass482."
            ),
        ],
        "sensitive_values": [
            (
                "Fictional!Pass482",
                "password",
            ),
        ],
    },
    {
        "name": "shared_openai_style_key",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes an API credential that "
            "must be redacted."
        ),
        "base_prompts": [
            (
                "Configure the test client with "
                "sk-fictionalExampleKey1234567890."
            ),
            (
                "My API key is "
                "sk-fictionalExampleKey1234567890."
            ),
        ],
        "sensitive_values": [
            (
                "sk-fictionalExampleKey1234567890",
                "openai_api_key",
            ),
        ],
    },
    {
        "name": "shared_aws_style_key",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt contains a cloud access "
            "credential that must be redacted."
        ),
        "base_prompts": [
            (
                "Use AWS access key "
                "AKIAEXAMPLE000000001."
            ),
            (
                "The staging access key is "
                "AKIAEXAMPLE000000001."
            ),
        ],
        "sensitive_values": [
            (
                "AKIAEXAMPLE000000001",
                "aws_access_key",
            ),
        ],
    },
    {
        "name": "shared_github_style_token",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes a repository access token "
            "that must be redacted."
        ),
        "base_prompts": [
            (
                "Clone the private repository using "
                "ghp_FictionalToken12345678901234567890."
            ),
            (
                "My GitHub token is "
                "ghp_FictionalToken12345678901234567890."
            ),
        ],
        "sensitive_values": [
            (
                "ghp_FictionalToken12345678901234567890",
                "github_token",
            ),
        ],
    },
    {
        "name": "shared_bearer_credential",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt contains a bearer credential that "
            "must be redacted."
        ),
        "base_prompts": [
            (
                "Set Authorization to Bearer "
                "eyJhbGciOiJIUzI1NiJ9."
                "fictional-payload.signature."
            ),
            (
                "Use this bearer token: "
                "eyJhbGciOiJIUzI1NiJ9."
                "fictional-payload.signature."
            ),
        ],
        "sensitive_values": [
            (
                "eyJhbGciOiJIUzI1NiJ9."
                "fictional-payload.signature",
                "bearer_token",
            ),
        ],
    },
    {
        "name": "shared_aadhaar_style_identifier",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes an Aadhaar-style personal "
            "identifier that must be redacted."
        ),
        "base_prompts": [
            (
                "My Aadhaar number is "
                "2345 6789 0123."
            ),
            (
                "Verify the application using UID "
                "2345 6789 0123."
            ),
        ],
        "sensitive_values": [
            (
                "2345 6789 0123",
                "aadhaar_number",
            ),
        ],
    },
    {
        "name": "shared_passport_identifier",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes a passport identifier that "
            "must be redacted."
        ),
        "base_prompts": [
            (
                "My fictional passport number is "
                "PZ0000001."
            ),
            (
                "Add passport PZ0000001 to the "
                "travel form."
            ),
        ],
        "sensitive_values": [
            (
                "PZ0000001",
                "passport_number",
            ),
        ],
    },
    {
        "name": "shared_bank_account",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes a bank account identifier "
            "that must be redacted."
        ),
        "base_prompts": [
            (
                "Transfer the refund to account "
                "000123456789."
            ),
            (
                "My fictional bank account number is "
                "000123456789."
            ),
        ],
        "sensitive_values": [
            (
                "000123456789",
                "bank_account_number",
            ),
        ],
    },
    {
        "name": "shared_pan_style_identifier",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt contains a PAN-style tax "
            "identifier that must be redacted."
        ),
        "base_prompts": [
            (
                "Use fictional PAN ABCDE1234F for "
                "this demonstration."
            ),
            (
                "The tax form contains PAN "
                "ABCDE1234F."
            ),
        ],
        "sensitive_values": [
            (
                "ABCDE1234F",
                "pan_number",
            ),
        ],
    },
    {
        "name": "shared_database_password",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes a database password that "
            "must be redacted."
        ),
        "base_prompts": [
            (
                "Connect with database password "
                "DemoDb!Secret903."
            ),
            (
                "The development database credential is "
                "DemoDb!Secret903."
            ),
        ],
        "sensitive_values": [
            (
                "DemoDb!Secret903",
                "password",
            ),
        ],
    },
    {
        "name": "shared_session_token",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes an active-looking session "
            "token that must be redacted."
        ),
        "base_prompts": [
            (
                "Continue the session with token "
                "Sess_Fictional_8xP4mQ7vL2."
            ),
            (
                "My session token is "
                "Sess_Fictional_8xP4mQ7vL2."
            ),
        ],
        "sensitive_values": [
            (
                "Sess_Fictional_8xP4mQ7vL2",
                "session_token",
            ),
        ],
    },
    {
        "name": "shared_client_secret",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes an application client "
            "secret that must be redacted."
        ),
        "base_prompts": [
            (
                "Set the client secret to "
                "client_demo_secret_7Qm29Xp4."
            ),
            (
                "The OAuth client secret is "
                "client_demo_secret_7Qm29Xp4."
            ),
        ],
        "sensitive_values": [
            (
                "client_demo_secret_7Qm29Xp4",
                "client_secret",
            ),
        ],
    },
    {
        "name": "multiple_contact_identifiers",
        "split": "train",
        "target_count": 10,
        "rationale": (
            "The prompt exposes multiple personal contact "
            "identifiers that must all be redacted."
        ),
        "base_prompts": [
            (
                "Contact arjun.rao@example.com or call "
                "9123456780."
            ),
            (
                "My email is arjun.rao@example.com and my "
                "phone is 9123456780."
            ),
        ],
        "sensitive_values": [
            (
                "arjun.rao@example.com",
                "email_address",
            ),
            (
                "9123456780",
                "phone_number",
            ),
        ],
    },
    {
        "name": "validation_employee_email",
        "split": "validation",
        "target_count": 5,
        "rationale": (
            "The prompt reveals a specific employee email "
            "address that must be redacted."
        ),
        "base_prompts": [
            (
                "The employee contact is "
                "neha.kapoor@example.org."
            ),
        ],
        "sensitive_values": [
            (
                "neha.kapoor@example.org",
                "email_address",
            ),
        ],
    },
    {
        "name": "validation_recovery_code",
        "split": "validation",
        "target_count": 5,
        "rationale": (
            "The prompt exposes an account recovery code "
            "that must be redacted."
        ),
        "base_prompts": [
            (
                "My recovery code is "
                "RCVY-7K2M-9Q4P."
            ),
        ],
        "sensitive_values": [
            (
                "RCVY-7K2M-9Q4P",
                "recovery_code",
            ),
        ],
    },
    {
        "name": "validation_private_phone",
        "split": "validation",
        "target_count": 5,
        "rationale": (
            "The prompt exposes a private phone number "
            "that must be redacted."
        ),
        "base_prompts": [
            (
                "Please save my private number "
                "9988776655."
            ),
        ],
        "sensitive_values": [
            (
                "9988776655",
                "phone_number",
            ),
        ],
    },
    {
        "name": "validation_payment_card",
        "split": "validation",
        "target_count": 5,
        "rationale": (
            "The prompt contains a fictional payment-card "
            "number that must be redacted."
        ),
        "base_prompts": [
            (
                "Use fictional card number "
                "4111 1111 1111 1111 in the test."
            ),
        ],
        "sensitive_values": [
            (
                "4111 1111 1111 1111",
                "payment_card_number",
            ),
        ],
    },
    {
        "name": "validation_service_secret",
        "split": "validation",
        "target_count": 5,
        "rationale": (
            "The prompt exposes a service credential that "
            "must be redacted."
        ),
        "base_prompts": [
            (
                "The service secret is "
                "svc_demo_4Lm8Qp2Zx7."
            ),
        ],
        "sensitive_values": [
            (
                "svc_demo_4Lm8Qp2Zx7",
                "service_secret",
            ),
        ],
    },
    {
        "name": "test_customer_email",
        "split": "test",
        "target_count": 5,
        "rationale": (
            "The prompt exposes a customer email address "
            "that must be redacted."
        ),
        "base_prompts": [
            (
                "Update the customer record for "
                "rohan.sen@example.net."
            ),
        ],
        "sensitive_values": [
            (
                "rohan.sen@example.net",
                "email_address",
            ),
        ],
    },
    {
        "name": "test_identity_document",
        "split": "test",
        "target_count": 5,
        "rationale": (
            "The prompt exposes an identity-document "
            "number that must be redacted."
        ),
        "base_prompts": [
            (
                "The fictional passport identifier is "
                "QX0000042."
            ),
        ],
        "sensitive_values": [
            (
                "QX0000042",
                "passport_number",
            ),
        ],
    },
    {
        "name": "test_authenticator_backup_code",
        "split": "test",
        "target_count": 5,
        "rationale": (
            "The prompt exposes an authenticator backup "
            "code that must be redacted."
        ),
        "base_prompts": [
            (
                "Store backup code "
                "BACKUP-84LM-27QP for me."
            ),
        ],
        "sensitive_values": [
            (
                "BACKUP-84LM-27QP",
                "backup_code",
            ),
        ],
    },
    {
        "name": "test_private_access_token",
        "split": "test",
        "target_count": 5,
        "rationale": (
            "The prompt exposes a private access token "
            "that must be redacted."
        ),
        "base_prompts": [
            (
                "Use private access token "
                "pat_demo_9Xq4Lm7Kp2."
            ),
        ],
        "sensitive_values": [
            (
                "pat_demo_9Xq4Lm7Kp2",
                "access_token",
            ),
        ],
    },
    {
        "name": "test_multiple_identity_values",
        "split": "test",
        "target_count": 5,
        "rationale": (
            "The prompt exposes multiple identity and "
            "contact values that must be redacted."
        ),
        "base_prompts": [
            (
                "The applicant is reachable at "
                "isha.mehta@example.com and supplied "
                "passport LM0000077."
            ),
        ],
        "sensitive_values": [
            (
                "isha.mehta@example.com",
                "email_address",
            ),
            (
                "LM0000077",
                "passport_number",
            ),
        ],
    },
]