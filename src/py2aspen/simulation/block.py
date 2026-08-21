"""Block object definitions for Aspen Plus simulations.

References BlockPlace / BlockDelete in CodeLibrary.py.  The shared ``Units``
dataclass and the ``_resolve_name`` helper live in
:mod:`py2aspen.simulation._common`.

``Block`` is an abstract base class; use its concrete subclasses (e.g.
:class:`RCSTR`, :class:`Radfrac`), which implement
:meth:`Block.get_type`.  The ``name`` argument is optional --- when omitted
it defaults to the uppercased name of the variable the object is assigned
to.

Placement and connection on the flowsheet are handled by the operations in
:mod:`py2aspen.flowsheet` (e.g. :func:`py2aspen.flowsheet.place`,
:func:`py2aspen.flowsheet.connect`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from typing import Any, Generic, TypeVar, cast, get_type_hints

from comtypes import COMError

from py2aspen.aspen_type import FlashType, HAPAttributeType, IHNode, PortType
from py2aspen.log import logger

from ._common import Units, _resolve_name, _unit_col

BlockInputT = TypeVar("BlockInputT", bound="BlockInput")
BlockResultsT = TypeVar("BlockResultsT", bound="BlockResults")


__all__ = [
    "DSTWU",
    "RCSTR",
    "Block",
    "BlockInput",
    "BlockResults",
    "DSTWUInput",
    "DSTWUResults",
    "Flash2",
    "Flash2Input",
    "Flash2Results",
    "Heater",
    "HeaterInput",
    "HeaterResults",
    "Mixer",
    "MixerInput",
    "MixerResults",
    "RCSTRInput",
    "RCSTRResults",
    "RPlug",
    "RPlugInput",
    "RPlugResults",
    "RYield",
    "RYieldInput",
    "RYieldResults",
    "Radfrac",
    "RadfracInput",
    "RadfracResults",
    "Splitter",
    "SplitterInput",
    "SplitterResults",
    "Units",
]


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
class BlockResults:
    """Base class for block result (Output) dataclasses.

    Each subclass (e.g. :class:`Flash2Results`) declares the output values its
    block exposes.  Each field carries its Aspen node name as the ``"alias"``
    metadata; a ``"unit_attr"`` metadata names the physical quantity so a
    :class:`Units` can target it for conversion.
    """

    units: Units | None = field(default=None)


class Block(ABC, Generic[BlockInputT, BlockResultsT]):
    """Base class for unit-operation blocks on the Aspen Plus flowsheet.

    Subclasses must implement :meth:`get_type`, :meth:`set_input` and
    :meth:`get_results`.  The ``name`` is optional and defaults to the
    uppercased variable the object is assigned to.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = _resolve_name(name)
        self._node: IHNode | None = None  # injected by flowsheet.place at exec time

    @abstractmethod
    def get_type(self) -> str:
        """Return the Aspen Plus equipment type string."""

    @abstractmethod
    def set_input(self, inputs: BlockInputT) -> None:
        """Apply *inputs* to this block; subclasses document supported fields."""

    @abstractmethod
    def get_results(self, units: Units | None = None) -> BlockResultsT:
        """Read this block's Output summary values into a :class:`BlockResults`.

        Values are returned in Aspen's current display units; pass a
        :class:`Units` (e.g. ``Units(pressure="atm")``) to convert the
        corresponding quantities to the given units.
        """

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

    def _get_results(self, results_cls: type[BlockResultsT], units: Units | None = None) -> BlockResultsT:
        """Read this block's Output summary values into *results_cls*.

        Each field's ``"alias"`` metadata names an ``Output`` node.  A field
        with a ``"unit_attr"`` metadata and a matching target unit in *units*
        is read via ``ValueForUnit`` (converted to that unit); other fields
        are read in the current display unit and their ``UnitString`` is
        recorded.
        """
        node = self._node
        if node is None:
            raise RuntimeError("block node not injected; call flowsheet.place first")
        values: dict[str, Any] = {}
        unit_kwargs: dict[str, str] = {}
        for f in fields(results_cls):
            if "alias" not in f.metadata:
                continue  # skip non-parameter fields (e.g. units)
            meta = f.metadata
            out_node = node.Elements("Output").Elements(meta["alias"])
            if out_node is None:
                values[f.name] = None
                continue
            try:
                if "unit_attr" in meta:
                    attr = meta["unit_attr"]
                    target = getattr(units, attr) if units is not None else None
                    if target is not None:
                        row = out_node.AttributeValue(HAPAttributeType.HAP_UNITROW)
                        col = _unit_col(out_node, row, target)
                        values[f.name] = out_node.ValueForUnit(row, col) if col is not None else None
                        unit_kwargs[attr] = target
                    else:
                        values[f.name] = out_node.AttributeValue(HAPAttributeType.HAP_VALUE)
                        try:
                            unit_kwargs.setdefault(attr, str(out_node.UnitString))
                        except COMError:
                            pass
                else:
                    values[f.name] = out_node.AttributeValue(HAPAttributeType.HAP_VALUE)
            except COMError:
                values[f.name] = None
        values["units"] = Units(**unit_kwargs) if unit_kwargs else None
        return results_cls(**values)


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


@dataclass
class RCSTRResults(BlockResults):
    """Outputs for :class:`RCSTR`."""

    temperature: float | None = field(default=None, metadata={"alias": "B_TEMP", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "B_PRES", "unit_attr": "pressure"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "B_VFRAC"})
    heat_duty: float | None = field(default=None, metadata={"alias": "QCALC", "unit_attr": "duty"})
    net_duty: float | None = field(default=None, metadata={"alias": "QNET", "unit_attr": "duty"})
    volume: float | None = field(default=None, metadata={"alias": "TOT_VOL", "unit_attr": "volume"})
    vapor_volume: float | None = field(default=None, metadata={"alias": "VAP_VOL", "unit_attr": "volume"})
    liquid_volume: float | None = field(default=None, metadata={"alias": "LIQ_VOL", "unit_attr": "volume"})
    residence_time: float | None = field(default=None, metadata={"alias": "TOT_RES_TIME"})
    convergence_status: str | None = field(default=None, metadata={"alias": "BLKSTAT"})
    convergence_message: str | None = field(default=None, metadata={"alias": "BLKMSG"})
    property_status: str | None = field(default=None, metadata={"alias": "PROPSTAT"})


class RCSTR(Block[RCSTRInput, RCSTRResults]):
    """Continuous stirred-tank reactor."""

    def get_type(self) -> str:
        return "RCSTR"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: RCSTRInput) -> None:
        """Apply RCSTR inputs from a :class:`RCSTRInput`."""
        self._set_input(inputs)

    def get_results(self, units: Units | None = None) -> RCSTRResults:
        """Read RCSTR Output summary values into a :class:`RCSTRResults`."""
        return self._get_results(RCSTRResults, units)


@dataclass
class RPlugResults(BlockResults):
    """Outputs for :class:`RPlug`."""

    heat_duty: float | None = field(default=None, metadata={"alias": "QCALC", "unit_attr": "duty"})
    min_temperature: float | None = field(default=None, metadata={"alias": "TMIN", "unit_attr": "temperature"})
    max_temperature: float | None = field(default=None, metadata={"alias": "TMAX", "unit_attr": "temperature"})
    residence_time: float | None = field(default=None, metadata={"alias": "RES_TIME"})
    coolant_inlet_temperature: float | None = field(default=None, metadata={"alias": "COOLANT_TIN", "unit_attr": "temperature"})
    coolant_inlet_vapor_fraction: float | None = field(default=None, metadata={"alias": "COOLANT_VIN"})
    convergence_status: str | None = field(default=None, metadata={"alias": "BLKSTAT"})
    convergence_message: str | None = field(default=None, metadata={"alias": "BLKMSG"})
    property_status: str | None = field(default=None, metadata={"alias": "PROPSTAT"})


class RPlug(Block[RPlugInput, RPlugResults]):
    """Plug-flow reactor."""

    def get_type(self) -> str:
        return "RPlug"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: RPlugInput) -> None:
        """Apply RPlug inputs from a :class:`RPlugInput`."""
        self._set_input(inputs)

    def get_results(self, units: Units | None = None) -> RPlugResults:
        """Read RPlug Output summary values into a :class:`RPlugResults`."""
        return self._get_results(RPlugResults, units)


@dataclass
class DSTWUResults(BlockResults):
    """Outputs for :class:`DSTWU`."""

    min_reflux_ratio: float | None = field(default=None, metadata={"alias": "MIN_REFLUX"})
    actual_reflux_ratio: float | None = field(default=None, metadata={"alias": "ACT_REFLUX"})
    min_stages: float | None = field(default=None, metadata={"alias": "MIN_STAGES"})
    actual_stages: float | None = field(default=None, metadata={"alias": "ACT_STAGES"})
    feed_stage: float | None = field(default=None, metadata={"alias": "FEED_LOCATN"})
    reboiler_duty: float | None = field(default=None, metadata={"alias": "REB_DUTY", "unit_attr": "duty"})
    condenser_duty: float | None = field(default=None, metadata={"alias": "COND_DUTY", "unit_attr": "duty"})
    distillate_temperature: float | None = field(default=None, metadata={"alias": "DISTIL_TEMP", "unit_attr": "temperature"})
    bottom_temperature: float | None = field(default=None, metadata={"alias": "BOTTOM_TEMP", "unit_attr": "temperature"})
    distillate_feed_fraction: float | None = field(default=None, metadata={"alias": "DIST_VS_FEED"})
    hetp: float | None = field(default=None, metadata={"alias": "HETP", "unit_attr": "length"})
    convergence_status: str | None = field(default=None, metadata={"alias": "BLKSTAT"})
    convergence_message: str | None = field(default=None, metadata={"alias": "BLKMSG"})
    property_status: str | None = field(default=None, metadata={"alias": "PROPSTAT"})


class DSTWU(Block[DSTWUInput, DSTWUResults]):
    """Shortcut distillation column."""

    def get_type(self) -> str:
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

    def get_results(self, units: Units | None = None) -> DSTWUResults:
        """Read DSTWU Output summary values into a :class:`DSTWUResults`."""
        return self._get_results(DSTWUResults, units)


@dataclass
class Flash2Results(BlockResults):
    """Outputs for :class:`Flash2`."""

    temperature: float | None = field(default=None, metadata={"alias": "B_TEMP", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "B_PRES", "unit_attr": "pressure"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "B_VFRAC"})
    vapor_fraction_mass: float | None = field(default=None, metadata={"alias": "MVFRAC"})
    heat_duty: float | None = field(default=None, metadata={"alias": "QCALC", "unit_attr": "duty"})
    net_duty: float | None = field(default=None, metadata={"alias": "QNET", "unit_attr": "duty"})
    liquid_ratio: float | None = field(default=None, metadata={"alias": "LIQ_RATIO"})
    pressure_drop: float | None = field(default=None, metadata={"alias": "PDROP", "unit_attr": "pressure"})
    convergence_status: str | None = field(default=None, metadata={"alias": "BLKSTAT"})
    convergence_message: str | None = field(default=None, metadata={"alias": "BLKMSG"})
    property_status: str | None = field(default=None, metadata={"alias": "PROPSTAT"})


class Flash2(Block[Flash2Input, Flash2Results]):
    """Two-outlet flash separator."""

    def get_type(self) -> str:
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

    def get_results(self, units: Units | None = None) -> Flash2Results:
        """Read Flash2 Output summary values into a :class:`Flash2Results`."""
        return self._get_results(Flash2Results, units)


@dataclass
class MixerResults(BlockResults):
    """Outputs for :class:`Mixer`."""

    temperature: float | None = field(default=None, metadata={"alias": "B_TEMP", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "B_PRES", "unit_attr": "pressure"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "B_VFRAC"})
    liquid_ratio: float | None = field(default=None, metadata={"alias": "LIQ_RATIO"})
    pressure_drop: float | None = field(default=None, metadata={"alias": "PDROP", "unit_attr": "pressure"})
    convergence_status: str | None = field(default=None, metadata={"alias": "BLKSTAT"})
    convergence_message: str | None = field(default=None, metadata={"alias": "BLKMSG"})
    property_status: str | None = field(default=None, metadata={"alias": "PROPSTAT"})


class Mixer(Block[MixerInput, MixerResults]):
    """Stream mixer."""

    def get_type(self) -> str:
        return "Mixer"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: MixerInput) -> None:
        """Apply Mixer inputs from a :class:`MixerInput`."""
        self._set_input(inputs)

    def get_results(self, units: Units | None = None) -> MixerResults:
        """Read Mixer Output summary values into a :class:`MixerResults`."""
        return self._get_results(MixerResults, units)


@dataclass
class HeaterResults(BlockResults):
    """Outputs for :class:`Heater` (flash-family summary)."""

    temperature: float | None = field(default=None, metadata={"alias": "B_TEMP", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "B_PRES", "unit_attr": "pressure"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "B_VFRAC"})
    heat_duty: float | None = field(default=None, metadata={"alias": "QCALC", "unit_attr": "duty"})
    net_duty: float | None = field(default=None, metadata={"alias": "QNET", "unit_attr": "duty"})
    pressure_drop: float | None = field(default=None, metadata={"alias": "PDROP", "unit_attr": "pressure"})
    convergence_status: str | None = field(default=None, metadata={"alias": "BLKSTAT"})
    convergence_message: str | None = field(default=None, metadata={"alias": "BLKMSG"})
    property_status: str | None = field(default=None, metadata={"alias": "PROPSTAT"})


class Heater(Block[HeaterInput, HeaterResults]):
    """Heater/cooler."""

    def get_type(self) -> str:
        return "Heater"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: HeaterInput) -> None:
        """Apply Heater inputs from a :class:`HeaterInput`."""
        self._set_input(inputs)

    def get_results(self, units: Units | None = None) -> HeaterResults:
        """Read Heater Output summary values into a :class:`HeaterResults`."""
        return self._get_results(HeaterResults, units)


@dataclass
class RadfracResults(BlockResults):
    """Outputs for :class:`Radfrac`."""

    condenser_temperature: float | None = field(default=None, metadata={"alias": "TOP_TEMP", "unit_attr": "temperature"})
    condenser_subcooled_temperature: float | None = field(default=None, metadata={"alias": "SCTEMP", "unit_attr": "temperature"})
    condenser_duty: float | None = field(default=None, metadata={"alias": "COND_DUTY", "unit_attr": "duty"})
    distillate_rate: float | None = field(default=None, metadata={"alias": "MOLE_D", "unit_attr": "total_flow_rate"})
    reflux_rate: float | None = field(default=None, metadata={"alias": "MOLE_L1", "unit_attr": "total_flow_rate"})
    reboiler_temperature: float | None = field(default=None, metadata={"alias": "BOTTOM_TEMP", "unit_attr": "temperature"})
    reboiler_duty: float | None = field(default=None, metadata={"alias": "REB_DUTY", "unit_attr": "duty"})
    bottoms_rate: float | None = field(default=None, metadata={"alias": "MOLE_B", "unit_attr": "total_flow_rate"})
    boilup_rate: float | None = field(default=None, metadata={"alias": "MOLE_VN", "unit_attr": "total_flow_rate"})
    boilup_ratio: float | None = field(default=None, metadata={"alias": "CMF_MAMX"})
    distillate_feed_ratio: float | None = field(default=None, metadata={"alias": "MOLE_DFR"})
    bottoms_feed_ratio: float | None = field(default=None, metadata={"alias": "MOLE_BFR"})
    convergence_status: str | None = field(default=None, metadata={"alias": "BLKSTAT"})
    convergence_message: str | None = field(default=None, metadata={"alias": "BLKMSG"})
    property_status: str | None = field(default=None, metadata={"alias": "PROPSTAT"})


class Radfrac(Block[RadfracInput, RadfracResults]):
    """Rigorous multi-stage distillation column."""

    def get_type(self) -> str:
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

    def get_results(self, units: Units | None = None) -> RadfracResults:
        """Read Radfrac Output summary values into a :class:`RadfracResults`."""
        return self._get_results(RadfracResults, units)


@dataclass
class SplitterResults(BlockResults):
    """Outputs for :class:`Splitter` (per-stream split data pending)."""

    convergence_status: str | None = field(default=None, metadata={"alias": "BLKSTAT"})
    convergence_message: str | None = field(default=None, metadata={"alias": "BLKMSG"})
    property_status: str | None = field(default=None, metadata={"alias": "PROPSTAT"})


class Splitter(Block[SplitterInput, SplitterResults]):
    """Stream splitter."""

    def get_type(self) -> str:
        return "Splitter"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: SplitterInput) -> None:
        """Apply Splitter inputs from a :class:`SplitterInput`."""
        self._set_input(inputs)

    def get_results(self, units: Units | None = None) -> SplitterResults:
        """Read Splitter Output status values into a :class:`SplitterResults`."""
        return self._get_results(SplitterResults, units)


@dataclass
class RYieldResults(BlockResults):
    """Outputs for :class:`RYield`."""

    temperature: float | None = field(default=None, metadata={"alias": "B_TEMP", "unit_attr": "temperature"})
    pressure: float | None = field(default=None, metadata={"alias": "B_PRES", "unit_attr": "pressure"})
    heat_duty: float | None = field(default=None, metadata={"alias": "QCALC", "unit_attr": "duty"})
    net_duty: float | None = field(default=None, metadata={"alias": "QNET", "unit_attr": "duty"})
    vapor_fraction: float | None = field(default=None, metadata={"alias": "B_VFRAC"})
    liquid_ratio: float | None = field(default=None, metadata={"alias": "LIQ_RATIO"})
    convergence_status: str | None = field(default=None, metadata={"alias": "BLKSTAT"})
    convergence_message: str | None = field(default=None, metadata={"alias": "BLKMSG"})
    property_status: str | None = field(default=None, metadata={"alias": "PROPSTAT"})


class RYield(Block[RYieldInput, RYieldResults]):
    """Yield reactor."""

    def get_type(self) -> str:
        return "RYield"

    def f_in(self) -> PortType:
        return PortType.FEED_IN

    def p_out(self) -> PortType:
        return PortType.PRODUCT_OUT

    def set_input(self, inputs: RYieldInput) -> None:
        """Apply RYield inputs from a :class:`RYieldInput`."""
        self._set_input(inputs)

    def get_results(self, units: Units | None = None) -> RYieldResults:
        """Read RYield Output summary values into a :class:`RYieldResults`."""
        return self._get_results(RYieldResults, units)
