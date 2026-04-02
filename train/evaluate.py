"""
CropSentinel AI  -  train/evaluate.py
Full evaluation script: runs inference on the validation set, prints a
per-class report, shows the top-5 confused pairs, and saves a confusion
matrix heatmap PNG.
"""

import json
import sys

import numpy as np

sys.path.insert(0, ".")

import matplotlib
matplotlib.use("Agg")   # non-interactive backend  -  safe for server environments
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report

from model.predictor        import CropDiseasePredictor
from model.trainer          import ModelTrainer
from utils.metrics_tracker  import MetricsTracker


def run_evaluation():
    print("Loading model and dataset...")

    try:
        with open("model/classes.json", "r") as f:
            class_names = json.load(f)
    except FileNotFoundError:
        print("[ERROR] model/classes.json not found. Run training first.")
        sys.exit(1)

    trainer = ModelTrainer(
        dataset_path=r"C:\Users\Rohith\OneDrive\Desktop\dataset\plantvillage_dataset\color",
        num_workers=0,
    )
    try:
        _, val_loader, _ = trainer._load_dataset()
    except Exception as e:
        print(f"[ERROR] Could not load dataset: {e}")
        sys.exit(1)

    try:
        predictor = CropDiseasePredictor()
    except Exception as e:
        print(f"[ERROR] Could not load predictor: {e}")
        sys.exit(1)

    tracker = MetricsTracker()
    print("Running inference on validation set...")
    try:
        metrics = tracker.compute_and_save(
            predictor.model, val_loader, class_names, predictor.device
        )
    except Exception as e:
        print(f"[ERROR] Evaluation failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("  EVALUATION RESULTS  -  CropSentinel AI")
    print("=" * 65)
    print(f"  Macro F1        : {metrics['macro_f1']*100:.2f}%")
    print(f"  Macro Precision : {metrics['macro_precision']*100:.2f}%")
    print(f"  Macro Recall    : {metrics['macro_recall']*100:.2f}%")
    print(f"  Accuracy        : {metrics['accuracy']*100:.2f}%")
    print(f"  Total Classes   : {metrics['num_classes']}")
    print("=" * 65)

    print("\nPER-CLASS RESULTS (sorted by F1, worst first):\n")
    per_class = metrics["per_class"]
    sorted_classes = sorted(per_class.items(), key=lambda x: x[1]["f1"])
    print(
        f"{'Class':<45} {'Precision':>10} {'Recall':>8} {'F1':>8} {'Support':>9}"
    )
    print("-" * 85)
    for name, vals in sorted_classes:
        print(
            f"{name:<45} "
            f"{vals['precision']*100:>9.1f}% "
            f"{vals['recall']*100:>7.1f}% "
            f"{vals['f1']*100:>7.1f}% "
            f"{vals['support']:>9}"
        )

    print("\nFinding most confused class pairs...")
    cm = np.array(metrics["confusion_matrix"])
    cm_no_diag = cm.copy()
    np.fill_diagonal(cm_no_diag, 0)

    confused_pairs = []
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            if i != j and cm_no_diag[i][j] > 0:
                confused_pairs.append((int(cm_no_diag[i][j]), class_names[i], class_names[j]))
    confused_pairs.sort(reverse=True)

    print("\nTOP 5 CONFUSED PAIRS:")
    print("-" * 65)
    for count, actual, predicted in confused_pairs[:5]:
        print(f"  {count:>4}x  '{actual}'")
        print(f"         misclassified as '{predicted}'")
        print()

    print("Generating confusion matrix plot...")
    try:
        fig, ax = plt.subplots(figsize=(22, 18))
        short_names = [
            n.replace("___", "\n").replace("_", " ") for n in class_names
        ]
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Greens",
            xticklabels=short_names,
            yticklabels=short_names,
            ax=ax,
            linewidths=0.3,
            cbar_kws={"label": "Predictions"},
        )
        ax.set_xlabel("Predicted Label", fontsize=13)
        ax.set_ylabel("True Label",      fontsize=13)
        ax.set_title(
            "CropSentinel AI  -  Confusion Matrix\nEnterprise 2026",
            fontsize=15,
            fontweight="bold",
        )
        plt.xticks(rotation=45, ha="right", fontsize=7)
        plt.yticks(rotation=0,  fontsize=7)
        plt.tight_layout()
        output_path = "model/confusion_matrix.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: {output_path}")
    except Exception as e:
        print(f"  [WARNING] Could not save confusion matrix plot: {e}")

    print("\n" + "=" * 65)
    print("  Evaluation complete.")
    print("  Open model/confusion_matrix.png to view the full matrix.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    run_evaluation()
