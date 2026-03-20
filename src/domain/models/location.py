from dataclasses import dataclass


@dataclass
class Location:
    id: str
    name: str
    type: str
    system: str | None = None
