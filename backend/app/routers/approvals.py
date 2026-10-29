from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import (
    Application, StagedAction, AuditLog, ApplicationStatus, ActionStatus
)
from backend.app.schemas.schemas import (
    ApplicationDetailResponse, StagedActionResponse, AuditLogResponse, ApprovalDecision
)
from backend.app.services.hitl_service import HITLService

router = APIRouter(prefix="/api/approvals", tags=["Human-in-the-Loop Approvals"])


@router.get("/pending", response_model=List[ApplicationDetailResponse])
def get_pending_approvals(db: Session = Depends(get_db)):
    """
    Returns all candidate applications currently awaiting human manager approval.
    """
    return (
        db.query(Application)
        .filter(Application.status == ApplicationStatus.PENDING_APPROVAL)
        .order_by(Application.created_at.desc())
        .all()
    )


@router.post("/decide/{app_id}", response_model=ApplicationDetailResponse)
def submit_decision(
    app_id: int,
    decision_in: ApprovalDecision,
    db: Session = Depends(get_db)
):
    """
    Manager endpoint to explicitly APPROVE or REJECT a staged application and action.
    """
    try:
        updated_app = HITLService.review_and_decide(
            db=db,
            application_id=app_id,
            decision=decision_in.decision,
            reviewer_name=decision_in.reviewer_name,
            notes=decision_in.notes,
            edited_payload=decision_in.edited_payload
        )
        return updated_app
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/execute/{app_id}", response_model=StagedActionResponse)
def execute_action(
    app_id: int,
    dispatcher_name: str = "COMMUNICATIONS_DISPATCHER",
    db: Session = Depends(get_db)
):
    """
    Post-approval execution: Triggers the real-world communication dispatch
    (email send / webhook) and locks state as COMMITTED.
    """
    try:
        executed_action = HITLService.execute_committed_action(
            db=db,
            application_id=app_id,
            actor=dispatcher_name
        )
        return executed_action
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/audit/{app_id}", response_model=List[AuditLogResponse])
def get_audit_trail(app_id: int, db: Session = Depends(get_db)):
    """
    Returns the complete, immutable audit trail for a candidate's journey.
    """
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.application_id == app_id)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )
    return logs
