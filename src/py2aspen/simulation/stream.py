"""Stream object definitions for Aspen Plus simulations.

References StreamPlace / StreamDelete / StreamConnect / StreamDisconnect in
CodeLibrary.py.

``Stream`` is an abstract base class; use its concrete subclasses (e.g.
:class:`MaterialStream`, :class:`HeatStream`), which implement
:meth:`Stream.get_type`.  The ``name`` argument is optional --- when omitted
it defaults to the uppercased name of the variable the object is assigned
to.

Placement and connection on the flowsheet are handled by the operations in
:mod:`py2aspen.flowsheet` (e.g. :func:`py2aspen.flowsheet.place`,
:func:`py2aspen.flowsheet.connect`).  Shared helpers live in
:mod:`py2aspen.simulation._common`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from typing import Any, Generic, TypeVar, cast, get_type_hints

from comtypes import COMError

from py2aspen.aspen_type import CompositionBasis, FlashType, FlowBasis, HAPAttributeType, IHNode
from py2aspen.log import logger

from ._common import Units, _resolve_name

StreamInputT = TypeVar("StreamInputT", bound="StreamInput")


__all__ = [
    "HeatStream",
    "MaterialStream",
    "MaterialStreamInput",
    "PowerStream",
    "Stream",
    "StreamInput",
    "WorkStream",
]


@dataclass
class StreamInput:
    """Base class for stream input parameter dataclasses.

    Each subclass (e.g. :class:`MaterialStreamInput`) declares the parameters
    its stream supports.  Each field carries its Aspen node name as the
    ``"alias"`` metadata, and an optional ``"sub"`` metadata names a child
    node (e.g. ``MIXED``).
    """

    units: Units | None = field(default=None)


class Stream(ABC, Generic[StreamInputT]):
    """Base class for material, heat, or work streams.

    Subclasses must implement :meth:`get_type` and :meth:`set_input`.  The
    ``name`` is optional and defaults to the uppercased variable the object
    is assigned to.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = _resolve_name(name)
        self._node: IHNode | None = None  # injected by flowsheet.place/bind at exec time

    @abstractmethod
    def get_type(self) -> str:
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

    def get_type(self) -> str:
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

    def get_type(self) -> str:
        return "HEAT"

    def set_input(self, inputs: StreamInput) -> None:
        """HeatStream has no configurable inputs."""
        raise NotImplementedError("HeatStream has no inputs to set")

    def get_input(self) -> StreamInput:
        """HeatStream has no configurable inputs."""
        raise NotImplementedError("HeatStream has no inputs to get")


class WorkStream(Stream[StreamInput]):
    """Work stream (empty Aspen type string)."""

    def get_type(self) -> str:
        return "WORK"

    def set_input(self, inputs: StreamInput) -> None:
        """WorkStream has no configurable inputs."""
        raise NotImplementedError("WorkStream has no inputs to set")

    def get_input(self) -> StreamInput:
        """WorkStream has no configurable inputs."""
        raise NotImplementedError("WorkStream has no inputs to get")


class PowerStream(Stream[StreamInput]):
    """power stream."""

    def get_type(self) -> str:
        return "POWER"

    def set_input(self, inputs: StreamInput) -> None:
        """PowerStream has no configurable inputs."""
        raise NotImplementedError("PowerStream has no inputs to set")

    def get_input(self) -> StreamInput:
        """PowerStream has no configurable inputs."""
        raise NotImplementedError("PowerStream has no inputs to get")
