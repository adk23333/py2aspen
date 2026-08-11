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
from dataclasses import dataclass, field, fields
from typing import Any, Generic, TypeVar, cast, get_type_hints

from comtypes import COMError

from py2aspen.aspen_type import CompositionBasis, FlashType, FlowBasis, HAPAttributeType, IHNode, PortType
from py2aspen.log import logger

BlockInputT = TypeVar("BlockInputT", bound="BlockInput")
StreamInputT = TypeVar("StreamInputT", bound="StreamInput")


__all__ = [
    "DSTWU",
    "RCSTR",
    "Block",
    "BlockInput",
    "DSTWUInput",
    "Flash2",
    "Flash2Input",
    "HeatStream",
    "Heater",
    "HeaterInput",
    "MaterialStream",
    "MaterialStreamInput",
    "Mixer",
    "MixerInput",
    "PowerStream",
    "RCSTRInput",
    "RPlug",
    "RPlugInput",
    "RYield",
    "RYieldInput",
    "Radfrac",
    "RadfracInput",
    "Splitter",
    "SplitterInput",
    "Stream",
    "StreamInput",
    "Units",
    "WorkStream",
]


@dataclass
class Units:
    """Unit specifications for block/stream input parameters.

    Attributes:
        temperature: C, K, F, R
        pressure: bar, atm, Pa, kPa, psi
        duty: Watt, kW, Btu/hr, cal/sec
        volume: cum, L, cuft, gal
        length: meter, ft, cm, mm, in
        heat_transfer_coefficient: kcal/hr-sqm-K, Btu/hr-ft2-R
        total_flow_rate: kg/hr, kmol/hr (basis-dependent)
        composition_flow: kg/hr, kmol/hr (basis-dependent)
    """

    temperature: str | None = None
    pressure: str | None = None
    duty: str | None = None
    volume: str | None = None
    length: str | None = None
    heat_transfer_coefficient: str | None = None
    total_flow_rate: str | None = None
    composition_flow: str | None = None


@dataclass
class BlockInput:
    """Base class for block input parameter dataclasses.

    Each subclass (e.g. :class:`RCSTRInput`) declares the parameters its block
    supports.  Each field carries its Aspen node name as the ``"alias"``
    metadata; a ``"spec_opt"`` metadata means ``SPEC_OPT`` must be written to
    that value before the parameter itself.
    """

    units: Units | None = field(default=None)


@dataclass
class StreamInput:
    """Base class for stream input parameter dataclasses.

    Each subclass (e.g. :class:`MaterialStreamInput`) declares the parameters
    its stream supports.  Each field carries its Aspen node name as the
    ``"alias"`` metadata, and an optional ``"sub"`` metadata names a child
    node (e.g. ``MIXED``).
    """

    units: Units | None = field(default=None)

@dataclass
class RCSTRInput(BlockInput):
    """Inputs for :class:`RCSTR` (temperature/duty/vapor_fraction set ``SPEC_OPT``)."""

    spec_type: str | None = field(default=None, metadata={"alias": "SPEC_TYPE"})
    volume: float | None = field(default=None, metadata={"alias": "VOL", "unit_attr": "volume"})
    residence_time: float | None = field(default=None, metadata={"alias": "RES_TIME"})
    temperature: float | None = field(default=None, metadata={"alias": "TEMP", "spec_opt": "TEMP", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "PRES", "unit_attr": "pressure"})
    duty: float | None = field(default=None, metadata={"alias": "DUTY", "spec_opt": "DUTY", "unit_attr": "duty"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "VFRAC", "spec_opt": "VFRAC"})
    phase: str | None = field(default=None, metadata={"alias": "PHASE"})
    phase_number: int | None = field(default=None, metadata={"alias": "NPHASE"})


@dataclass
class RPlugInput(BlockInput):
    """Inputs for :class:`RPlug`."""

    reactor_type: str | None = field(default=None, metadata={"alias": "TYPE"})
    operating_condition: str | None = field(default=None, metadata={"alias": "OPT_TSPEC"})
    reactor_temperature: float | None = field(default=None, metadata={"alias": "REAC_TEMP", "unit_attr": "temperature"})
    temperature: float | None = field(default=None, metadata={"alias": "TEMP", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "PRES", "unit_attr": "pressure"})
    phase: str | None = field(default=None, metadata={"alias": "PHASE"})
    phase_number: int | None = field(default=None, metadata={"alias": "NPHASE"})
    tube_length: float | None = field(default=None, metadata={"alias": "LENGTH", "unit_attr": "length"})
    tube_diameter: float | None = field(default=None, metadata={"alias": "DIAM", "unit_attr": "length"})
    number_of_tubes: int | None = field(default=None, metadata={"alias": "NTUBE"})
    heat_transfer_coefficient: float | None = field(default=None, metadata={"alias": "U", "unit_attr": "heat_transfer_coefficient"})
    pressure_drop_option: str | None = field(default=None, metadata={"alias": "OPT_PDROP"})
    process_pressure_drop: float | None = field(default=None, metadata={"alias": "PDROP", "unit_attr": "pressure"})
    activate_reactions: str | None = field(default=None, metadata={"alias": "REACSYS"})


@dataclass
class DSTWUInput(BlockInput):
    """Inputs for :class:`DSTWU`."""

    stage_reflux_option: str | None = field(default=None, metadata={"alias": "OPT_NTRR"})
    number_of_stages: int | None = field(default=None, metadata={"alias": "NSTAGE"})
    reflux_ratio: float | None = field(default=None, metadata={"alias": "RR"})
    condenser_pressure: float | None = field(default=None, metadata={"alias": "PTOP", "unit_attr": "pressure"})
    reboiler_pressure: float | None = field(default=None, metadata={"alias": "PBOT", "unit_attr": "pressure"})
    light_key: str | None = field(default=None, metadata={"alias": "LIGHTKEY"})
    heavy_key: str | None = field(default=None, metadata={"alias": "HEAVYKEY"})
    light_key_recovery: float | None = field(default=None, metadata={"alias": "RECOVL"})
    heavy_key_recovery: float | None = field(default=None, metadata={"alias": "RECOVH"})
    condenser_option: str | None = field(default=None, metadata={"alias": "OPT_RDV"})
    distillate_vapor_fraction: float | None = field(default=None, metadata={"alias": "RDV"})


@dataclass
class Flash2Input(BlockInput):
    """Inputs for :class:`Flash2`."""

    flash_type: FlashType | None = field(default=None, metadata={"alias": "SPEC_OPT"})
    temperature: float | None = field(default=None, metadata={"alias": "TEMP", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "PRES", "unit_attr": "pressure"})
    duty: float | None = field(default=None, metadata={"alias": "DUTY", "unit_attr": "duty"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "VFRAC"})
    phase: str | None = field(default=None, metadata={"alias": "Phase"})
    phase_number: int | None = field(default=None, metadata={"alias": "NPhase"})
    temperature_estimate: float | None = field(default=None, metadata={"alias": "T_EST", "unit_attr": "temperature"})
    pressure_estimate: float | None = field(default=None, metadata={"alias": "P_EST", "unit_attr": "pressure"})
    max_iteration: int | None = field(default=None, metadata={"alias": "MAXIT"})
    error_tolerance: float | None = field(default=None, metadata={"alias": "TOL"})


@dataclass
class MixerInput(BlockInput):
    """Inputs for :class:`Mixer`."""

    pressure: float | None = field(default=None, metadata={"alias": "PRES", "unit_attr": "pressure"})
    phase: str | None = field(default=None, metadata={"alias": "Phase"})
    phase_number: int | None = field(default=None, metadata={"alias": "NPhase"})
    temperature_estimate: float | None = field(default=None, metadata={"alias": "T_EST", "unit_attr": "temperature"})
    max_iteration: int | None = field(default=None, metadata={"alias": "MAXIT"})
    error_tolerance: float | None = field(default=None, metadata={"alias": "TOL"})


@dataclass
class HeaterInput(BlockInput):
    """Inputs for :class:`Heater`."""

    flash_type: FlashType | None = field(default=None, metadata={"alias": "SPEC_OPT"})
    temperature: float | None = field(default=None, metadata={"alias": "TEMP", "unit_attr": "temperature"})
    temperature_change: float | None = field(default=None, metadata={"alias": "DELT", "unit_attr": "temperature"})
    degrees_superheating: float | None = field(default=None, metadata={"alias": "DEGSUP", "unit_attr": "temperature"})
    degrees_subcooling: float | None = field(default=None, metadata={"alias": "DEGSUB", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "PRES", "unit_attr": "pressure"})
    duty: float | None = field(default=None, metadata={"alias": "DUTY", "unit_attr": "duty"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "VFRAC"})
    pressure_drop_correlation: str | None = field(default=None, metadata={"alias": "DPPARM"})
    phase: str | None = field(default=None, metadata={"alias": "Phase"})
    phase_number: int | None = field(default=None, metadata={"alias": "NPhase"})
    temperature_estimate: float | None = field(default=None, metadata={"alias": "T_EST", "unit_attr": "temperature"})
    pressure_estimate: float | None = field(default=None, metadata={"alias": "P_EST", "unit_attr": "pressure"})
    max_iteration: int | None = field(default=None, metadata={"alias": "MAXIT"})
    error_tolerance: float | None = field(default=None, metadata={"alias": "TOL"})


@dataclass
class RadfracInput(BlockInput):
    """Inputs for :class:`Radfrac`."""

    calculation_type: str | None = field(default=None, metadata={"alias": "CALC_MODE"})
    number_of_stages: int | None = field(default=None, metadata={"alias": "NSTAGE"})
    condenser_type: str | None = field(default=None, metadata={"alias": "CONDENSER"})
    reboiler_type: str | None = field(default=None, metadata={"alias": "REBOILER"})
    phase: str | None = field(default=None, metadata={"alias": "Phase"})
    phase_number: int | None = field(default=None, metadata={"alias": "NPhase"})
    convergence_method: str | None = field(default=None, metadata={"alias": "CONV_METH"})
    reflux_ratio: float | None = field(default=None, metadata={"alias": "BASIS_RR"})
    condenser_pressure: float | None = field(default=None, metadata={"alias": "PRES1", "unit_attr": "pressure"})


@dataclass
class SplitterInput(BlockInput):
    """Inputs for :class:`Splitter`."""

    pressure: float | None = field(default=None, metadata={"alias": "PRES1", "unit_attr": "pressure"})
    phase: str | None = field(default=None, metadata={"alias": "Phase"})
    phase_number: int | None = field(default=None, metadata={"alias": "NPhase"})
    max_iteration: int | None = field(default=None, metadata={"alias": "MAXIT"})
    error_tolerance: float | None = field(default=None, metadata={"alias": "TOL"})


@dataclass
class RYieldInput(BlockInput):
    """Inputs for :class:`RYield`."""

    flash_type: FlashType | None = field(default=None, metadata={"alias": "SPEC_OPT"})
    temperature: float | None = field(default=None, metadata={"alias": "TEMP", "unit_attr": "temperature"})
    temperature_change: float | None = field(default=None, metadata={"alias": "DELT", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "PRES", "unit_attr": "pressure"})
    duty: float | None = field(default=None, metadata={"alias": "DUTY", "unit_attr": "duty"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "VFRAC"})
    phase: str | None = field(default=None, metadata={"alias": "Phase"})
    phase_number: int | None = field(default=None, metadata={"alias": "NPhase"})
    yield_calc_option: str | None = field(default=None, metadata={"alias": "USER_YIELD"})
    activate_reactions: str | None = field(default=None, metadata={"alias": "REACSYS"})
    temperature_estimate: float | None = field(default=None, metadata={"alias": "T_EST", "unit_attr": "temperature"})
    pressure_estimate: float | None = field(default=None, metadata={"alias": "P_EST", "unit_attr": "pressure"})
    max_iteration: int | None = field(default=None, metadata={"alias": "MAXIT"})
    error_tolerance: float | None = field(default=None, metadata={"alias": "TOL"})


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


class Block(ABC, Generic[BlockInputT]):
    """Base class for unit-operation blocks on the Aspen Plus flowsheet.

    Subclasses must implement :meth:`type` and :meth:`set_input`.  The
    ``name`` is optional and defaults to the uppercased variable the object
    is assigned to.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = _resolve_name(name)
        self._node: IHNode | None = None  # injected by flowsheet.place at exec time

    @abstractmethod
    def type(self) -> str:
        """Return the Aspen Plus equipment type string."""

    @abstractmethod
    def set_input(self, inputs: BlockInputT) -> None:
        """Apply *inputs* to this block; subclasses document supported fields."""

    def get_input(self) -> BlockInputT:
        """Read this block's current Input parameters into a :class:`BlockInput`."""
        node = self._node
        if node is None:
            raise RuntimeError("block node not injected; call flowsheet.place first")
        input_cls = cast(type[BlockInputT], get_type_hints(type(self).set_input)["inputs"])
        values: dict[str, Any] = {}
        unit_kwargs: dict[str, str] = {}
        for f in fields(input_cls):
            if "alias" not in f.metadata:
                continue  # skip non-parameter fields (e.g. units)
            meta = f.metadata
            param_node = node.Elements("Input").Elements(meta["alias"])
            if param_node is None:
                values[f.name] = None
                continue
            try:
                values[f.name] = param_node.AttributeValue(HAPAttributeType.HAP_VALUE)
                if "unit_attr" in meta and meta["unit_attr"] not in unit_kwargs:
                    unit_val = param_node.AttributeValue(HAPAttributeType.HAP_UOM)
                    if unit_val is not None:
                        unit_kwargs[meta["unit_attr"]] = str(unit_val)
            except COMError:
                values[f.name] = None
        values["units"] = Units(**unit_kwargs) if unit_kwargs else None
        return input_cls(**values)

    def _set_input(self, inputs: BlockInputT) -> None:
        """Write every non-``None`` field of *inputs* to this block.

        Each field's ``"alias"`` metadata names the ``Input`` node; a
        ``"spec_opt"`` metadata is written to ``SPEC_OPT`` first.  Values are
        written via ``AttributeValue`` (an indexed property, PROPERTYPUT
        cParams=2, see properties.py) on the ``HAP_VALUE`` attribute.
        """
        node = self._node
        if node is None:
            raise RuntimeError("block node not injected; call flowsheet.place first")

        def log_write(param: str, attr: HAPAttributeType, value: object) -> None:
            logger.debug("set {}/Input/{} {} = {}", node.Name(), param, attr.name, value)

        def write(param: str, value: object) -> None:
            log_write(param, HAPAttributeType.HAP_VALUE, value)
            param_node = node.Elements("Input").Elements(param)
            cast(Any, param_node).AttributeValue[HAPAttributeType.HAP_VALUE, 0] = value

        def write_unit(param: str, unit: str) -> None:
            log_write(param, HAPAttributeType.HAP_UOM, unit)
            param_node = node.Elements("Input").Elements(param)
            cast(Any, param_node).AttributeValue[HAPAttributeType.HAP_UOM, 0] = unit

        for f in fields(inputs):
            if "alias" not in f.metadata:
                continue  # skip non-parameter fields (e.g. units)
            value = getattr(inputs, f.name)
            if value is None:
                continue
            meta = f.metadata
            if "spec_opt" in meta:
                write("SPEC_OPT", meta["spec_opt"])
            if "unit_attr" in meta and inputs.units is not None:
                unit_val = getattr(inputs.units, meta["unit_attr"])
                if unit_val is not None:
                    write_unit(meta["alias"], unit_val)
            write(meta["alias"], value)


class RCSTR(Block[RCSTRInput]):
    """Continuous stirred-tank reactor."""

    def type(self) -> str:
        return "RCSTR"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: RCSTRInput) -> None:
        """Apply RCSTR inputs from a :class:`RCSTRInput`."""
        self._set_input(inputs)


class RPlug(Block[RPlugInput]):
    """Plug-flow reactor."""

    def type(self) -> str:
        return "RPlug"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: RPlugInput) -> None:
        """Apply RPlug inputs from a :class:`RPlugInput`."""
        self._set_input(inputs)


class DSTWU(Block[DSTWUInput]):
    """Shortcut distillation column."""

    def type(self) -> str:
        return "DSTWU"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def d_out(self) -> PortType:
        return PortType.DISTILLATE_OUT

    def b_out(self) -> PortType:
        return PortType.BOTTOMS_OUT

    def set_input(self, inputs: DSTWUInput) -> None:
        """Apply DSTWU inputs from a :class:`DSTWUInput`."""
        self._set_input(inputs)


class Flash2(Block[Flash2Input]):
    """Two-outlet flash separator."""

    def type(self) -> str:
        return "Flash2"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def v_out(self) -> PortType:
        return PortType.VAPOR_OUT

    def l_out(self) -> PortType:
        return PortType.LIQUID_OUT

    def set_input(self, inputs: Flash2Input) -> None:
        """Apply Flash2 inputs from a :class:`Flash2Input`."""
        self._set_input(inputs)


class Mixer(Block[MixerInput]):
    """Stream mixer."""

    def type(self) -> str:
        return "Mixer"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: MixerInput) -> None:
        """Apply Mixer inputs from a :class:`MixerInput`."""
        self._set_input(inputs)


class Heater(Block[HeaterInput]):
    """Heater/cooler."""

    def type(self) -> str:
        return "Heater"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: HeaterInput) -> None:
        """Apply Heater inputs from a :class:`HeaterInput`."""
        self._set_input(inputs)


class Radfrac(Block[RadfracInput]):
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

    def set_input(self, inputs: RadfracInput) -> None:
        """Apply Radfrac inputs from a :class:`RadfracInput`."""
        self._set_input(inputs)


class Splitter(Block[SplitterInput]):
    """Stream splitter."""

    def type(self) -> str:
        return "Splitter"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: SplitterInput) -> None:
        """Apply Splitter inputs from a :class:`SplitterInput`."""
        self._set_input(inputs)


class RYield(Block[RYieldInput]):
    """Yield reactor."""

    def type(self) -> str:
        return "RYield"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: RYieldInput) -> None:
        """Apply RYield inputs from a :class:`RYieldInput`."""
        self._set_input(inputs)


class Stream(ABC, Generic[StreamInputT]):
    """Base class for material, heat, or work streams.

    Subclasses must implement :meth:`type` and :meth:`set_input`.  The
    ``name`` is optional and defaults to the uppercased variable the object
    is assigned to.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = _resolve_name(name)
        self._node: IHNode | None = None  # injected by flowsheet.place/bind at exec time

    @abstractmethod
    def type(self) -> str:
        """Return the Aspen Plus stream type string."""

    @abstractmethod
    def set_input(self, inputs: StreamInputT) -> None:
        """Apply *inputs* to this stream; subclasses document supported fields."""

    def get_input(self) -> StreamInputT:
        """Read this stream's current Input parameters into a :class:`StreamInput`."""
        node = self._node
        if node is None:
            raise RuntimeError("stream node not injected; call flowsheet.place/bind first")
        input_cls = cast(type[StreamInputT], get_type_hints(type(self).set_input)["inputs"])
        values: dict[str, Any] = {}
        unit_kwargs: dict[str, str] = {}
        for f in fields(input_cls):
            meta = f.metadata
            if "alias" not in meta:
                continue  # skip non-parameter fields (e.g. units)
            param_node = node.Elements("Input").Elements(meta["alias"])
            if param_node is None:
                values[f.name] = None
                continue
            try:
                if "basis" in meta:
                    basis_node = param_node.Elements(meta["sub"]) if "sub" in meta else param_node
                    if basis_node is None:
                        values[f.name] = None
                        continue
                    values[f.name] = basis_node.AttributeValue(HAPAttributeType.HAP_BASIS)
                elif "comps" in meta:
                    comp_node = param_node.Elements(meta["sub"]) if "sub" in meta else param_node
                    if comp_node is None:
                        values[f.name] = None
                        continue
                    comp_values: dict[str, Any] = {}
                    for elem in comp_node.Elements:
                        elem_node = cast(IHNode, elem)
                        comp_values[str(elem_node.Name())] = elem_node.AttributeValue(HAPAttributeType.HAP_VALUE)
                    values[f.name] = comp_values
                    if "unit_attr" in meta and meta["unit_attr"] not in unit_kwargs:
                        unit_val = comp_node.AttributeValue(HAPAttributeType.HAP_UOM)
                        if unit_val is not None:
                            unit_kwargs[meta["unit_attr"]] = str(unit_val)
                else:
                    param_node = param_node.Elements(meta["sub"]) if "sub" in meta else param_node
                    if param_node is None:
                        values[f.name] = None
                        continue
                    values[f.name] = param_node.AttributeValue(HAPAttributeType.HAP_VALUE)
                    if "unit_attr" in meta and meta["unit_attr"] not in unit_kwargs:
                        unit_val = param_node.AttributeValue(HAPAttributeType.HAP_UOM)
                        if unit_val is not None:
                            unit_kwargs[meta["unit_attr"]] = str(unit_val)
            except COMError:
                values[f.name] = None
        values["units"] = Units(**unit_kwargs) if unit_kwargs else None
        return input_cls(**values)

    def _set_input(self, inputs: StreamInputT) -> None:
        """Write every non-``None`` field of *inputs* to this stream.

        Each field's ``"alias"`` metadata names the ``Input`` node, and an
        optional ``"sub"`` metadata names a child node (e.g. ``MIXED``).
        Values are written via ``AttributeValue`` (an indexed property,
        PROPERTYPUT cParams=2, see properties.py); a ``"basis"`` metadata
        targets ``HAP_BASIS``, a ``"comps"`` metadata writes per-component
        values, and everything else writes ``HAP_VALUE``.
        """
        node = self._node
        if node is None:
            raise RuntimeError("stream node not injected; call flowsheet.place/bind first")

        def param_node(param: str, sub: str | None) -> IHNode:
            pn = node.Elements("Input").Elements(param)
            if sub is not None:
                pn = pn.Elements(sub)
            return pn

        def log_write(param: str, attr: HAPAttributeType, value: object, sub: str | None = None, comp: str | None = None) -> None:
            path = f"{node.Name()}/Input/{param}"
            if sub is not None:
                path += f"/{sub}"
            if comp is not None:
                path += f"/{comp}"
            logger.debug("set {} {} = {}", path, attr.name, value)

        for f in fields(inputs):
            if "alias" not in f.metadata:
                continue  # skip non-parameter fields (e.g. units)
            value = getattr(inputs, f.name)
            if value is None:
                continue
            meta = f.metadata
            if "unit_attr" in meta and inputs.units is not None:
                unit_val = getattr(inputs.units, meta["unit_attr"])
                if unit_val is not None:
                    target_unit = param_node(meta["alias"], meta.get("sub"))
                    log_write(meta["alias"], HAPAttributeType.HAP_UOM, unit_val, meta.get("sub"))
                    cast(Any, target_unit).AttributeValue[HAPAttributeType.HAP_UOM, 0] = unit_val
            if "basis" in meta:
                log_write(meta["alias"], HAPAttributeType.HAP_BASIS, value, meta.get("sub"))
                cast(Any, param_node(meta["alias"], meta.get("sub"))).AttributeValue[
                    HAPAttributeType.HAP_BASIS, 0
                ] = value
            elif "comps" in meta:
                if "basis_value" in meta:
                    basis = meta["basis_value"]
                    basis_override = getattr(inputs, f"{f.name}_basis", None)
                    if basis_override is not None:
                        basis = basis_override
                    log_write("BASIS", HAPAttributeType.HAP_VALUE, basis, meta.get("sub"))
                    cast(Any, param_node("BASIS", meta.get("sub"))).AttributeValue[
                        HAPAttributeType.HAP_VALUE, 0
                    ] = basis
                for comp, comp_value in cast(dict[str, Any], value).items():
                    log_write(meta["alias"], HAPAttributeType.HAP_VALUE, comp_value, meta.get("sub"), comp)
                    cast(Any, param_node(meta["alias"], meta.get("sub")).Elements(comp)).AttributeValue[
                        HAPAttributeType.HAP_VALUE, 0
                    ] = comp_value
            else:
                log_write(meta["alias"], HAPAttributeType.HAP_VALUE, value, meta.get("sub"))
                cast(Any, param_node(meta["alias"], meta.get("sub"))).AttributeValue[
                    HAPAttributeType.HAP_VALUE, 0
                ] = value


@dataclass
class MaterialStreamInput(StreamInput):
    """Inputs for :class:`MaterialStream`."""

    flash_type: FlashType | None = field(default=None, metadata={"alias": "MIXED_SPEC", "sub": "MIXED"})
    temperature: float | None = field(default=None, metadata={"alias": "TEMP", "sub": "MIXED", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "PRES", "sub": "MIXED", "unit_attr": "pressure"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "VFRAC", "sub": "MIXED"})
    total_flow_basis: FlowBasis | None = field(default=None, metadata={"alias": "FLOWBASE", "sub": "MIXED"})
    total_flow_rate: float | None = field(default=None, metadata={"alias": "TOTFLOW", "sub": "MIXED", "unit_attr": "total_flow_rate"})
    composition: dict[str, float] | None = field(default=None, metadata={"alias": "FLOW", "sub": "MIXED", "comps": True, "unit_attr": "composition_flow", "basis_value": "MASS-FRAC"})
    composition_basis: CompositionBasis | None = field(default=None)


class MaterialStream(Stream[MaterialStreamInput]):
    """Material stream."""

    def type(self) -> str:
        return "MATERIAL"

    def set_input(self, inputs: MaterialStreamInput) -> None:
        """Apply MaterialStream inputs from a :class:`MaterialStreamInput`.

        Supported fields: ``flash_type``, ``temperature``, ``pressure``,
        ``vapor_fraction``, ``total_flow_rate``, ``total_flow_basis``,
        ``composition``, ``composition_basis``.
        """
        self._set_input(inputs)


class HeatStream(Stream[StreamInput]):
    """Heat stream."""

    def type(self) -> str:
        return "HEAT"

    def set_input(self, inputs: StreamInput) -> None:
        """HeatStream has no configurable inputs."""
        raise NotImplementedError("HeatStream has no inputs to set")

    def get_input(self) -> StreamInput:
        """HeatStream has no configurable inputs."""
        raise NotImplementedError("HeatStream has no inputs to get")



class WorkStream(Stream[StreamInput]):
    """Work stream (empty Aspen type string)."""

    def type(self) -> str:
        return "WORK"

    def set_input(self, inputs: StreamInput) -> None:
        """WorkStream has no configurable inputs."""
        raise NotImplementedError("WorkStream has no inputs to set")

    def get_input(self) -> StreamInput:
        """WorkStream has no configurable inputs."""
        raise NotImplementedError("WorkStream has no inputs to get")



class PowerStream(Stream[StreamInput]):
    """power stream."""

    def type(self) -> str:
        return "POWER"

    def set_input(self, inputs: StreamInput) -> None:
        """PowerStream has no configurable inputs."""
        raise NotImplementedError("PowerStream has no inputs to set")

    def get_input(self) -> StreamInput:
        """PowerStream has no configurable inputs."""
        raise NotImplementedError("PowerStream has no inputs to get")
