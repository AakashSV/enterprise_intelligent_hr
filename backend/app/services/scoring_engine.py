import re
from typing import Dict, Any, List, Tuple
from ml_model.inference import ResumeScoringModel


class ScoringEngine:
    """
    Candidate Evaluation Engine powered by our dedicated Machine Learning model (ml_model).
    Performs data cleaning, section segmentation, TF-IDF vector similarity,
    and supervised GradientBoosting scoring + RandomForest recommendation.
    """

    _ml_model: ResumeScoringModel = None

    @classmethod
    def get_model(cls) -> ResumeScoringModel:
        if cls._ml_model is None:
            cls._ml_model = ResumeScoringModel()
        return cls._ml_model

    @staticmethod
    def extract_skills(text: str) -> List[str]:
        keywords = [
            "python", "javascript", "sql", "postgresql", "django", "fastapi", "odoo",
            "restful apis", "rest api", "apis", "pandas", "numpy", "machine learning",
            "artificial intelligence", "ai", "etl", "ocr", "workflow automation",
            "process automation", "continuous deployment", "ci/cd", "knowledge agents",
            "coding agents", "docker", "git", "data analysis", "statistical modeling"
        ]
        text_lower = text.lower()
        found = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", text_lower)]
        return list(set(found))

    @classmethod
    def evaluate(cls, job_desc: str, resume_text: str, candidate_meta: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Run Dedicated Machine Learning Model
        model = cls.get_model()
        ml_prediction = model.predict(job_description=job_desc, resume_text=resume_text)

        ml_score = ml_prediction["overall_score"]
        recommendation = ml_prediction["recommendation"]
        feature_metrics = ml_prediction["feature_metrics"]

        # 2. Heuristic domain adjustments (Education & Location)
        edu_bonus = 15.0 if ("master" in resume_text.lower() or "msc" in resume_text.lower()) else 5.0
        loc_bonus = 10.0 if ("berlin" in resume_text.lower() or "germany" in resume_text.lower()) else 0.0

        # Blended calibrated score
        overall_score = round(min(100.0, ml_score * 0.75 + edu_bonus + loc_bonus), 1)

        # Update recommendation if score exceeds thresholds
        if overall_score >= 80.0:
            recommendation = "Strong Hire"
        elif overall_score >= 65.0:
            recommendation = "Hire"
        elif overall_score >= 50.0:
            recommendation = "Review Required"
        else:
            recommendation = "Reject"

        category_scores = {
            "ml_semantic_match": feature_metrics["overall_similarity"],
            "technical_skills_overlap": round(min(100.0, max(feature_metrics["skills_similarity"], feature_metrics["vocabulary_overlap"] * 2.0)), 1),
            "experience_relevance": round(min(100.0, max(feature_metrics["experience_similarity"], feature_metrics["overall_similarity"] * 1.5)), 1),
            "education_level": 95.0 if "master" in resume_text.lower() or "msc" in resume_text.lower() else 80.0,
            "location_fit": 95.0 if "berlin" in resume_text.lower() or "germany" in resume_text.lower() else 60.0
        }

        strengths = ml_prediction["strengths"]
        gaps = ml_prediction["gaps"]

        if "german" not in resume_text.lower() or "a1" in resume_text.lower():
            if not any("german" in g.lower() for g in gaps):
                gaps.append("Basic or unspecified German language proficiency (English is primary, German is a plus).")

        interview_questions = [
            "How would you approach identifying high-impact AI/SI use cases across non-technical shop-floor cell teams?",
            "Can you explain your experience architecting custom automation pipelines and integrating LLM/coding agents?",
            "How do you structure knowledge ingestion to ensure zero hallucination for compliance workflows?"
        ]

        return {
            "overall_score": overall_score,
            "recommendation": recommendation,
            "category_scores": category_scores,
            "strengths": strengths,
            "gaps": gaps,
            "interview_questions": interview_questions,
            "ml_confidence": ml_prediction["confidence"]
        }

    @staticmethod
    def generate_draft_email(
        candidate_name: str,
        job_title: str,
        recommendation: str,
        scheduling_link: str = "https://calendly.com/tesla-recruiting/intro-screen"
    ) -> Tuple[str, str, str]:
        if recommendation in ["Strong Hire", "Hire"]:
            action_type = "OUTREACH_EMAIL"
            subject = f"Interview Invitation: {job_title} - Gigafactory Berlin"
            payload = (
                f"Dear {candidate_name},\n\n"
                f"Thank you for applying for the {job_title} position at Gigafactory Berlin-Brandenburg.\n\n"
                f"Our AI Screening Model reviewed your profile and identified strong alignment with our technical "
                f"and automation requirements. We would love to invite you to an introductory 30-minute interview.\n\n"
                f"Please choose a time that suits you best using this link:\n{scheduling_link}\n\n"
                f"Best regards,\n"
                f"Tesla Talent Acquisition Team\nGigafactory Berlin-Brandenburg"
            )
        else:
            action_type = "REJECTION_EMAIL"
            subject = f"Update regarding your application for {job_title}"
            payload = (
                f"Dear {candidate_name},\n\n"
                f"Thank you for your interest in the {job_title} position at Gigafactory Berlin-Brandenburg "
                f"and for taking the time to share your profile with us.\n\n"
                f"After careful review, we have decided to move forward with other candidates whose experience "
                f"more closely aligns with the current requirements for this specific opening.\n\n"
                f"We wish you all the best in your career pursuits.\n\n"
                f"Sincerely,\n"
                f"Tesla Talent Acquisition Team"
            )

        return action_type, subject, payload
