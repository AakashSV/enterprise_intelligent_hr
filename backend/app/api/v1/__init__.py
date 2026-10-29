from fastapi import APIRouter
from backend.app.api.v1 import (
    hiring, onboarding, helpdesk, attendance, payroll, events, analytics, approvals, integrations
)

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(hiring.router)
api_v1_router.include_router(onboarding.router)
api_v1_router.include_router(helpdesk.router)
api_v1_router.include_router(attendance.router)
api_v1_router.include_router(payroll.router)
api_v1_router.include_router(events.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(approvals.router)
api_v1_router.include_router(integrations.router)
