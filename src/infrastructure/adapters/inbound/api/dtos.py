from pydantic import BaseModel


class SyncResultDTO(BaseModel):
    entity: str
    count: int


class SyncResponseDTO(BaseModel):
    results: list[SyncResultDTO]


class HealthResponseDTO(BaseModel):
    status: str
