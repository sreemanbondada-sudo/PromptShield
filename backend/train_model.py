import csv
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline


BASE_DIRECTORY = Path(__file__).parent
DATASET_PATH = BASE_DIRECTORY / "data" / "prompts.csv"
MODEL_DIRECTORY = BASE_DIRECTORY / "models"
MODEL_PATH = MODEL_DIRECTORY / "prompt_classifier.joblib"
METRICS_PATH = MODEL_DIRECTORY / "metrics.json"


def load_dataset() -> tuple[list[str], list[int]]:
    """Load prompts and binary labels from the CSV dataset."""
    prompts = []
    labels = []

    with DATASET_PATH.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as dataset_file:
        reader = csv.DictReader(dataset_file)

        for row in reader:
            prompts.append(row["prompt"])
            labels.append(int(row["label"]))

    return prompts, labels


def create_pipeline() -> Pipeline:
    """Create a TF-IDF and Logistic Regression pipeline."""
    features = FeatureUnion(
        [
            (
                "word_features",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                ),
            ),
            (
                "character_features",
                TfidfVectorizer(
                    analyzer="char_wb",
                    lowercase=True,
                    ngram_range=(3, 5),
                    sublinear_tf=True,
                ),
            ),
        ]
    )

    return Pipeline(
        [
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def train_model() -> None:
    """Train, evaluate and save the prompt classifier."""
    prompts, labels = load_dataset()

    training_prompts, testing_prompts, training_labels, testing_labels = (
        train_test_split(
            prompts,
            labels,
            test_size=0.25,
            random_state=42,
            stratify=labels,
        )
    )

    model = create_pipeline()
    model.fit(training_prompts, training_labels)

    predictions = model.predict(testing_prompts)

    metrics = {
        "dataset_size": len(prompts),
        "training_size": len(training_prompts),
        "testing_size": len(testing_prompts),
        "accuracy": accuracy_score(
            testing_labels,
            predictions,
        ),
        "confusion_matrix": confusion_matrix(
            testing_labels,
            predictions,
        ).tolist(),
        "classification_report": classification_report(
            testing_labels,
            predictions,
            target_names=["safe", "malicious"],
            output_dict=True,
            zero_division=0,
        ),
    }

    MODEL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(model, MODEL_PATH)

    METRICS_PATH.write_text(
        json.dumps(metrics, indent=4),
        encoding="utf-8",
    )

    print(f"Dataset size: {metrics['dataset_size']}")
    print(f"Training samples: {metrics['training_size']}")
    print(f"Testing samples: {metrics['testing_size']}")
    print(f"Accuracy: {metrics['accuracy']:.2%}")
    print(f"Model saved to: {MODEL_PATH}")
    print(f"Metrics saved to: {METRICS_PATH}")


if __name__ == "__main__":
    train_model()