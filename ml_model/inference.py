import os
import json
import numpy as np
import joblib
from typing import Dict, Any, List
from sklearn.metrics.pairwise import cosine_similarity
from ml_model.training.clean_data import TextCleaner


class ResumeScoringModel:
    """
    Dedicated inference engine for candidate resume vs job description scoring.
    Loads trained model artifacts and computes calibrated match metrics,
    section-level similarities, and recommended decisions.
    """

    def __init__(self, artifacts_dir: str = None):
        if artifacts_dir is None:
            # Default to relative directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            artifacts_dir = os.path.join(current_dir, "artifacts")

        self.artifacts_dir = artifacts_dir
        self.cleaner = TextCleaner()
        self.vectorizer = None
        self.regressor = None
        self.classifier = None
        self.metadata = {}
        self.load_artifacts()

    def load_artifacts(self):
        vec_path = os.path.join(self.artifacts_dir, "vectorizer.joblib")
        reg_path = os.path.join(self.artifacts_dir, "regressor_model.joblib")
        clf_path = os.path.join(self.artifacts_dir, "classifier_model.joblib")
        meta_path = os.path.join(self.artifacts_dir, "metadata.json")

        if not (os.path.exists(vec_path) and os.path.exists(reg_path) and os.path.exists(clf_path)):
            raise FileNotFoundError(
                f"Model artifacts not found in {self.artifacts_dir}. Please run 'python -m ml_model.training.train_model' first."
            )

        self.vectorizer = joblib.load(vec_path)
        self.regressor = joblib.load(reg_path)
        self.classifier = joblib.load(clf_path)

        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

    def predict(self, job_description: str, resume_text: str) -> Dict[str, Any]:
        """
        Executes end-to-end data cleaning, section segmentation, feature extraction,
        and ML model prediction.
        """
        # 1. Clean and normalize
        clean_jd = self.cleaner.normalize_text(job_description)
        clean_resume = self.cleaner.normalize_text(resume_text)
        sections = self.cleaner.segment_sections(resume_text)

        # 2. Extract features
        tfidf_pair = self.vectorizer.transform([clean_jd, clean_resume])
        overall_sim = float(cosine_similarity(tfidf_pair[0:1], tfidf_pair[1:2])[0][0])

        def sec_sim(section_text: str) -> float:
            if not section_text.strip():
                return 0.0
            sec_tfidf = self.vectorizer.transform([section_text])
            return float(cosine_similarity(tfidf_pair[0:1], sec_tfidf)[0][0])

        exp_sim = sec_sim(sections.get("experience", ""))
        skills_sim = sec_sim(sections.get("skills", ""))
        summary_sim = sec_sim(sections.get("summary", ""))

        tokens_jd = set(clean_jd.split())
        tokens_res = set(clean_resume.split())
        jaccard = len(tokens_jd.intersection(tokens_res)) / max(1, len(tokens_jd.union(tokens_res)))
        length_ratio = min(2.0, len(clean_resume.split()) / max(1, len(clean_jd.split())))

        feature_vector = np.array([[
            overall_sim,
            exp_sim,
            skills_sim,
            summary_sim,
            jaccard,
            length_ratio
        ]])

        # 3. Model predictions
        predicted_score = float(self.regressor.predict(feature_vector)[0])
        predicted_score = max(0.0, min(100.0, round(predicted_score, 1)))

        pred_class = int(self.classifier.predict(feature_vector)[0])
        class_prob = self.classifier.predict_proba(feature_vector)[0]
        confidence = float(np.max(class_prob))

        label_map = self.metadata.get("label_map", {
            "3": "Strong Hire",
            "2": "Hire",
            "1": "Review",
            "0": "Reject"
        })
        recommendation = label_map.get(str(pred_class), "Review")

        # 4. Generate Explainable Strengths & Gaps
        strengths = []
        gaps = []

        if overall_sim >= 0.25:
            strengths.append(f"Strong overall semantic alignment with job description ({round(overall_sim * 100, 1)}% textual similarity).")
        if skills_sim >= 0.25:
            strengths.append(f"Direct match in technical skills section ({round(skills_sim * 100, 1)}% match).")
        if exp_sim >= 0.20:
            strengths.append(f"Work experience demonstrates relevant industry project exposure ({round(exp_sim * 100, 1)}% match).")

        if skills_sim < 0.15:
            gaps.append("Low direct match in declared skills against required technologies.")
        if overall_sim < 0.20:
            gaps.append("General experience vocabulary diverges from primary role requirements.")

        if not strengths:
            strengths.append("Candidate demonstrates baseline educational background.")

        return {
            "overall_score": predicted_score,
            "recommendation": recommendation,
            "confidence": round(confidence, 2),
            "feature_metrics": {
                "overall_similarity": round(overall_sim * 100, 1),
                "skills_similarity": round(skills_sim * 100, 1),
                "experience_similarity": round(exp_sim * 100, 1),
                "summary_similarity": round(summary_sim * 100, 1),
                "vocabulary_overlap": round(jaccard * 100, 1)
            },
            "strengths": strengths,
            "gaps": gaps,
            "cleaned_sections": {
                "skills_length": len(sections.get("skills", "").split()),
                "experience_length": len(sections.get("experience", "").split())
            }
        }


if __name__ == "__main__":
    model = ResumeScoringModel()
    print("Model initialized successfully!")
