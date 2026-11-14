"""Root router."""

from fastapi import APIRouter

from app.api import health
from app.api.api_keys import router as api_key_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.jobs import router as job_router
from app.api.settings import router as settings_router
from app.api.templates import build_template_router
from app.api.users import router as user_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(build_template_router())
api_router.include_router(build_template_router(), prefix="/api", include_in_schema=False)
api_router.include_router(auth_router, prefix="/api")
api_router.include_router(user_router, prefix="/api")
api_router.include_router(api_key_router, prefix="/api")
api_router.include_router(audit_router, prefix="/api")
api_router.include_router(job_router, prefix="/api")
api_router.include_router(settings_router, prefix="/api")
