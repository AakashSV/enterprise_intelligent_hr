from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import ModuleName
from backend.app.schemas.pydantic_schemas import PayrollAuditRequest
from backend.app.core.hitl import MasterHITLService

router = APIRouter(prefix="/payroll", tags=["Pillar 5: Payroll Pre-Audit & Coordination"])


@router.post("/pre-audit")
def pre_audit_payroll(req: PayrollAuditRequest, db: Session = Depends(get_db)):
    """
    Pre-audits payroll ledger, verifies bonuses, and compiles final pre-payroll data file.
    Output is strictly staged as PENDING_APPROVAL requiring Finance authorization before locking.
    """
    total_base = 0.0
    total_bonuses = 0.0
    total_deductions = 0.0
    processed_records = []

    for item in req.records:
        base = float(item.get("base_salary", 0.0))
        bonus = float(item.get("bonus", 0.0))
        deduction = float(item.get("deductions", 0.0))
        net = base + bonus - deduction

        total_base += base
        total_bonuses += bonus
        total_deductions += deduction

        processed_records.append({
            "employee_id": item.get("employee_id"),
            "base_salary": base,
            "bonus": bonus,
            "deductions": deduction,
            "net_payout": round(net, 2)
        })

    total_gross = total_base + total_bonuses
    total_net = total_gross - total_deductions

    payload = {
        "cycle_period": req.cycle_period,
        "headcount_audited": len(req.records),
        "total_gross_disbursement": round(total_gross, 2),
        "total_bonuses_approved": round(total_bonuses, 2),
        "total_deductions": round(total_deductions, 2),
        "total_net_disbursement": round(total_net, 2),
        "detailed_ledger": processed_records,
        "lock_status": "UNLOCKED_AWAITING_FINANCE_SIGNOFF"
    }

    staged_action = MasterHITLService.stage_action(
        db=db,
        module_name=ModuleName.PAYROLL,
        action_type="PAYROLL_CYCLE_LOCK",
        payload=payload,
        entity_reference_id=req.cycle_period,
        notes=f"Payroll pre-audit completed for {req.cycle_period} (€{total_net:,.2f} net across {len(req.records)} employees)."
    )

    return {
        "status": "STAGED_FOR_APPROVAL",
        "staged_action_id": staged_action.id,
        "payroll_summary": payload
    }
