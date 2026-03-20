"""Unit tests for SyncService."""

import pytest

from src.application.ports.data_source_port import DataSourcePort
from src.application.ports.import_port import ImportPort
from src.application.services.sync_service import SyncResult, SyncService
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
