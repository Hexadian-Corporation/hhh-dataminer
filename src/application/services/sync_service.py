import asyncio
import logging
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar

from src.application.ports.data_source_port import DataSourcePort
from src.application.ports.import_port import ImportPort
from src.domain.models import Commodity, Contract, Distance, EntityType, Location, Ship
from src.domain.services.hierarchy_validator import HierarchyValidator

logger = logging.getLogger(__name__)

_SEMAPHORE_LIMIT = 5
_T = TypeVar("_T")


@dataclass
class SyncResult:
    entity: str
    count: int


class SyncService:
    """Orchestrates the fetch → merge → import pipeline for all entity types."""

    def __init__(
        self,
        sources: list[DataSourcePort],
        import_adapter: ImportPort,
        hierarchy_validator: HierarchyValidator | None = None,
    ) -> None:
        self._sources = sources
        self._import = import_adapter
        self._hierarchy_validator = hierarchy_validator or HierarchyValidator()
        # One semaphore per source adapter to cap concurrent requests per upstream API.
        self._semaphores: dict[int, asyncio.Semaphore] = {
            id(source): asyncio.Semaphore(_SEMAPHORE_LIMIT) for source in sources
        }

    async def sync_all(self) -> list[SyncResult]:
        """Run a full sync for every entity type and return per-entity results.

        Locations are imported first because distances reference location IDs.
        The remaining four entity types are then fetched and imported in parallel.
        """
        locations_result = await self.sync_entity(EntityType.LOCATIONS)
        remaining = [e for e in EntityType if e != EntityType.LOCATIONS]
        other_results = await asyncio.gather(*[self.sync_entity(entity) for entity in remaining])
        return [locations_result] + list(other_results)

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

    async def _guarded(self, source: DataSourcePort, coro: Coroutine[Any, Any, _T]) -> _T:
        """Await *coro* while holding the per-source concurrency-limit semaphore."""
        async with self._semaphores[id(source)]:
            return await coro

    async def _sync_locations(self) -> int:
        all_results: list[list[Location]] = await asyncio.gather(
            *[self._guarded(source, source.fetch_locations()) for source in self._sources]
        )
        merged: dict[str, Location] = {}
        for locations in all_results:
            for loc in locations:
                merged[loc.id] = loc
        locations = list(merged.values())
        count = await self._import.import_locations(locations)

        report = self._hierarchy_validator.validate(locations)
        if report.is_valid:
            logger.info("✅ Hierarchy valid (%d locations)", report.total_locations)
        else:
            logger.warning(
                "⚠️ Hierarchy issues found: %d errors, %d warnings",
                len(report.errors),
                len(report.warnings),
            )
            for issue in report.issues:
                logger.log(
                    logging.ERROR if issue.severity == "ERROR" else logging.WARNING,
                    "  - [%s] %s: %s",
                    issue.severity,
                    issue.rule,
                    issue.message,
                )

        return count

    async def _sync_distances(self) -> int:
        all_results: list[list[Distance]] = await asyncio.gather(
            *[self._guarded(source, source.fetch_distances()) for source in self._sources]
        )
        merged: dict[tuple[str, str], Distance] = {}
        for distances in all_results:
            for dist in distances:
                merged[(dist.from_id, dist.to_id)] = dist
        return await self._import.import_distances(list(merged.values()))

    async def _sync_ships(self) -> int:
        all_results: list[list[Ship]] = await asyncio.gather(
            *[self._guarded(source, source.fetch_ships()) for source in self._sources]
        )
        merged: dict[str, Ship] = {}
        for ships in all_results:
            for ship in ships:
                merged[ship.id] = ship
        return await self._import.import_ships(list(merged.values()))

    async def _sync_commodities(self) -> int:
        all_results: list[list[Commodity]] = await asyncio.gather(
            *[self._guarded(source, source.fetch_commodities()) for source in self._sources]
        )
        merged: dict[str, Commodity] = {}
        for commodities in all_results:
            for commodity in commodities:
                merged[commodity.id] = commodity
        return await self._import.import_commodities(list(merged.values()))

    async def _sync_contracts(self) -> int:
        all_results: list[list[Contract]] = await asyncio.gather(
            *[self._guarded(source, source.fetch_contracts()) for source in self._sources]
        )
        merged: dict[str, Contract] = {}
        for contracts in all_results:
            for contract in contracts:
                merged[contract.id] = contract
        return await self._import.import_contracts(list(merged.values()))
