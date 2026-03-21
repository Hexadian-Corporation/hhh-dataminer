import httpx
import opyoid

from src.application.ports.import_port import ImportPort
from src.application.services.sync_service import SyncService
from src.domain.services.hierarchy_validator import HierarchyValidator
from src.infrastructure.adapters.outbound.hhh.hhh_import_adapter import HhhImportAdapter
from src.infrastructure.config.settings import Settings


class AppModule(opyoid.Module):
    """opyoid DI module — binds all application components."""

    def configure(self) -> None:
        settings = Settings()
        self.bind(Settings, to_instance=settings)
        self.bind(httpx.AsyncClient, to_instance=httpx.AsyncClient())
        self.bind(HhhImportAdapter, scope=opyoid.SingletonScope)
        self.bind(ImportPort, to_class=HhhImportAdapter, scope=opyoid.SingletonScope)
        self.bind(HierarchyValidator, scope=opyoid.SingletonScope)
        self.bind(SyncService, to_provider=_SyncServiceProvider, scope=opyoid.SingletonScope)


class _SyncServiceProvider(opyoid.Provider[SyncService]):
    """Provides a SyncService with the registered ImportPort and no sources (initial setup)."""

    def __init__(self, import_adapter: ImportPort, hierarchy_validator: HierarchyValidator) -> None:
        self._import_adapter = import_adapter
        self._hierarchy_validator = hierarchy_validator

    def get(self) -> SyncService:
        return SyncService(
            sources=[],
            import_adapter=self._import_adapter,
            hierarchy_validator=self._hierarchy_validator,
        )
