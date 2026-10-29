import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.entities import (
    Job, Candidate, Application, ApplicationStatus, ActionStatus, ActionType, StagedAction, AuditLog
)
from backend.app.services.scoring_engine import ScoringEngine
from backend.app.services.hitl_service import HITLService

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


def test_complete_hitl_state_machine_and_audit(db):
    # 1. Create Job
    job = Job(
        req_id="TESLA-285983",
        title="AI Adoption & Implementation Internship",
        description="Tesla Cell department SI tools, Python automation, and coding agents at Gigafactory Berlin.",
        department="Tesla SI"
    )
    db.add(job)
    db.commit()

    # 2. Candidate
    resume_text = """
    Aakash Sajikumar Vijayalekshmy
    Berlin, Germany | MSc Data Science student at Arden University
    Backend Developer with 4+ years experience in Python automation, reducing manual overhead by 35%.
    Partnered with stakeholders to identify AI use cases, requirements, and workflow automations.
    Integrated OCR and ETL data pipelines, cutting manual entry by 60%.
    English C1, German A1.
    """
    candidate = Candidate(
        name="Aakash Sajikumar Vijayalekshmy",
        email="aakashsv220@gmail.com",
        location="Berlin, Germany",
        education="MSc Data Science",
        raw_resume=resume_text
    )
    db.add(candidate)
    db.commit()

    # 3. Create Application (Initial DRAFT state)
    app = Application(job_id=job.id, candidate_id=candidate.id, status=ApplicationStatus.DRAFT)
    db.add(app)
    db.commit()

    HITLService.log_state_change(db, app.id, "NONE", ApplicationStatus.DRAFT.value, "SYSTEM", "Application created")
    db.commit()

    # 4. Run Evaluation & Stage for Approval
    evaluation = ScoringEngine.evaluate(job.description, candidate.raw_resume, {})
    assert evaluation["overall_score"] >= 60
    assert evaluation["recommendation"] in ["Strong Hire", "Hire", "Review Required"]

    action_type, subject, payload = ScoringEngine.generate_draft_email(
        candidate.name, job.title, evaluation["recommendation"]
    )
    action = StagedAction(
        application_id=app.id,
        action_type=ActionType(action_type),
        status=ActionStatus.PENDING_APPROVAL,
        recipient=candidate.email,
        subject=subject,
        payload=payload
    )
    db.add(action)
    db.commit()

    app = HITLService.stage_for_approval(db, app, notes="Evaluation ready for recruiter review")
    assert app.status == ApplicationStatus.PENDING_APPROVAL
    assert action.status == ActionStatus.PENDING_APPROVAL

    # 5. Human Decision: APPROVE
    app = HITLService.review_and_decide(
        db=db,
        application_id=app.id,
        decision="APPROVE",
        reviewer_name="Sarah (HR Lead)",
        notes="Strong alignment with automation requirements.",
        edited_payload=None
    )
    assert app.status == ApplicationStatus.APPROVED
    db.refresh(action)
    assert action.status == ActionStatus.APPROVED
    assert action.reviewed_by == "Sarah (HR Lead)"

    # 6. Execute Dispatch (Commit)
    executed_action = HITLService.execute_committed_action(db, app.id, actor="DISPATCHER_ROBOT")
    db.refresh(app)
    assert app.status == ApplicationStatus.COMMITTED
    assert executed_action.status == ActionStatus.EXECUTED

    # 7. Check Audit Trail integrity
    logs = db.query(AuditLog).filter(AuditLog.application_id == app.id).order_by(AuditLog.id.asc()).all()
    assert len(logs) >= 4
    transitions = [(log.from_status, log.to_status) for log in logs]
    assert ("NONE", "DRAFT") in transitions
    assert ("DRAFT", "PENDING_APPROVAL") in transitions
    assert ("PENDING_APPROVAL", "APPROVED") in transitions
    assert ("APPROVED", "COMMITTED") in transitions
