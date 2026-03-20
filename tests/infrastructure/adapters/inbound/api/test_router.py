"""Integration tests for the API router."""

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexadian_auth_common.fastapi import JWTAuthDependency, _stub_jwt_auth, register_exception_handlers

from src.application.services.sync_service import SyncResult, SyncService
from src.domain.models.entity_type import EntityType
from src.infrastructure.adapters.inbound.api.router import create_router

_JWT_SECRET = "test-secret-for-dataminer-tests-at-least-32b"
_SYNC_PERMISSION = "hhh:data:sync"


def _make_token(permissions: list[str] | None = None) -> str:
    payload = {
        "sub": "test-user",
        "username": "testuser",
        "permissions": permissions if permissions is not None else [_SYNC_PERMISSION],
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _build_app(sync_service: SyncService) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    jwt_auth = JWTAuthDependency(secret=_JWT_SECRET)
    app.dependency_overrides[_stub_jwt_auth] = jwt_auth
    app.include_router(create_router(sync_service))
    return app


class _StubSyncService:
    """Minimal stub that satisfies SyncService's interface for router tests."""

    async def sync_all(self) -> list[SyncResult]:
        return [SyncResult(entity=e.value, count=0) for e in EntityType]

    async def sync_entity(self, entity: EntityType) -> SyncResult:
        return SyncResult(entity=entity.value, count=42)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_returns_ok() -> None:
    app = _build_app(_StubSyncService())  # type: ignore[arg-type]
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /sync — full sync
# ---------------------------------------------------------------------------


def test_sync_all_requires_auth() -> None:
    app = _build_app(_StubSyncService())  # type: ignore[arg-type]
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/sync")

    assert response.status_code == 401


def test_sync_all_requires_correct_permission() -> None:
    app = _build_app(_StubSyncService())  # type: ignore[arg-type]
    token = _make_token(permissions=["other:permission"])
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/sync", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_sync_all_returns_results() -> None:
    app = _build_app(_StubSyncService())  # type: ignore[arg-type]
    token = _make_token()
    client = TestClient(app)

    response = client.post("/sync", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == len(EntityType)


# ---------------------------------------------------------------------------
# POST /sync/{entity} — single entity sync
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entity", [e.value for e in EntityType])
def test_sync_entity_requires_auth(entity: str) -> None:
    app = _build_app(_StubSyncService())  # type: ignore[arg-type]
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(f"/sync/{entity}")

    assert response.status_code == 401


@pytest.mark.parametrize("entity", [e.value for e in EntityType])
def test_sync_entity_returns_result(entity: str) -> None:
    app = _build_app(_StubSyncService())  # type: ignore[arg-type]
    token = _make_token()
    client = TestClient(app)

    response = client.post(f"/sync/{entity}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["entity"] == entity
    assert data["count"] == 42


def test_sync_unknown_entity_returns_422() -> None:
    app = _build_app(_StubSyncService())  # type: ignore[arg-type]
    token = _make_token()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/sync/unknown-entity", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422
