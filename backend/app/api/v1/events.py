from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import ModuleName
from backend.app.schemas.pydantic_schemas import EventPlanRequest
from backend.app.core.hitl import MasterHITLService

router = APIRouter(prefix="/events", tags=["Pillar 6: Company Event Planning"])


@router.post("/plan-offsite")
def plan_company_event(req: EventPlanRequest, db: Session = Depends(get_db)):
    """
    Coordinates company offsite specs, summarizes budget allocation,
    and drafts calendar invite staged as PENDING_APPROVAL.
    """
    total_budget = req.headcount * req.budget_per_head
    catering_allocation = round(total_budget * 0.45, 2)
    venue_allocation = round(total_budget * 0.35, 2)
    activities_allocation = round(total_budget * 0.20, 2)

    calendar_invite_body = (
        f"Team Offsite: {req.event_title}\n\n"
        f"📅 Date: {req.target_date}\n"
        f"📍 Location: {req.location}\n"
        f"👥 Attendees: {req.headcount} team members\n\n"
        f"Agenda Highlights:\n" + "\n".join([f"• {item}" for item in (req.agenda_highlights or ["Team Sync", "Tech Workshops", "Networking Dinner"])]) + "\n\n"
        f"Please RSVP by Friday."
    )

    payload = {
        "event_title": req.event_title,
        "target_date": req.target_date,
        "location": req.location,
        "headcount": req.headcount,
        "budget_breakdown": {
            "total_budget": total_budget,
            "catering": catering_allocation,
            "venue_hire": venue_allocation,
            "team_activities": activities_allocation
        },
        "calendar_invite_payload": {
            "title": f"Offsite: {req.event_title}",
            "body": calendar_invite_body
        }
    }

    staged_action = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.EVENT_PLANNING,
        action_type="EVENT_SCHEDULE_AND_CALENDAR_INVITE",
        payload=payload,
        entity_reference_id=req.event_title,
        notes=f"Staged offsite plan '{req.event_title}' (€{total_budget:,.2f} for {req.headcount} people)."
    )

    return {
        "status": "STAGED_FOR_APPROVAL",
        "staged_action_id": staged_action.id,
        "event_summary": payload
    }
