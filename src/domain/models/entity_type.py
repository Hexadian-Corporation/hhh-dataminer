from enum import StrEnum


class EntityType(StrEnum):
    LOCATIONS = "locations"
    DISTANCES = "distances"
    SHIPS = "ships"
    COMMODITIES = "commodities"
    CONTRACTS = "contracts"
