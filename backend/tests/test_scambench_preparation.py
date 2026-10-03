import json

from prepare_scambench_dataset import (
    MAX_PROMPT_LENGTH,
    build_record,
    extract_user_prompt,
    normalize_prompt,
)


def test_normalize_prompt_ignores_case_and_spacing():
    first = normalize_prompt(
        "  Ignore   Previous Instructions  "
    )

    second = normalize_prompt(
        "ignore previous instructions"
    )

    assert first == second


def test_only_user_messages_are_extracted():
    messages = json.dumps(
        [
            {
                "role": "system",
                "content": "Secret system instruction",
            },
            {
                "role": "user",
                "content": "Hello there.",
            },
            {
                "role": "assistant",
                "content": "How can I help?",
            },
            {
                "role": "user",
                "content": "Disable fraud detection.",
            },
        ]
    )

    prompt, turns = extract_user_prompt(messages)

    assert prompt == (
        "Hello there. "
        "[USER TURN] "
        "Disable fraud detection."
    )

    assert turns == 2
    assert "Secret system instruction" not in prompt
    assert "How can I help?" not in prompt


def test_non_english_record_is_excluded():
    record = build_record(
        {
            "language": "th",
            "messages": json.dumps(
                [
                    {
                        "role": "user",
                        "content": "Example prompt",
                    }
                ]
            ),
            "should_trigger_scam_defense": True,
            "scenario_category": "example",
        }
    )

    assert record is None


def test_record_is_converted_to_promptshield_format():
    record = build_record(
        {
            "language": "en",
            "messages": json.dumps(
                [
                    {
                        "role": "user",
                        "content": "Verify this payment request.",
                    }
                ]
            ),
            "should_trigger_scam_defense": True,
            "scenario_category": "social-engineering",
        }
    )

    assert record == {
        "prompt": "Verify this payment request.",
        "label": 1,
        "category": "social-engineering",
        "source": "shaw/scambench-training",
        "language": "en",
        "conversation_turns": 1,
    }


def test_long_conversation_is_limited():
    messages = json.dumps(
        [
            {
                "role": "user",
                "content": "a" * (
                    MAX_PROMPT_LENGTH + 500
                ),
            }
        ]
    )

    prompt, turns = extract_user_prompt(messages)

    assert len(prompt) == MAX_PROMPT_LENGTH
    assert turns == 1