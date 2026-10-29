import json
import os
from typing import List, Dict, Any


def get_training_samples() -> List[Dict[str, Any]]:
    """
    Constructs a diverse, ground-truth labeled dataset of Resume and JD pairs
    for training the candidate scoring and classification model.
    Labels:
      3: Strong Match (>= 85%)
      2: Good / Moderate Match (70% - 84%)
      1: Partial Match (50% - 69%)
      0: Mismatch / Reject (< 50%)
    """
    samples = [
        # Sample 1: Perfect / Strong match for AI Automation & Implementation Intern
        {
            "job_title": "AI Adoption & Implementation Internship",
            "job_description": """
            Tesla Gigafactory Berlin Cell department. Driving integration of SI tools and workflows.
            Focus on Tesla internal SI platforms, coding agents, workflow automations, and operational efficiency.
            Requirements: Enrolled in Bachelor or Master program in Computer Science, Data Science, Engineering.
            Interest in Artificial Intelligence, Python, data analysis tools, process optimization.
            English fluent, German is a plus.
            """,
            "resume": """
            Backend Developer and MSc Data Science student in Berlin. 4+ years experience identifying
            manual processes and implementing AI-ready automation and digital workflows with measurable impact.
            Python solutions cutting manual processing overhead by 35%. OCR document processing cutting data entry by 60%.
            Automated recurring data ingestion, schema validation, and ETL pipelines.
            Skills: Python, Django, PostgreSQL, Pandas, NumPy, RESTful APIs, machine learning, data science.
            Education: Arden University Germany, MSc Data Science (Present). English C1, German A1.
            """,
            "label": 3,
            "target_score": 92.0
        },
        # Sample 2: Strong match for Python Backend / Automation Engineer
        {
            "job_title": "Python Automation Engineer",
            "job_description": """
            Looking for a Python Backend Engineer to build automated ETL pipelines, REST APIs,
            and data integration workflows. Must have hands-on experience with SQL, PostgreSQL,
            Docker, and API design. Experience with automated testing and continuous deployment.
            """,
            "resume": """
            Python Developer with 3 years experience building RESTful APIs using FastAPI and Django.
            Engineered automated data ingestion and ETL jobs in PostgreSQL. Integrated automated unit tests
            and CI/CD pipelines. Proficient in Python, SQL, Docker, Linux, and Git.
            """,
            "label": 3,
            "target_score": 88.0
        },
        # Sample 3: Moderate match (good data skills, but lacks backend automation depth)
        {
            "job_title": "AI Adoption & Implementation Internship",
            "job_description": """
            Driving integration of AI tools, coding agents, and process automations.
            Requirements: Student in Data Science or Engineering, Python, data analysis tools.
            """,
            "resume": """
            Bachelor in Business Analytics student. Experience using Excel, PowerBI, and basic Python
            for descriptive statistics and marketing data analysis. Interested in AI and workflow automation.
            Fluent in English and German.
            """,
            "label": 2,
            "target_score": 70.0
        },
        # Sample 4: Partial match (frontend focused, lacking Python & AI automation)
        {
            "job_title": "AI Adoption & Implementation Internship",
            "job_description": """
            Tesla Cell department. Focus on Python automation, coding agents, and ETL data workflows.
            Computer Science or Data Science background required.
            """,
            "resume": """
            Frontend React Developer with 2 years experience building responsive UI web interfaces.
            HTML, CSS, JavaScript, Tailwind, React. Minor exposure to Python in introductory university coursework.
            Seeking to transition into AI and data roles.
            """,
            "label": 1,
            "target_score": 55.0
        },
        # Sample 5: Complete Mismatch (Accounting / Non-technical)
        {
            "job_title": "AI Adoption & Implementation Internship",
            "job_description": """
            Tesla Cell department. Focus on internal SI platforms, Python automation, and coding agents.
            Engineering or Computer Science enrollment.
            """,
            "resume": """
            Senior Accountant with 8 years experience in payroll processing, corporate tax audits,
            and financial ledger balancing using QuickBooks and Excel. Certified Public Accountant (CPA).
            Strong attention to detail in financial compliance.
            """,
            "label": 0,
            "target_score": 25.0
        },
        # Sample 6: Complete Mismatch (Sales & Hospitality)
        {
            "job_title": "Python Automation Engineer",
            "job_description": """
            Python backend developer to build automated ETL pipelines, REST APIs, and database migrations.
            """,
            "resume": """
            Experienced Hospitality Manager with 5 years managing hotel front desk operations,
            customer bookings, and staff scheduling. Proficient in POS systems and customer relationship management.
            """,
            "label": 0,
            "target_score": 15.0
        },
        # Sample 7: Strong match for Machine Learning / NLP Engineer
        {
            "job_title": "Machine Learning Engineer (NLP)",
            "job_description": """
            Develop NLP and LLM applications, embeddings, semantic search, and document classification models.
            Required: Python, PyTorch/TensorFlow, Hugging Face, Scikit-learn, vector search, data preprocessing.
            """,
            "resume": """
            Machine Learning Engineer with MSc in Computer Science. Built end-to-end document parsing
            and semantic search pipelines using Sentence-Transformers and Scikit-learn. Extensive experience
            in text preprocessing, tokenization, PyTorch, Python, and deploying inference microservices.
            """,
            "label": 3,
            "target_score": 95.0
        },
        # Sample 8: Moderate match for ML Engineer (Good developer, junior in ML)
        {
            "job_title": "Machine Learning Engineer (NLP)",
            "job_description": """
            Develop NLP and LLM applications, embeddings, semantic search, and text classification models.
            Required: Python, NLP, Hugging Face, Scikit-learn.
            """,
            "resume": """
            Backend Python Software Engineer with 3 years building web services. Recently completed
            certifications in Deep Learning and NLP. Familiar with Scikit-learn, Pandas, and basic text tokenization.
            """,
            "label": 2,
            "target_score": 72.0
        }
    ]
    return samples


def save_dataset(filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    samples = get_training_samples()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)
    print(f"Saved {len(samples)} training samples to {filepath}")


if __name__ == "__main__":
    save_dataset("ml_model/data/training_data.json")
