import csv
import json
from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from ml_detector import (
    DEFAULT_CLASSIFICATION_THRESHOLD,
    load_model,
)


BASE_DIRECTORY = Path(__file__).parent

CHALLENGE_DATASET_PATH = (
    BASE_DIRECTORY
    / "data"
    / "challenge_prompts.csv"
)

OUTPUT_PATH = (
    BASE_DIRECTORY
    / "models"
    / "challenge_metrics.json"
)


def load_challenge_dataset():
    """Load the independent challenge dataset."""
    prompts = []
    labels = []
    categories = []

    with CHALLENGE_DATASET_PATH.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as dataset_file:
        reader = csv.DictReader(dataset_file)

        for row in reader:
            prompts.append(row["prompt"])
            labels.append(int(row["label"]))
            categories.append(row["category"])

    return prompts, labels, categories


def evaluate_model():
    """Evaluate the model on unseen challenge prompts."""
    prompts, labels, categories = (
        load_challenge_dataset()
    )

    model = load_model()
    probabilities = model.predict_proba(prompts)

    malicious_index = list(
        model.classes_
    ).index(1)

    malicious_probabilities = [
        float(row[malicious_index])
        for row in probabilities
    ]

    predictions = [
        int(
            probability
            >= DEFAULT_CLASSIFICATION_THRESHOLD
        )
        for probability in malicious_probabilities
    ]

    incorrect_predictions = []

    for index, prediction in enumerate(predictions):
        if prediction != labels[index]:
            incorrect_predictions.append(
                {
                    "prompt": prompts[index],
                    "category": categories[index],
                    "expected_label": labels[index],
                    "predicted_label": prediction,
                    "malicious_probability": round(
                        malicious_probabilities[index],
                        4,
                    ),
                }
            )

    metrics = {
        "dataset_size": len(prompts),
        "threshold": (
            DEFAULT_CLASSIFICATION_THRESHOLD
        ),
        "accuracy": accuracy_score(
            labels,
            predictions,
        ),
        "precision": precision_score(
            labels,
            predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            labels,
            predictions,
            zero_division=0,
        ),
        "f1_score": f1_score(
            labels,
            predictions,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(
            labels,
            predictions,
        ).tolist(),
        "classification_report": classification_report(
            labels,
            predictions,
            target_names=["safe", "malicious"],
            output_dict=True,
            zero_division=0,
        ),
        "incorrect_predictions": incorrect_predictions,
    }

    OUTPUT_PATH.write_text(
        json.dumps(metrics, indent=4),
        encoding="utf-8",
    )

    print(f"Challenge samples: {metrics['dataset_size']}")

    print(
        f"Threshold: {metrics['threshold']:.2f}"
    )

    print(f"Accuracy: {metrics['accuracy']:.2%}")
    print(f"Precision: {metrics['precision']:.2%}")
    print(f"Recall: {metrics['recall']:.2%}")
    print(f"F1 score: {metrics['f1_score']:.2%}")

    print(
        "Incorrect predictions: "
        f"{len(incorrect_predictions)}"
    )

    print(f"Metrics saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    evaluate_model()
    