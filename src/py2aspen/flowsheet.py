"""Block and Stream objects for Aspen Plus flowsheets.

References BlockPlace / BlockDelete / StreamPlace / StreamDelete /
StreamConnect / StreamDisconnect in CodeLibrary.py.

``Block`` and ``Stream`` are abstract base classes; use their concrete
subclasses (e.g. :class:`RCSTR`, :class:`Radfrac`, :class:`MaterialStream`,
:class:`HeatStream`), which implement :meth:`Block.type` / :meth:`Stream.type`.
The ``name`` argument is optional --- when omitted it defaults to the
uppercased name of the variable the object is assigned to.

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

Examples::

    b1 = Radfrac()          # name defaults to "B1"
    s1 = MaterialStream()   # name defaults to "S1"
    s2 = MaterialStream()   # name defaults to "S2"

    # Module-level functions as chain starters; connect recovers the block
    # from the bound port method ``b1.f_in``
    action = connect(s1, b1.f_in).place(b1, s2)
    aspen.exec(action)

    # Equivalent form using the Action constructor
    action = (
        Action()
        .place(b1, s1)
        .connect(s1, b1.f_in)
        .disconnect(s1, b1.f_in)
        .delete(b1)
    )
    aspen.exec(action)
"""

from __future__ import annotations

import dis
import sys
from abc import ABC, abstractmethod
from typing import Callable, cast

from py2aspen.aspen_type import IHNode, PortType
from py2aspen.log import logger


def _resolve_name(name: str | None) -> str:
    """Return *name*, or the uppercased variable name when *name* is None."""
    if name is not None:
        return name
    frame = sys._getframe(2)  # caller of __init__
    for ins in dis.get_instructions(frame.f_code):
        if ins.offset > frame.f_lasti and ins.opname.startswith("STORE_"):
            if ins.argval is not None:
                return ins.argval.upper()
            raise ValueError("cannot infer name from this assignment")
    raise ValueError("cannot infer name: object not assigned to a variable")


class Block(ABC):
    """Base class for unit-operation blocks on the Aspen Plus flowsheet.

    Subclasses must implement :meth:`type`.  The ``name`` is optional and
    defaults to the uppercased variable the object is assigned to.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = _resolve_name(name)

    @abstractmethod
    def type(self) -> str:
        """Return the Aspen Plus equipment type string."""


class RCSTR(Block):
    """Continuous stirred-tank reactor."""

    def type(self) -> str:
        return "RCSTR"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT


class RPlug(Block):
    """Plug-flow reactor."""

    def type(self) -> str:
        return "RPlug"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT


class DSTWU(Block):
    """Shortcut distillation column."""

    def type(self) -> str:
        return "DSTWU"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def d_out(self) -> PortType:
        return PortType.DISTILLATE_OUT

    def b_out(self) -> PortType:
        return PortType.BOTTOMS_OUT


class Flash2(Block):
    """Two-outlet flash separator."""

    def type(self) -> str:
        return "Flash2"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def v_out(self) -> PortType:
        return PortType.VAPOR_OUT

    def l_out(self) -> PortType:
        return PortType.LIQUID_OUT


class Mixer(Block):
    """Stream mixer."""

    def type(self) -> str:
        return "Mixer"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT


class Heater(Block):
    """Heater/cooler."""

    def type(self) -> str:
        return "Heater"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT


class Radfrac(Block):
    """Rigorous multi-stage distillation column."""

    def type(self) -> str:
        return "Radfrac"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def d_out(self) -> PortType:
        return PortType.DISTILLATE_OUT

    def ld_out(self) -> PortType:
        return PortType.LIQUID_DISTILLATE_OUT

    def b_out(self) -> PortType:
        return PortType.BOTTOMS_OUT


class Splitter(Block):
    """Stream splitter."""

    def type(self) -> str:
        return "Splitter"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT


class RYield(Block):
    """Yield reactor."""

    def type(self) -> str:
        return "RYield"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT


class Stream(ABC):
    """Base class for material, heat, or work streams.

    Subclasses must implement :meth:`type`.  The ``name`` is optional and
    defaults to the uppercased variable the object is assigned to.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = _resolve_name(name)

    @abstractmethod
    def type(self) -> str:
        """Return the Aspen Plus stream type string."""


class MaterialStream(Stream):
    """Material stream."""

    def type(self) -> str:
        return "MATERIAL"


class HeatStream(Stream):
    """Heat stream."""

    def type(self) -> str:
        return "HEAT"


class WorkStream(Stream):
    """Work stream (empty Aspen type string)."""

    def type(self) -> str:
        return "WORK"

class PowerStream(Stream):
    """power stream."""

    def type(self) -> str:
        return "POWER"


def place(*items: Block | Stream) -> Action:
    """Return a new Action with place operations as the first step."""
    return Action().place(*items)


def delete(*items: Block | Stream) -> Action:
    """Return a new Action with delete operations as the first step."""
    return Action().delete(*items)


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

    def connect(self, stream: Stream, port: Callable[[], PortType]) -> Action:
        """Record a connect operation.

        The owning block is recovered from the bound port method (e.g. ``b1.f_in``).
        """
        block = cast(Block, getattr(port, "__self__"))
        self._operations.append(("connect", (block, stream, port())))
        return self

    def disconnect(self, stream: Stream, port: Callable[[], PortType]) -> Action:
        """Record a disconnect operation.

        The owning block is recovered from the bound port method (e.g. ``b1.f_in``).
        """
        block = cast(Block, getattr(port, "__self__"))
        self._operations.append(("disconnect", (block, stream, port())))
        return self

    def _execute(self) -> None:
        """Execute all recorded operations using the injected node references."""
        assert self._blocks_node is not None and self._streams_node is not None, (
            "nodes must be injected via _inject_nodes before _execute"
        )
        bn = self._blocks_node
        sn = self._streams_node
        for op_name, args in self._operations:
            if op_name == "place":
                item = args[0]
                if isinstance(item, Block):
                    bn.Elements.Add(f"{item.name}!{item.type()}")
                    logger.info("Placed block {} (type {})", item.name, item.type())
                else:
                    sn.Elements.Add(f"{item.name}!{item.type()}")
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
                    logger.error(
                        "Block {} not found; skipping connect of stream {}", block.name, stream.name
                    )
                    continue
                port_node = block_node.Elements("Ports").Elements(port)
                if port_node is None:
                    logger.error(
                        "Port {} not found on block {}; skipping connect of stream {}",
                        port,
                        block.name,
                        stream.name,
                    )
                    continue
                port_node.Elements.Add(stream.name)
                logger.info("Connected stream {} to block {} port {}", stream.name, block.name, port)
            elif op_name == "disconnect":
                block, stream, port = cast("tuple[Block, Stream, PortType]", args)
                block_node = bn.Elements(block.name)
                if block_node is None:
                    logger.error(
                        "Block {} not found; skipping disconnect of stream {}", block.name, stream.name
                    )
                    continue
                port_node = block_node.Elements("Ports").Elements(port)
                if port_node is None:
                    logger.error(
                        "Port {} not found on block {}; skipping disconnect of stream {}",
                        port,
                        block.name,
                        stream.name,
                    )
                    continue
                port_node.Elements.Remove(stream.name)
                logger.info("Disconnected stream {} from block {} port {}", stream.name, block.name, port)
