"""Shared helpers for the simulation package (block.py / stream.py)."""

from __future__ import annotations

import dis
import sys
from dataclasses import dataclass


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
