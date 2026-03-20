from abc import ABC, abstractmethod

from src.domain.models import Commodity, Contract, Distance, Location, Ship


class DataSourcePort(ABC):
    """Abstract port for fetching game data from an external source."""

    @abstractmethod
    async def fetch_locations(self) -> list[Location]:
        """Fetch all locations from the data source."""

    @abstractmethod
    async def fetch_distances(self) -> list[Distance]:
        """Fetch all inter-location distances from the data source."""

    @abstractmethod
    async def fetch_ships(self) -> list[Ship]:
        """Fetch all ships from the data source."""

    @abstractmethod
    async def fetch_commodities(self) -> list[Commodity]:
        """Fetch all commodities from the data source."""

    @abstractmethod
    async def fetch_contracts(self) -> list[Contract]:
        """Fetch all contracts from the data source."""
