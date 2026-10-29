from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Job, Candidate, Application, StagedAction, ActionStatus, LifecycleState

router = APIRouter(prefix="/analytics", tags=["Pillar 7: Workforce Analytics & Reports"])


@router.get("/summary")
def get_workforce_summary(db: Session = Depends(get_db)):
    """
    Computes natural-language workforce metrics and operational KPIs (Read-only query).
    """
    total_jobs = db.query(Job).count()
    total_candidates = db.query(Candidate).count()
    total_applications = db.query(Application).count()

    pending_approvals = db.query(StagedAction).filter(StagedAction.status == ActionStatus.PENDING_APPROVAL).count()
    approved_actions = db.query(StagedAction).filter(StagedAction.status == ActionStatus.APPROVED).count()
    executed_actions = db.query(StagedAction).filter(StagedAction.status == ActionStatus.EXECUTED).count()

    # Department breakdown
    jobs = db.query(Job).all()
    dept_distribution = {}
    for j in jobs:
        dept_distribution[j.department] = dept_distribution.get(j.department, 0) + 1

    # Executive NL narrative
    nl_insights = (
        f"Michelle HR System Status: Currently tracking {total_jobs} active job requisitions across "
        f"{len(dept_distribution)} departments. A total of {total_candidates} candidate profiles and "
        f"{total_applications} application lifecycles have been processed through the ML scoring engine. "
        f"There are currently {pending_approvals} actions staged in the HITL review queue awaiting human authorization."
    )

    return {
        "kpis": {
            "total_open_requisitions": total_jobs,
            "total_candidates_screened": total_candidates,
            "total_applications": total_applications,
            "hitl_pending_reviews": pending_approvals,
            "hitl_approved_actions": approved_actions,
            "hitl_executed_actions": executed_actions
        },
        "department_distribution": dept_distribution,
        "executive_narrative": nl_insights
    }
