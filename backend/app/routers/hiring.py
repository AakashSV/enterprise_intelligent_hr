from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import (
    Job, Candidate, Application, Scorecard, StagedAction, ApplicationStatus, ActionType, ActionStatus
)
from backend.app.schemas.schemas import (
    JobCreate, JobResponse, CandidateResponse, ScorecardResponse,
    ApplicationDetailResponse, ScreenRequest
)
from backend.app.services.scoring_engine import ScoringEngine
from backend.app.services.hitl_service import HITLService

router = APIRouter(prefix="/api/hiring", tags=["Hiring & Sourcing"])


@router.post("/jobs", response_model=JobResponse)
def create_job(job_in: JobCreate, db: Session = Depends(get_db)):
    existing = db.query(Job).filter(Job.req_id == job_in.req_id).first()
    if existing:
        return existing
    job = Job(
        req_id=job_in.req_id,
        title=job_in.title,
        department=job_in.department,
        location=job_in.location,
        description=job_in.description,
        requirements=job_in.requirements or []
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.id.desc()).all()


@router.post("/screen", response_model=ApplicationDetailResponse)
def screen_candidate(req: ScreenRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job requisition not found")

    # 1. Parse & create candidate
    extracted_skills = ScoringEngine.extract_skills(req.raw_resume)
    candidate = Candidate(
        name=req.candidate_name,
        email=req.candidate_email,
        phone=req.candidate_phone,
        location=req.candidate_location,
        education=req.candidate_education,
        raw_resume=req.raw_resume,
        parsed_skills=extracted_skills
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    # 2. Create Application in DRAFT state
    application = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        status=ApplicationStatus.DRAFT
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    HITLService.log_state_change(
        db,
        application_id=application.id,
        from_status="NONE",
        to_status=ApplicationStatus.DRAFT.value,
        actor="SYSTEM",
        notes=f"Candidate {candidate.name} parsed and created."
    )

    # 3. Run Scoring Engine
    evaluation = ScoringEngine.evaluate(
        job_desc=job.description,
        resume_text=candidate.raw_resume,
        candidate_meta={"location": candidate.location, "education": candidate.education}
    )

    scorecard = Scorecard(
        application_id=application.id,
        overall_score=evaluation["overall_score"],
        recommendation=evaluation["recommendation"],
        category_scores=evaluation["category_scores"],
        strengths=evaluation["strengths"],
        gaps=evaluation["gaps"],
        interview_questions=evaluation["interview_questions"]
    )
    db.add(scorecard)

    # 4. Generate Drafted Payload (Pending Approval)
    action_type_str, subject, payload = ScoringEngine.generate_draft_email(
        candidate_name=candidate.name,
        job_title=job.title,
        recommendation=evaluation["recommendation"]
    )

    action = StagedAction(
        application_id=application.id,
        action_type=ActionType(action_type_str),
        status=ActionStatus.PENDING_APPROVAL,
        recipient=candidate.email or "unspecified@candidate.com",
        subject=subject,
        payload=payload
    )
    db.add(action)
    db.commit()

    # 5. Transition to PENDING_APPROVAL via HITL Service
    application = HITLService.stage_for_approval(
        db,
        application=application,
        notes=f"Scorecard calculated ({scorecard.overall_score}/100, {scorecard.recommendation}). Payload staged."
    )

    db.refresh(application)
    return application


@router.get("/applications/{app_id}", response_model=ApplicationDetailResponse)
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.get("/applications", response_model=List[ApplicationDetailResponse])
def list_applications(db: Session = Depends(get_db)):
    return db.query(Application).order_by(Application.id.desc()).all()
