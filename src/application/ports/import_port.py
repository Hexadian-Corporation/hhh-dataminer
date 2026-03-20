from abc import ABC, abstractmethod

from src.domain.models import Commodity, Contract, Distance, Location, Ship


class ImportPort(ABC):
    """Abstract port for importing game data into HHH backend services."""

    @abstractmethod
    async def import_locations(self, locations: list[Location]) -> int:
        """Import locations into the maps service. Returns the number of records imported."""

    @abstractmethod
    async def import_distances(self, distances: list[Distance]) -> int:
        """Import distances into the maps service. Returns the number of records imported."""

    @abstractmethod
    async def import_ships(self, ships: list[Ship]) -> int:
        """Import ships into the ships service. Returns the number of records imported."""

    @abstractmethod
    async def import_commodities(self, commodities: list[Commodity]) -> int:
        """Import commodities into the commodities service. Returns the number of records imported."""

    @abstractmethod
    async def import_contracts(self, contracts: list[Contract]) -> int:
        """Import contracts into the contracts service. Returns the number of records imported."""
