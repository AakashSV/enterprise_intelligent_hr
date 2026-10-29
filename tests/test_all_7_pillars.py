import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.entities import (
    Job, Candidate, Application, StagedAction, ActionStatus, ModuleName, AuditLog
)
from backend.app.core.hitl import MasterHITLService
from backend.app.ml.predict import MLScoringEngine

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_pillar_1_hiring_and_ml_scoring(db):
    engine = MLScoringEngine.get_instance()
    jd = "Tesla Gigafactory Berlin Cell department. Python automation, coding agents, ETL pipelines."
    resume = "MSc Data Science student in Berlin with 4+ years in Python automation and ETL pipelines."
    eval_res = engine.evaluate_candidate(jd, resume)

    assert eval_res["overall_score"] > 50.0
    assert eval_res["recommendation"] in ["Strong Hire", "Hire", "Review Required"]
    assert "dense_semantic_similarity" in eval_res["category_breakdown"]


def test_all_7_pillars_hitl_lifecycle_and_audit(db):
    # 1. Pillar 1: Hiring
    staged_hiring = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.HIRING,
        action_type="OUTREACH_INTERVIEW_INVITE",
        payload={"candidate": "Aakash", "email": "aakash@example.com", "score": 90.0},
        entity_reference_id="APP-101"
    )
    assert staged_hiring.status == ActionStatus.PENDING_APPROVAL

    # 2. Pillar 2: Onboarding
    staged_onboarding = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.ONBOARDING,
        action_type="ONBOARDING_PACKAGE",
        payload={"employee": "Elena Rostova", "department": "Battery Cell", "hardware": ["MacBook Pro"]},
        entity_reference_id="EMP-202"
    )
    assert staged_onboarding.status == ActionStatus.PENDING_APPROVAL

    # 3. Pillar 3: Helpdesk
    staged_helpdesk = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.HELPDESK,
        action_type="GRIEVANCE_TICKET_ESCALATION",
        payload={"employee": "David K", "issue": "Overtime calculation dispute"},
        entity_reference_id="TICKET-303"
    )
    assert staged_helpdesk.status == ActionStatus.PENDING_APPROVAL

    # 4. Pillar 4: Attendance Anomaly
    staged_attendance = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.ATTENDANCE,
        action_type="OVERTIME_ANOMALY_REVIEW",
        payload={"employee": "Marcus Weber", "overtime_hours": 12.5, "flag": "EXCESSIVE_HOURS"},
        entity_reference_id="ATT-404"
    )
    assert staged_attendance.status == ActionStatus.PENDING_APPROVAL

    # 5. Pillar 5: Payroll Pre-Audit
    staged_payroll = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.PAYROLL,
        action_type="PAYROLL_CYCLE_LOCK",
        payload={"period": "October 2026", "net_disbursement": 450000.0, "lock_state": "PENDING_FINANCE"},
        entity_reference_id="OCT-2026"
    )
    assert staged_payroll.status == ActionStatus.PENDING_APPROVAL

    # 6. Pillar 6: Event Planning
    staged_event = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.EVENT_PLANNING,
        action_type="OFFSITE_CALENDAR_INVITE",
        payload={"title": "Q4 Strategy Summit", "location": "Potsdam", "budget": 8500.0},
        entity_reference_id="EVT-606"
    )
    assert staged_event.status == ActionStatus.PENDING_APPROVAL

    # Verify all 6 are queued in PENDING_APPROVAL
    pending_items = db.query(StagedAction).filter(StagedAction.status == ActionStatus.PENDING_APPROVAL).all()
    assert len(pending_items) == 6

    # Test Human Decision: APPROVE Payroll Lock
    decided_payroll = MasterHITLService.review_and_decide(
        db=db,
        staged_action_id=staged_payroll.id,
        decision="APPROVE",
        reviewer_id="VP_Finance_Director",
        notes="Pre-audit numbers reconciled against ledger. Approved for release."
    )
    assert decided_payroll.status == ActionStatus.APPROVED

    # Test Post-Approval Execution Dispatch
    executed_payroll = MasterHITLService.execute_action(
        db=db,
        staged_action_id=decided_payroll.id,
        dispatcher_actor="PAYROLL_DISPATCH_BOT"
    )
    assert executed_payroll.status == ActionStatus.EXECUTED

    # Test Human Decision: REJECT Event Plan (Budget revision required)
    decided_event = MasterHITLService.review_and_decide(
        db=db,
        staged_action_id=staged_event.id,
        decision="REJECT",
        reviewer_id="HR_Operations_Lead",
        notes="Budget exceeds Q4 cap. Re-quote venue."
    )
    assert decided_event.status == ActionStatus.REJECTED

    # Audit Trail Integrity Check
    logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    assert len(logs) >= 8
    payroll_logs = [l for l in logs if l.staged_action_id == staged_payroll.id]
    assert len(payroll_logs) == 3
    transitions = [(l.previous_state, l.new_state) for l in payroll_logs]
    assert ("NONE", "PENDING_APPROVAL") in transitions
    assert ("PENDING_APPROVAL", "APPROVED") in transitions
    assert ("APPROVED", "EXECUTED") in transitions
