"""Flowsheet operations for Aspen Plus simulations.

References BlockPlace / BlockDelete / StreamPlace / StreamDelete /
StreamConnect / StreamDisconnect in CodeLibrary.py.

Blocks and streams are defined in :mod:`py2aspen.simulation` (e.g.
:class:`py2aspen.simulation.Radfrac`, :class:`py2aspen.simulation.MaterialStream`).

The operations are exposed in two forms:

- **Module-level functions** — each one creates a new ``Action`` and returns
  ``Action().<name>(*args)``, so ``place(x, y)`` is equivalent to
  ``Action().place(x, y)``.  For ``connect``/``disconnect`` the ``block`` is
  recovered from the bound port method passed as ``port``, so
  ``connect(s1, b1.f_in)`` is equivalent to
  ``Action().connect(s1, b1.f_in)``.
- **``Action`` methods** — record an operation onto an existing ``Action``
  instance and return ``self``, enabling chainable sequences.

Both forms produce the same result; choose whichever reads better at the call
site.  ``UnitAspen.exec`` injects the Aspen tree node references and replays
every recorded operation in order.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from py2aspen.aspen_type import IHNode, PortType
from py2aspen.log import logger
from py2aspen.simulation import Block, Stream


def place(*items: Block | Stream) -> Action:
    """Return a new Action with place operations as the first step."""
    return Action().place(*items)


def delete(*items: Block | Stream) -> Action:
    """Return a new Action with delete operations as the first step."""
    return Action().delete(*items)


def bind(*items: Block | Stream) -> Action:
    """Return a new Action with bind operations as the first step.

    Binds existing blocks/streams (already present in the Aspen file) by name,
    without placing new ones.
    """
    return Action().bind(*items)


def connect(stream: Stream, port: Callable[[], PortType]) -> Action:
    """Return a new Action with a connect operation as the first step.

    The owning block is recovered from the bound port method (e.g. ``b1.f_in``).
    """
    return Action().connect(stream, port)


def disconnect(stream: Stream, port: Callable[[], PortType]) -> Action:
    """Return a new Action with a disconnect operation as the first step.

    The owning block is recovered from the bound port method (e.g. ``b1.f_in``).
    """
    return Action().disconnect(stream, port)


class Action:
    """Operation builder that records sequences of Block/Stream operations.

    Build operation sequences via chainable calls, then execute them
    through :meth:`UnitAspen.exec`.  Node references are injected by
    ``UnitAspen`` at execution time --- the caller never passes them directly.
    """

    def __init__(self) -> None:
        self._blocks_node: IHNode | None = None
        self._streams_node: IHNode | None = None
        self._operations: list[tuple[str, tuple[Block | Stream] | tuple[Block, Stream, PortType]]] = []

    def _inject_nodes(self, blocks_node: IHNode, streams_node: IHNode) -> None:
        self._blocks_node = blocks_node
        self._streams_node = streams_node

    def place(self, *items: Block | Stream) -> Action:
        """Record place operations for one or more items."""
        for item in items:
            self._operations.append(("place", (item,)))
        return self

    def delete(self, *items: Block | Stream) -> Action:
        """Record delete operations for one or more items."""
        for item in items:
            self._operations.append(("delete", (item,)))
        return self

    def bind(self, *items: Block | Stream) -> Action:
        """Record bind operations for one or more existing items."""
        for item in items:
            self._operations.append(("bind", (item,)))
        return self

    def connect(self, stream: Stream, port: Callable[[], PortType]) -> Action:
        """Record a connect operation.

        The owning block is recovered from the bound port method (e.g. ``b1.f_in``).
        """
        block = cast(Block, cast(Any, port).__self__)
        self._operations.append(("connect", (block, stream, port())))
        return self

    def disconnect(self, stream: Stream, port: Callable[[], PortType]) -> Action:
        """Record a disconnect operation.

        The owning block is recovered from the bound port method (e.g. ``b1.f_in``).
        """
        block = cast(Block, cast(Any, port).__self__)
        self._operations.append(("disconnect", (block, stream, port())))
        return self

    def _execute(self) -> None:
        """Execute all recorded operations using the injected node references."""
        if self._blocks_node is None or self._streams_node is None:
            raise RuntimeError(
                "nodes must be injected via _inject_nodes before _execute"
            )
        bn = self._blocks_node
        sn = self._streams_node
        for op_name, args in self._operations:
            if op_name == "bind":
                item = args[0]
                if isinstance(item, Block):
                    node = bn.Elements(item.name)
                    if node is None:
                        raise RuntimeError(f"Block {item.name} not found; cannot bind")
                    item._node = node  # bind existing block node
                    logger.info("Bound block {} (existing)", item.name)
                else:
                    node = sn.Elements(item.name)
                    if node is None:
                        raise RuntimeError(f"Stream {item.name} not found; cannot bind")
                    item._node = node  # bind existing stream node
                    logger.info("Bound stream {} (existing)", item.name)
            elif op_name == "place":
                item = args[0]
                if isinstance(item, Block):
                    node = bn.Elements.Add(f"{item.name}!{item.type()}")
                    item._node = node  # bind the block node for property setters
                    logger.info("Placed block {} (type {})", item.name, item.type())
                else:
                    node = sn.Elements.Add(f"{item.name}!{item.type()}")
                    item._node = node  # bind the stream node for property setters
                    logger.info("Placed stream {} (type {})", item.name, item.type())
            elif op_name == "delete":
                item = args[0]
                if isinstance(item, Block):
                    bn.Elements.Remove(item.name)
                    logger.info("Deleted block {}", item.name)
                else:
                    sn.Elements.Remove(item.name)
                    logger.info("Deleted stream {}", item.name)
            elif op_name == "connect":
                block, stream, port = cast("tuple[Block, Stream, PortType]", args)
                block_node = bn.Elements(block.name)
                if block_node is None:
                    raise RuntimeError(
                        f"Block {block.name} not found; cannot connect stream {stream.name}"
                    )
                port_node = block_node.Elements("Ports").Elements(port)
                if port_node is None:
                    raise RuntimeError(
                        f"Port {port} not found on block {block.name}; cannot connect stream {stream.name}"
                    )
                port_node.Elements.Add(stream.name)
                logger.info("Connected stream {} to block {} port {}", stream.name, block.name, port)
            elif op_name == "disconnect":
                block, stream, port = cast("tuple[Block, Stream, PortType]", args)
                block_node = bn.Elements(block.name)
                if block_node is None:
                    raise RuntimeError(
                        f"Block {block.name} not found; cannot disconnect stream {stream.name}"
                    )
                port_node = block_node.Elements("Ports").Elements(port)
                if port_node is None:
                    raise RuntimeError(
                        f"Port {port} not found on block {block.name}; cannot disconnect stream {stream.name}"
                    )
                port_node.Elements.Remove(stream.name)
                logger.info("Disconnected stream {} from block {} port {}", stream.name, block.name, port)
