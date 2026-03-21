"""
Simulation results — structured output from the BESS engine.

Design principle (from CLAUDE.md):
    **Log everything the future needs.**  The simulation engine logs all
    intermediate quantities at every timestep — per-mechanism degradation
    increments, constraint violations, thermal headroom, full degradation
    state vector.  Storage is cheap; reconstructing state from sparse logs
    is not.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, Sequence

import numpy as np
import pandas as pd


@dataclass
class TimestepRecord:
    """
    Complete state snapshot at one simulation timestep.

    Every field is logged for every timestep — no sparsity, no sampling.
    This enables downstream model-vs-actual comparison at full resolution.
    """

    # --- Time & dispatch --------------------------------------------------
    timestamp: np.datetime64
    """Timestamp of this step."""

    step_index: int
    """Zero-based step index within the simulation."""

    power_commanded_kw: float
    """Power from the dispatch schedule (kW).  Neg=charge, pos=discharge."""

    power_actual_kw: float
    """Power actually executed after constraint enforcement (kW).
    May differ from commanded if SOC/thermal/C-rate limits were hit."""

    # --- Electrical state -------------------------------------------------
    soc_pct: float
    """State of charge at end of this step (%)."""

    voltage_v: float
    """Terminal voltage at end of this step (V), pack-level."""

    current_a: float
    """Battery current during this step (A).  Negative=charge, positive=discharge."""

    # --- Thermal state ----------------------------------------------------
    temperature_c: float
    """Battery temperature at end of this step (°C)."""

    heat_generated_w: float
    """Heat generated during this step (W) = I² × R."""

    # --- Energy accounting ------------------------------------------------
    energy_charged_kwh: float
    """Energy charged during this step (kWh, unsigned).  Zero if discharging."""

    energy_discharged_kwh: float
    """Energy discharged during this step (kWh, unsigned).  Zero if charging."""

    # --- Constraint enforcement -------------------------------------------
    power_clipped: bool = False
    """True if the commanded power was clipped by any constraint."""

    clip_reason: str = ""
    """Human-readable reason for clipping, if any.
    Possible values: 'soc_min', 'soc_max', 'c_rate', 'temperature',
    'inverter_limit', 'voltage_limit', or comma-separated combinations."""

    # --- Degradation hook (populated by Task 2B) --------------------------
    soh_capacity_pct: float = 100.0
    """State of health — remaining capacity as % of nameplate.
    Updated by the degradation model (Task 2B).  Defaults to 100 % when
    no degradation model is active."""

    soh_resistance_pct: float = 100.0
    """State of health — resistance as % of BOL resistance.
    100 % means no change from BOL.  >100 % means resistance has grown."""

    # --- Extra fields for extensibility -----------------------------------
    extras: dict = field(default_factory=dict)
    """Arbitrary key-value pairs for future extensions.
    Task 2B will populate degradation mechanism breakdowns here:
        extras = {
            "q_li_ah": ...,
            "q_neg_ah": ...,
            "q_pos_ah": ...,
            "r_internal_ohm": ...,
            "degradation_limiting_mechanism": "lithium_loss",
        }
    """


@dataclass
class SimulationResults:
    """
    Complete simulation output — all timestep records plus aggregate KPIs.

    Usage
    -----
    >>> results = engine.run(dispatch)
    >>> df = results.to_dataframe()
    >>> print(results.kpis)
    """

    records: list[TimestepRecord] = field(default_factory=list)
    """Ordered list of per-timestep records."""

    config_snapshot: Optional[dict] = None
    """Serialised BESSConfig used for this simulation (for reproducibility)."""

    def __len__(self) -> int:
        return len(self.records)

    def append(self, record: TimestepRecord) -> None:
        """Append a timestep record."""
        self.records.append(record)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert all timestep records to a pandas DataFrame.

        The ``extras`` dict is flattened: each key becomes a column
        prefixed with ``x_`` (e.g., ``extras["q_li_ah"]`` → column ``x_q_li_ah``).
        """
        rows = []
        for rec in self.records:
            row = {
                "timestamp": rec.timestamp,
                "step_index": rec.step_index,
                "power_commanded_kw": rec.power_commanded_kw,
                "power_actual_kw": rec.power_actual_kw,
                "soc_pct": rec.soc_pct,
                "voltage_v": rec.voltage_v,
                "current_a": rec.current_a,
                "temperature_c": rec.temperature_c,
                "heat_generated_w": rec.heat_generated_w,
                "energy_charged_kwh": rec.energy_charged_kwh,
                "energy_discharged_kwh": rec.energy_discharged_kwh,
                "power_clipped": rec.power_clipped,
                "clip_reason": rec.clip_reason,
                "soh_capacity_pct": rec.soh_capacity_pct,
                "soh_resistance_pct": rec.soh_resistance_pct,
            }
            # Flatten extras with prefix
            for k, v in rec.extras.items():
                row[f"x_{k}"] = v
            rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.set_index("timestamp")
        return df

    # --- Aggregate KPIs ---------------------------------------------------

    @property
    def kpis(self) -> dict:
        """
        Compute aggregate Key Performance Indicators for the simulation.

        Returns a dict with operational KPIs.  Financial KPIs are out of
        scope (Task 4).

        KPI definitions follow the landscape survey and I/O spec.
        """
        if not self.records:
            return {}

        df = self.to_dataframe()

        total_charged = float(df["energy_charged_kwh"].sum())
        total_discharged = float(df["energy_discharged_kwh"].sum())

        # Extract columns used by multiple KPIs
        soc = df["soc_pct"]
        temps = df["temperature_c"]

        # Round-trip efficiency — SOC-corrected.
        #
        # AC-side energy alone can't capture RTE for balanced dispatches
        # (same power in both directions gives E_in = E_out = 100 % by
        # construction).  The real losses show up as SOC drift: the
        # battery doesn't return to its starting SOC after a full cycle.
        #
        # Formula:
        #   RTE = E_discharged_AC / (E_charged_AC + E_soc_deficit)
        #
        # where E_soc_deficit = (initial_SOC − final_SOC) / 100 × capacity_kWh
        # is the net energy the battery contributed from its initial reserves.
        #
        # For complete cycles (SOC returns to start): E_soc_deficit ≈ 0
        #   → RTE = E_out / E_in (standard formula, < 100 % due to losses)
        # For balanced AC dispatch: E_out = E_in, E_soc_deficit > 0
        #   → RTE = E_out / (E_out + losses) < 100 %
        initial_soc_pct = (
            self.config_snapshot.get("initial_soc_pct", 50.0)
            if self.config_snapshot
            else 50.0
        )
        final_soc_pct = float(soc.iloc[-1])
        nameplate_kwh = (
            self.config_snapshot["cell"]["nominal_capacity_ah"]
            * self.config_snapshot["cell"]["nominal_voltage"]
            * self.config_snapshot["pack"]["cells_in_series"]
            * self.config_snapshot["pack"]["strings_in_parallel"]
            / 1000.0
            if self.config_snapshot
            else 0.0
        )
        soc_deficit_kwh = (initial_soc_pct - final_soc_pct) / 100.0 * nameplate_kwh
        rte_denominator = total_charged + soc_deficit_kwh

        rte = (
            (total_discharged / rte_denominator * 100.0)
            if rte_denominator > 0
            else 0.0
        )

        # Constraint violations
        n_clipped = int(df["power_clipped"].sum())
        clip_fraction = n_clipped / len(df) * 100.0 if len(df) > 0 else 0.0

        # SOH at end of simulation
        final_soh_cap = float(df["soh_capacity_pct"].iloc[-1])
        final_soh_res = float(df["soh_resistance_pct"].iloc[-1])

        return {
            "total_energy_charged_kwh": round(total_charged, 2),
            "total_energy_discharged_kwh": round(total_discharged, 2),
            "round_trip_efficiency_pct": round(rte, 2),
            "n_timesteps": len(df),
            "n_clipped_timesteps": n_clipped,
            "clip_fraction_pct": round(clip_fraction, 2),
            "soc_min_pct": round(float(soc.min()), 2),
            "soc_max_pct": round(float(soc.max()), 2),
            "soc_mean_pct": round(float(soc.mean()), 2),
            "temperature_min_c": round(float(temps.min()), 2),
            "temperature_max_c": round(float(temps.max()), 2),
            "temperature_mean_c": round(float(temps.mean()), 2),
            "final_soh_capacity_pct": round(final_soh_cap, 2),
            "final_soh_resistance_pct": round(final_soh_res, 2),
        }

    def summary(self) -> str:
        """Human-readable simulation summary."""
        k = self.kpis
        if not k:
            return "SimulationResults: empty (no timesteps recorded)"
        return (
            f"SimulationResults: {k['n_timesteps']} timesteps\n"
            f"  Energy charged:     {k['total_energy_charged_kwh']:.1f} kWh\n"
            f"  Energy discharged:  {k['total_energy_discharged_kwh']:.1f} kWh\n"
            f"  Round-trip eff.:    {k['round_trip_efficiency_pct']:.1f} %\n"
            f"  SOC range:          [{k['soc_min_pct']:.1f}, {k['soc_max_pct']:.1f}] %\n"
            f"  Temperature range:  [{k['temperature_min_c']:.1f}, "
            f"{k['temperature_max_c']:.1f}] °C\n"
            f"  Clipped timesteps:  {k['n_clipped_timesteps']} "
            f"({k['clip_fraction_pct']:.1f} %)\n"
            f"  Final SOH (cap):    {k['final_soh_capacity_pct']:.1f} %\n"
            f"  Final SOH (res):    {k['final_soh_resistance_pct']:.1f} %"
        )
