import hmac
import hashlib
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.models.entities import Job, Candidate, Application, Scorecard, LifecycleState, ModuleName
from backend.app.ml.predict import MLScoringEngine
from backend.app.core.hitl import MasterHITLService

router = APIRouter(prefix="/integrations", tags=["HRMS Integrations & Webhooks"])

WEBHOOK_SECRET = "michelle_hrms_shared_secret_2026"


class WebhookCandidatePayload(BaseModel):
    source_hrms: str = "Workday"  # e.g., "Workday", "Personio", "BambooHR"
    external_event_id: str
    target_req_code: str
    candidate_name: str
    candidate_email: str
    candidate_phone: Optional[str] = None
    raw_resume_text: str


@router.post("/webhook/simulate")
def simulate_hrms_webhook(
    payload: WebhookCandidatePayload,
    db: Session = Depends(get_db)
):
    """
    Simulates receiving an incoming real-time Webhook from an external enterprise HRMS (e.g., Workday).
    Validates payload, runs ML parsing and scoring, and stages the action as PENDING_APPROVAL.
    """
    # 1. Match Job Requisition
    job = db.query(Job).filter(Job.req_code == payload.target_req_code).first()
    if not job:
        job = db.query(Job).first()
        if not job:
            raise HTTPException(status_code=404, detail="No active job requisitions available.")

    # 2. Run MSc ML Evaluation Engine
    engine = MLScoringEngine.get_instance()
    evaluation = engine.evaluate_candidate(
        job_desc=job.description,
        resume_input=payload.raw_resume_text
    )

    # 3. Create Candidate & Application
    candidate = Candidate(
        full_name=payload.candidate_name,
        email=payload.candidate_email,
        phone=payload.candidate_phone,
        raw_resume_text=payload.raw_resume_text,
        parsed_sections=evaluation["parsed_sections"]
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    application = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        lifecycle_state=LifecycleState.PENDING_APPROVAL
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
            f"Thank you for applying via {payload.source_hrms} for the {job.title} role at {job.department}.\n"
            f"Our AI Screening Engine evaluated your profile with an exceptional match score of "
            f"{scorecard.overall_score}/100. We would like to invite you to an introductory interview.\n\n"
            f"Please choose a time slot: https://calendly.com/tesla-recruiting/screen\n\n"
            f"Best regards,\nTalent Acquisition Team"
        )
    else:
        action_type = "REJECTION_NOTIFICATION"
        subject = f"Update regarding your application for {job.title}"
        body = (
            f"Dear {candidate.full_name},\n\n"
            f"Thank you for your interest in the {job.title} role via {payload.source_hrms}.\n"
            f"After reviewing your profile, we have decided to advance other candidates whose current "
            f"skills more closely align with this specific opening.\n\n"
            f"Best regards,\nTalent Acquisition Team"
        )

    staged_payload = {
        "source_system": payload.source_hrms,
        "external_event_id": payload.external_event_id,
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

    # 6. Stage in Master HITL Gate
    staged = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.HIRING,
        action_type=action_type,
        payload=staged_payload,
        entity_reference_id=str(application.id),
        notes=f"Live Webhook Ingestion from {payload.source_hrms}. Score: {scorecard.overall_score}/100."
    )

    return {
        "status": "WEBHOOK_INGESTED_AND_STAGED",
        "source_hrms": payload.source_hrms,
        "application_id": application.id,
        "staged_action_id": staged.id,
        "candidate_name": candidate.full_name,
        "score": scorecard.overall_score,
        "recommendation": scorecard.recommendation
    }
