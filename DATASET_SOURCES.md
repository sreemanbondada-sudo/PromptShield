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

## ScamBench Training Corpus

- Repository: [shaw/scambench-training](https://huggingface.co/datasets/shaw/scambench-training)
- Licence: CC BY-SA 4.0
- Intended purpose: multilingual scam, social-engineering, phishing, prompt-injection and agent-safety research
- Upstream size: 37,423 multi-turn records
- PromptShield usage: experimental candidate-model research only
- Production status: not promoted

### Prepared PromptShield subset

PromptShield prepares a controlled English subset using `backend/prepare_scambench_dataset.py`.

| Split | Safe | Malicious | Total |
|---|---:|---:|---:|
| Train | 4,000 | 4,000 | 8,000 |
| Validation | 500 | 500 | 1,000 |
| Test | 750 | 750 | 1,500 |
| **Total** | **5,250** | **5,250** | **10,500** |

The preparation process:

- preserves the upstream train, validation and test boundaries;
- selects English-language records;
- extracts only messages with the `user` role;
- excludes system prompts, assistant responses and reasoning traces;
- joins multi-turn user messages using `[USER TURN]`;
- limits prompts to the application's 5,000-character input boundary;
- creates balanced safe and malicious subsets;
- removes normalized duplicates across selected splits;
- uses a deterministic random seed;
- records preparation metadata in `scambench_preparation_report.json`.

Validation confirmed:

- all required columns are present;
- labels are binary and balanced;
- every record contains at least one user turn;
- prompts remain within the configured length limit;
- no selected prompts overlap across ScamBench splits;
- no exact overlaps exist with PromptShield, deepset or NeurAlchemy datasets.

### Licence notice

The normalized ScamBench CSV files are adapted from the ScamBench Training Corpus and remain subject to the Creative Commons Attribution-ShareAlike 4.0 licence.

The preparation and evaluation scripts are part of the PromptShield source code. The dataset content retains its upstream attribution and applicable share-alike terms.

### Experimental result

A separate ScamBench candidate was trained with approximately 12,944 combined records. It improved scam and social-engineering coverage but was not promoted because no evaluated single-model or ensemble configuration improved all established PromptShield evaluation sets without increasing false positives.

The current production model remains unchanged.

## Guardian0369 Prompt-injection-and-PII

- Source: https://huggingface.co/datasets/Guardian0369/Prompt-injection-and-PII
- Current status: Under review
- Reported size: 2,139 synthetic examples
- Language: English
- Relevant content:
  - Normal prompts
  - Prompt-injection examples
  - PII and document examples
  - Developer-secret examples
  - Hard-negative examples
- License status: Listed as `other`; redistribution and training permissions require clarification.
- Schema status: Dataset files do not all use the same columns.
- Security consideration: Examples may contain synthetic credentials, personal information and reasoning traces.
- Production decision: Not included in PromptShield training until licensing, schema mapping, sanitization and split integrity are verified.
### Guardian0369 technical review

A privacy-safe metadata and schema inspection was completed against repository revision:

```text
4fbd7338a757c6c6b61311a7eb997b3ef7edcae1