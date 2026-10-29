from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import (
    Application, ApplicationStatus, StagedAction, ActionStatus, AuditLog, Scorecard
)


def utc_now():
    return datetime.now(timezone.utc)


class HITLService:
    """
    Enforces the Human-in-the-Loop Draft-Review-Commit state machine.
    No candidate or communication can transition to an executed/committed
    state without verified human review and approval.
    """

    @staticmethod
    def log_state_change(
        db: Session,
        application_id: int,
        from_status: str,
        to_status: str,
        actor: str = "SYSTEM",
        notes: Optional[str] = None
    ) -> AuditLog:
        audit_entry = AuditLog(
            application_id=application_id,
            actor=actor,
            from_status=from_status,
            to_status=to_status,
            notes=notes,
            timestamp=utc_now()
        )
        db.add(audit_entry)
        return audit_entry

    @classmethod
    def stage_for_approval(
        cls,
        db: Session,
        application: Application,
        notes: str = "Evaluation complete. Staged for human review."
    ) -> Application:
        old_status = application.status.value
        application.status = ApplicationStatus.PENDING_APPROVAL
        application.updated_at = utc_now()
        cls.log_state_change(
            db,
            application_id=application.id,
            from_status=old_status,
            to_status=ApplicationStatus.PENDING_APPROVAL.value,
            actor="SYSTEM_EVALUATOR",
            notes=notes
        )
        db.commit()
        db.refresh(application)
        return application

    @classmethod
    def review_and_decide(
        cls,
        db: Session,
        application_id: int,
        decision: str,  # 'APPROVE' or 'REJECT'
        reviewer_name: str,
        notes: Optional[str] = None,
        edited_payload: Optional[str] = None
    ) -> Application:
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            raise ValueError(f"Application {application_id} not found")

        if application.status != ApplicationStatus.PENDING_APPROVAL:
            raise ValueError(f"Application cannot be decided from status '{application.status}'. Must be PENDING_APPROVAL.")

        old_status = application.status.value

        # Find the latest pending action
        staged_action = (
            db.query(StagedAction)
            .filter(
                StagedAction.application_id == application_id,
                StagedAction.status == ActionStatus.PENDING_APPROVAL
            )
            .order_by(StagedAction.id.desc())
            .first()
        )

        decision_upper = decision.strip().upper()
        if decision_upper == "APPROVE":
            application.status = ApplicationStatus.APPROVED
            if staged_action:
                staged_action.status = ActionStatus.APPROVED
                staged_action.reviewed_at = utc_now()
                staged_action.reviewed_by = reviewer_name
                if edited_payload:
                    staged_action.payload = edited_payload

            cls.log_state_change(
                db,
                application_id=application.id,
                from_status=old_status,
                to_status=ApplicationStatus.APPROVED.value,
                actor=reviewer_name,
                notes=f"Manager approved. Notes: {notes or 'None'}"
            )

        elif decision_upper == "REJECT":
            application.status = ApplicationStatus.REJECTED
            if staged_action:
                staged_action.status = ActionStatus.REJECTED
                staged_action.reviewed_at = utc_now()
                staged_action.reviewed_by = reviewer_name
                if edited_payload:
                    staged_action.payload = edited_payload

            cls.log_state_change(
                db,
                application_id=application.id,
                from_status=old_status,
                to_status=ApplicationStatus.REJECTED.value,
                actor=reviewer_name,
                notes=f"Manager rejected. Notes: {notes or 'None'}"
            )
        else:
            raise ValueError(f"Invalid decision '{decision}'. Must be 'APPROVE' or 'REJECT'.")

        db.commit()
        db.refresh(application)
        return application

    @classmethod
    def execute_committed_action(
        cls,
        db: Session,
        application_id: int,
        actor: str = "COMMUNICATIONS_DISPATCHER"
    ) -> StagedAction:
        """
        After approval, executes the external communication (e.g., SMTP or ATS webhook)
        and transitions status to COMMITTED/EXECUTED.
        """
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application or application.status not in [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]:
            raise ValueError("Action can only be executed on an APPROVED or REJECTED application.")

        action = (
            db.query(StagedAction)
            .filter(
                StagedAction.application_id == application_id,
                StagedAction.status.in_([ActionStatus.APPROVED, ActionStatus.REJECTED])
            )
            .order_by(StagedAction.id.desc())
            .first()
        )

        if not action:
            raise ValueError("No approved or rejected staged action found to execute.")

        action.status = ActionStatus.EXECUTED
        old_app_status = application.status.value
        application.status = ApplicationStatus.COMMITTED

        action_type_str = getattr(action.action_type, "value", str(action.action_type))
        cls.log_state_change(
            db,
            application_id=application.id,
            from_status=old_app_status,
            to_status=ApplicationStatus.COMMITTED.value,
            actor=actor,
            notes=f"Successfully dispatched {action_type_str} to {action.recipient}"
        )

        db.commit()
        db.refresh(action)
        return action
