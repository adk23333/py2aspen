"""Block and Stream object definitions for Aspen Plus simulations.

References BlockPlace / BlockDelete / StreamPlace / StreamDelete /
StreamConnect / StreamDisconnect in CodeLibrary.py.

``Block`` and ``Stream`` are abstract base classes; use their concrete
subclasses (e.g. :class:`RCSTR`, :class:`Radfrac`, :class:`MaterialStream`,
:class:`HeatStream`), which implement :meth:`Block.get_type` /
:meth:`Stream.get_type`.  The ``name`` argument is optional --- when
omitted it defaults to the uppercased name of the variable the object is
assigned to.

Placement and connection on the flowsheet are handled by the operations in
:mod:`py2aspen.flowsheet` (e.g. :func:`py2aspen.flowsheet.place`,
:func:`py2aspen.flowsheet.connect`).

Implementation is split into :mod:`py2aspen.simulation.block` and
:mod:`py2aspen.simulation.stream`; this package re-exports their public
names.
"""

from . import block, stream
from .block import *
from .stream import *

__all__ = block.__all__ + stream.__all__
