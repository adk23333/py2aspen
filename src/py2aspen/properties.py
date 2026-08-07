"""Component data models and management for Aspen Plus.

Reads the per-component parameter collections under
``\\Data\\Components\\Specifications\\Input`` (``ANAME`` / ``TYPE`` / ``DBNAME`` /
``CASN``).  Each collection is keyed by the component id; the element's
``Name`` is that id and its ``Value`` holds the parameter value.

Note: the collection names above were verified against Aspen Plus V14
(``solid1.bkp``).  There is no ``NAME``/``ALIAS`` collection (those names were
used by older versions); the mappings are ``id`` = element ``Name()``,
``type`` = ``TYPE`` (e.g. ``CONV``/``NC``), ``name`` = ``DBNAME`` (databank
name), ``alias`` = ``ANAME``, ``cas`` = ``CASN``.  A component may exist in a
collection yet have no value (e.g. ``COAL``): its ``Value()`` returns ``None``
rather than raising, so ``None`` is preserved and never stringified to
``"None"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from comtypes import COMError

from py2aspen.aspen_type import IHNode


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


class ComponentManager:
    """Manages the components under an Aspen Plus components node.

    The node passed to :meth:`__init__` should be
    ``app.Tree.Elements("Data").Elements("Components")``; the manager then
    descends to the ``Specifications\\Input`` collections ``ANAME``/``TYPE``/
    ``DBNAME``/``CASN``.
    """

    def __init__(self, components_node: IHNode) -> None:
        self._node = components_node.Elements("Specifications").Elements("Input")

    def _value(self, collection: str, comp_id: str) -> str | None:
        """Return the value of *collection* for *comp_id*, or ``None`` if absent."""
        coll_node = self._node.Elements(collection)
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
        name_elements = self._node.Elements("ANAME").Elements
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
