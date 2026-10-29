# MSc Thesis Evaluation: Michelle HR Model Performance

## 1. Continuous Match Regressor (GradientBoosting)
- **Mean Absolute Error (MAE):** `0.00`
- **Root Mean Squared Error (RMSE):** `0.00`
- **$R^2$ Score:** `1.000`

## 2. Decision Classifier Performance (Random Forest)
```text
                 precision    recall  f1-score   support

    Strong Hire       1.00      1.00      1.00         3
           Hire       1.00      1.00      1.00         1
Review Required       1.00      1.00      1.00         1
         Reject       1.00      1.00      1.00         1

       accuracy                           1.00         6
      macro avg       1.00      1.00      1.00         6
   weighted avg       1.00      1.00      1.00         6

```

## 3. Feature Importance Breakdown

| Rank | Feature Metric | Contribution Weight |
| :---: | :--- | :---: |
| 1 | Token Vocabulary Jaccard | 40.11% |
| 2 | Global Semantic Similarity (Transformer) | 36.47% |
| 3 | Length / Density Ratio | 23.42% |
| 4 | Summary Alignment | 0.00% |
| 5 | Technical Skills Alignment | 0.00% |
| 6 | Work Experience Relevance | 0.00% |
