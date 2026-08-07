"""Block and Stream object definitions for Aspen Plus simulations.

References BlockPlace / BlockDelete / StreamPlace / StreamDelete /
StreamConnect / StreamDisconnect in CodeLibrary.py.

``Block`` and ``Stream`` are abstract base classes; use their concrete
subclasses (e.g. :class:`RCSTR`, :class:`Radfrac`, :class:`MaterialStream`,
:class:`HeatStream`), which implement :meth:`Block.type` / :meth:`Stream.type`.
The ``name`` argument is optional --- when omitted it defaults to the
uppercased name of the variable the object is assigned to.

Placement and connection on the flowsheet are handled by the operations in
:mod:`py2aspen.flowsheet` (e.g. :func:`py2aspen.flowsheet.place`,
:func:`py2aspen.flowsheet.connect`).
"""

from __future__ import annotations

import dis
import sys
from abc import ABC, abstractmethod

from py2aspen.aspen_type import PortType


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
