"""Hierarchy validation for imported location data."""

import logging
from datetime import UTC, datetime

from src.domain.models.location import Location
from src.domain.models.validation_report import ValidationIssue, ValidationReport

logger = logging.getLogger(__name__)

# Valid parent types per child type.
# STATION/OUTPOST can exist at any level, so there is no rank-based ordering.
VALID_PARENTS: dict[str, set[str]] = {
    "PLANET": {"STAR"},
    "MOON": {"PLANET"},
    "CITY": {"PLANET", "MOON"},
    "STATION": {"STAR", "PLANET", "MOON", "CITY"},
    "OUTPOST": {"STAR", "PLANET", "MOON", "CITY"},
    "GATEWAY": {"STAR"},
}

MAX_DEPTH = 6


class HierarchyValidator:
    """Validates the location hierarchy after import. Read-only / idempotent."""

    def validate(self, locations: list[Location]) -> ValidationReport:
        """Run all five validation checks against the provided locations."""
        by_id: dict[str, Location] = {loc.id: loc for loc in locations}
        issues: list[ValidationIssue] = []

        issues.extend(self._check_orphans(by_id))
        issues.extend(self._check_cycles(by_id))
        issues.extend(self._check_type_hierarchy(by_id))
        issues.extend(self._check_roots(by_id))
        issues.extend(self._check_depth(by_id))

        return ValidationReport(
            total_locations=len(locations),
            issues=issues,
            checked_at=datetime.now(UTC),
        )

    # ------------------------------------------------------------------
    # 1. Orphan check
    # ------------------------------------------------------------------

    @staticmethod
    def _check_orphans(by_id: dict[str, Location]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for loc in by_id.values():
            if loc.parent_id and loc.parent_id not in by_id:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        rule="ORPHAN",
                        location_id=loc.id,
                        message=f"Location '{loc.name}' references non-existent parent '{loc.parent_id}'",
                        details={"parent_id": loc.parent_id},
                    )
                )
        return issues

    # ------------------------------------------------------------------
    # 2. Cycle detection (DFS with three-colour marking)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_cycles(by_id: dict[str, Location]) -> list[ValidationIssue]:
        WHITE, GRAY, BLACK = 0, 1, 2  # noqa: N806
        color: dict[str, int] = {loc_id: WHITE for loc_id in by_id}
        issues: list[ValidationIssue] = []

        def _dfs(loc_id: str, path: list[str]) -> None:
            color[loc_id] = GRAY
            path.append(loc_id)
            parent_id = by_id[loc_id].parent_id
            if parent_id and parent_id in by_id:
                if color[parent_id] == GRAY:
                    cycle_start = path.index(parent_id)
                    cycle = path[cycle_start:]
                    issues.append(
                        ValidationIssue(
                            severity="ERROR",
                            rule="CYCLE",
                            location_id=loc_id,
                            message=f"Circular reference detected: {' → '.join(cycle)} → {parent_id}",
                            details={"cycle": cycle},
                        )
                    )
                elif color[parent_id] == WHITE:
                    _dfs(parent_id, path)
            color[loc_id] = BLACK
            path.pop()

        for loc_id in by_id:
            if color[loc_id] == WHITE:
                _dfs(loc_id, [])

        return issues

    # ------------------------------------------------------------------
    # 3. Type hierarchy validation
    # ------------------------------------------------------------------

    @staticmethod
    def _check_type_hierarchy(by_id: dict[str, Location]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for loc in by_id.values():
            if not loc.parent_id or loc.parent_id not in by_id:
                continue
            parent = by_id[loc.parent_id]
            child_type = loc.type.upper()
            parent_type = parent.type.upper()
            allowed = VALID_PARENTS.get(child_type, set())
            if allowed and parent_type not in allowed:
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        rule="TYPE_VIOLATION",
                        location_id=loc.id,
                        message=(
                            f"'{loc.name}' (type {child_type}) cannot be a child of "
                            f"'{parent.name}' (type {parent_type})"
                        ),
                        details={
                            "child_type": child_type,
                            "parent_type": parent_type,
                            "allowed_parents": sorted(allowed),
                        },
                    )
                )
        return issues

    # ------------------------------------------------------------------
    # 4. Root validation — one STAR root per system
    # ------------------------------------------------------------------

    @staticmethod
    def _check_roots(by_id: dict[str, Location]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        roots_by_system: dict[str | None, list[Location]] = {}
        for loc in by_id.values():
            if not loc.parent_id:
                roots_by_system.setdefault(loc.system, []).append(loc)

        for system, roots in roots_by_system.items():
            if len(roots) > 1:
                root_names = [r.name for r in roots]
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        rule="ROOT_VIOLATION",
                        location_id=roots[0].id,
                        message=f"System '{system}' has {len(roots)} root locations: {', '.join(root_names)}",
                        details={"system": system, "root_ids": [r.id for r in roots]},
                    )
                )
        return issues

    # ------------------------------------------------------------------
    # 5. Depth check — max 6 levels
    # ------------------------------------------------------------------

    @staticmethod
    def _check_depth(by_id: dict[str, Location]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        reported: set[str] = set()

        for loc in by_id.values():
            depth = 1
            current = loc
            visited: set[str] = {current.id}
            while current.parent_id and current.parent_id in by_id:
                if current.parent_id in visited:
                    break  # cycle — handled by cycle check
                visited.add(current.parent_id)
                current = by_id[current.parent_id]
                depth += 1

            if depth > MAX_DEPTH and loc.id not in reported:
                reported.add(loc.id)
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        rule="DEPTH_VIOLATION",
                        location_id=loc.id,
                        message=f"Location '{loc.name}' is at depth {depth}, exceeding maximum of {MAX_DEPTH}",
                        details={"depth": depth, "max_depth": MAX_DEPTH},
                    )
                )
        return issues
