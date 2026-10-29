from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import (
    StagedAction, ActionStatus, AuditLog, ModuleName, Application, LifecycleState
)


def utc_now():
    return datetime.now(timezone.utc)


class MasterHITLService:
    """
    Central Human-in-the-Loop (HITL) Policy Engine.
    Governs state transitions, staged action approvals, and immutable audit logs
    across all 7 HR functional pillars.
    """

    @classmethod
    def stage_action(
        cls,
        db: Session,
        module_name: ModuleName,
        action_type: str,
        payload: Dict[str, Any],
        entity_reference_id: Optional[str] = None,
        notes: str = "Automated draft staged for human review."
    ) -> StagedAction:
        """
        Creates a new action strictly in PENDING_APPROVAL status.
        No execution is triggered at this stage.
        """
        staged_action = StagedAction(
            module_name=module_name,
            action_type=action_type,
            entity_reference_id=entity_reference_id,
            payload=payload,
            status=ActionStatus.PENDING_APPROVAL,
            created_at=utc_now()
        )
        db.add(staged_action)
        db.commit()
        db.refresh(staged_action)

        # Log creation in audit trail
        audit_entry = AuditLog(
            staged_action_id=staged_action.id,
            module_name=module_name,
            actor="SYSTEM_AI",
            previous_state="NONE",
            new_state=ActionStatus.PENDING_APPROVAL.value,
            reviewer_notes=notes,
            timestamp=utc_now()
        )
        db.add(audit_entry)
        db.commit()

        return staged_action

    @classmethod
    def review_and_decide(
        cls,
        db: Session,
        staged_action_id: int,
        decision: str,  # 'APPROVE' or 'REJECT'
        reviewer_id: str,
        notes: Optional[str] = None,
        edited_payload: Optional[Dict[str, Any]] = None
    ) -> StagedAction:
        """
        Manager approval gate. Explicitly accepts or rejects the staged payload.
        """
        action = db.query(StagedAction).filter(StagedAction.id == staged_action_id).first()
        if not action:
            raise ValueError(f"Staged action #{staged_action_id} not found")

        if action.status != ActionStatus.PENDING_APPROVAL:
            raise ValueError(f"Cannot decide on action with status '{action.status}'. Must be PENDING_APPROVAL.")

        prev_status = action.status.value
        dec_upper = decision.strip().upper()

        if dec_upper == "APPROVE":
            action.status = ActionStatus.APPROVED
            action.reviewed_at = utc_now()
            action.approved_by_user_id = reviewer_id
            action.reviewer_notes = notes
            if edited_payload is not None:
                action.payload = edited_payload

            # If this is linked to a hiring application, update application state
            if action.module_name == ModuleName.HIRING and action.entity_reference_id:
                try:
                    app = db.query(Application).filter(Application.id == int(action.entity_reference_id)).first()
                    if app:
                        app.lifecycle_state = LifecycleState.APPROVED
                except Exception:
                    pass

        elif dec_upper == "REJECT":
            action.status = ActionStatus.REJECTED
            action.reviewed_at = utc_now()
            action.approved_by_user_id = reviewer_id
            action.reviewer_notes = notes

            if action.module_name == ModuleName.HIRING and action.entity_reference_id:
                try:
                    app = db.query(Application).filter(Application.id == int(action.entity_reference_id)).first()
                    if app:
                        app.lifecycle_state = LifecycleState.REJECTED
                except Exception:
                    pass
        else:
            raise ValueError(f"Invalid decision '{decision}'. Must be 'APPROVE' or 'REJECT'.")

        # Record immutable audit log
        audit = AuditLog(
            staged_action_id=action.id,
            module_name=action.module_name,
            actor=reviewer_id,
            previous_state=prev_status,
            new_state=action.status.value,
            reviewer_notes=notes or f"Manager marked as {dec_upper}",
            timestamp=utc_now()
        )
        db.add(audit)
        db.commit()
        db.refresh(action)
        return action

    @classmethod
    def execute_action(
        cls,
        db: Session,
        staged_action_id: int,
        dispatcher_actor: str = "EXECUTION_INTEGRATION_AGENT"
    ) -> StagedAction:
        """
        Post-approval dispatch: Finalizes the action in real-world systems
        and locks the status as EXECUTED.
        """
        action = db.query(StagedAction).filter(StagedAction.id == staged_action_id).first()
        if not action:
            raise ValueError(f"Staged action #{staged_action_id} not found")

        if action.status not in [ActionStatus.APPROVED, ActionStatus.REJECTED]:
            raise ValueError(f"Action must be APPROVED or REJECTED to execute. Current: {action.status}")

        prev_status = action.status.value
        action.status = ActionStatus.EXECUTED

        # If hiring application, mark as committed
        if action.module_name == ModuleName.HIRING and action.entity_reference_id:
            try:
                app = db.query(Application).filter(Application.id == int(action.entity_reference_id)).first()
                if app:
                    app.lifecycle_state = LifecycleState.COMMITTED
            except Exception:
                pass

        audit = AuditLog(
            staged_action_id=action.id,
            module_name=action.module_name,
            actor=dispatcher_actor,
            previous_state=prev_status,
            new_state=ActionStatus.EXECUTED.value,
            reviewer_notes=f"Dispatched {action.action_type} for {action.module_name.value}",
            timestamp=utc_now()
        )
        db.add(audit)
        db.commit()
        db.refresh(action)
        return action
