import httpx

from src.application.ports.import_port import ImportPort
from src.domain.models import Commodity, Contract, Distance, Location, Ship
from src.infrastructure.config.settings import Settings


class HhhImportAdapter(ImportPort):
    """HTTP client that pushes game data to the HHH backend services."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = http_client

    async def import_locations(self, locations: list[Location]) -> int:
        payload = [
            {"id": loc.id, "name": loc.name, "type": loc.type, "system": loc.system, "parent_id": loc.parent_id}
            for loc in locations
        ]
        await self._post(f"{self._settings.maps_service_url}/locations/bulk", payload)
        return len(locations)

    async def import_distances(self, distances: list[Distance]) -> int:
        payload = [{"from_id": d.from_id, "to_id": d.to_id, "distance_km": d.distance_km} for d in distances]
        await self._post(f"{self._settings.maps_service_url}/distances/bulk", payload)
        return len(distances)

    async def import_ships(self, ships: list[Ship]) -> int:
        payload = [
            {"id": s.id, "name": s.name, "manufacturer": s.manufacturer, "cargo_scu": s.cargo_scu} for s in ships
        ]
        await self._post(f"{self._settings.ships_service_url}/ships/bulk", payload)
        return len(ships)

    async def import_commodities(self, commodities: list[Commodity]) -> int:
        payload = [
            {"id": c.id, "name": c.name, "category": c.category, "base_price_uec": c.base_price_uec}
            for c in commodities
        ]
        await self._post(f"{self._settings.commodities_service_url}/commodities/bulk", payload)
        return len(commodities)

    async def import_contracts(self, contracts: list[Contract]) -> int:
        payload = [{"id": c.id, "title": c.title, "type": c.type, "payout_uec": c.payout_uec} for c in contracts]
        await self._post(f"{self._settings.contracts_service_url}/contracts/bulk", payload)
        return len(contracts)

    async def _post(self, url: str, payload: list[dict]) -> None:
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
