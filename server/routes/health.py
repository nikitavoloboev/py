"""Health check route."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(
        default="ok", description="Service status marker for external monitors."
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health_check() -> HealthResponse:
    """Expose a simple health probe endpoint."""
    return HealthResponse()
