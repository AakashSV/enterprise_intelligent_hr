from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import ModuleName
from backend.app.schemas.pydantic_schemas import AttendanceAuditRequest
from backend.app.core.hitl import MasterHITLService

router = APIRouter(prefix="/attendance", tags=["Pillar 4: Attendance & Time Tracking"])


@router.post("/audit-timesheet")
def audit_attendance(req: AttendanceAuditRequest, db: Session = Depends(get_db)):
    """
    Audits timesheet punches for anomalies (unusual overtime, missing punches)
    and stages manager review card as PENDING_APPROVAL.
    """
    total_hours = sum(req.logged_hours)
    anomalies = []

    # Flag overtime (> 45 hours in standard 40h week)
    if total_hours > 45.0:
        anomalies.append(f"Excessive overtime flagged: {total_hours}h worked (threshold: 45h).")

    # Flag single-day spike (> 10h)
    for idx, hrs in enumerate(req.logged_hours):
        day_name = ["Mon", "Tue", "Wed", "Thu", "Fri"][idx] if idx < 5 else f"Day {idx+1}"
        if hrs > 10.0:
            anomalies.append(f"Single-day shift spike on {day_name}: {hrs}h logged.")
        elif hrs == 0.0:
            anomalies.append(f"Potential unlogged day or unexcused absence on {day_name}.")

    payload = {
        "employee_id": req.employee_id,
        "employee_name": req.employee_name,
        "week_start": req.week_start,
        "total_logged_hours": total_hours,
        "standard_hours": 40.0,
        "overtime_hours": max(0.0, total_hours - 40.0),
        "requested_pto_days": req.requested_pto_days,
        "anomalies_detected": anomalies,
        "status_recommendation": "FLAGGED_FOR_AUDIT" if anomalies else "STANDARD_REVIEW"
    }

    staged_action = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.ATTENDANCE,
        action_type="TIMESHEET_ANOMALY_REVIEW",
        payload=payload,
        entity_reference_id=req.employee_id,
        notes=f"Attendance audit for {req.employee_name} ({req.week_start}): {len(anomalies)} anomalies detected."
    )

    return {
        "status": "STAGED_FOR_APPROVAL",
        "staged_action_id": staged_action.id,
        "audit_summary": payload
    }
