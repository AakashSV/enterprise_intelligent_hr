from typing import List, Optional
import tempfile
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import (
    Job, Candidate, Application, Scorecard, LifecycleState, ModuleName
)
from backend.app.schemas.pydantic_schemas import (
    JobCreate, JobResponse, ScreenCandidateRequest, StagedActionResponse
)
from backend.app.ml.clean_data import DataPreprocessor
from backend.app.ml.predict import MLScoringEngine
from backend.app.core.hitl import MasterHITLService

router = APIRouter(prefix="/hiring", tags=["Pillar 1: Hiring & Sourcing"])


@router.post("/jobs", response_model=JobResponse)
def create_job(job_in: JobCreate, db: Session = Depends(get_db)):
    existing = db.query(Job).filter(Job.req_code == job_in.req_code).first()
    if existing:
        return existing
    job = Job(
        req_code=job_in.req_code,
        title=job_in.title,
        department=job_in.department,
        location=job_in.location,
        description=job_in.description,
        required_skills=job_in.required_skills or []
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.id.desc()).all()


@router.post("/screen")
def screen_candidate(req: ScreenCandidateRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job requisition not found")

    # 1. Run MSc ML Evaluation Engine
    engine = MLScoringEngine.get_instance()
    evaluation = engine.evaluate_candidate(
        job_desc=job.description,
        resume_input=req.raw_resume_text
    )

    # 2. Persist Candidate
    candidate = Candidate(
        full_name=req.candidate_name,
        email=req.candidate_email,
        phone=req.candidate_phone,
        raw_resume_text=req.raw_resume_text,
        parsed_sections=evaluation["parsed_sections"]
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    # 3. Create Application
    application = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        lifecycle_state=LifecycleState.SCORED
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    # 4. Save Scorecard
    scorecard = Scorecard(
        application_id=application.id,
        overall_score=evaluation["overall_score"],
        recommendation=evaluation["recommendation"],
        category_breakdown=evaluation["category_breakdown"],
        strengths=evaluation["strengths"],
        gaps=evaluation["gaps"],
        generated_interview_questions=evaluation["generated_interview_questions"]
    )
    db.add(scorecard)
    db.commit()

    # 5. Formulate Email Draft Payload
    rec = evaluation["recommendation"]
    if rec in ["Strong Hire", "Hire"]:
        action_type = "OUTREACH_INTERVIEW_INVITE"
        subject = f"Interview Invitation: {job.title} - Gigafactory Berlin"
        body = (
            f"Dear {candidate.full_name},\n\n"
            f"Thank you for applying for the {job.title} position at {job.department}.\n"
            f"Our AI Screening Engine evaluated your profile with an exceptional match score of "
            f"{scorecard.overall_score}/100. We would like to invite you to an introductory interview.\n\n"
            f"Please choose a slot that suits you best: https://calendly.com/tesla-recruiting/screen\n\n"
            f"Best regards,\nTalent Acquisition Team"
        )
    else:
        action_type = "REJECTION_NOTIFICATION"
        subject = f"Update regarding your application for {job.title}"
        body = (
            f"Dear {candidate.full_name},\n\n"
            f"Thank you for your interest in the {job.title} role at {job.department}.\n"
            f"After reviewing your profile, we have decided to advance other candidates whose current "
            f"experience more closely matches this specific opening.\n\n"
            f"We wish you all the best in your career pursuits.\n\n"
            f"Best regards,\nTalent Acquisition Team"
        )

    payload = {
        "candidate_id": candidate.id,
        "candidate_name": candidate.full_name,
        "candidate_email": candidate.email,
        "job_title": job.title,
        "match_score": scorecard.overall_score,
        "recommendation": scorecard.recommendation,
        "category_breakdown": scorecard.category_breakdown,
        "strengths": scorecard.strengths,
        "gaps": scorecard.gaps,
        "interview_questions": scorecard.generated_interview_questions,
        "email_subject": subject,
        "email_body": body
    }

    # 6. Stage via Unified Master HITL Service
    staged = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.HIRING,
        action_type=action_type,
        payload=payload,
        entity_reference_id=str(application.id),
        notes=f"Candidate evaluated with score {scorecard.overall_score}/100 ({scorecard.recommendation}). Payload staged."
    )

    application.lifecycle_state = LifecycleState.PENDING_APPROVAL
    db.commit()

    return {
        "status": "STAGED_FOR_APPROVAL",
        "application_id": application.id,
        "staged_action_id": staged.id,
        "candidate": candidate.full_name,
        "scorecard": {
            "score": scorecard.overall_score,
            "recommendation": scorecard.recommendation,
            "category_breakdown": scorecard.category_breakdown,
            "strengths": scorecard.strengths,
            "gaps": scorecard.gaps,
            "interview_questions": scorecard.generated_interview_questions
        },
        "staged_payload": payload
    }


@router.post("/upload-resume")
async def upload_resume_file(
    job_id: int = Form(...),
    candidate_name: str = Form(...),
    candidate_email: Optional[str] = Form(None),
    candidate_phone: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts uploaded .pdf, .docx, or .txt resume file.
    Extracts text, masks PII, runs ML scoring, and stages outreach/rejection as PENDING_APPROVAL.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job requisition not found")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".doc", ".txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, DOCX, or TXT.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 1. Parse text using DataPreprocessor
        raw_text = DataPreprocessor.parse_document(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    if not raw_text or len(raw_text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Unable to extract meaningful text from the uploaded file.")

    # Delegate to screening logic
    req = ScreenCandidateRequest(
        job_id=job_id,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        candidate_phone=candidate_phone,
        raw_resume_text=raw_text
    )
    return screen_candidate(req=req, db=db)

