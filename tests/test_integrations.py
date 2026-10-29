import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.entities import Job, StagedAction, ActionStatus, ModuleName
from backend.app.api.v1.integrations import simulate_hrms_webhook, WebhookCandidatePayload

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


def test_live_hrms_webhook_ingestion(db):
    # 1. Create Job Requisition
    job = Job(
        req_code="285983",
        title="AI Adoption & Implementation Internship",
        department="Tesla SI / Battery Cell",
        description="Tesla Gigafactory Berlin Cell department. Python automation, coding agents, ETL pipelines."
    )
    db.add(job)
    db.commit()

    # 2. Simulate Workday Webhook Payload
    payload = WebhookCandidatePayload(
        source_hrms="Workday",
        external_event_id="WD-EVENT-998811",
        target_req_code="285983",
        candidate_name="Elena Rostova",
        candidate_email="elena.rostova@example.com",
        raw_resume_text="Senior Python Automation Engineer with 5+ years experience building automated ETL pipelines and ML integrations in Berlin."
    )

    res = simulate_hrms_webhook(payload=payload, db=db)

    assert res["status"] == "WEBHOOK_INGESTED_AND_STAGED"
    assert res["source_hrms"] == "Workday"
    assert res["score"] > 60.0

    # 3. Verify it is staged as PENDING_APPROVAL
    staged = db.query(StagedAction).filter(StagedAction.id == res["staged_action_id"]).first()
    assert staged is not None
    assert staged.status == ActionStatus.PENDING_APPROVAL
    assert staged.module_name == ModuleName.HIRING
    assert "OUTREACH" in staged.action_type or "INTERVIEW" in staged.action_type
