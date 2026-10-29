from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.app.models.entities import ApplicationStatus, ActionType, ActionStatus


class JobCreate(BaseModel):
    req_id: str
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    description: str
    requirements: Optional[List[str]] = None


class JobResponse(BaseModel):
    id: int
    req_id: str
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    description: str
    requirements: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    education: Optional[str] = None
    raw_resume: str
    parsed_skills: Optional[List[str]] = None


class CandidateResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    education: Optional[str] = None
    parsed_skills: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScorecardResponse(BaseModel):
    id: int
    application_id: int
    overall_score: float
    recommendation: str
    category_scores: Dict[str, float]
    strengths: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    interview_questions: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StagedActionResponse(BaseModel):
    id: int
    application_id: int
    action_type: ActionType
    status: ActionStatus
    recipient: str
    subject: Optional[str] = None
    payload: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    actor: str
    from_status: str
    to_status: str
    notes: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ApplicationDetailResponse(BaseModel):
    id: int
    status: ApplicationStatus
    job: JobResponse
    candidate: CandidateResponse
    scorecard: Optional[ScorecardResponse] = None
    staged_actions: List[StagedActionResponse] = []
    audit_logs: List[AuditLogResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScreenRequest(BaseModel):
    job_id: int
    candidate_name: str
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    candidate_location: Optional[str] = None
    candidate_education: Optional[str] = None
    raw_resume: str


class ApprovalDecision(BaseModel):
    decision: str = Field(..., description="'APPROVE' or 'REJECT'")
    reviewer_name: str
    notes: Optional[str] = None
    edited_payload: Optional[str] = None  # Manager can tweak the drafted email/letter before approving
