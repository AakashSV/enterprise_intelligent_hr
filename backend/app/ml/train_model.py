import os
import json
import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from backend.app.ml.clean_data import DataPreprocessor
from backend.app.ml.features import FeatureExtractor


def get_training_dataset():
    return [
        {
            "jd": "Tesla Gigafactory Berlin Cell department. SI tools, Python automation, coding agents, ETL pipelines, process optimization. Enrolled in Master/Bachelor Computer Science, Data Science.",
            "resume": "Backend Developer & MSc Data Science student in Berlin. 4+ years in Python automation cutting overhead by 35%. OCR document processing, ETL pipelines, schema validation. Skills: Python, Django, PostgreSQL, Pandas, NumPy, REST APIs, ML.",
            "score": 92.0,
            "label": 3  # Strong Hire
        },
        {
            "jd": "Python Backend Automation Engineer. Build automated ETL pipelines, REST APIs, SQL, PostgreSQL, Docker, CI/CD.",
            "resume": "Python Developer with 3 years experience building RESTful APIs using FastAPI and Django. Automated data ingestion and ETL jobs in PostgreSQL. Proficient in Python, SQL, Docker, Git.",
            "score": 88.0,
            "label": 3  # Strong Hire
        },
        {
            "jd": "AI Adoption & Implementation Intern. Python, data analysis tools, process automations. Student in Data Science or Engineering.",
            "resume": "Bachelor in Business Analytics student. Experience using Excel, PowerBI, and basic Python for descriptive statistics and marketing data analysis. Fluent in English and German.",
            "score": 68.0,
            "label": 2  # Hire
        },
        {
            "jd": "Tesla Cell department. Focus on Python automation, coding agents, and ETL data workflows.",
            "resume": "Frontend React Developer with 2 years experience building responsive UI web interfaces. HTML, CSS, JavaScript, React. Minor exposure to Python in coursework.",
            "score": 52.0,
            "label": 1  # Review Required
        },
        {
            "jd": "AI Adoption & Implementation Internship. Tesla Cell department SI platforms, Python automation.",
            "resume": "Senior Accountant with 8 years experience in payroll processing, corporate tax audits, and financial ledger balancing using QuickBooks and Excel. Certified Public Accountant.",
            "score": 20.0,
            "label": 0  # Reject
        },
        {
            "jd": "Machine Learning Engineer NLP. Develop LLM applications, embeddings, semantic search, and document classification. Python, PyTorch, Scikit-learn, vector search.",
            "resume": "Machine Learning Engineer with MSc in Computer Science. Built end-to-end document parsing and semantic search pipelines using Sentence-Transformers and Scikit-learn. PyTorch, Python.",
            "score": 94.0,
            "label": 3  # Strong Hire
        }
    ]


def train_and_export_models(artifacts_dir: str = "backend/app/ml/artifacts"):
    os.makedirs(artifacts_dir, exist_ok=True)
    samples = get_training_dataset()

    preprocessor = DataPreprocessor()
    extractor = FeatureExtractor()

    corpus = []
    processed_samples = []

    for s in samples:
        clean_jd = preprocessor.normalize_text(s["jd"])
        clean_res = preprocessor.normalize_text(s["resume"])
        sections = preprocessor.segment_sections(s["resume"])

        corpus.append(clean_jd)
        corpus.append(clean_res)
        processed_samples.append({
            "clean_jd": clean_jd,
            "clean_res": clean_res,
            "sections": sections,
            "score": s["score"],
            "label": s["label"]
        })

    extractor.fit_corpus(corpus)

    X = []
    y_score = []
    y_class = []

    for item in processed_samples:
        feat = extractor.extract_feature_vector(
            clean_jd=item["clean_jd"],
            clean_resume=item["clean_res"],
            sections=item["sections"]
        )
        X.append(feat)
        y_score.append(item["score"])
        y_class.append(item["label"])

    X = np.array(X)
    y_score = np.array(y_score)
    y_class = np.array(y_class)

    regressor = GradientBoostingRegressor(n_estimators=80, learning_rate=0.1, max_depth=3, random_state=42)
    regressor.fit(X, y_score)

    classifier = RandomForestClassifier(n_estimators=40, max_depth=4, random_state=42)
    classifier.fit(X, y_class)

    # Save artifacts
    joblib.dump(extractor.tfidf, os.path.join(artifacts_dir, "vectorizer.joblib"))
    joblib.dump(regressor, os.path.join(artifacts_dir, "regressor_model.joblib"))
    joblib.dump(classifier, os.path.join(artifacts_dir, "classifier_model.joblib"))

    metadata = {
        "model_version": "2.0.0",
        "feature_names": [
            "global_semantic_similarity", "experience_relevance", "skills_relevance",
            "summary_relevance", "token_jaccard", "length_density_ratio"
        ],
        "label_map": {
            "3": "Strong Hire",
            "2": "Hire",
            "1": "Review Required",
            "0": "Reject"
        }
    }
    with open(os.path.join(artifacts_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"[SUCCESS] Trained and exported model artifacts to {artifacts_dir}/")


if __name__ == "__main__":
    train_and_export_models()
