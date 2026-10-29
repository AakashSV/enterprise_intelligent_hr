import re
import unicodedata
from typing import Dict, List, Any


class TextCleaner:
    """
    Dedicated Data Cleaning & Preprocessing pipeline for HR Resumes and Job Descriptions.
    Handles noise removal, unicode normalization, contact masking, section extraction,
    and technical token standardizing.
    """

    SECTION_HEADERS = [
        "summary", "objective", "experience", "work experience", "employment history",
        "skills", "core skills", "technical skills", "education", "certifications",
        "projects", "languages", "responsibilities", "requirements", "what you'll do",
        "what you'll bring", "qualifications"
    ]

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Cleans unicode characters, strips non-ASCII noise, removes URLs, emails, phone numbers,
        and standardizes whitespace.
        """
        if not text:
            return ""

        # Normalize unicode (ligatures, accents)
        text = unicodedata.normalize("NFKD", text)

        # Replace bullet points and weird dashes
        text = re.sub(r"[•●▪■◆★*–—―]", " ", text)

        # Mask emails and phone numbers for privacy during feature modeling
        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", " [EMAIL] ", text)
        text = re.sub(r"(\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", " [PHONE] ", text)
        text = re.sub(r"https?://\S+|www\.\S+", " [URL] ", text)

        # Replace non-alphanumeric except necessary delimiters with spaces
        text = re.sub(r"[^\w\s\.\,\+\#\-\/]", " ", text)

        # Normalize common technical acronyms and terms
        text = re.sub(r"\bci\/cd\b", "continuous_integration", text, flags=re.IGNORECASE)
        text = re.sub(r"\brestful apis?\b|\brest apis?\b", "rest_api", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmachine learning\b|\bml\b", "machine_learning", text, flags=re.IGNORECASE)
        text = re.sub(r"\bartificial intelligence\b|\bai\b", "artificial_intelligence", text, flags=re.IGNORECASE)
        text = re.sub(r"\bdata science\b", "data_science", text, flags=re.IGNORECASE)
        text = re.sub(r"\betl pipelines?\b|\betl\b", "etl_pipeline", text, flags=re.IGNORECASE)

        # Standardize multiple spaces and newlines
        text = re.sub(r"\s+", " ", text).strip().lower()
        return text

    @classmethod
    def segment_sections(cls, raw_text: str) -> Dict[str, str]:
        """
        Splits a resume into functional sections: summary, experience, skills, education, others.
        """
        sections: Dict[str, str] = {
            "summary": "",
            "experience": "",
            "skills": "",
            "education": "",
            "general": ""
        }

        lines = raw_text.splitlines()
        current_section = "general"

        for line in lines:
            clean_line = line.strip().lower()
            if not clean_line:
                continue

            # Check if this line looks like a section header
            matched_header = False
            for header in cls.SECTION_HEADERS:
                if clean_line.startswith(header) or clean_line == header:
                    if "summary" in header or "objective" in header:
                        current_section = "summary"
                    elif "experience" in header or "employment" in header or "history" in header:
                        current_section = "experience"
                    elif "skill" in header:
                        current_section = "skills"
                    elif "education" in header or "qualification" in header:
                        current_section = "education"
                    else:
                        current_section = "general"
                    matched_header = True
                    break

            if not matched_header:
                sections[current_section] += " " + line

        # Clean each section's text
        for sec in sections:
            sections[sec] = cls.normalize_text(sections[sec])

        return sections
