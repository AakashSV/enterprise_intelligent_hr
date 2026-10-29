import os
import json
import joblib
import numpy as np
from typing import Dict, Any, List
from backend.app.ml.clean_data import DataPreprocessor
from backend.app.ml.features import FeatureExtractor


class MLScoringEngine:
    """
    MSc Hybrid Candidate Evaluation Engine.
    Executes Document Parsing (.pdf/.docx), PII Normalization, Section Segmentation,
    Dense Semantic Feature Extraction, and Scikit-Learn Model Inference.
    """

    _instance = None

    def __init__(self, artifacts_dir: str = None):
        if artifacts_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            artifacts_dir = os.path.join(current_dir, "artifacts")

        self.artifacts_dir = artifacts_dir
        self.preprocessor = DataPreprocessor()
        self.feature_extractor = FeatureExtractor()
        self.regressor = None
        self.classifier = None
        self.metadata = {}
        self.load_artifacts()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MLScoringEngine()
        return cls._instance

    def load_artifacts(self):
        vec_path = os.path.join(self.artifacts_dir, "vectorizer.joblib")
        reg_path = os.path.join(self.artifacts_dir, "regressor_model.joblib")
        clf_path = os.path.join(self.artifacts_dir, "classifier_model.joblib")
        meta_path = os.path.join(self.artifacts_dir, "metadata.json")

        if not (os.path.exists(vec_path) and os.path.exists(reg_path) and os.path.exists(clf_path)):
            from backend.app.ml.train_model import train_and_export_models
            train_and_export_models(self.artifacts_dir)

        self.feature_extractor.tfidf = joblib.load(vec_path)
        self.regressor = joblib.load(reg_path)
        self.classifier = joblib.load(clf_path)

        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

    def evaluate_candidate(self, job_desc: str, resume_input: str) -> Dict[str, Any]:
        """
        End-to-end evaluation:
        1. Document Extraction (.pdf / .docx / raw text)
        2. Normalization & PII Masking
        3. Structural Section Segmentation
        4. Feature Vector Generation
        5. Continuous Regressor Score & Categorical Classification
        6. Explainable Strengths, Gaps, and Interview Questions
        """
        # 1. Parse text from input (can be file path or raw string)
        raw_text = self.preprocessor.parse_document(resume_input)

        # 2. Clean & Segment
        clean_jd = self.preprocessor.normalize_text(job_desc, preserve_pii=True)
        clean_resume = self.preprocessor.normalize_text(raw_text, preserve_pii=False)
        sections = self.preprocessor.segment_sections(raw_text)

        # 3. Extract Features
        feat_vector = self.feature_extractor.extract_feature_vector(
            clean_jd=clean_jd,
            clean_resume=clean_resume,
            sections=sections
        ).reshape(1, -1)

        # 4. Model Predictions
        predicted_score = float(self.regressor.predict(feat_vector)[0])
        predicted_score = round(max(0.0, min(100.0, predicted_score)), 1)

        pred_class = int(self.classifier.predict(feat_vector)[0])
        label_map = self.metadata.get("label_map", {
            "3": "Strong Hire",
            "2": "Hire",
            "1": "Review Required",
            "0": "Reject"
        })
        recommendation = label_map.get(str(pred_class), "Review Required")

        # 5. Extract explainable metrics
        global_sim = round(float(feat_vector[0][0]) * 100, 1)
        exp_sim = round(float(feat_vector[0][1]) * 100, 1)
        skills_sim = round(float(feat_vector[0][2]) * 100, 1)
        vocab_overlap = round(float(feat_vector[0][4]) * 100, 1)

        strengths = []
        gaps = []

        if global_sim >= 20.0 or predicted_score >= 80.0:
            strengths.append(f"Strong semantic alignment with role responsibilities ({global_sim}% vector similarity).")
        if skills_sim >= 20.0:
            strengths.append(f"Verified core skills match in technical domain ({skills_sim}% match).")
        if exp_sim >= 15.0:
            strengths.append(f"Practical work history demonstrates relevant industry experience ({exp_sim}% match).")

        if skills_sim < 15.0:
            gaps.append("Direct match in declared technical skills could be strengthened.")
        if "german" not in raw_text.lower() or "a1" in raw_text.lower():
            gaps.append("Basic or unspecified German language proficiency (English is primary, German is a plus).")

        if not strengths:
            strengths.append("Candidate demonstrates baseline educational qualifications.")

        interview_questions = [
            "How would you approach identifying high-impact AI/SI use cases across operational workflows?",
            "Can you explain your experience architecting custom automation pipelines and integrating LLM/coding agents?",
            "How do you structure knowledge ingestion to ensure zero hallucination for compliance workflows?"
        ]

        return {
            "overall_score": predicted_score,
            "recommendation": recommendation,
            "category_breakdown": {
                "dense_semantic_similarity": global_sim,
                "skills_alignment": skills_sim,
                "experience_relevance": exp_sim,
                "vocabulary_overlap": vocab_overlap
            },
            "strengths": strengths,
            "gaps": gaps,
            "generated_interview_questions": interview_questions,
            "parsed_sections": sections,
            "raw_text_preview": raw_text[:500]
        }
