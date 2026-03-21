from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ValidationIssue:
    severity: str  # "ERROR" | "WARNING"
    rule: str  # "ORPHAN" | "CYCLE" | "TYPE_VIOLATION" | "ROOT_VIOLATION" | "DEPTH_VIOLATION"
    location_id: str
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    total_locations: int
    issues: list[ValidationIssue]
    checked_at: datetime

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "ERROR"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "WARNING"]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
