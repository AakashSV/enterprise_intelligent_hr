from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.app.models.entities import LifecycleState, ModuleName, ActionStatus


class JobCreate(BaseModel):
    req_code: str
    title: str
    department: str
    location: Optional[str] = "Remote / On-site"
    description: str
    required_skills: Optional[List[str]] = []


class JobResponse(BaseModel):
    id: int
    req_code: str
    title: str
    department: str
    location: Optional[str]
    description: str
    required_skills: Optional[List[str]]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScreenCandidateRequest(BaseModel):
    job_id: int
    candidate_name: str
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    raw_resume_text: str  # Can be raw text or file path


class StagedActionResponse(BaseModel):
    id: int
    module_name: ModuleName
    action_type: str
    entity_reference_id: Optional[str] = None
    payload: Any  # Can be dict, string email, or list
    status: ActionStatus
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    approved_by_user_id: Optional[str] = None
    reviewer_notes: Optional[str] = None

    class Config:
        from_attributes = True


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., description="'APPROVE' or 'REJECT'")
    reviewer_id: str
    notes: Optional[str] = None
    edited_payload: Optional[Any] = None


class AuditLogResponse(BaseModel):
    id: int
    staged_action_id: Optional[int]
    module_name: ModuleName
    actor: str
    previous_state: str
    new_state: str
    reviewer_notes: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


# Pillar 2: Onboarding Request
class OnboardingRequest(BaseModel):
    employee_name: str
    role_title: str
    department: str
    start_date: str
    salary_offered: float
    equipment_needed: Optional[List[str]] = ["MacBook Pro", "YubiKey", "Monitor"]


# Pillar 3: Helpdesk Query
class HelpdeskQueryRequest(BaseModel):
    employee_name: str
    query_text: str
    category: Optional[str] = "GENERAL"  # "BENEFITS", "LEAVE", "GRIEVANCE", "PAYROLL"


# Pillar 4: Attendance Anomaly Request
class AttendanceAuditRequest(BaseModel):
    employee_id: str
    employee_name: str
    week_start: str
    logged_hours: List[float]  # Mon to Fri hours
    requested_pto_days: Optional[int] = 0


# Pillar 5: Payroll Pre-Audit Request
class PayrollAuditRequest(BaseModel):
    cycle_period: str  # e.g., "October 2026"
    records: List[Dict[str, Any]]  # [{employee_id, base_salary, bonus, deductions, approved_hours}]


# Pillar 6: Event Request
class EventPlanRequest(BaseModel):
    event_title: str
    target_date: str
    location: str
    headcount: int
    budget_per_head: float
    agenda_highlights: Optional[List[str]] = []
