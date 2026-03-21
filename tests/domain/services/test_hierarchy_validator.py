"""Unit tests for HierarchyValidator."""

from src.domain.models.location import Location
from src.domain.services.hierarchy_validator import HierarchyValidator


def _loc(
    id: str,
    name: str,
    type: str,
    system: str | None = None,
    parent_id: str | None = None,
) -> Location:
    return Location(id=id, name=name, type=type, system=system, parent_id=parent_id)


class TestValidHierarchy:
    """Scenario: Valid hierarchy — Stanton system reference."""

    def test_valid_stanton_hierarchy(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("planet1", "Crusader", "PLANET", system="Stanton", parent_id="star1"),
            _loc("planet2", "ArcCorp", "PLANET", system="Stanton", parent_id="star1"),
            _loc("planet3", "Hurston", "PLANET", system="Stanton", parent_id="star1"),
            _loc("planet4", "microTech", "PLANET", system="Stanton", parent_id="star1"),
            _loc("moon1", "Cellin", "MOON", system="Stanton", parent_id="planet1"),
            _loc("moon2", "Daymar", "MOON", system="Stanton", parent_id="planet1"),
            _loc("moon3", "Yela", "MOON", system="Stanton", parent_id="planet1"),
            _loc("city1", "Area 18", "CITY", system="Stanton", parent_id="planet2"),
            _loc("city2", "Lorville", "CITY", system="Stanton", parent_id="planet3"),
            _loc("city3", "New Babbage", "CITY", system="Stanton", parent_id="planet4"),
            _loc("station1", "Port Olisar", "STATION", system="Stanton", parent_id="planet1"),
            _loc("station2", "CRU-L1", "STATION", system="Stanton", parent_id="planet1"),
            _loc("station3", "ARC-L3", "STATION", system="Stanton", parent_id="planet2"),
            _loc("gw1", "Stanton-Pyro Gateway", "GATEWAY", system="Stanton", parent_id="star1"),
        ]

        validator = HierarchyValidator()
        report = validator.validate(locations)

        assert report.is_valid is True
        assert len(report.issues) == 0
        assert report.total_locations == 15


class TestOrphanDetection:
    """Scenario: Orphan location — parent_id points to non-existent location."""

    def test_orphan_detected(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("station1", "Orphan Station", "STATION", system="Stanton", parent_id="deleted_planet"),
        ]

        report = HierarchyValidator().validate(locations)

        assert report.is_valid is False
        assert len(report.errors) == 1
        assert report.errors[0].rule == "ORPHAN"
        assert report.errors[0].location_id == "station1"
        assert "deleted_planet" in report.errors[0].message


class TestCycleDetection:
    """Scenario: Circular reference — A→B→C→A."""

    def test_cycle_detected(self) -> None:
        locations = [
            _loc("a", "Location A", "PLANET", system="Stanton", parent_id="c"),
            _loc("b", "Location B", "PLANET", system="Stanton", parent_id="a"),
            _loc("c", "Location C", "PLANET", system="Stanton", parent_id="b"),
        ]

        report = HierarchyValidator().validate(locations)

        assert report.is_valid is False
        cycle_issues = [i for i in report.issues if i.rule == "CYCLE"]
        assert len(cycle_issues) >= 1
        assert cycle_issues[0].severity == "ERROR"


class TestTypeViolation:
    """Scenario: Type violation — Moon as child of Station."""

    def test_type_violation_detected(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("station1", "Some Station", "STATION", system="Stanton", parent_id="star1"),
            _loc("moon1", "Bad Moon", "MOON", system="Stanton", parent_id="station1"),
        ]

        report = HierarchyValidator().validate(locations)

        type_issues = [i for i in report.issues if i.rule == "TYPE_VIOLATION"]
        assert len(type_issues) == 1
        assert type_issues[0].severity == "WARNING"
        assert type_issues[0].location_id == "moon1"
        assert "MOON" in type_issues[0].message
        assert "STATION" in type_issues[0].message


class TestRootViolation:
    """Scenario: Multiple roots — 2 stars with no parent in same system."""

    def test_multiple_roots_detected(self) -> None:
        locations = [
            _loc("star1", "Star A", "STAR", system="Stanton"),
            _loc("star2", "Star B", "STAR", system="Stanton"),
        ]

        report = HierarchyValidator().validate(locations)

        root_issues = [i for i in report.issues if i.rule == "ROOT_VIOLATION"]
        assert len(root_issues) == 1
        assert root_issues[0].severity == "WARNING"
        assert "2" in root_issues[0].message


class TestDepthViolation:
    """Scenario: Deep chain — 7-level nesting exceeds max 6."""

    def test_depth_violation_detected(self) -> None:
        locations = [
            _loc("l1", "Level 1", "STAR", system="Stanton"),
            _loc("l2", "Level 2", "PLANET", system="Stanton", parent_id="l1"),
            _loc("l3", "Level 3", "MOON", system="Stanton", parent_id="l2"),
            _loc("l4", "Level 4", "CITY", system="Stanton", parent_id="l3"),
            _loc("l5", "Level 5", "STATION", system="Stanton", parent_id="l4"),
            _loc("l6", "Level 6", "OUTPOST", system="Stanton", parent_id="l5"),
            _loc("l7", "Level 7", "STATION", system="Stanton", parent_id="l6"),
        ]

        report = HierarchyValidator().validate(locations)

        depth_issues = [i for i in report.issues if i.rule == "DEPTH_VIOLATION"]
        assert len(depth_issues) == 1
        assert depth_issues[0].severity == "WARNING"
        assert depth_issues[0].location_id == "l7"
        assert depth_issues[0].details["depth"] == 7


class TestMixedIssues:
    """Scenario: Mixed issues — orphan + type violation in same dataset."""

    def test_mixed_issues_detected(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("station1", "Orphan Station", "STATION", system="Stanton", parent_id="deleted_planet"),
            _loc("station2", "Some Station", "STATION", system="Stanton", parent_id="star1"),
            _loc("moon1", "Bad Moon", "MOON", system="Stanton", parent_id="station2"),
        ]

        report = HierarchyValidator().validate(locations)

        assert report.is_valid is False
        assert len(report.errors) == 1
        assert len(report.warnings) == 1
        assert report.errors[0].rule == "ORPHAN"
        assert report.warnings[0].rule == "TYPE_VIOLATION"


class TestEmptyDataset:
    """Scenario: Empty dataset — no locations."""

    def test_empty_dataset(self) -> None:
        report = HierarchyValidator().validate([])

        assert report.is_valid is True
        assert len(report.issues) == 0
        assert report.total_locations == 0


class TestValidationReportProperties:
    """Test ValidationReport properties."""

    def test_checked_at_is_set(self) -> None:
        report = HierarchyValidator().validate([])
        assert report.checked_at is not None

    def test_errors_and_warnings_filtering(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("star2", "Extra Star", "STAR", system="Stanton"),
            _loc("station1", "Orphan", "STATION", system="Stanton", parent_id="missing"),
        ]

        report = HierarchyValidator().validate(locations)

        assert len(report.errors) == 1  # ORPHAN
        assert len(report.warnings) == 1  # ROOT_VIOLATION
        assert report.is_valid is False  # has errors


class TestStationAtAnyLevel:
    """Stations can be children of STAR, PLANET, MOON, or CITY."""

    def test_station_under_star(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("s1", "Station A", "STATION", system="Stanton", parent_id="star1"),
        ]
        report = HierarchyValidator().validate(locations)
        type_issues = [i for i in report.issues if i.rule == "TYPE_VIOLATION"]
        assert len(type_issues) == 0

    def test_station_under_planet(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("p1", "Crusader", "PLANET", system="Stanton", parent_id="star1"),
            _loc("s1", "Port Olisar", "STATION", system="Stanton", parent_id="p1"),
        ]
        report = HierarchyValidator().validate(locations)
        type_issues = [i for i in report.issues if i.rule == "TYPE_VIOLATION"]
        assert len(type_issues) == 0

    def test_station_under_moon(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("p1", "Crusader", "PLANET", system="Stanton", parent_id="star1"),
            _loc("m1", "Cellin", "MOON", system="Stanton", parent_id="p1"),
            _loc("s1", "Kareah", "STATION", system="Stanton", parent_id="m1"),
        ]
        report = HierarchyValidator().validate(locations)
        type_issues = [i for i in report.issues if i.rule == "TYPE_VIOLATION"]
        assert len(type_issues) == 0

    def test_station_under_city(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("p1", "Hurston", "PLANET", system="Stanton", parent_id="star1"),
            _loc("c1", "Lorville", "CITY", system="Stanton", parent_id="p1"),
            _loc("s1", "TDD Lorville", "STATION", system="Stanton", parent_id="c1"),
        ]
        report = HierarchyValidator().validate(locations)
        type_issues = [i for i in report.issues if i.rule == "TYPE_VIOLATION"]
        assert len(type_issues) == 0


class TestGatewayValidation:
    """Gateways can only be children of STAR."""

    def test_gateway_under_star_is_valid(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("gw1", "Stanton-Pyro Gateway", "GATEWAY", system="Stanton", parent_id="star1"),
        ]
        report = HierarchyValidator().validate(locations)
        type_issues = [i for i in report.issues if i.rule == "TYPE_VIOLATION"]
        assert len(type_issues) == 0

    def test_gateway_under_planet_is_invalid(self) -> None:
        locations = [
            _loc("star1", "Stanton", "STAR", system="Stanton"),
            _loc("p1", "Crusader", "PLANET", system="Stanton", parent_id="star1"),
            _loc("gw1", "Bad Gateway", "GATEWAY", system="Stanton", parent_id="p1"),
        ]
        report = HierarchyValidator().validate(locations)
        type_issues = [i for i in report.issues if i.rule == "TYPE_VIOLATION"]
        assert len(type_issues) == 1
        assert type_issues[0].location_id == "gw1"
