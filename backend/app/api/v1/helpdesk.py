from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import ModuleName
from backend.app.schemas.pydantic_schemas import HelpdeskQueryRequest
from backend.app.core.hitl import MasterHITLService

router = APIRouter(prefix="/helpdesk", tags=["Pillar 3: HR Helpdesk & Ticketing"])

# Mock Company Policy Document Store
POLICY_KB = {
    "pto": "Employees are entitled to 30 days of paid vacation per calendar year. Up to 5 unused days may roll over to Q1.",
    "remote": "Hybrid work allows up to 2 remote days per week subject to direct manager pre-approval.",
    "insurance": "Comprehensive private health, dental, and disability coverage is provided from Day 1 of employment.",
    "overtime": "Overtime must be pre-authorized by team leads and is compensated at 1.5x standard hourly wage."
}


@router.post("/query")
def process_helpdesk_ticket(req: HelpdeskQueryRequest, db: Session = Depends(get_db)):
    """
    Evaluates employee query against policy documents.
    Sensitive queries (grievances, compensation disputes) are strictly staged for Human Manager review.
    """
    text_lower = req.query_text.lower()
    is_sensitive = any(w in text_lower for w in ["grievance", "harassment", "dispute", "salary cut", "discrimination", "lawsuit"])

    # Policy RAG matching
    matched_policy = "Standard Company Employee Handbook (Rev 2026)"
    if "vacation" in text_lower or "pto" in text_lower or "leave" in text_lower:
        policy_answer = POLICY_KB["pto"]
    elif "remote" in text_lower or "home" in text_lower:
        policy_answer = POLICY_KB["remote"]
    elif "insurance" in text_lower or "health" in text_lower or "medical" in text_lower:
        policy_answer = POLICY_KB["insurance"]
    else:
        policy_answer = "Your query has been analyzed against company policies. For case-specific inquiries, HR review is required."

    draft_response = (
        f"Hello {req.employee_name},\n\n"
        f"Regarding your query: '{req.query_text}'\n\n"
        f"Company Policy Reference:\n{policy_answer}\n\n"
        f"Best regards,\nMichelle HR Support"
    )

    payload = {
        "employee_name": req.employee_name,
        "query": req.query_text,
        "category": req.category,
        "is_sensitive": is_sensitive,
        "policy_grounding": matched_policy,
        "draft_response": draft_response
    }

    # If sensitive or policy requires review, stage in HITL gate
    staged_action = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.HELPDESK,
        action_type="HELPDESK_TICKET_RESPONSE",
        payload=payload,
        entity_reference_id=req.employee_name,
        notes=f"Helpdesk ticket from {req.employee_name}. Sensitive: {is_sensitive}."
    )

    return {
        "status": "STAGED_FOR_APPROVAL" if is_sensitive else "DRAFT_READY",
        "staged_action_id": staged_action.id,
        "payload": payload
    }
