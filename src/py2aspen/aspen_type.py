"""Aspen Plus shared type definitions.

Used by main (UnitAspen), simulation (Block / Stream) and flowsheet (Action).
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

class HAPAttributeType(IntEnum):
    """Aspen Plus node attribute numbers (official ``HAPAttributeNumber``)."""

    HAP_VALUE = 0  # value
    HAP_RESERVED1 = 1  # reserved
    HAP_UNITROW = 2  # unit row
    HAP_UNITCOL = 3  # unit column
    HAP_RESERVED2 = 4  # reserved
    HAP_OPTIONLIST = 5  # option list
    HAP_RECORDTYPE = 6  # record type
    HAP_ENTERABLE = 7  # enterable
    HAP_UPPERLIMIT = 8  # upper limit
    HAP_LOWERLIMIT = 9  # lower limit
    HAP_VALUEDEFAULT = 10  # default value
    HAP_USERENTERED = 11  # user-entered flag
    HAP_COMPSTATUS = 12  # input completeness status
    HAP_BASIS = 13  # basis (total-flow Mass/Mole/StdVol, etc.)
    HAP_INOUT = 14  # input/output
    HAP_PORTSEX = 15  # port extension
    HAP_MULTIPORT = 16  # multiple ports
    HAP_PORTTYPE = 17  # port type
    HAP_OUTVAR = 18  # output variable
    HAP_PROMPT = 19  # prompt text
    HAP_PRETENDNOTENTERED = 20  # pretend not entered
    HAP_HELPFILENAME = 21  # help file name
    HAP_HELPID = 22  # help ID
    HAP_FIRSTPAIR = 23  # first pair
    HAP_NODENAME = 24  # node name
    HAP_METHOD = 25  # method
    HAP_MARKED = 26  # marked flag
    HAP_VOLATILE = 27  # volatile flag
    HAP_SECTION = 28  # section
    HAP_DEFNAME = 29  # default name
    HAP_CANADD = 30  # can add
    HAP_CANDELETE = 31  # can delete
    HAP_CANRENAME = 32  # can rename
    HAP_CANHIDE = 33  # can hide
    HAP_CANREVEAL = 34  # can reveal
    HAP_CANCLEAR = 35  # can clear
    HAP_CANCOPY = 36  # can copy
    HAP_CANPASTE = 37  # can paste
    HAP_HASCHILDREN = 38  # has children
    HAP_PLOTLABEL = 39  # plot label
    HAP_BIRDCAGE = 40
    HAP_STREAMCLASS = 42  # stream class
    HAP_HASCOMMENTS = 43  # has comments
    HAP_CANHAVECOMMENTS = 44  # can have comments
    HAP_UNDERLYINGPATH = 45  # underlying path
    HAP_ISHIDDEN = 47  # hidden flag
    HAP_HIDEVIEW = 48  # hide view
    HAP_ANALYSISFLAG = 49  # analysis flag
    HAP_SPECSTREAM = 50  # specification stream
    HAP_REORDER = 51  # can reorder
    HAP_ISREALSYMBOL = 52  # is a real symbol
    HAP_CANEXPORT = 58  # can export
    HAP_BASETYPE = 59  # base type
    HAP_HIERARCHYFLAG = 63  # hierarchy flag
    HAP_HIERPATH = 64  # hierarchy path
    HAP_FULLNAME = 65  # full name
    HAP_CANTEMPLAPPEND = 66  # can append template
    HAP_ACTIVESTATE = 67  # active state
    HAP_CANIMPORT = 68  # can import
    HAP_HASEOMSG = 69  # has EO message
    HAP_SHOWEOMSG = 70  # show EO message
    HAP_EOEXPORT = 72  # EO export
    HAP_EOIMPORT = 73  # EO import
    HAP_NAVPATH = 74  # navigation path
    HAP_HIERNAME = 76  # hierarchy name
    HAP_REVEALLIST = 77  # reveal list
    HAP_DEFRECONCILE = 78  # default reconcile
    HAP_EONODENAME = 79  # EO node name
    HAP_UOM = 81  # unit of measure
    HAP_UOMSET = 82  # unit set

class PortType(StrEnum):
    """Aspen Plus block port connection strings."""

    FEED_IN = "F(IN)"
    PRODUCT_OUT = "P(OUT)"
    BOTTOMS_OUT = "B(OUT)"
    DISTILLATE_OUT = "D(OUT)"
    LIQUID_DISTILLATE_OUT = "LD(OUT)"
    VAPOR_OUT = "V(OUT)"
    LIQUID_OUT = "L(OUT)"

class FlashType(StrEnum):
    """Aspen Plus flash type (``SPEC_OPT`` / ``MIXED_SPEC`` values)."""

    TP = "TP"  # temperature & pressure
    TV = "TV"  # temperature & vapor fraction
    PV = "PV"  # pressure & vapor fraction
    TD = "TD"  # temperature & heat duty
    TQ = "TQ"  # temperature & heat duty
    PD = "PD"  # pressure & heat duty
    PQ = "PQ"  # pressure & heat duty
    TS = "TS"  # temperature & entropy
    PS = "PS"  # pressure & entropy
    T = "T"  # temperature only
    P = "P"  # pressure only
    V = "V"  # vapor fraction only
    S = "S"  # entropy only
    H = "H"  # enthalpy only
    Q = "Q"  # heat duty only

class FlowBasis(StrEnum):
    """Total-flow basis for material streams (``FLOWBASE/MIXED`` values)."""

    MASS = "MASS"  # mass flow basis
    MOLE = "MOLE"  # molar flow basis
    STDVOL = "STDVOL"  # standard-volume flow basis

class CompositionBasis(StrEnum):
    """Composition basis for material streams (``BASIS/MIXED`` values)."""

    MASS_FRAC = "MASS-FRAC"  # mass fraction
    MOLE_FRAC = "MOLE-FRAC"  # mole fraction
    STDVOL_FRAC = "STDVOL-FRAC"  # standard-volume fraction
    MASS_FLOW = "MASS-FLOW"  # mass flow per component
    MOLE_FLOW = "MOLE-FLOW"  # mole flow per component
    STDVOL_FLOW = "STDVOL-FLOW"  # standard-volume flow per component
    MASS_CONC = "MASS-CONC"  # mass concentration per component
    MOLE_CONC = "MOLE-CONC"  # mole concentration per component
