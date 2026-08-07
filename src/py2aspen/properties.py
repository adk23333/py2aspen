"""Property data models and management for Aspen Plus.

Reads the per-component parameter collections under
``\\Data\\Components\\Specifications\\Input`` (``ANAME`` / ``TYPE`` / ``DBNAME`` /
``CASN``).  Each collection is keyed by the component id; the element's
``Name`` is that id and its ``Value`` holds the parameter value.

Note: the collection names above were verified against Aspen Plus V14
(``solid1.bkp``).  There is no ``NAME``/``ALIAS`` collection (those names were
used by older versions); the mappings are ``id`` = element ``Name()``,
``type`` = ``TYPE`` (e.g. ``CONV``/``NC``), ``name`` = ``DBNAME`` (databank
name), ``alias`` = ``ANAME``, ``cas`` = ``CASN``.  A property may exist in a
collection yet have no value (e.g. ``COAL``): its ``Value()`` returns ``None``
rather than raising, so ``None`` is preserved and never stringified to
``"None"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from comtypes import COMError

from py2aspen.aspen_type import IHNode


class BaseMethodType(StrEnum):
    """Aspen Plus global base property methods (``GBASEOPSET`` values)."""

    BK10 = "BK10"
    CHAO_SEA = "CHAO-SEA"
    CPA = "CPA"
    ELECNRTL = "ELECNRTL"
    ENRTL_RK = "ENRTL-RK"
    ENRTL_SR = "ENRTL-SR"
    IAPWS_95 = "IAPWS-95"
    IDEAL = "IDEAL"
    NRTL = "NRTL"
    NRTL_SAC = "NRTL-SAC"
    PC_SAFT = "PC-SAFT"
    PENG_ROB = "PENG-ROB"
    POLYNRTL = "POLYNRTL"
    PSRK = "PSRK"
    SOLIDS = "SOLIDS"
    SRK = "SRK"
    UNIFAC = "UNIFAC"
    UNIQUAC = "UNIQUAC"
    VTPR = "VTPR"
    WILSON = "WILSON"
    WILS_GLR = "WILS-GLR"
    IF97 = "IF97"
    PITZER = "PITZER"


@dataclass
class Component:
    """A component record read from Aspen Plus.

    Attributes:
        id: Component identifier (always present).
        type: Component type, e.g. ``CONV`` or ``NC``.
        name: Component name (databank name).
        alias: Component alias (attribute name).
        cas: CAS registry number.
    """

    id: str
    type: str | None = None
    name: str | None = None
    alias: str | None = None
    cas: str | None = None


class PropertiesManager:
    """Manages the properties under an Aspen Plus Data node.

    The node passed to :meth:`__init__` should be ``app.Tree.Elements("Data")``.
    ``components_node`` descends to ``Components\\Specifications\\Input``
    (``ANAME``/``TYPE``/``DBNAME``/``CASN``); ``properties_node`` descends to
    ``Properties\\Specifications\\Input`` (e.g. ``GBASEOPSET``).
    """

    def __init__(self, data_node: IHNode) -> None:
        self.components_node = data_node.Elements("Components").Elements("Specifications").Elements("Input")
        self.properties_node = data_node.Elements("Properties").Elements("Specifications").Elements("Input")

    def _value(self, collection: str, comp_id: str) -> str | None:
        """Return the value of *collection* for *comp_id*, or ``None`` if absent."""
        coll_node = self.components_node.Elements(collection)
        if coll_node is None:
            return None
        node = coll_node.Elements(comp_id)
        if node is None:
            return None
        try:
            value = node.Value()
        except COMError:
            return None
        return str(value) if value is not None else None

    def get_all_components(
        self,
        *,
        type: bool = True,
        name: bool = True,
        alias: bool = True,
        cas: bool = True,
    ) -> list[Component]:
        """Return all components.

        The ``id`` is always read (it cannot be empty); the other attributes
        are fetched according to the flags, which default to ``True`` and stay
        ``None`` when a flag is disabled or the value is absent.
        """
        components: list[Component] = []
        name_elements = self.components_node.Elements("ANAME").Elements
        for elem in name_elements:
            comp_id = str(cast(IHNode, elem).Name())
            comp = Component(id=comp_id)
            if type:
                comp.type = self._value("TYPE", comp_id)
            if name:
                comp.name = self._value("DBNAME", comp_id)
            if alias:
                comp.alias = self._value("ANAME", comp_id)
            if cas:
                comp.cas = self._value("CASN", comp_id)
            components.append(comp)
        return components

    @property
    def base_method(self) -> BaseMethodType | None:
        """Global base property method (``GBASEOPSET``)."""
        node = self.properties_node.Elements("GBASEOPSET")
        if node is None:
            return None
        try:
            value = node.Value()
        except COMError:
            return None
        if value is None:
            return None
        try:
            return BaseMethodType(str(value))
        except ValueError:
            return None

    @base_method.setter
    def base_method(self, method: BaseMethodType) -> None:
        """Set the global base property method.

        Suppress dialogs before calling and run the engine afterwards to
        refresh binary interaction parameters (BIPs).
        """
        node = self.properties_node.Elements("GBASEOPSET")
        # Value 是带索引属性（PROPERTYPUT cParams=2），须经 __setitem__ 写入
        cast(Any, node.Value)[0] = method.value
