from dataclasses import dataclass


@dataclass
class Contract:
    id: str
    title: str
    type: str
    payout_uec: float
