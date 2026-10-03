import csv
import json
import random
import re
from pathlib import Path

from datasets import load_dataset


BASE_DIRECTORY = Path(__file__).parent
OUTPUT_DIRECTORY = BASE_DIRECTORY / "data" / "external"

DATASET_NAME = "shaw/scambench-training"
RANDOM_SEED = 42
MAX_PROMPT_LENGTH = 5000

SPLIT_TARGETS = {
    "train": {
        0: 4000,
        1: 4000,
    },
    "validation": {
        0: 500,
        1: 500,
    },
    "test": {
        0: 750,
        1: 750,
    },
}


def normalize_prompt(prompt: str) -> str:
    """Normalize text for duplicate detection."""
    return re.sub(
        r"\s+",
        " ",
        prompt,
    ).strip().casefold()


def extract_user_prompt(messages_value) -> tuple[str, int]:
    """Extract and join only user messages."""
    if isinstance(messages_value, str):
        try:
            messages = json.loads(messages_value)
        except json.JSONDecodeError:
            return "", 0
    elif isinstance(messages_value, list):
        messages = messages_value
    else:
        return "", 0

    user_messages = []

    for message in messages:
        if not isinstance(message, dict):
            continue

        if message.get("role") != "user":
            continue

        content = message.get("content")

        if not isinstance(content, str):
            continue

        cleaned_content = re.sub(
            r"\s+",
            " ",
            content,
        ).strip()

        if cleaned_content:
            user_messages.append(cleaned_content)

    if not user_messages:
        return "", 0

    combined_prompt = " [USER TURN] ".join(
        user_messages
    )

    if len(combined_prompt) > MAX_PROMPT_LENGTH:
        combined_prompt = combined_prompt[
            -MAX_PROMPT_LENGTH:
        ]

    return combined_prompt, len(user_messages)


def build_record(row: dict) -> dict | None:
    """Convert one ScamBench record to PromptShield format."""
    if row.get("language") != "en":
        return None

    prompt, conversation_turns = extract_user_prompt(
        row.get("messages")
    )

    if not prompt:
        return None

    label = int(
        bool(row.get("should_trigger_scam_defense"))
    )

    category = row.get("scenario_category")

    if not isinstance(category, str) or not category.strip():
        category = (
            "scambench_attack"
            if label == 1
            else "legitimate"
        )

    return {
        "prompt": prompt,
        "label": label,
        "category": category.strip(),
        "source": "shaw/scambench-training",
        "language": "en",
        "conversation_turns": conversation_turns,
    }


def sample_split(
    split_name: str,
    targets: dict[int, int],
    excluded_fingerprints: set[str],
) -> tuple[list[dict], dict]:
    """Create a deterministic balanced sample from one split."""
    print(f"Streaming ScamBench {split_name} split...")

    dataset = load_dataset(
        DATASET_NAME,
        split=split_name,
        streaming=True,
    )

    random_generator = random.Random(
        f"{RANDOM_SEED}-{split_name}"
    )

    reservoirs = {
        0: [],
        1: [],
    }

    eligible_counts = {
        0: 0,
        1: 0,
    }

    split_fingerprints = set()

    for row in dataset:
        record = build_record(row)

        if record is None:
            continue

        label = record["label"]
        fingerprint = normalize_prompt(
            record["prompt"]
        )

        if not fingerprint:
            continue

        if fingerprint in excluded_fingerprints:
            continue

        if fingerprint in split_fingerprints:
            continue

        split_fingerprints.add(fingerprint)
        eligible_counts[label] += 1

        target_size = targets[label]
        reservoir = reservoirs[label]

        if len(reservoir) < target_size:
            reservoir.append(record)
            continue

        replacement_index = random_generator.randrange(
            eligible_counts[label]
        )

        if replacement_index < target_size:
            reservoir[replacement_index] = record

    selected_records = (
        reservoirs[0] + reservoirs[1]
    )

    random_generator.shuffle(selected_records)

    selected_fingerprints = {
        normalize_prompt(record["prompt"])
        for record in selected_records
    }

    report = {
        "split": split_name,
        "eligible_safe_records": eligible_counts[0],
        "eligible_attack_records": eligible_counts[1],
        "selected_safe_records": len(reservoirs[0]),
        "selected_attack_records": len(reservoirs[1]),
        "selected_total": len(selected_records),
    }

    return (
        selected_records,
        {
            "report": report,
            "fingerprints": selected_fingerprints,
        },
    )


def write_csv(
    split_name: str,
    records: list[dict],
) -> Path:
    """Write normalized records to a CSV file."""
    output_path = (
        OUTPUT_DIRECTORY
        / f"scambench_{split_name}.csv"
    )

    with output_path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=[
                "prompt",
                "label",
                "category",
                "source",
                "language",
                "conversation_turns",
            ],
        )

        writer.writeheader()
        writer.writerows(records)

    return output_path


def prepare_scambench_dataset() -> None:
    """Prepare controlled ScamBench training and test data."""
    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    global_fingerprints = set()
    reports = {}

    for split_name in (
        "train",
        "validation",
        "test",
    ):
        records, result = sample_split(
            split_name=split_name,
            targets=SPLIT_TARGETS[split_name],
            excluded_fingerprints=(
                global_fingerprints
            ),
        )

        output_path = write_csv(
            split_name=split_name,
            records=records,
        )

        global_fingerprints.update(
            result["fingerprints"]
        )

        reports[split_name] = result["report"]

        print(
            f"{split_name}: "
            f"{len(records)} records saved to "
            f"{output_path}"
        )

    report_path = (
        OUTPUT_DIRECTORY
        / "scambench_preparation_report.json"
    )

    report = {
        "dataset": DATASET_NAME,
        "language": "en",
        "random_seed": RANDOM_SEED,
        "maximum_prompt_length": (
            MAX_PROMPT_LENGTH
        ),
        "extraction_policy": (
            "Only user-role messages are joined. "
            "System prompts, assistant responses and "
            "reasoning traces are excluded."
        ),
        "splits": reports,
        "cross_split_duplicate_policy": (
            "Normalized prompts selected for an earlier "
            "split are excluded from later splits."
        ),
    }

    report_path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )

    print(
        "ScamBench preparation report saved to: "
        f"{report_path}"
    )


if __name__ == "__main__":
    prepare_scambench_dataset()