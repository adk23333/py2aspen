"""
Requires a reachable Aspen Plus COM server.  The ProgID (CLSID) and the
target machine are read from environment variables and the module fails
with ``RuntimeError`` if they are missing:

- ``ASPEN_PROGID``: Aspen Plus CLSID, e.g. ``{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}``
- ``ASPEN_MACHINE``: remote host name/IP; omit for a local connection
- ``LOG_LEVEL``: loguru level (e.g. ``DEBUG`` / ``INFO``); default ``INFO``
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from dotenv import load_dotenv

from py2aspen import (
    BaseMethodType,
    CompositionBasis,
    Flash2,
    Flash2Input,
    FlashType,
    FlowBasis,
    MaterialStream,
    MaterialStreamInput,
    UnitAspen,
    Units,
    logger,
    place,
)
from py2aspen.log import set_level

load_dotenv(Path(__file__).resolve().parent.parent / ".env.dev")

PROGID = os.environ.get("ASPEN_PROGID")
MACHINE = os.environ.get("ASPEN_MACHINE")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

set_level(LOG_LEVEL)
logger.info("Log level set to {}", LOG_LEVEL)

assert PROGID is not None, "environment variable ASPEN_PROGID is not set; cannot connect to Aspen Plus"


@pytest.fixture
def aspen() -> Iterator[UnitAspen]:
    assert PROGID is not None  # module-level guard already raised if missing
    logger.info("Connecting to Aspen Plus (machine={}, progid={})", MACHINE, PROGID)
    aspen = UnitAspen(PROGID, machine=MACHINE)
    with aspen:
        aspen.suppress_dialogs(True)
        yield aspen
    logger.info("Closed Aspen Plus connection")


def test_flash2_example(aspen: UnitAspen) -> None:
    """Run a water/methanol flash separation end to end."""
    logger.info("Creating a blank simulation")
    aspen.create_simulation()
    aspen.set_visible(False)

    logger.info("Adding components WATER / METHANOL")
    aspen.properties.set_component("WATER")
    aspen.properties.set_component("METHANOL")

    logger.info("Setting base method to NRTL-RK")
    aspen.properties.base_method = BaseMethodType.NRTL_RK
    aspen.engine_reinit()

    logger.info("Building flowsheet: Flash2 B1 with feed S1, products VAP / LIQ")
    b1 = Flash2(name="B1")
    s1 = MaterialStream(name="S1")
    vap = MaterialStream(name="VAP")
    liq = MaterialStream(name="LIQ")
    aspen.exec(
        place(b1, s1, vap, liq)
        .connect(s1, b1.f_in)
        .connect(vap, b1.v_out)
        .connect(liq, b1.l_out)
    )

    logger.info("Setting feed stream S1 (40 C, 1 bar, 1000 kg/h)")
    s1.set_input(
        MaterialStreamInput(
            flash_type=FlashType.TP,
            temperature=40.0,
            pressure=1.0,
            total_flow_rate=1000.0,
            total_flow_basis=FlowBasis.MASS,
            composition={"WATER": 600.0, "METHANOL": 400.0},
            composition_basis=CompositionBasis.MASS_FLOW,
            units=Units(
                pressure="bar",
                temperature="C",
                total_flow_rate="kg/hr",
                composition_flow="kg/hr",
            ),
        )
    )

    logger.info("Setting Flash2 block B1 (85 C, 1 bar)")
    b1.set_input(
        Flash2Input(flash_type=FlashType.TP, temperature=85.0, pressure=1, units=Units(pressure="bar"))
    )

    logger.info("Running the simulation")
    aspen.engine_run()
    logger.success("Simulation finished")

    logger.info("Reading Flash2 B1 results in current display units")
    res = b1.get_results()
    assert res.temperature is not None
    assert res.pressure is not None
    assert res.units is not None and res.units.pressure is not None
    logger.info("B1 temperature = {} {}", res.temperature, res.units.temperature)

    logger.info("Reading Flash2 B1 pressure converted to atm")
    res_atm = b1.get_results(units=Units(pressure="atm"))
    assert res_atm.units is not None and res_atm.units.pressure == "atm"
    assert res_atm.pressure is not None
    # quantities not targeted by ``units`` stay in their current display units
    assert res_atm.temperature == pytest.approx(res.temperature)
