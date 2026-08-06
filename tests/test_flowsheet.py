"""Tests for py2aspen.flowsheet.

No real Aspen Plus instance is required: the COM node tree is mocked by the
``ElementsNode`` class, which mirrors the minimal ``IHNode`` surface used by
``Action._execute``.
"""

from __future__ import annotations

from typing import cast

import pytest

from py2aspen.aspen_type import IHNode, PortType
from py2aspen.flowsheet import (
    RCSTR,
    Action,
    HeatStream,
    MaterialStream,
    Radfrac,
    WorkStream,
    connect,
    delete,
    disconnect,
    place,
)


class ElementsNode:
    """Mock of the COM Elements collection: iterable, indexable by name, with Add/Remove."""

    def __init__(self) -> None:
        self.added: list[str] = []
        self.removed: list[str] = []
        self.children: dict[str, ElementsNode] = {}

    @property
    def Elements(self) -> ElementsNode:
        return self

    def Add(self, value: str) -> None:
        self.added.append(value)

    def Remove(self, value: str) -> None:
        self.removed.append(value)

    def __call__(self, name: str | None = None) -> ElementsNode:
        if name is None:
            return self
        return self.children.setdefault(name, ElementsNode())


@pytest.fixture
def tree() -> tuple[ElementsNode, ElementsNode]:
    """Mock block and stream node roots."""
    return ElementsNode(), ElementsNode()


def _run(action: Action, tree: tuple[ElementsNode, ElementsNode]) -> None:
    blocks, streams = tree
    action._inject_nodes(cast("IHNode", blocks), cast("IHNode", streams))
    action._execute()



# --- name resolution ---


def test_name_explicit_wins() -> None:
    assert Radfrac("B1").name == "B1"


def test_name_inferred_from_variable() -> None:
    b1 = Radfrac()
    s1 = MaterialStream()
    assert b1.name == "B1"
    assert s1.name == "S1"


def test_name_inferred_inside_function() -> None:
    def make_stream() -> HeatStream:
        col = HeatStream()
        return col

    assert make_stream().name == "COL"


def test_unassigned_object_raises_value_error() -> None:
    def unnamed() -> WorkStream:
        return WorkStream()

    with pytest.raises(ValueError):
        unnamed()


# --- Action: place / connect / disconnect / delete ---


def test_chained_operations(tree: tuple[ElementsNode, ElementsNode]) -> None:
    reactor = RCSTR()
    feed = MaterialStream()

    action = (
        Action()
        .place(reactor, feed)
        .connect(feed, reactor.f_in)
        .disconnect(feed, reactor.f_in)
        .delete(reactor)
    )
    _run(action, tree)

    blocks, streams = tree
    assert blocks.added == ["REACTOR!RCSTR"]
    assert streams.added == ["FEED!MATERIAL"]
    assert blocks.removed == ["REACTOR"]
    port = blocks.children["REACTOR"].children["Ports"].children["F(IN)"]
    assert port.added == ["FEED"]
    assert port.removed == ["FEED"]


def test_place_multiple_items_in_one_call(tree: tuple[ElementsNode, ElementsNode]) -> None:
    b1 = Radfrac()
    b2 = RCSTR()
    s1 = MaterialStream()

    _run(place(b1, b2, s1), tree)

    blocks, streams = tree
    assert blocks.added == ["B1!Radfrac", "B2!RCSTR"]
    assert streams.added == ["S1!MATERIAL"]


def test_delete_multiple_items_in_one_call(tree: tuple[ElementsNode, ElementsNode]) -> None:
    b1 = Radfrac()
    s1 = MaterialStream()
    action = Action().delete(b1, s1)

    _run(action, tree)

    blocks, streams = tree
    assert blocks.removed == ["B1"]
    assert streams.removed == ["S1"]


def test_execute_before_inject_nodes_raises() -> None:
    with pytest.raises(AssertionError):
        Action().place(Radfrac("B1"))._execute()


# --- Module-level functions as chain starters ---


def test_place_module_function(tree: tuple[ElementsNode, ElementsNode]) -> None:
    b1 = Radfrac()
    s1 = MaterialStream()

    _run(place(b1, s1), tree)

    blocks, streams = tree
    assert blocks.added == ["B1!Radfrac"]
    assert streams.added == ["S1!MATERIAL"]


def test_delete_module_function(tree: tuple[ElementsNode, ElementsNode]) -> None:
    b1 = Radfrac()
    s1 = MaterialStream()

    _run(delete(b1, s1), tree)

    blocks, streams = tree
    assert blocks.removed == ["B1"]
    assert streams.removed == ["S1"]


def test_connect_module_function_reinfers_block() -> None:
    b1 = Radfrac()
    s1 = MaterialStream()
    action = connect(s1, b1.f_in)
    assert action._operations == [("connect", (b1, s1, PortType.FEED_IN))]


def test_disconnect_module_function_reinfers_block() -> None:
    b1 = Radfrac()
    s1 = MaterialStream()
    action = disconnect(s1, b1.f_in)
    assert action._operations == [("disconnect", (b1, s1, PortType.FEED_IN))]
