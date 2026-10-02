from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from evaluate_model import load_challenge_dataset
from ml_detector import load_model


THRESHOLDS = [
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
]


def evaluate_thresholds():
    """Compare classification thresholds."""
    prompts, labels, _ = load_challenge_dataset()
    model = load_model()

    probabilities = model.predict_proba(prompts)

    malicious_index = list(
        model.classes_
    ).index(1)

    malicious_probabilities = [
        float(row[malicious_index])
        for row in probabilities
    ]

    print(
        "Threshold | Accuracy | Precision | "
        "Recall | F1"
    )

    print("-" * 56)

    for threshold in THRESHOLDS:
        predictions = [
            int(probability >= threshold)
            for probability in malicious_probabilities
        ]

        accuracy = accuracy_score(
            labels,
            predictions,
        )

        precision = precision_score(
            labels,
            predictions,
            zero_division=0,
        )

        recall = recall_score(
            labels,
            predictions,
            zero_division=0,
        )

        f1 = f1_score(
            labels,
            predictions,
            zero_division=0,
        )

        print(
            f"{threshold:9.2f} | "
            f"{accuracy:8.2%} | "
            f"{precision:9.2%} | "
            f"{recall:6.2%} | "
            f"{f1:6.2%}"
        )


if __name__ == "__main__":
    evaluate_thresholds()