from dataclasses import dataclass

from src.application.ports.data_source_port import DataSourcePort
from src.application.ports.import_port import ImportPort
from src.domain.models import Commodity, Contract, Distance, EntityType, Location, Ship


@dataclass
class SyncResult:
    entity: str
    count: int


class SyncService:
    """Orchestrates the fetch → merge → import pipeline for all entity types."""

    def __init__(self, sources: list[DataSourcePort], import_adapter: ImportPort) -> None:
        self._sources = sources
        self._import = import_adapter

    async def sync_all(self) -> list[SyncResult]:
        """Run a full sync for every entity type and return per-entity results."""
        results = []
        for entity in EntityType:
            results.append(await self.sync_entity(entity))
        return results

    async def sync_entity(self, entity: EntityType) -> SyncResult:
        """Fetch, merge, and import a single entity type."""
        match entity:
            case EntityType.LOCATIONS:
                count = await self._sync_locations()
            case EntityType.DISTANCES:
                count = await self._sync_distances()
            case EntityType.SHIPS:
                count = await self._sync_ships()
            case EntityType.COMMODITIES:
                count = await self._sync_commodities()
            case EntityType.CONTRACTS:
                count = await self._sync_contracts()
        return SyncResult(entity=entity.value, count=count)

    # ------------------------------------------------------------------
    # Private helpers — one per entity type
    # ------------------------------------------------------------------

    async def _sync_locations(self) -> int:
        merged: dict[str, Location] = {}
        for source in self._sources:
            for loc in await source.fetch_locations():
                merged[loc.id] = loc
        return await self._import.import_locations(list(merged.values()))

    async def _sync_distances(self) -> int:
        merged: dict[tuple[str, str], Distance] = {}
        for source in self._sources:
            for dist in await source.fetch_distances():
                merged[(dist.from_id, dist.to_id)] = dist
        return await self._import.import_distances(list(merged.values()))

    async def _sync_ships(self) -> int:
        merged: dict[str, Ship] = {}
        for source in self._sources:
            for ship in await source.fetch_ships():
                merged[ship.id] = ship
        return await self._import.import_ships(list(merged.values()))

    async def _sync_commodities(self) -> int:
        merged: dict[str, Commodity] = {}
        for source in self._sources:
            for commodity in await source.fetch_commodities():
                merged[commodity.id] = commodity
        return await self._import.import_commodities(list(merged.values()))

    async def _sync_contracts(self) -> int:
        merged: dict[str, Contract] = {}
        for source in self._sources:
            for contract in await source.fetch_contracts():
                merged[contract.id] = contract
        return await self._import.import_contracts(list(merged.values()))
