from dataclasses import dataclass


@dataclass
class Commodity:
    id: str
    name: str
    category: str
    base_price_uec: float
