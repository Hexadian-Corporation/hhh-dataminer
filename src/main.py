import opyoid
import uvicorn
from fastapi import FastAPI
from hexadian_auth_common.fastapi import JWTAuthDependency, _stub_jwt_auth, register_exception_handlers

from src.application.services.sync_service import SyncService
from src.infrastructure.adapters.inbound.api.router import create_router
from src.infrastructure.config.dependencies import AppModule
from src.infrastructure.config.settings import Settings


def create_app() -> FastAPI:
    """FastAPI application factory."""
    injector = opyoid.Injector([AppModule()])
    settings = injector.inject(Settings)
    sync_service = injector.inject(SyncService)

    app = FastAPI(title="hhh-dataminer", description="Game data mining and import orchestration for H³")

    register_exception_handlers(app)

    jwt_auth = JWTAuthDependency(secret=settings.jwt_secret)
    app.dependency_overrides[_stub_jwt_auth] = jwt_auth

    app.include_router(create_router(sync_service))

    return app


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    uvicorn.run("src.main:app", host="0.0.0.0", port=8008, reload=True)
