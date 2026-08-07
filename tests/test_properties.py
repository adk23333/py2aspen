"""Tests for py2aspen.properties.

No real Aspen Plus instance is required: the component node tree is mocked by
the ``Mock*`` classes, which mirror the minimal ``IHNode`` / ``IHNodeCol``
surface used by ``ComponentManager`` (``Elements(name)`` / ``Elements`` /
``Name()`` / ``Value()``).
"""

from __future__ import annotations

from py2aspen.properties import ComponentManager


class MockComponent:
    """One per-component entry: ``Name()`` is the id, ``Value()`` the value."""

    def __init__(self, name: str, value: str | None) -> None:
        self._name = name
        self._value = value

    def Name(self) -> str:
        return self._name

    def Value(self) -> str | None:
        return self._value


class MockEntryCollection:
    """Iterable + callable mock of an ``IHNodeCol`` of component entries."""

    def __init__(self, data: dict[str, str | None]) -> None:
        self._entries = {cid: MockComponent(cid, val) for cid, val in data.items()}

    def __iter__(self):
        return iter(self._entries.values())

    def __call__(self, comp_id: str) -> MockComponent | None:
        return self._entries.get(comp_id)


class MockParamNode:
    """Mock of one parameter node (ANAME / TYPE / DBNAME / CASN)."""

    def __init__(self, data: dict[str, str | None]) -> None:
        self._collection = MockEntryCollection(data)

    @property
    def Elements(self) -> MockEntryCollection:
        return self._collection


class MockInputNode:
    """Mock of ``Specifications\\Input``: ``Elements(name)`` -> ``MockParamNode``."""

    def __init__(self, collections: dict[str, dict[str, str | None]]) -> None:
        self._params = {name: MockParamNode(data) for name, data in collections.items()}

    def Elements(self, name: str) -> MockParamNode | None:
        return self._params.get(name)


class MockSpecificationsNode:
    """Mock of ``Specifications``: ``Elements("Input")`` -> ``MockInputNode``."""

    def __init__(self, input_node: MockInputNode) -> None:
        self._input = input_node

    def Elements(self, name: str) -> MockInputNode:
        assert name == "Input"
        return self._input


class MockComponentsNode:
    """Mock of ``Data\\Components``: ``Elements("Specifications")``."""

    def __init__(self, input_node: MockInputNode) -> None:
        self._spec = MockSpecificationsNode(input_node)

    def Elements(self, name: str) -> MockSpecificationsNode:
        assert name == "Specifications"
        return self._spec


def _make_components_node() -> MockComponentsNode:
    """Build a mocked Data\\Components tree matching the real V14 collections."""
    input_node = MockInputNode(
        {
            "ANAME": {"H2O": "H2O", "N2": "N2", "O2": "O2", "COAL": None},
            "TYPE": {"H2O": "CONV", "N2": "CONV", "O2": "CONV", "COAL": "NC"},
            "DBNAME": {"H2O": "WATER", "N2": "NITROGEN", "O2": "OXYGEN", "COAL": None},
            "CASN": {"H2O": "7732-18-5", "N2": "7727-37-9", "O2": "7782-44-7", "COAL": None},
        }
    )
    return MockComponentsNode(input_node)

# --- ComponentManager ---


def test_get_all_components_default_fetches_all() -> None:
    mgr = ComponentManager(_make_components_node())
    comps = mgr.get_all_components()

    assert [c.id for c in comps] == ["H2O", "N2", "O2", "COAL"]
    water = comps[0]
    assert water.type == "CONV"
    assert water.name == "WATER"
    assert water.alias == "H2O"
    assert water.cas == "7732-18-5"


def test_get_all_components_missing_value_is_none() -> None:
    mgr = ComponentManager(_make_components_node())
    comps = mgr.get_all_components()

    coal = comps[3]
    assert coal.id == "COAL"
    assert coal.type == "NC"
    assert coal.name is None  # DBNAME value is None
    assert coal.alias is None  # ANAME value is None
    assert coal.cas is None  # CASN value is None


def test_get_all_components_selective_flags() -> None:
    mgr = ComponentManager(_make_components_node())
    comps = mgr.get_all_components(type=False, cas=False)

    water = comps[0]
    assert water.id == "H2O"
    assert water.type is None  # skipped
    assert water.name == "WATER"
    assert water.alias == "H2O"
    assert water.cas is None  # skipped
    assert water.cas is None  # skipped
