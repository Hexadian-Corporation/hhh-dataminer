"""Unit tests for HhhImportAdapter."""

import httpx
import pytest
import respx

from src.domain.models import Commodity, Contract, Distance, Location, Ship
from src.infrastructure.adapters.outbound.hhh.hhh_import_adapter import HhhImportAdapter
from src.infrastructure.config.settings import Settings


def _make_adapter() -> tuple[HhhImportAdapter, Settings]:
    settings = Settings(
        maps_service_url="http://maps",
        ships_service_url="http://ships",
        commodities_service_url="http://commodities",
        contracts_service_url="http://contracts",
    )
    client = httpx.AsyncClient()
    return HhhImportAdapter(settings=settings, http_client=client), settings


@respx.mock
async def test_import_locations_posts_to_maps_service() -> None:
    locs = [Location(id="loc1", name="Hurston", type="planet", system="Stanton")]
    respx.post("http://maps/locations/bulk").mock(return_value=httpx.Response(200))

    adapter, _ = _make_adapter()
    count = await adapter.import_locations(locs)

    assert count == 1
    assert respx.calls.call_count == 1


@respx.mock
async def test_import_distances_posts_to_maps_service() -> None:
    dists = [Distance(from_id="loc1", to_id="loc2", distance_km=500.0)]
    respx.post("http://maps/distances/bulk").mock(return_value=httpx.Response(200))

    adapter, _ = _make_adapter()
    count = await adapter.import_distances(dists)

    assert count == 1


@respx.mock
async def test_import_ships_posts_to_ships_service() -> None:
    ships = [Ship(id="s1", name="Caterpillar", manufacturer="Drake", cargo_scu=576)]
    respx.post("http://ships/ships/bulk").mock(return_value=httpx.Response(200))

    adapter, _ = _make_adapter()
    count = await adapter.import_ships(ships)

    assert count == 1


@respx.mock
async def test_import_commodities_posts_to_commodities_service() -> None:
    commodities = [Commodity(id="c1", name="Agricium", category="Metal", base_price_uec=875.0)]
    respx.post("http://commodities/commodities/bulk").mock(return_value=httpx.Response(200))

    adapter, _ = _make_adapter()
    count = await adapter.import_commodities(commodities)

    assert count == 1


@respx.mock
async def test_import_contracts_posts_to_contracts_service() -> None:
    contracts = [Contract(id="ct1", title="Haul supplies", type="hauling", payout_uec=10_000.0)]
    respx.post("http://contracts/contracts/bulk").mock(return_value=httpx.Response(200))

    adapter, _ = _make_adapter()
    count = await adapter.import_contracts(contracts)

    assert count == 1


@respx.mock
async def test_import_raises_on_http_error() -> None:
    respx.post("http://maps/locations/bulk").mock(return_value=httpx.Response(500))

    adapter, _ = _make_adapter()
    with pytest.raises(httpx.HTTPStatusError):
        await adapter.import_locations([Location(id="loc1", name="X", type="planet")])


async def test_import_empty_list_returns_zero() -> None:
    settings = Settings()
    client = httpx.AsyncClient()

    with respx.mock:
        respx.post("http://localhost:8003/locations/bulk").mock(return_value=httpx.Response(200))
        adapter = HhhImportAdapter(settings=settings, http_client=client)
        count = await adapter.import_locations([])

    assert count == 0
