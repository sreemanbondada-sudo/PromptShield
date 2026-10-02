from pathlib import Path

import joblib


DEFAULT_MODEL_PATH = (
    Path(__file__).parent
    / "models"
    / "prompt_classifier.joblib"
)
DEFAULT_CLASSIFICATION_THRESHOLD = 0.55

_model = None


def load_model(
    model_path: Path = DEFAULT_MODEL_PATH,
):
    """Load the locally generated trusted ML model."""
    global _model

    if _model is None:
        if not model_path.exists():
            raise RuntimeError(
                "The prompt-classification model was not found. "
                "Run python train_model.py first."
            )

        _model = joblib.load(model_path)

    return _model


def analyze_prompt_with_ml(
    prompt: str,
    threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
) -> dict:
    """Predict whether a prompt is malicious."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(
            "The classification threshold must be "
            "between 0.0 and 1.0."
        )

    model = load_model()

    probabilities = model.predict_proba([prompt])[0]
    malicious_class_index = list(
        model.classes_
    ).index(1)

    malicious_probability = float(
        probabilities[malicious_class_index]
    )

    return {
        "is_malicious": (
            malicious_probability >= threshold
        ),
        "malicious_probability": round(
            malicious_probability,
            4,
        ),
        "threshold": threshold,
        "model_type": "TF-IDF Logistic Regression",
    }