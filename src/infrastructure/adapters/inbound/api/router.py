from typing import Annotated

from fastapi import APIRouter, Depends
from hexadian_auth_common.context import UserContext
from hexadian_auth_common.fastapi import require_permission

from src.application.services.sync_service import SyncService
from src.domain.models.entity_type import EntityType
from src.infrastructure.adapters.inbound.api.dtos import HealthResponseDTO, SyncResponseDTO, SyncResultDTO

_SYNC_PERMISSION = "hhh:data:sync"
_SyncAuth = Annotated[UserContext, Depends(require_permission(_SYNC_PERMISSION))]


def create_router(sync_service: SyncService) -> APIRouter:
    """Factory that returns a configured APIRouter with all dataminer endpoints."""
    router = APIRouter()

    @router.get("/health", response_model=HealthResponseDTO)
    async def health() -> HealthResponseDTO:
        return HealthResponseDTO(status="ok")

    @router.post("/sync", response_model=SyncResponseDTO)
    async def sync_all(
        _user: _SyncAuth,
    ) -> SyncResponseDTO:
        results = await sync_service.sync_all()
        return SyncResponseDTO(results=[SyncResultDTO(entity=r.entity, count=r.count) for r in results])

    @router.post("/sync/{entity}", response_model=SyncResultDTO)
    async def sync_entity(
        entity: EntityType,
        _user: _SyncAuth,
    ) -> SyncResultDTO:
        result = await sync_service.sync_entity(entity)
        return SyncResultDTO(entity=result.entity, count=result.count)

    return router
