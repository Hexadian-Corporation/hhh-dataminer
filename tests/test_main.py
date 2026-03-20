"""Tests for the FastAPI application factory and DI wiring."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.main import create_app


def test_create_app_returns_fastapi_instance() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)


def test_create_app_registers_expected_routes() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/health" in paths
    assert "/sync" in paths
    assert "/sync/{entity}" in paths


def test_health_endpoint_accessible_without_auth() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/sync", "/sync/locations"])
def test_protected_endpoints_require_auth(path: str) -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(path)

    assert response.status_code == 401
