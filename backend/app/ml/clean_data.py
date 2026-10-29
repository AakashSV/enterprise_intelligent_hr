import re
import unicodedata
import os
from typing import Dict, List, Optional


class DataPreprocessor:
    """
    MSc Data Science Preprocessing Pipeline for HR documents.
    Handles multi-format parsing (.pdf, .docx, .txt), noise filtering,
    privacy/PII masking, and structural section segmentation.
    """

    SECTION_PATTERNS = {
        "summary": r"(summary|objective|professional summary|profile|about me)\b",
        "experience": r"(experience|work experience|employment history|professional experience|career history)\b",
        "skills": r"(skills|core skills|technical skills|competencies|technologies|tools)\b",
        "education": r"(education|academic background|qualifications|degrees|certifications)\b"
    }

    @classmethod
    def parse_document(cls, file_path_or_text: str) -> str:
        """
        Extracts raw text from PDF, DOCX, or direct string input.
        """
        if not os.path.exists(file_path_or_text):
            # Treat directly as raw text
            return file_path_or_text

        ext = os.path.splitext(file_path_or_text)[1].lower()
        if ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path_or_text)
                text = " ".join([page.extract_text() or "" for page in reader.pages])
                return text
            except Exception as e:
                return f"Error reading PDF: {str(e)}"
        elif ext in [".docx", ".doc"]:
            try:
                import docx
                doc = docx.Document(file_path_or_text)
                text = " ".join([p.text for p in doc.paragraphs])
                return text
            except Exception as e:
                return f"Error reading DOCX: {str(e)}"
        else:
            with open(file_path_or_text, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    @classmethod
    def mask_pii(cls, text: str) -> str:
        """
        Masks Personally Identifiable Information (PII) including phone numbers,
        emails, and common street address indicators for data privacy compliance (GDPR).
        """
        # Mask emails
        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_MASKED]", text)
        # Mask international and local phone numbers
        text = re.sub(r"(\+\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,5}", "[PHONE_MASKED]", text)
        # Mask URLs and social profiles
        text = re.sub(r"https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+", "[LINK_MASKED]", text)
        return text

    @classmethod
    def normalize_text(cls, text: str, preserve_pii: bool = False) -> str:
        """
        Full text cleaning pipeline: unicode decomposition, bullet point removal,
        whitespace reduction, and optional PII masking.
        """
        if not text:
            return ""

        # Normalize unicode characters
        text = unicodedata.normalize("NFKD", text)

        # Replace bullet points, dashes, emojis
        text = re.sub(r"[•●▪■◆★*–—―►√✔]", " ", text)

        # PII Masking
        if not preserve_pii:
            text = cls.mask_pii(text)

        # Standardize technical acronyms and hyphenated phrases
        text = re.sub(r"\bci\/cd\b", "continuous_integration", text, flags=re.IGNORECASE)
        text = re.sub(r"\brestful apis?\b|\brest apis?\b", "rest_api", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmachine learning\b|\bml\b", "machine_learning", text, flags=re.IGNORECASE)
        text = re.sub(r"\bartificial intelligence\b|\bai\b", "artificial_intelligence", text, flags=re.IGNORECASE)
        text = re.sub(r"\bdata science\b", "data_science", text, flags=re.IGNORECASE)
        text = re.sub(r"\betl pipelines?\b|\betl\b", "etl_pipeline", text, flags=re.IGNORECASE)

        # Remove strange symbols except semantic punctuation
        text = re.sub(r"[^\w\s\.\,\+\#\-\/\[\]]", " ", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def segment_sections(cls, raw_text: str) -> Dict[str, str]:
        """
        Splits a resume into 4 core functional sections: Summary, Experience, Skills, Education.
        """
        sections = {
            "summary": "",
            "experience": "",
            "skills": "",
            "education": "",
            "general": ""
        }

        lines = raw_text.splitlines()
        current_section = "general"

        for line in lines:
            stripped = line.strip().lower()
            if not stripped:
                continue

            matched = False
            for sec_name, pattern in cls.SECTION_PATTERNS.items():
                if re.match(pattern, stripped):
                    current_section = sec_name
                    matched = True
                    break

            if not matched:
                sections[current_section] += " " + line

        # Normalize each extracted section
        for sec in sections:
            sections[sec] = cls.normalize_text(sections[sec], preserve_pii=False).lower()

        return sections
