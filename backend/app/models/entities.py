import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Enum, ForeignKey, JSON
)
from sqlalchemy.orm import relationship, synonym
from backend.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class LifecycleState(str, enum.Enum):
    DRAFT = "DRAFT"
    PARSED = "PARSED"
    SCORED = "SCORED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMMITTED = "COMMITTED"


# Backward compatibility aliases
ApplicationStatus = LifecycleState
ActionType = str


class ModuleName(str, enum.Enum):
    HIRING = "HIRING"
    ONBOARDING = "ONBOARDING"
    OFFBOARDING = "OFFBOARDING"
    HELPDESK = "HELPDESK"
    ATTENDANCE = "ATTENDANCE"
    PAYROLL = "PAYROLL"
    EVENT_PLANNING = "EVENT_PLANNING"
    ANALYTICS = "ANALYTICS"


class ActionStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    req_code = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    department = Column(String(128), nullable=False)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    required_skills = Column(JSON, nullable=True)
    status = Column(String(32), default="OPEN", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Aliases for compatibility
    req_id = synonym("req_code")
    requirements = synonym("required_skills")

    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), index=True, nullable=True)
    phone = Column(String(64), nullable=True)
    location = Column(String(255), nullable=True)
    education = Column(Text, nullable=True)
    raw_resume_text = Column(Text, nullable=False)
    parsed_sections = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Aliases
    name = synonym("full_name")
    raw_resume = synonym("raw_resume_text")
    parsed_skills = synonym("parsed_sections")

    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    lifecycle_state = Column(Enum(LifecycleState), default=LifecycleState.DRAFT, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    status = synonym("lifecycle_state")

    job = relationship("Job", back_populates="applications")
    candidate = relationship("Candidate", back_populates="applications")
    scorecard = relationship("Scorecard", back_populates="application", uselist=False, cascade="all, delete-orphan")
    staged_actions = relationship("StagedAction", back_populates="application", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="application", cascade="all, delete-orphan")


class Scorecard(Base):
    __tablename__ = "scorecards"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, nullable=False)
    overall_score = Column(Float, nullable=False)
    recommendation = Column(String(64), nullable=False)
    category_breakdown = Column(JSON, nullable=False)
    strengths = Column(JSON, nullable=True)
    gaps = Column(JSON, nullable=True)
    generated_interview_questions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    category_scores = synonym("category_breakdown")
    interview_questions = synonym("generated_interview_questions")

    application = relationship("Application", back_populates="scorecard")


class StagedAction(Base):
    __tablename__ = "staged_actions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=True)
    module_name = Column(Enum(ModuleName), default=ModuleName.HIRING, nullable=False, index=True)
    action_type = Column(String(128), nullable=False)
    entity_reference_id = Column(String(128), nullable=True)
    recipient = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=False)
    status = Column(Enum(ActionStatus), default=ActionStatus.PENDING_APPROVAL, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    approved_by_user_id = Column(String(128), nullable=True)
    reviewer_notes = Column(Text, nullable=True)

    reviewed_by = synonym("approved_by_user_id")

    application = relationship("Application", back_populates="staged_actions")
    audit_logs = relationship("AuditLog", back_populates="staged_action", cascade="all, delete-orphan")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=True)
    staged_action_id = Column(Integer, ForeignKey("staged_actions.id", ondelete="CASCADE"), nullable=True)
    module_name = Column(Enum(ModuleName), default=ModuleName.HIRING, nullable=False)
    actor = Column(String(128), nullable=False)
    previous_state = Column(String(64), nullable=False)
    new_state = Column(String(64), nullable=False)
    reviewer_notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False)

    from_status = synonym("previous_state")
    to_status = synonym("new_state")
    notes = synonym("reviewer_notes")

    application = relationship("Application", back_populates="audit_logs")
    staged_action = relationship("StagedAction", back_populates="audit_logs")
