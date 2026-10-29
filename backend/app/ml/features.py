import os
import re
import numpy as np
from typing import Dict, List, Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class FeatureExtractor:
    """
    Feature Engineering & Vectorization Engine.
    Combines n-gram TF-IDF representations with dense semantic embeddings
    to construct multi-dimensional feature vectors for candidate scoring.
    """

    def __init__(self):
        self.tfidf = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english",
            min_df=1
        )
        self.transformer_model = None
        self._init_transformer()

    def _init_transformer(self):
        """Attempts to load sentence-transformers; falls back cleanly if unavailable."""
        try:
            from sentence_transformers import SentenceTransformer
            self.transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("[INFO] Loaded SentenceTransformer 'all-MiniLM-L6-v2' for dense embeddings.")
        except Exception:
            self.transformer_model = None
            print("[INFO] Operating in TF-IDF dense projection mode.")

    def fit_corpus(self, texts: List[str]):
        """Fits TF-IDF vocabulary on domain corpus."""
        self.tfidf.fit(texts)

    def compute_dense_similarity(self, text_a: str, text_b: str) -> float:
        """Computes semantic cosine similarity via dense Transformer or TF-IDF."""
        if not text_a.strip() or not text_b.strip():
            return 0.0

        if self.transformer_model is not None:
            try:
                emb_a = self.transformer_model.encode([text_a])
                emb_b = self.transformer_model.encode([text_b])
                return float(cosine_similarity(emb_a, emb_b)[0][0])
            except Exception:
                pass

        # TF-IDF Cosine Similarity Fallback
        vecs = self.tfidf.transform([text_a, text_b])
        return float(cosine_similarity(vecs[0:1], vecs[1:2])[0][0])

    def extract_feature_vector(
        self,
        clean_jd: str,
        clean_resume: str,
        sections: Dict[str, str]
    ) -> np.ndarray:
        """
        Constructs the unified 6-dimensional feature vector:
        1. Global Semantic Similarity (JD <-> Full Resume)
        2. Experience Section Relevance
        3. Skills Section Relevance
        4. Summary Section Relevance
        5. Token Jaccard Overlap
        6. Length / Density Ratio
        """
        global_sim = self.compute_dense_similarity(clean_jd, clean_resume)
        exp_sim = self.compute_dense_similarity(clean_jd, sections.get("experience", ""))
        skills_sim = self.compute_dense_similarity(clean_jd, sections.get("skills", ""))
        summary_sim = self.compute_dense_similarity(clean_jd, sections.get("summary", ""))

        # Token Jaccard
        tokens_jd = set(clean_jd.split())
        tokens_res = set(clean_resume.split())
        jaccard = len(tokens_jd.intersection(tokens_res)) / max(1, len(tokens_jd.union(tokens_res)))

        # Length Ratio (normalized)
        len_ratio = min(2.5, len(clean_resume.split()) / max(1, len(clean_jd.split())))

        return np.array([
            global_sim,
            exp_sim,
            skills_sim,
            summary_sim,
            jaccard,
            len_ratio
        ])
