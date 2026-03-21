"""Unit tests for SyncService."""

import asyncio
import time

import pytest

from src.application.ports.data_source_port import DataSourcePort
from src.application.ports.import_port import ImportPort
from src.application.services.sync_service import _SEMAPHORE_LIMIT, SyncResult, SyncService
from src.domain.models import Commodity, Contract, Distance, EntityType, Location, Ship


class _StubSource(DataSourcePort):
    """Stub DataSourcePort that returns configurable test data."""

    def __init__(
        self,
        locations: list[Location] | None = None,
        distances: list[Distance] | None = None,
        ships: list[Ship] | None = None,
        commodities: list[Commodity] | None = None,
        contracts: list[Contract] | None = None,
    ) -> None:
        self._locations = locations or []
        self._distances = distances or []
        self._ships = ships or []
        self._commodities = commodities or []
        self._contracts = contracts or []

    async def fetch_locations(self) -> list[Location]:
        return self._locations

    async def fetch_distances(self) -> list[Distance]:
        return self._distances

    async def fetch_ships(self) -> list[Ship]:
        return self._ships

    async def fetch_commodities(self) -> list[Commodity]:
        return self._commodities

    async def fetch_contracts(self) -> list[Contract]:
        return self._contracts


class _StubImport(ImportPort):
    """Stub ImportPort that captures imported data for assertions."""

    def __init__(self) -> None:
        self.locations: list[Location] = []
        self.distances: list[Distance] = []
        self.ships: list[Ship] = []
        self.commodities: list[Commodity] = []
        self.contracts: list[Contract] = []

    async def import_locations(self, locations: list[Location]) -> int:
        self.locations = locations
        return len(locations)

    async def import_distances(self, distances: list[Distance]) -> int:
        self.distances = distances
        return len(distances)

    async def import_ships(self, ships: list[Ship]) -> int:
        self.ships = ships
        return len(ships)

    async def import_commodities(self, commodities: list[Commodity]) -> int:
        self.commodities = commodities
        return len(commodities)

    async def import_contracts(self, contracts: list[Contract]) -> int:
        self.contracts = contracts
        return len(contracts)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_entity_locations_no_sources() -> None:
    importer = _StubImport()
    service = SyncService(sources=[], import_adapter=importer)

    result = await service.sync_entity(EntityType.LOCATIONS)

    assert result == SyncResult(entity="locations", count=0)
    assert importer.locations == []


@pytest.mark.asyncio
async def test_sync_entity_locations_single_source() -> None:
    loc = Location(id="loc1", name="Hurston", type="planet", system="Stanton")
    importer = _StubImport()
    source = _StubSource(locations=[loc])
    service = SyncService(sources=[source], import_adapter=importer)

    result = await service.sync_entity(EntityType.LOCATIONS)

    assert result == SyncResult(entity="locations", count=1)
    assert importer.locations == [loc]


@pytest.mark.asyncio
async def test_sync_entity_locations_deduplication() -> None:
    """Later source wins when two sources share the same ID."""
    loc_v1 = Location(id="loc1", name="Hurston v1", type="planet")
    loc_v2 = Location(id="loc1", name="Hurston v2", type="planet", system="Stanton")
    importer = _StubImport()
    source1 = _StubSource(locations=[loc_v1])
    source2 = _StubSource(locations=[loc_v2])
    service = SyncService(sources=[source1, source2], import_adapter=importer)

    result = await service.sync_entity(EntityType.LOCATIONS)

    assert result == SyncResult(entity="locations", count=1)
    assert importer.locations == [loc_v2]


@pytest.mark.asyncio
async def test_sync_entity_distances() -> None:
    dist = Distance(from_id="loc1", to_id="loc2", distance_km=1_000.0)
    importer = _StubImport()
    source = _StubSource(distances=[dist])
    service = SyncService(sources=[source], import_adapter=importer)

    result = await service.sync_entity(EntityType.DISTANCES)

    assert result == SyncResult(entity="distances", count=1)
    assert importer.distances == [dist]


@pytest.mark.asyncio
async def test_sync_entity_ships() -> None:
    ship = Ship(id="ship1", name="Caterpillar", manufacturer="Drake", cargo_scu=576)
    importer = _StubImport()
    source = _StubSource(ships=[ship])
    service = SyncService(sources=[source], import_adapter=importer)

    result = await service.sync_entity(EntityType.SHIPS)

    assert result == SyncResult(entity="ships", count=1)
    assert importer.ships == [ship]


@pytest.mark.asyncio
async def test_sync_entity_commodities() -> None:
    commodity = Commodity(id="c1", name="Agricium", category="Metal", base_price_uec=875.0)
    importer = _StubImport()
    source = _StubSource(commodities=[commodity])
    service = SyncService(sources=[source], import_adapter=importer)

    result = await service.sync_entity(EntityType.COMMODITIES)

    assert result == SyncResult(entity="commodities", count=1)
    assert importer.commodities == [commodity]


@pytest.mark.asyncio
async def test_sync_entity_contracts() -> None:
    contract = Contract(id="ct1", title="Haul medical supplies", type="hauling", payout_uec=25_000.0)
    importer = _StubImport()
    source = _StubSource(contracts=[contract])
    service = SyncService(sources=[source], import_adapter=importer)

    result = await service.sync_entity(EntityType.CONTRACTS)

    assert result == SyncResult(entity="contracts", count=1)
    assert importer.contracts == [contract]


@pytest.mark.asyncio
async def test_sync_all_returns_one_result_per_entity() -> None:
    importer = _StubImport()
    service = SyncService(sources=[], import_adapter=importer)

    results = await service.sync_all()

    assert len(results) == len(EntityType)
    entities = {r.entity for r in results}
    assert entities == {e.value for e in EntityType}


@pytest.mark.asyncio
async def test_sync_all_with_data() -> None:
    loc = Location(id="loc1", name="Hurston", type="planet")
    ship = Ship(id="ship1", name="Caterpillar", manufacturer="Drake", cargo_scu=576)
    importer = _StubImport()
    source = _StubSource(locations=[loc], ships=[ship])
    service = SyncService(sources=[source], import_adapter=importer)

    results = await service.sync_all()

    by_entity = {r.entity: r.count for r in results}
    assert by_entity["locations"] == 1
    assert by_entity["ships"] == 1
    assert by_entity["distances"] == 0
    assert by_entity["commodities"] == 0
    assert by_entity["contracts"] == 0


@pytest.mark.asyncio
async def test_sync_all_locations_imported_before_others() -> None:
    """Locations must be fully imported before other entity syncs start."""
    import_order: list[str] = []

    class _OrderedImport(_StubImport):
        async def import_locations(self, locations: list[Location]) -> int:
            import_order.append("locations")
            return await super().import_locations(locations)

        async def import_distances(self, distances: list[Distance]) -> int:
            import_order.append("distances")
            return await super().import_distances(distances)

        async def import_ships(self, ships: list[Ship]) -> int:
            import_order.append("ships")
            return await super().import_ships(ships)

        async def import_commodities(self, commodities: list[Commodity]) -> int:
            import_order.append("commodities")
            return await super().import_commodities(commodities)

        async def import_contracts(self, contracts: list[Contract]) -> int:
            import_order.append("contracts")
            return await super().import_contracts(contracts)

    loc = Location(id="loc1", name="Hurston", type="planet")
    importer = _OrderedImport()
    source = _StubSource(locations=[loc])
    service = SyncService(sources=[source], import_adapter=importer)

    await service.sync_all()

    assert import_order[0] == "locations", "locations must be imported first"
    assert set(import_order[1:]) == {"distances", "ships", "commodities", "contracts"}


@pytest.mark.asyncio
async def test_sync_sources_fetched_in_parallel() -> None:
    """All sources should be fetched concurrently, not sequentially."""
    delay = 0.05  # 50 ms per fetch

    class _SlowSource(_StubSource):
        async def fetch_ships(self) -> list[Ship]:
            await asyncio.sleep(delay)
            return self._ships

    ship1 = Ship(id="s1", name="Caterpillar", manufacturer="Drake", cargo_scu=576)
    ship2 = Ship(id="s2", name="Hull C", manufacturer="MISC", cargo_scu=4_608)
    importer = _StubImport()
    source1 = _SlowSource(ships=[ship1])
    source2 = _SlowSource(ships=[ship2])
    service = SyncService(sources=[source1, source2], import_adapter=importer)

    start = time.monotonic()
    result = await service.sync_entity(EntityType.SHIPS)
    elapsed = time.monotonic() - start

    # Two 50 ms fetches run in parallel → elapsed ≈ 1× delay, cap at 1.8× for CI headroom
    assert elapsed < delay * 1.8, f"Expected parallel fetch (~{delay}s) but took {elapsed:.3f}s"
    assert result.count == 2


@pytest.mark.asyncio
async def test_sync_all_entity_types_run_in_parallel() -> None:
    """After locations are imported the remaining 4 entity types run concurrently."""
    delay = 0.05

    class _SlowImport(_StubImport):
        async def import_distances(self, distances: list[Distance]) -> int:
            await asyncio.sleep(delay)
            return await super().import_distances(distances)

        async def import_ships(self, ships: list[Ship]) -> int:
            await asyncio.sleep(delay)
            return await super().import_ships(ships)

        async def import_commodities(self, commodities: list[Commodity]) -> int:
            await asyncio.sleep(delay)
            return await super().import_commodities(commodities)

        async def import_contracts(self, contracts: list[Contract]) -> int:
            await asyncio.sleep(delay)
            return await super().import_contracts(contracts)

    importer = _SlowImport()
    service = SyncService(sources=[], import_adapter=importer)

    start = time.monotonic()
    await service.sync_all()
    elapsed = time.monotonic() - start

    # 4 parallel imports of ~50 ms each → elapsed ≈ 1× delay; 3× cap leaves room for CI jitter
    assert elapsed < delay * 3, f"Expected parallel entity sync (~{delay}s) but took {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_semaphore_limits_concurrent_source_requests() -> None:
    """Each source adapter has a semaphore capping concurrent fetches at _SEMAPHORE_LIMIT."""
    max_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    class _CountingSource(_StubSource):
        async def fetch_ships(self) -> list[Ship]:
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.01)
            async with lock:
                current_concurrent -= 1
            return self._ships

    source = _CountingSource()
    importer = _StubImport()
    service = SyncService(sources=[source], import_adapter=importer)

    # Drive _SEMAPHORE_LIMIT + 2 concurrent calls through the same source
    over_limit = _SEMAPHORE_LIMIT + 2
    await asyncio.gather(
        *[service._guarded(source, source.fetch_ships()) for _ in range(over_limit)]
    )

    assert max_concurrent <= _SEMAPHORE_LIMIT
