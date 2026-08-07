"""Aspen Plus shared type definitions.

Used by main (UnitAspen), simulate (Block / Stream) and flowsheet (Action).
Values reference CodeLibrary.py.
"""

from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING

from comtypes.client.lazybind import Dispatch

APP = Dispatch
IHNode = Dispatch  # runtime: after lazybind all tree nodes are Dispatch

if TYPE_CHECKING:
    from comtypes.gen import Happ  # type: ignore[import-untyped]
    APP = Happ.IHapp  # IHapp from generated type library
    IHNode = Happ.IHNode  # more precise static type for tree nodes
        


class Phase(StrEnum):
    """Phases: LIQUID, VAPOR, SOLID."""

    LIQUID = "L"
    VAPOR = "V"
    SOLID = "S"


class PhaseNumber(IntEnum):
    """Number of phases: 1, 2, 3."""

    ONE = 1
    TWO = 2
    THREE = 3


class PortType(StrEnum):
    """Aspen Plus block port connection strings."""

    FEED_IN = "F(IN)"
    PRODUCT_OUT = "P(OUT)"
    BOTTOMS_OUT = "B(OUT)"
    DISTILLATE_OUT = "D(OUT)"
    LIQUID_DISTILLATE_OUT = "LD(OUT)"
    VAPOR_OUT = "V(OUT)"
    LIQUID_OUT = "L(OUT)"
