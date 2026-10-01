import pytest

from sensitive_detector import (
    calculate_entropy,
    detect_sensitive_data,
)


@pytest.mark.parametrize(
    ("text", "expected_type"),
    [
        (
            "Contact me at student@example.com",
            "email_address",
        ),
        (
            "My number is 9876543210",
            "phone_number",
        ),
        (
            "API key: sk-abcdefghijklmnopqrstuvwxyz1234567890",
            "openai_api_key",
        ),
        (
            "AWS key: AKIA1234567890ABCDEF",
            "aws_access_key",
        ),
        (
            "password=MySecretPassword123",
            "password_assignment",
        ),
        (
            "api_key=VerySecretValue12345",
            "secret_assignment",
        ),
        (
            "-----BEGIN PRIVATE KEY-----",
            "private_key",
        ),
    ],
)
def test_known_sensitive_values_are_detected(text, expected_type):
    result = detect_sensitive_data(text)
    detected_types = [
        finding["type"]
        for finding in result["findings"]
    ]

    assert result["contains_sensitive_data"] is True
    assert expected_type in detected_types
    assert "[REDACTED]" in result["redacted_text"]


def test_high_entropy_secret_is_detected():
    text = "Token: aB3dE5fG7hJ9kL2mN4pQ6rS8"

    result = detect_sensitive_data(text)
    detected_types = [
        finding["type"]
        for finding in result["findings"]
    ]

    assert "high_entropy_secret" in detected_types
    assert "[REDACTED]" in result["redacted_text"]


@pytest.mark.parametrize(
    "text",
    [
        "Explain how encryption works.",
        "This is an ordinary sentence.",
        "thisisalongordinarywordwithoutnumbers",
        "The project deadline is tomorrow.",
    ],
)
def test_safe_text_is_not_redacted(text):
    result = detect_sensitive_data(text)

    assert result["contains_sensitive_data"] is False
    assert result["findings"] == []
    assert result["redacted_text"] == text


def test_random_text_has_higher_entropy():
    repeated_text_entropy = calculate_entropy("aaaaaaaaaaaaaaaaaaaa")
    random_text_entropy = calculate_entropy("aB3dE5fG7hJ9kL2mN4pQ")

    assert random_text_entropy > repeated_text_entropy