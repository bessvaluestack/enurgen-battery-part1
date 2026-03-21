"""
BESS Engine — PySAM BatteryStateful wrapper for DUET digital twin.

Task 2A of the Valuestack / Enurgen BESS PoC.

This package provides a forward-simulation engine for battery energy storage
systems.  Given a dispatch schedule (power vs. time), it steps through a
PySAM BatteryStateful model and logs every intermediate quantity needed for
model-vs-actual comparison and downstream degradation analysis (Task 2B).

Quick start
-----------
>>> from bess_engine import BESSConfig, load_dispatch, BESSEngine
>>> cfg = BESSConfig.from_defaults("NMC")
>>> dispatch = load_dispatch("dispatch.csv")
>>> engine = BESSEngine(cfg)
>>> results = engine.run(dispatch)
>>> results.to_dataframe().to_csv("sim_output.csv")
"""

from bess_engine.config import (
    CellChemistry,
    CellParams,
    PackParams,
    InverterParams,
    ThermalParams,
    ConstraintParams,
    BESSConfig,
)
from bess_engine.dispatch import DispatchSchedule, load_dispatch
from bess_engine.engine import BESSEngine
from bess_engine.results import TimestepRecord, SimulationResults

__all__ = [
    "CellChemistry",
    "CellParams",
    "PackParams",
    "InverterParams",
    "ThermalParams",
    "ConstraintParams",
    "BESSConfig",
    "DispatchSchedule",
    "load_dispatch",
    "BESSEngine",
    "TimestepRecord",
    "SimulationResults",
]

__version__ = "0.1.0"
