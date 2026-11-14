"""Liveness and readiness routes."""

from fastapi import APIRouter, Response, status

from app.schemas.health import HealthResponse, ReadyResponse
from app.services import health as health_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return health_service.liveness()


@router.get("/ready", response_model=ReadyResponse)
def ready(response: Response) -> ReadyResponse:
    result = health_service.readiness()
    if result.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
