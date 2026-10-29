from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import StagedAction, ActionStatus, AuditLog, ModuleName
from backend.app.schemas.pydantic_schemas import (
    StagedActionResponse, ApprovalDecisionRequest, AuditLogResponse
)
from backend.app.core.hitl import MasterHITLService

router = APIRouter(prefix="/approvals", tags=["Unified HITL Approval Hub"])


@router.get("/pending", response_model=List[StagedActionResponse])
def get_pending_actions(
    module: Optional[ModuleName] = None,
    db: Session = Depends(get_db)
):
    """
    Returns all staged payloads currently awaiting human manager approval across any/all 7 HR pillars.
    """
    query = db.query(StagedAction).filter(StagedAction.status == ActionStatus.PENDING_APPROVAL)
    if module:
        query = query.filter(StagedAction.module_name == module)
    return query.order_by(StagedAction.created_at.desc()).all()


@router.post("/decide/{action_id}", response_model=StagedActionResponse)
def submit_approval_decision(
    action_id: int,
    decision_in: ApprovalDecisionRequest,
    db: Session = Depends(get_db)
):
    """
    Manager endpoint to explicitly APPROVE or REJECT any staged action.
    """
    try:
        updated_action = MasterHITLService.review_and_decide(
            db=db,
            staged_action_id=action_id,
            decision=decision_in.decision,
            reviewer_id=decision_in.reviewer_id,
            notes=decision_in.notes,
            edited_payload=decision_in.edited_payload
        )
        return updated_action
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/execute/{action_id}", response_model=StagedActionResponse)
def dispatch_action(
    action_id: int,
    dispatcher_id: str = "EXECUTION_AGENT",
    db: Session = Depends(get_db)
):
    """
    Post-approval execution: dispatches the action to external systems and locks status as EXECUTED.
    """
    try:
        executed_action = MasterHITLService.execute_action(
            db=db,
            staged_action_id=action_id,
            dispatcher_actor=dispatcher_id
        )
        return executed_action
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/audit", response_model=List[AuditLogResponse])
def get_all_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Returns the immutable chronological audit ledger.
    """
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
