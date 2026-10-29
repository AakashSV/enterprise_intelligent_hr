from backend.app.database import SessionLocal, Base, engine
from backend.app.models.entities import Job, Candidate, Application, Scorecard, StagedAction, AuditLog
from backend.app.models.entities import ApplicationStatus, ActionType, ActionStatus
from backend.app.services.scoring_engine import ScoringEngine
from backend.app.services.hitl_service import HITLService

# Ensure tables exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 1. Create Tesla Job Requisition
tesla_job = db.query(Job).filter(Job.req_id == "285983").first()
if not tesla_job:
    tesla_job = Job(
        req_id="285983",
        title="AI Adoption & Implementation Internship (m/f/d)",
        department="Tesla SI / Battery Cell",
        location="Grünheide (Mark), Brandenburg",
        description="""
        The SI Adoption & Implementation Intern will play a key role in driving the integration of SI tools and workflows within Tesla's Cell department at Gigafactory Berlin-Brandenburg. Working closely with the Sr. Technical Program Manager, the intern will support the identification, evaluation, and implementation of SI solutions — with a focus on Tesla's internal SI platforms and Coding Agents — to improve operational efficiency, data analysis, and team productivity across the Cell organization.
        
        Requirements:
        - Currently enrolled in a Bachelor's or Master's program in Engineering, Computer Science, Data Science, Business Informatics, or a related field
        - Profound interest in Artificial Intelligence, digital transformation, and process optimization.
        - Good knowledge of English, both written and spoken; German is a plus
        - Proficiency in common MS Office applications; experience with data analysis tools is a plus
        - Analytical mindset with a structured, problem-solving approach
        - Ability to work both independently and collaboratively in a fast-paced, cross-functional environment
        - Strong communication skills
        """,
        requirements=[
            "Enrolled student (BSc/MSc)",
            "AI / Digital Transformation interest",
            "Data analysis & automation tools",
            "English C1 / German is a plus",
            "Process optimization & stakeholder communication"
        ]
    )
    db.add(tesla_job)
    db.commit()
    db.refresh(tesla_job)
    print(f"Created Job: {tesla_job.title} ({tesla_job.req_id})")
else:
    print(f"Job {tesla_job.req_id} already exists.")

# 2. Add Candidate Aakash
aakash = db.query(Candidate).filter(Candidate.email == "aakashsv220@gmail.com").first()
resume_text = """
Aakash Sajikumar Vijayalekshmy
(AI Adoption & Implementation Intern)
Berlin, Germany | aakashsv220@gmail.com | +91 8589915896 (WhatsApp) | linkedin.com/in/aakash-sv

SUMMARY
Backend Developer and MSc Data Science student based in Berlin with 4+ years of experience identifying manual processes and implementing AI-ready automation and digital workflows with measurable impact. Delivered Python solutions that cut manual processing overhead by 35% and reduced manual data entry by 60%, working with technical and business stakeholders from requirements through release. Academic focus on AI, machine learning and statistical modeling, with a structured, analytical approach to process optimization and a strong interest in driving AI adoption across teams.

EXPERIENCE
SF Investments GmbH | Backend Developer September 2025 – Present | Germany
• Architected and deployed custom Python automation tools, turning manual workflows into digital processes and reducing manual processing overhead by 35%.
• Partnered directly with technical and business stakeholders to identify use cases, define requirements, and iteratively scope, test and release automation enhancements.
• Automated recurring data ingestion, schema validation and ETL pipelines, cutting pipeline runtimes and eliminating recurring data discrepancies.
• Built clean, modular backend services in a continuous deployment environment aligned with strict production reliability standards.

HTIC Global | Python / Odoo Developer January 2022 – January 2025 | India
• Integrated OCR-based document processing to streamline invoice and record parsing, reducing manual data entry by 60%.
• Developed and deployed an end-to-end internal HRMS automating employee onboarding, lifecycle management and attendance tracking for 200+ users.
• Spearheaded aviation ERP customization modules, automating critical compliance workflows and multi-departmental reporting.
• Engineered enterprise ERP solutions on Odoo 14 & 15 using Python, PostgreSQL and XML for diverse business verticals.
• Optimized backend queries and database indexes to sustain high concurrency, system responsiveness and long-term maintainability.

Quest Innovative Solutions | Web Developer Intern July 2021 – January 2022 | India
• Developed RESTful backend APIs and microservices using Django and Python to power automated client data flows.
• Implemented schema validation, exception logging and ORM query optimization, improving service stability and reducing response latencies.

CORE SKILLS
AI & Analytics: Artificial Intelligence • Machine Learning • Statistical Modeling • OCR Document Processing • Data Analysis
Process Optimization: Process Automation • Workflow Automation • Requirements Gathering • ETL Pipelines • Reporting
Programming & Data: Python • JavaScript • SQL • PostgreSQL • Pandas • NumPy • RESTful APIs
Platforms: Odoo ERP (14 & 15) • Django • HRMS Development • Continuous Deployment
Languages: English (C1 – Advanced/Professional) • German (A1 – Basic)

EDUCATION
Arden University – Germany February 2025 – Present
MSc Data Science – Data Science, Machine Learning, Statistical Modeling, ETL & Data Pipelines, AI
Noorul Islam Centre for Higher Education – India August 2017 – March 2021
B.Tech Information Technology – Software Engineering, Data Structures & Algorithms, Database Systems, Computer Networks
"""

if not aakash:
    aakash = Candidate(
        name="Aakash Sajikumar Vijayalekshmy",
        email="aakashsv220@gmail.com",
        phone="+91 8589915896",
        location="Berlin, Germany",
        education="MSc Data Science (Arden University)",
        raw_resume=resume_text,
        parsed_skills=ScoringEngine.extract_skills(resume_text)
    )
    db.add(aakash)
    db.commit()
    db.refresh(aakash)
    print(f"Created Candidate: {aakash.name}")

# Check if application already exists
existing_app = db.query(Application).filter(
    Application.job_id == tesla_job.id,
    Application.candidate_id == aakash.id
).first()

if not existing_app:
    # 3. Create Application
    app = Application(
        job_id=tesla_job.id,
        candidate_id=aakash.id,
        status=ApplicationStatus.DRAFT
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    HITLService.log_state_change(
        db,
        application_id=app.id,
        from_status="NONE",
        to_status=ApplicationStatus.DRAFT.value,
        actor="SYSTEM",
        notes="Candidate application initialized from resume submission."
    )

    # 4. Score Candidate
    evaluation = ScoringEngine.evaluate(
        job_desc=tesla_job.description,
        resume_text=aakash.raw_resume,
        candidate_meta={"location": aakash.location, "education": aakash.education}
    )

    scorecard = Scorecard(
        application_id=app.id,
        overall_score=evaluation["overall_score"],
        recommendation=evaluation["recommendation"],
        category_scores=evaluation["category_scores"],
        strengths=evaluation["strengths"],
        gaps=evaluation["gaps"],
        interview_questions=evaluation["interview_questions"]
    )
    db.add(scorecard)

    # 5. Generate and stage draft payload
    action_type_str, subject, payload = ScoringEngine.generate_draft_email(
        candidate_name=aakash.name,
        job_title=tesla_job.title,
        recommendation=evaluation["recommendation"]
    )

    action = StagedAction(
        application_id=app.id,
        action_type=ActionType(action_type_str),
        status=ActionStatus.PENDING_APPROVAL,
        recipient=aakash.email,
        subject=subject,
        payload=payload
    )
    db.add(action)
    db.commit()

    # 6. Stage for approval
    HITLService.stage_for_approval(
        db,
        application=app,
        notes=f"Evaluation complete. Score: {scorecard.overall_score}/100. Staged draft {action_type_str} for manager approval."
    )
    print(f"Staged Application {app.id} for human manager approval!")
else:
    print(f"Application already exists with status: {existing_app.status}")

db.close()
