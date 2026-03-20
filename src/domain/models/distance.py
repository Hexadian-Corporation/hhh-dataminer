from dataclasses import dataclass


@dataclass
class Distance:
    from_id: str
    to_id: str
    distance_km: float
