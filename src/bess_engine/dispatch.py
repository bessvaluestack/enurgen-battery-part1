"""
Dispatch schedule loading and validation.

The dispatch schedule is the primary input to the BESS simulation engine.
It is a time series of power commands (kW) at the simulation timestep
resolution.

Convention (matching CLAUDE.md):
    - **Negative values = charging** (power flowing into the battery)
    - **Positive values = discharging** (power flowing out of the battery)

Expected CSV format::

    Date/Time,pwr_kw
    01/01 00:01:00,-7065.755
    01/01 00:02:00,-7038.300
    ...

The ``Date/Time`` column is parsed flexibly.  If no year is present, the
current year is assumed.  Timezone-naive timestamps are kept as-is.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


@dataclass
class DispatchSchedule:
    """
    Validated dispatch schedule ready for simulation.

    Attributes
    ----------
    timestamps : np.ndarray
        Array of datetime64 timestamps, one per command.
    power_kw : np.ndarray
        Power commands in kW.  Negative = charge, positive = discharge.
    timestep_s : int
        Uniform timestep duration in seconds (derived from timestamps).
    """

    timestamps: np.ndarray
    power_kw: np.ndarray
    timestep_s: int

    def __len__(self) -> int:
        return len(self.power_kw)

    @property
    def duration_hours(self) -> float:
        """Total schedule duration in hours."""
        return len(self) * self.timestep_s / 3600.0

    @property
    def total_charge_energy_kwh(self) -> float:
        """Total energy commanded for charging (kWh), unsigned."""
        charging = self.power_kw[self.power_kw < 0]
        return float(np.abs(charging).sum() * self.timestep_s / 3600.0)

    @property
    def total_discharge_energy_kwh(self) -> float:
        """Total energy commanded for discharging (kWh), unsigned."""
        discharging = self.power_kw[self.power_kw > 0]
        return float(discharging.sum() * self.timestep_s / 3600.0)

    def summary(self) -> str:
        """Human-readable summary of the dispatch schedule."""
        n_charge = int((self.power_kw < 0).sum())
        n_discharge = int((self.power_kw > 0).sum())
        n_idle = int((self.power_kw == 0).sum())
        return (
            f"DispatchSchedule: {len(self)} timesteps "
            f"({self.duration_hours:.1f} h) @ {self.timestep_s}s resolution\n"
            f"  Charging steps:    {n_charge} "
            f"({self.total_charge_energy_kwh:.1f} kWh commanded)\n"
            f"  Discharging steps: {n_discharge} "
            f"({self.total_discharge_energy_kwh:.1f} kWh commanded)\n"
            f"  Idle steps:        {n_idle}\n"
            f"  Power range:       [{self.power_kw.min():.1f}, "
            f"{self.power_kw.max():.1f}] kW"
        )


def load_dispatch(
    source: str | Path | pd.DataFrame,
    *,
    time_col: str = "Date/Time",
    power_col: str = "pwr_kw",
    expected_timestep_s: Optional[int] = 60,
) -> DispatchSchedule:
    """
    Load and validate a dispatch schedule from CSV or DataFrame.

    Parameters
    ----------
    source : str, Path, or pd.DataFrame
        Path to a CSV file, or an already-loaded DataFrame.
    time_col : str
        Name of the timestamp column.
    power_col : str
        Name of the power column (kW).
    expected_timestep_s : int or None
        If provided, validates that the schedule has uniform timesteps
        at this resolution.  Set to None to auto-detect.

    Returns
    -------
    DispatchSchedule
        Validated schedule ready for simulation.

    Raises
    ------
    FileNotFoundError
        If CSV path does not exist.
    ValueError
        If required columns are missing, timestamps are non-uniform,
        or data contains NaN values.
    """
    # --- Load data --------------------------------------------------------
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Dispatch file not found: {path}")
        df = pd.read_csv(path)
    elif isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        raise TypeError(
            f"Expected str, Path, or DataFrame, got {type(source).__name__}"
        )

    # --- Validate columns -------------------------------------------------
    if time_col not in df.columns:
        raise ValueError(
            f"Time column '{time_col}' not found. "
            f"Available columns: {list(df.columns)}"
        )
    if power_col not in df.columns:
        raise ValueError(
            f"Power column '{power_col}' not found. "
            f"Available columns: {list(df.columns)}"
        )

    # --- Parse timestamps -------------------------------------------------
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(time_col).reset_index(drop=True)

    timestamps = df[time_col].values  # numpy datetime64 array

    # --- Validate uniform timestep ----------------------------------------
    if len(timestamps) < 2:
        raise ValueError("Dispatch schedule must have at least 2 timesteps.")

    diffs = np.diff(timestamps).astype("timedelta64[s]").astype(float)
    median_dt = float(np.median(diffs))

    if expected_timestep_s is not None:
        # Check against expected
        tolerance = expected_timestep_s * 0.01  # 1 % tolerance
        if abs(median_dt - expected_timestep_s) > tolerance:
            raise ValueError(
                f"Expected timestep of {expected_timestep_s}s but median "
                f"interval is {median_dt:.1f}s."
            )
        actual_timestep_s = expected_timestep_s
    else:
        actual_timestep_s = int(round(median_dt))

    # Warn about non-uniform intervals (but allow minor jitter)
    max_deviation = float(np.max(np.abs(diffs - actual_timestep_s)))
    if max_deviation > actual_timestep_s * 0.05:
        warnings.warn(
            f"Non-uniform timesteps detected: max deviation "
            f"{max_deviation:.1f}s from {actual_timestep_s}s. "
            f"Results may be inaccurate for non-uniform schedules.",
            UserWarning,
            stacklevel=2,
        )

    # --- Validate power data ----------------------------------------------
    power_kw = df[power_col].values.astype(np.float64)

    if np.any(np.isnan(power_kw)):
        n_nan = int(np.isnan(power_kw).sum())
        raise ValueError(
            f"Power column contains {n_nan} NaN values. "
            f"Fill or remove missing data before simulation."
        )

    return DispatchSchedule(
        timestamps=timestamps,
        power_kw=power_kw,
        timestep_s=actual_timestep_s,
    )


def make_constant_dispatch(
    power_kw: float,
    duration_hours: float,
    timestep_s: int = 60,
    start: str = "2025-01-01 00:00:00",
) -> DispatchSchedule:
    """
    Generate a constant-power dispatch schedule (useful for testing).

    Parameters
    ----------
    power_kw : float
        Constant power command.  Negative = charge, positive = discharge.
    duration_hours : float
        Total duration in hours.
    timestep_s : int
        Timestep in seconds.
    start : str
        Start timestamp (ISO format string).

    Returns
    -------
    DispatchSchedule
    """
    n_steps = int(duration_hours * 3600 / timestep_s)
    timestamps = pd.date_range(start, periods=n_steps, freq=f"{timestep_s}s")
    power = np.full(n_steps, power_kw, dtype=np.float64)
    return DispatchSchedule(
        timestamps=timestamps.values,
        power_kw=power,
        timestep_s=timestep_s,
    )


def make_cycling_dispatch(
    charge_power_kw: float,
    discharge_power_kw: float,
    charge_hours: float,
    discharge_hours: float,
    n_cycles: int,
    timestep_s: int = 60,
    rest_hours: float = 0.0,
    start: str = "2025-01-01 00:00:00",
) -> DispatchSchedule:
    """
    Generate a repeating charge/discharge cycling schedule (for testing).

    Parameters
    ----------
    charge_power_kw : float
        Charging power (will be made negative if positive is passed).
    discharge_power_kw : float
        Discharging power (will be made positive if negative is passed).
    charge_hours : float
        Duration of each charge phase.
    discharge_hours : float
        Duration of each discharge phase.
    n_cycles : int
        Number of full charge/discharge cycles.
    timestep_s : int
        Timestep resolution in seconds.
    rest_hours : float
        Optional rest period between charge and discharge phases.
    start : str
        Start timestamp.

    Returns
    -------
    DispatchSchedule
    """
    charge_power_kw = -abs(charge_power_kw)
    discharge_power_kw = abs(discharge_power_kw)

    steps_charge = int(charge_hours * 3600 / timestep_s)
    steps_discharge = int(discharge_hours * 3600 / timestep_s)
    steps_rest = int(rest_hours * 3600 / timestep_s)

    # Build one cycle: charge → rest → discharge → rest
    cycle = np.concatenate([
        np.full(steps_charge, charge_power_kw),
        np.full(steps_rest, 0.0),
        np.full(steps_discharge, discharge_power_kw),
        np.full(steps_rest, 0.0),
    ])

    power = np.tile(cycle, n_cycles)
    n_steps = len(power)
    timestamps = pd.date_range(start, periods=n_steps, freq=f"{timestep_s}s")

    return DispatchSchedule(
        timestamps=timestamps.values,
        power_kw=power,
        timestep_s=timestep_s,
    )
