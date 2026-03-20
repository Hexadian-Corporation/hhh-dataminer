from dataclasses import dataclass


@dataclass
class Ship:
    id: str
    name: str
    manufacturer: str
    cargo_scu: int
