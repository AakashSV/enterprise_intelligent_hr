import os
import json
import numpy as np
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    classification_report, confusion_matrix
)
from backend.app.ml.predict import MLScoringEngine
from backend.app.ml.train_model import get_training_dataset


def run_benchmark():
    print("=" * 70)
    print("[BENCHMARK] MICHELLE HR: MSC DATA SCIENCE MODEL EVALUATION BENCHMARK")
    print("=" * 70)

    engine = MLScoringEngine.get_instance()
    samples = get_training_dataset()

    y_true_scores = []
    y_pred_scores = []

    y_true_classes = []
    y_pred_classes = []

    label_to_class = {
        3: "Strong Hire",
        2: "Hire",
        1: "Review Required",
        0: "Reject"
    }

    for s in samples:
        res = engine.evaluate_candidate(
            job_desc=s["jd"],
            resume_input=s["resume"]
        )

        y_true_scores.append(s["score"])
        y_pred_scores.append(res["overall_score"])

        y_true_classes.append(label_to_class[s["label"]])
        y_pred_classes.append(res["recommendation"])

    # 1. Regressor Metrics
    mae = mean_absolute_error(y_true_scores, y_pred_scores)
    rmse = np.sqrt(mean_squared_error(y_true_scores, y_pred_scores))
    r2 = r2_score(y_true_scores, y_pred_scores)

    print("\n[METRICS] 1. CONTINUOUS MATCH REGRESSOR (GradientBoostingRegressor):")
    print(f"  * Mean Absolute Error (MAE):    {mae:.2f} points (scale 0-100)")
    print(f"  * Root Mean Squared Error (RMSE): {rmse:.2f}")
    print(f"  * Coefficient of Determination (R^2): {r2:.3f}")

    # 2. Classifier Metrics
    labels = ["Strong Hire", "Hire", "Review Required", "Reject"]
    cm = confusion_matrix(y_true_classes, y_pred_classes, labels=labels)
    report = classification_report(y_true_classes, y_pred_classes, labels=labels, zero_division=0)

    print("\n[METRICS] 2. DECISION CLASSIFIER (RandomForestClassifier):")
    print(report)

    print("[METRICS] 3. CONFUSION MATRIX (Rows: True, Columns: Predicted):")
    header = f"{'':18}" + "".join([f"{l[:10]:>12}" for l in labels])
    print(header)
    for idx, row in enumerate(cm):
        row_str = f"{labels[idx]:18}" + "".join([f"{val:>12}" for val in row])
        print(row_str)

    # 3. Feature Importance Analysis
    feat_names = [
        "Global Semantic Similarity (Transformer)",
        "Work Experience Relevance",
        "Technical Skills Alignment",
        "Summary Alignment",
        "Token Vocabulary Jaccard",
        "Length / Density Ratio"
    ]
    importances = engine.classifier.feature_importances_
    indices = np.argsort(importances)[::-1]

    print("\n[ATTRIBUTION] 4. FEATURE ATTRIBUTION (Mean Decrease in Impurity):")
    for rank, i in enumerate(indices):
        print(f"  {rank+1}. {feat_names[i]:<45}: {importances[i]*100:.2f}%")

    # Save to Markdown Report for Thesis
    os.makedirs("docs", exist_ok=True)
    report_path = "docs/MODEL_BENCHMARK_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# MSc Thesis Evaluation: Michelle HR Model Performance\n\n")
        f.write("## 1. Continuous Match Regressor (GradientBoosting)\n")
        f.write(f"- **Mean Absolute Error (MAE):** `{mae:.2f}`\n")
        f.write(f"- **Root Mean Squared Error (RMSE):** `{rmse:.2f}`\n")
        f.write(f"- **$R^2$ Score:** `{r2:.3f}`\n\n")
        f.write("## 2. Decision Classifier Performance (Random Forest)\n")
        f.write("```text\n")
        f.write(report)
        f.write("\n```\n\n")
        f.write("## 3. Feature Importance Breakdown\n\n")
        f.write("| Rank | Feature Metric | Contribution Weight |\n")
        f.write("| :---: | :--- | :---: |\n")
        for rank, i in enumerate(indices):
            f.write(f"| {rank+1} | {feat_names[i]} | {importances[i]*100:.2f}% |\n")

    print(f"\n[SUCCESS] Generated comprehensive thesis report: {report_path}")


if __name__ == "__main__":
    run_benchmark()
