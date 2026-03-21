"""
Passthrough (no-op) degradation model.

This model applies no degradation — capacity stays at 100 % and resistance
stays at BOL.  It exists so that Task 2A's engine can be tested with a
degradation model attached (verifying the interface contract) without
requiring the full NREL Smith 2017 implementation from Task 2B.

It also serves as a minimal reference implementation for anyone building
a new degradation model — just subclass or duck-type this pattern.
"""

from __future__ import annotations

from dataclasses import dataclass

# Import from the engine module to keep the protocol definition in one place.
# Circular import is avoided because this module is not imported by engine.py
# at module level — it's only used by callers who explicitly attach it.
from bess_engine.engine import DegradationState


class PassthroughDegradation:
    """
    No-op degradation model — always returns 100 % SOH.

    Conforms to ``DegradationModelProtocol`` (duck typing).

    Usage
    -----
    >>> from degradation import PassthroughDegradation
    >>> from bess_engine import BESSEngine, BESSConfig
    >>> engine = BESSEngine(BESSConfig.from_defaults("NMC"),
    ...                     degradation_model=PassthroughDegradation())
    """

    def __init__(self):
        self._state = DegradationState(
            capacity_fraction=1.0,
            resistance_fraction=1.0,
        )
        self._total_ah = 0.0
        self._total_time_s = 0.0

    def update(
        self,
        dt_s: float,
        soc_pct: float,
        temperature_c: float,
        current_a: float,
        voltage_v: float,
        dod_pct: float,
    ) -> DegradationState:
        """
        Advance degradation by one step (no-op — state unchanged).

        Still tracks cumulative Ah throughput and time for diagnostic use.
        """
        self._total_ah += abs(current_a) * dt_s / 3600.0
        self._total_time_s += dt_s
        return self._state

    def get_state(self) -> DegradationState:
        """Return current degradation state (always 100 % healthy)."""
        return self._state

    def get_mechanism_breakdown(self) -> dict:
        """
        Return per-mechanism state for logging.

        Even the passthrough model logs cumulative throughput — useful for
        verifying that the engine is passing data through correctly.
        """
        return {
            "degradation_model": "passthrough",
            "total_ah_throughput": round(self._total_ah, 2),
            "total_time_hours": round(self._total_time_s / 3600.0, 2),
            "capacity_fraction": self._state.capacity_fraction,
            "resistance_fraction": self._state.resistance_fraction,
        }
