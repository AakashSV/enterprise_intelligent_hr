import os
import json
import numpy as np
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.pipeline import Pipeline

from ml_model.training.clean_data import TextCleaner
from ml_model.training.build_dataset import get_training_samples


class ModelTrainer:
    """
    Trains the proprietary candidate matching and scoring ML model.
    Extracts multi-faceted semantic features from cleaned text,
    and fits both a score regressor (0-100) and recommendation classifier.
    """

    def __init__(self, artifacts_dir: str = "ml_model/artifacts"):
        self.artifacts_dir = artifacts_dir
        os.makedirs(self.artifacts_dir, exist_ok=True)
        self.cleaner = TextCleaner()
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            stop_words="english"
        )
        self.regressor = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42
        )
        self.classifier = RandomForestClassifier(
            n_estimators=50,
            max_depth=4,
            random_state=42
        )

    def extract_features_for_pair(self, clean_jd: str, clean_resume: str, resume_sections: dict) -> np.ndarray:
        """
        Extracts multi-dimensional feature vector for a (JD, Resume) pair:
        1. Full semantic cosine similarity
        2. Experience section similarity
        3. Skills section similarity
        4. Summary section similarity
        5. Token overlap / Jaccard similarity
        6. Length ratio
        """
        # Vectorize
        tfidf_pair = self.vectorizer.transform([clean_jd, clean_resume])
        overall_sim = float(cosine_similarity(tfidf_pair[0:1], tfidf_pair[1:2])[0][0])

        # Section similarities
        def sec_sim(section_text: str) -> float:
            if not section_text.strip():
                return 0.0
            sec_tfidf = self.vectorizer.transform([section_text])
            return float(cosine_similarity(tfidf_pair[0:1], sec_tfidf)[0][0])

        exp_sim = sec_sim(resume_sections.get("experience", ""))
        skills_sim = sec_sim(resume_sections.get("skills", ""))
        summary_sim = sec_sim(resume_sections.get("summary", ""))

        # Token set Jaccard
        tokens_jd = set(clean_jd.split())
        tokens_res = set(clean_resume.split())
        jaccard = len(tokens_jd.intersection(tokens_res)) / max(1, len(tokens_jd.union(tokens_res)))

        length_ratio = min(2.0, len(clean_resume.split()) / max(1, len(clean_jd.split())))

        return np.array([
            overall_sim,
            exp_sim,
            skills_sim,
            summary_sim,
            jaccard,
            length_ratio
        ])

    def train(self):
        samples = get_training_samples()
        print(f"Loaded {len(samples)} training pairs.")

        # 1. Clean all texts
        corpus = []
        cleaned_pairs = []

        for s in samples:
            clean_jd = self.cleaner.normalize_text(s["job_description"])
            clean_res = self.cleaner.normalize_text(s["resume"])
            sections = self.cleaner.segment_sections(s["resume"])

            corpus.append(clean_jd)
            corpus.append(clean_res)
            cleaned_pairs.append({
                "clean_jd": clean_jd,
                "clean_res": clean_res,
                "sections": sections,
                "target_score": s["target_score"],
                "label": s["label"]
            })

        # 2. Fit TF-IDF Vectorizer on cleaned domain corpus
        print("Fitting TF-IDF Vectorizer on domain corpus...")
        self.vectorizer.fit(corpus)

        # 3. Build Feature Matrix
        X = []
        y_score = []
        y_class = []

        for pair in cleaned_pairs:
            feats = self.extract_features_for_pair(
                clean_jd=pair["clean_jd"],
                clean_resume=pair["clean_res"],
                resume_sections=pair["sections"]
            )
            X.append(feats)
            y_score.append(pair["target_score"])
            y_class.append(pair["label"])

        X = np.array(X)
        y_score = np.array(y_score)
        y_class = np.array(y_class)

        print(f"Feature matrix shape: {X.shape}")

        # 4. Train Regressor & Classifier
        print("Training GradientBoostingRegressor for continuous match score...")
        self.regressor.fit(X, y_score)

        print("Training RandomForestClassifier for categorical recommendation...")
        self.classifier.fit(X, y_class)

        # 5. Save Artifacts
        joblib.dump(self.vectorizer, os.path.join(self.artifacts_dir, "vectorizer.joblib"))
        joblib.dump(self.regressor, os.path.join(self.artifacts_dir, "regressor_model.joblib"))
        joblib.dump(self.classifier, os.path.join(self.artifacts_dir, "classifier_model.joblib"))

        metadata = {
            "model_version": "1.0.0",
            "feature_names": [
                "overall_similarity", "experience_similarity", "skills_similarity",
                "summary_similarity", "token_jaccard", "length_ratio"
            ],
            "label_map": {
                "3": "Strong Hire",
                "2": "Hire",
                "1": "Review",
                "0": "Reject"
            }
        }
        with open(os.path.join(self.artifacts_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"[SUCCESS] Successfully trained and exported model artifacts to {self.artifacts_dir}/")


if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.train()
