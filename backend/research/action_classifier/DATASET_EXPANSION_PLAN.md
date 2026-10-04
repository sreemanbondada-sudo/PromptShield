# PromptShield Contextual Dataset Expansion Plan

## Objective

Expand the validated 32-record seed dataset into a balanced 800-record contextual action dataset.

The dataset will train and evaluate a candidate model that predicts:

- `allow`
- `review`
- `redact`
- `block`

The current production application remains unchanged throughout this research.

## Target Size

| Split | Allow | Review | Redact | Block | Total |
|---|---:|---:|---:|---:|---:|
| Train | 150 | 150 | 150 | 150 | 600 |
| Validation | 25 | 25 | 25 | 25 | 100 |
| Test | 25 | 25 | 25 | 25 | 100 |
| Total | 200 | 200 | 200 | 200 | 800 |

## Isolation Rules

- Research remains on `research/contextual-action-model`.
- Production files are not modified.
- Production model files are not overwritten.
- Render and Vercel continue using `main`.
- Candidate models use separate filenames.
- Candidate reports remain under the research directory.
- The final test split is not used for training or threshold selection.

## General Dataset Requirements

Every record must:

1. Use fictional information.
2. Follow `dataset_schema.json`.
3. Contain one primary expected action.
4. Include a clear rationale.
5. Belong to one semantic template group.
6. Appear in exactly one dataset split.
7. Contain accurate sensitive spans when applicable.
8. Avoid exact or normalized duplicates.
9. Avoid private or real-world credentials.
10. Avoid copying private user content.

## Semantic Diversity

The expanded dataset must include:

- Formal writing
- Informal writing
- Short commands
- Multi-sentence requests
- Questions
- Statements
- Indirect requests
- Euphemistic wording
- Minor spelling errors
- Irregular spacing
- Mixed capitalization
- Defensive and educational language
- Hypothetical framing
- Claimed authorization
- Explicit lack of authorization
- Uncertain intent
- Sensitive information in natural conversation

Punctuation-only changes do not count as meaningful diversity.

## Allow Coverage

`allow` records should cover benign, legal, educational and defensive requests.

### Allow families

- Legal travel requirements
- Passport renewal
- Lost-document assistance
- Embassy and official-authority guidance
- Defensive cybersecurity
- Prompt-injection education
- Password-policy design
- Token-storage guidance
- Authentication best practices
- Privacy education
- Data-redaction guidance
- Security incident recovery
- Compliance questions
- Secure software development
- Academic discussion of harmful behaviour
- News or policy analysis
- Explanations of why unlawful activity is harmful
- Authorized defensive testing at a high level
- General AI safety questions
- Harmless mentions of sensitive-data field names

### Allow hard negatives

Allow examples must deliberately include words also found in harmful or sensitive prompts, such as:

- passport
- password
- token
- secret
- bypass
- injection
- attack
- unauthorized
- border
- verification

The complete meaning must remain benign.

## Review Coverage

`review` records should contain genuine ambiguity.

### Review families

- Claimed testing without authorization context
- Vague requests to avoid verification
- Unexplained access requests
- Indirect requests for restricted information
- Hypothetical evasion requests
- Dual-use technical questions
- Requests with unclear ownership
- Suspicious urgency
- Euphemistic language
- Partial or incomplete harmful intent
- Quoted suspicious text with unclear purpose
- Requests to inspect possible sensitive values
- Unclear identity-verification scenarios
- Ambiguous automation requests
- Requests that could support either defence or misuse

### Review requirements

A review prompt must not be merely unfamiliar.

It must contain a real reason why both benign and harmful interpretations remain plausible.

## Redact Coverage

`redact` records must expose an actual fictional sensitive value.

### Redact families

- Email addresses
- Phone numbers
- Passwords
- Passphrases
- API keys
- Access tokens
- Bearer tokens
- Cloud access keys
- GitHub-style tokens
- Private-key markers
- Database connection URLs
- Passport identifiers
- Aadhaar identifiers
- Payment-card-shaped values
- Bank-account identifiers
- Employee identifiers
- Customer identifiers
- Session identifiers
- Recovery codes
- Secret assignments
- Multiple sensitive values in one prompt

### Redact requirements

- The exact sensitive span must be recorded.
- Span offsets must match the prompt.
- Only the value should be redacted where possible.
- A discussion about a sensitive-data type without an actual value must not be labelled `redact`.
- Fictional values should preserve realistic structure without using real credentials.

## Block Coverage

`block` records should clearly request actionable harmful, unlawful or security-bypassing assistance.

### Block families

- Prompt-instruction override
- Hidden system-instruction extraction
- Safety-control bypass
- Unauthorized authentication bypass
- Credential theft
- Session theft
- Unauthorized system access
- Account takeover
- Evasion of identity verification
- Evasion of access controls
- Unlawful-entry facilitation
- Fraud facilitation
- Phishing assistance
- Malicious impersonation
- Data theft
- Secret extraction
- Destructive system interference
- Malware-related harmful assistance
- Concealment of harmful actions
- Requests combining harmful intent with sensitive values

### Block requirements

- Harmful intent must be sufficiently clear.
- The prompt must request action or facilitation.
- Merely discussing a harmful topic is insufficient.
- Defensive, legal and recovery-oriented comparisons must exist in `allow`.
- Ambiguous cases must remain `review`.

## Contextual Comparison Groups

Each major concept should contain nearby examples with different actions.

### Travel-document group

| Meaning | Action |
|---|---|
| Legal entry requirements | `allow` |
| Lost passport assistance | `allow` |
| Actual passport identifier | `redact` |
| Unclear document-check avoidance | `review` |
| Actionable unlawful-entry request | `block` |

### Authentication group

| Meaning | Action |
|---|---|
| Secure authentication guidance | `allow` |
| Actual credential exposure | `redact` |
| Claimed bypass testing without context | `review` |
| Unauthorized bypass request | `block` |

### Prompt-security group

| Meaning | Action |
|---|---|
| Defensive prompt-injection education | `allow` |
| Quoted suspicious text for analysis | `allow` |
| Unclear request to disregard a restriction | `review` |
| Direct instruction override and extraction | `block` |

### Token group

| Meaning | Action |
|---|---|
| Token-storage best practices | `allow` |
| Actual fictional token exposure | `redact` |
| Unclear request to inspect or reuse a token | `review` |
| Request to steal or misuse another token | `block` |

## Split Construction

Semantic template families must be assigned before prompt generation.

A template group may appear in only one split.

### Training split

- Used for model fitting
- Contains the greatest variety
- Contains 600 records
- May be revised before final training

### Validation split

- Used for model selection
- Used for threshold calibration
- Contains 100 records
- Must not contain training template families

### Test split

- Used only for final evaluation
- Contains 100 records
- Must not influence feature selection
- Must not influence threshold selection
- Must not be modified in response to candidate errors

## Generation Strategy

1. Define semantic families.
2. Assign each family to one split.
3. Create multiple meaningfully different prompts per family.
4. Generate fictional sensitive values separately.
5. Calculate sensitive spans programmatically.
6. Validate every generated record.
7. Review samples manually.
8. Freeze the test split.
9. Save a generation report.
10. Record the random seed.

## Quality Checks

The validator must confirm:

- Exactly 800 records
- Exactly 200 records per action
- Expected split sizes
- Expected per-split class balance
- Valid JSON Lines
- Valid record identifiers
- Valid action values
- Valid source values
- Correct split values
- Correct sensitive-span offsets
- No overlapping sensitive spans
- No duplicate identifiers
- No normalized duplicate prompts
- No template-group leakage
- No missing rationales
- No blank prompts

## Manual Review

Before training, manually inspect samples from:

- Every action
- Every split
- Every semantic family
- Every sensitive-data type
- Every obfuscation strategy
- Every difficult comparison group

Manual review must specifically search for:

- Incorrect labels
- Unrealistic prompts
- Accidental sensitive data
- Excessive keyword shortcuts
- Near duplicates
- Weak rationales
- Overly obvious class-specific phrasing
- Harmful details beyond what is required for classification

## Baseline

The 32-record seed baseline produced:

- Accuracy: 59.38%
- Balanced accuracy: 59.38%
- Macro F1: 56.39%
- Incorrect decisions: 13

Observed weaknesses:

- Only one of eight expected block prompts was blocked.
- Six expected block prompts were reduced to review.
- One expected block prompt was allowed.
- Four expected review prompts were allowed.
- One natural-language sensitive disclosure became review.
- One benign security-related prompt became review.

These figures are diagnostic because the seed dataset is small.

## Candidate Evaluation

Every candidate must report:

- Accuracy
- Balanced accuracy
- Macro F1
- Per-action precision
- Per-action recall
- Per-action F1
- Confusion matrix
- False-block rate
- False-redaction rate
- Harmful false-allow rate
- Sensitive-data false-allow rate
- Prediction latency
- Saved-model size

## Promotion Gate

The candidate will remain isolated unless it:

1. Improves block recall substantially.
2. Improves contextual redact recall.
3. Preserves strong allow precision.
4. Handles ambiguous prompts through review.
5. Maintains an acceptable false-block rate.
6. Maintains an acceptable false-redaction rate.
7. Passes validation and untouched test evaluation.
8. Fits free-tier deployment limits.
9. Passes all existing automated tests.
10. Receives explicit approval before integration.

## Authentication Scope

The production application remains administrator-only during this research.

Normal user registration, user login and role-based access control belong to a later independent phase.