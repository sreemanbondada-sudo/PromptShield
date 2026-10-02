# PromptShield Dataset Sources

## Purpose

PromptShield uses labelled prompt data to train and evaluate
an advisory binary classifier:

- `0`: benign prompt
- `1`: malicious prompt injection or jailbreak

Machine-learning output does not independently block requests.
An ML-only detection recommends manual review.

## Local Baseline Dataset

### PromptShield manually constructed baseline

- File: `backend/data/prompts.csv`
- Rows: 80
- Benign rows: 40
- Malicious rows: 40
- Categories:
  - safe
  - prompt_injection
  - system_prompt_extraction
  - jailbreak
  - role_manipulation
- Purpose: initial development and regression testing
- Limitation: small size and manually constructed wording

### PromptShield challenge set

- File: `backend/data/challenge_prompts.csv`
- Rows: 20
- Purpose: early false-positive and false-negative evaluation
- Limitation: too small to represent production performance

## External Source 1

### deepset/prompt-injections

- Publisher: deepset
- Repository:
  `https://huggingface.co/datasets/deepset/prompt-injections`
- Licence: Apache License 2.0
- Format: prompt text and binary label
- Published splits: train and test
- Planned use: independent external benchmark
- Data rule: preserve the official test split
- Attribution: retain the publisher, URL and licence

## External Source 2

### neuralchemy/Prompt-injection-dataset

- Publisher: NeurAlchemy
- Repository:
  `https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset`
- Configuration: `core`
- Licence: Apache License 2.0
- Fields:
  - text
  - label
  - category
  - source
  - severity
  - group identifier
  - augmentation indicator
  - tags
- Published splits:
  - train
  - validation
  - test
- Planned use: expanded classical ML dataset
- Data rule: preserve official group-aware splits
- Attribution: retain the publisher, URL and licence

## Normalized Schema

Imported records will use these fields:

| Field | Purpose |
|---|---|
| `prompt` | Prompt text |
| `label` | `0` for benign or `1` for malicious |
| `category` | Benign or attack category |
| `source_dataset` | Original dataset |
| `original_split` | Original train, validation or test split |
| `group_id` | Identifier connecting related variants |
| `is_augmented` | Whether the record is synthetic |
| `prompt_hash` | Normalized duplicate-detection hash |

## Dataset Quality Rules

PromptShield dataset processing must:

1. Preserve official train, validation and test splits.
2. Never train on external test records.
3. Remove blank and malformed records.
4. Remove exact duplicates within each split.
5. Detect overlap between different splits.
6. Preserve source and category metadata.
7. Keep related groups within the same split.
8. Avoid data with unclear usage rights.
9. Report class and category distributions.
10. Keep machine-learning output advisory.

## Leakage Prevention

Prompts or closely related variants must not occur in both
training and evaluation data.

Where group identifiers exist, every record from one group must
remain in the same split.

The original PromptShield challenge set remains separate from
training data.

## Limitations

Public prompt-security datasets can contain:

- Incorrect labels
- Duplicate prompts
- Synthetic examples
- Offensive or unsafe text
- Unclear category boundaries
- Wording shortcuts that inflate performance

Imported data must be validated before model training.