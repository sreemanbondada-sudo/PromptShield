# PromptShield

PromptShield is an explainable security gateway that analyzes user prompts before they reach an AI application. It combines deterministic security rules, sensitive-data detection, machine learning, cryptographic protection and tamper-evident logging.

## Project Status

The backend security foundation is operational.

- 85 automated tests passing
- Hybrid rule-based and ML detection
- Sensitive-data detection and redaction
- HMAC-SHA-256 integrity verification
- AES-256-GCM encrypted storage
- Tamper-evident SQLite audit chain
- Independent ML challenge evaluation
- React dashboard planned

## Features

### Prompt attack detection

PromptShield detects patterns associated with:

- Prompt injection
- Jailbreak attempts
- System-prompt extraction
- Role manipulation

The rule engine returns:

- Attack category
- Risk score and level
- Matched patterns
- Human-readable explanation
- Recommended action

### Sensitive-data protection

The sensitive-data detector recognizes:

- Email addresses
- Phone numbers
- API keys
- AWS access keys
- Private-key indicators
- Password and secret assignments
- High-entropy secret-like strings

Sensitive values are replaced with `[REDACTED]`.

### Hybrid machine-learning detection

PromptShield includes a TF-IDF and Logistic Regression classifier using:

- Word n-grams
- Character n-grams
- Balanced classification weights

The main `/analyze` endpoint combines deterministic rules and machine-learning output.

Decision priority:

1. Rule-based attack: `block`
2. Sensitive data: `redact`
3. ML-only suspicion: `review`
4. No detection: `allow`

The ML model is advisory because the current dataset is still small.

### ML evaluation

Current development datasets:

- 80 labelled training and development prompts
- 20 independent challenge prompts
- Provisional classification threshold: `0.55`

Current challenge-set results:

- Accuracy: 90.00%
- Precision: 83.33%
- Recall: 100.00%
- F1 score: 90.91%

These results represent an early validation baseline and should not be interpreted as production-level performance.

### HMAC integrity verification

PromptShield uses HMAC-SHA-256 to verify that trusted messages and system prompts have not been modified.

Signature verification uses constant-time comparison to reduce timing-attack risk.

### AES-GCM protected storage

Redacted prompt previews are encrypted using AES-256-GCM before being stored in SQLite.

The protected-storage design provides:

- Confidentiality
- Ciphertext integrity
- Random nonce generation
- Event-specific authenticated context
- Detection of modified ciphertext
- Protection against ciphertext swapping

Original sensitive values are not stored. There is intentionally no public decryption endpoint.

### Tamper-evident audit chain

Every security event contains:

- The previous event hash
- Its own HMAC-SHA-256 event hash

Changing or rearranging protected event data breaks the chain and can be detected through the audit-verification API.

### Privacy-aware event storage

PromptShield stores security metadata such as:

- Risk level and score
- Attack category
- Recommended action
- Matched rule names
- Detected sensitive-data types
- Prompt length
- Audit hashes

It does not store the original unredacted prompt.

## Architecture

```mermaid
flowchart TD
    A[User prompt] --> B[FastAPI gateway]
    B --> C[Rule engine]
    B --> D[Sensitive-data detector]
    B --> E[ML classifier]
    C --> F[Hybrid decision engine]
    D --> F
    E --> F
    F --> G[Allow, review, redact or block]
    F --> H[Audit event]
    H --> I[HMAC hash chain]
    F --> J[Redacted preview]
    J --> K[AES-GCM encryption]
    I --> L[SQLite]
    K --> L
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Application status |
| GET | `/health` | Health check |
| POST | `/analyze` | Hybrid prompt and sensitive-data analysis |
| POST | `/ml/analyze` | Standalone ML classification |
| GET | `/events` | Recent security events |
| GET | `/statistics` | Security statistics |
| POST | `/integrity/verify` | HMAC-SHA-256 verification |
| GET | `/audit/verify` | Audit-chain verification |

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Technology Stack

### Implemented

- Python
- FastAPI
- Pydantic
- SQLite
- scikit-learn
- pytest
- HMAC-SHA-256
- AES-256-GCM
- python-dotenv

### Planned

- React
- Vite
- GitHub Actions
- Cloud deployment

## Project Structure

```text
PromptShield/
├── backend/
│   ├── data/
│   │   ├── prompts.csv
│   │   └── challenge_prompts.csv
│   ├── models/
│   │   ├── prompt_classifier.joblib
│   │   ├── metrics.json
│   │   └── challenge_metrics.json
│   ├── tests/
│   ├── audit_service.py
│   ├── database.py
│   ├── detector.py
│   ├── encryption_service.py
│   ├── evaluate_model.py
│   ├── evaluate_thresholds.py
│   ├── integrity_service.py
│   ├── main.py
│   ├── ml_detector.py
│   ├── schemas.py
│   ├── sensitive_detector.py
│   ├── train_model.py
│   └── requirements.txt
├── .gitignore
└── README.md
```

## Local Setup

### 1. Clone the repository

```powershell
git clone https://github.com/sreemanbondada-sudo/PromptShield.git
cd PromptShield\backend
```

### 2. Create a virtual environment

```powershell
py -m venv .venv
```

Activate it in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create `backend/.env` based on `.env.example`.

Generate an HMAC key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Generate a Base64-encoded AES-256 key:

```powershell
python -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Add them to `.env`:

```env
PROMPTSHIELD_HMAC_KEY=your-private-hmac-key
PROMPTSHIELD_AES_KEY=your-base64-encoded-aes-key
```

Never commit `.env` or share its secret values.

### 5. Train the ML model

```powershell
python train_model.py
```

### 6. Evaluate the model

```powershell
python evaluate_model.py
python evaluate_thresholds.py
```

### 7. Run the tests

Run tests from the `backend` directory:

```powershell
python -m pytest -v
```

### 8. Start the API

```powershell
python -m uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Security Limitations

PromptShield is currently an academic and portfolio project.

Current limitations include:

- Small, manually constructed ML datasets
- No user authentication or authorization
- No API rate limiting
- No production key-management service
- No public encrypted-preview retrieval workflow
- SQLite is intended for local development
- Detection rules require continued evaluation against new attacks

Do not use the current version as the only security control protecting a production AI system.

## Testing

The test suite covers:

- Rule-based attack detection
- Safe-prompt handling
- Sensitive-data detection
- Secret redaction
- Entropy analysis
- FastAPI endpoints
- SQLite storage and statistics
- HMAC generation and verification
- AES-GCM encryption and decryption
- Ciphertext tampering
- Ciphertext-swapping protection
- Audit-chain verification
- ML inference
- Hybrid decision priority
- Temporary test-database isolation

Current result:

```text
85 passed
```

## Roadmap

- Expand and diversify the ML datasets
- Add stronger final holdout evaluation
- Add configuration validation
- Configure CORS
- Add API authentication and authorization
- Add rate limiting
- Build the React security dashboard
- Add GitHub Actions continuous integration
- Deploy the backend and frontend
- Add screenshots and demonstration material

## Author

Sreeman Bondada