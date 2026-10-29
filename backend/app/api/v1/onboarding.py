from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import ModuleName
from backend.app.schemas.pydantic_schemas import OnboardingRequest, StagedActionResponse
from backend.app.core.hitl import MasterHITLService

router = APIRouter(prefix="/onboarding", tags=["Pillar 2: Onboarding & Offboarding"])


@router.post("/generate-checklist")
def generate_onboarding_package(req: OnboardingRequest, db: Session = Depends(get_db)):
    """
    Generates dynamic onboarding package: IT hardware provisioning, access roles,
    and draft contract terms, staged strictly as PENDING_APPROVAL.
    """
    # Dynamic department tasks
    dept_tasks = {
        "Engineering": [
            "GitHub Enterprise access & 2FA enrollment",
            "AWS / Cloud sandbox environment credentials",
            "CI/CD build pipeline role assignment"
        ],
        "Tesla SI / Battery Cell": [
            "Shop-floor cell manufacturing safety induction",
            "Internal SI platform & coding agent API token access",
            "Cleanroom protocol clearance certification"
        ],
        "General": [
            "HR portal & benefits portal registration",
            "Workplace Slack / Teams workspace invite",
            "Direct deposit banking setup"
        ]
    }

    selected_tasks = dept_tasks.get(req.department, dept_tasks["General"]) + dept_tasks["General"]

    payload = {
        "employee_name": req.employee_name,
        "role_title": req.role_title,
        "department": req.department,
        "start_date": req.start_date,
        "salary_offered": req.salary_offered,
        "it_hardware_provisioning": req.equipment_needed,
        "access_provisioning_tasks": selected_tasks,
        "contract_terms_summary": (
            f"Full-time employment as {req.role_title} within {req.department}. "
            f"Annual compensation €{req.salary_offered:,.2f}. Standard probation period of 6 months. "
            f"Effective start date: {req.start_date}."
        )
    }

    staged_action = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.ONBOARDING,
        action_type="ONBOARDING_PACKAGE_AND_CONTRACT",
        payload=payload,
        entity_reference_id=req.employee_name,
        notes=f"Generated onboarding checklist and contract terms for {req.employee_name} ({req.role_title})."
    )

    return {
        "status": "STAGED_FOR_APPROVAL",
        "staged_action_id": staged_action.id,
        "employee": req.employee_name,
        "package": payload
    }
