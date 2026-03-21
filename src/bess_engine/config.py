"""
Configuration dataclasses for the BESS simulation engine.

Design principles (from CLAUDE.md):
- **Datasheet-parameterizable by default.**  Every field should be derivable
  from a standard manufacturer datasheet and system configuration spec.
- **Chemistry-pluggable, not chemistry-locked.**  Changing chemistry changes
  parameter values via ``CellChemistry``, never model code.

The top-level ``BESSConfig`` aggregates all sub-configs and provides a
``from_defaults(chemistry)`` factory that populates typical datasheet values
for common chemistries (NMC, LFP, LTO).  Users override individual fields
as needed.

Hierarchy mapping (per solar_plant_hierarchy_annotated.md, adapted for BESS):
    Cell → Module → Rack (≈ String) → Container/Block → System
PySAM BatteryStateful models at the *cell* level and scales via series/parallel
counts.  This config mirrors that approach.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Chemistry enumeration
# ---------------------------------------------------------------------------

class CellChemistry(Enum):
    """
    Supported cell chemistry identifiers.

    Each chemistry maps to a default parameter set.  SAM's
    BatteryStateful uses integer codes internally:
        0 = Lead-acid (not supported here)
        1 = Li-ion NMC / graphite
        2 = Li-ion Vanadium redox flow (not supported)
        3 = Li-ion Iron flow (not supported)
    The mapping to PySAM's ``chem`` parameter is handled in ``BESSConfig``.
    """
    NMC = "NMC"      # Nickel Manganese Cobalt / graphite
    LFP = "LFP"      # Lithium Iron Phosphate / graphite
    LTO = "LTO"      # Lithium Titanate (anode) — typically paired with NMC/LMO cathode
    NCA = "NCA"      # Nickel Cobalt Aluminum / graphite


# ---------------------------------------------------------------------------
# Cell-level parameters (from datasheet voltage-discharge curve)
# ---------------------------------------------------------------------------

@dataclass
class CellParams:
    """
    Single-cell electrochemical parameters.

    These are extracted from the manufacturer's voltage-vs-discharge curve at
    a known C-rate, following the Tremblay-Dessaint model used by PySAM
    (see NREL 64641 §Voltage Model).

    All voltages in V, capacities in Ah, resistance in Ohm.
    """

    chemistry: CellChemistry = CellChemistry.NMC

    # --- Capacity ---
    nominal_capacity_ah: float = 75.0
    """Nameplate cell capacity at reference C-rate (Ah)."""

    nominal_voltage: float = 3.6
    """Nominal cell voltage (V). Used for energy calculations."""

    # --- Voltage curve data points (Tremblay-Dessaint model inputs) ---
    # These come directly from the datasheet discharge curve.
    voltage_full: float = 4.2
    """Fully-charged open-circuit voltage (V)."""

    voltage_exp: float = 4.05
    """Voltage at end of exponential zone (V)."""

    voltage_nom: float = 3.4
    """Voltage at end of nominal zone (V), just before steep drop-off."""

    capacity_exp_pct: float = 8.0
    """Percent of capacity removed at end of exponential zone (%)."""

    capacity_nom_pct: float = 97.0
    """Percent of capacity removed at end of nominal zone (%)."""

    # --- Internal resistance ---
    internal_resistance_ohm: float = 0.001
    """Cell internal resistance at ~50 % SOC and reference temperature (Ω).
    This is the DC resistance from the datasheet or HPPC pulse test."""

    # --- C-rate limits ---
    max_charge_rate: float = 1.0
    """Maximum continuous charge C-rate (e.g. 1.0 = 1C)."""

    max_discharge_rate: float = 1.0
    """Maximum continuous discharge C-rate (e.g. 1.0 = 1C)."""


# ---------------------------------------------------------------------------
# Pack / bank configuration
# ---------------------------------------------------------------------------

@dataclass
class PackParams:
    """
    Battery pack / bank topology.

    Defines how cells are arranged into series strings and parallel groups
    to reach the desired system voltage and capacity.  PySAM BatteryStateful
    scales the single-cell model by these counts.
    """

    cells_in_series: int = 200
    """Number of cells connected in series (determines pack voltage).
    Example: 200 × 3.6 V = 720 V nominal."""

    strings_in_parallel: int = 100
    """Number of parallel strings (determines pack capacity).
    Example: 100 × 75 Ah × 3.6 V = 27 MWh at cell level."""

    # Derived convenience properties ----------------------------------------

    @property
    def nominal_voltage_v(self) -> float:
        """Pack-level nominal voltage (V).  Requires cell params at usage site."""
        # NOTE: actual voltage depends on CellParams; this is a topology-only class.
        # Caller should compute: cells_in_series * cell.nominal_voltage
        raise NotImplementedError(
            "Use cells_in_series * cell.nominal_voltage directly."
        )


# ---------------------------------------------------------------------------
# Inverter / power conversion
# ---------------------------------------------------------------------------

@dataclass
class InverterParams:
    """
    Bidirectional inverter / power conversion system (PCS) parameters.

    SAM models conversion losses as single-point efficiencies for AC↔DC.
    For higher fidelity, replace with an efficiency curve f(load_fraction).
    """

    ac_dc_efficiency: float = 0.96
    """AC-to-DC conversion efficiency during charging (0–1)."""

    dc_ac_efficiency: float = 0.96
    """DC-to-AC conversion efficiency during discharging (0–1)."""

    max_power_kw: float = 10_000.0
    """Maximum rated AC power of the PCS (kW).
    Dispatch commands exceeding this will be clipped."""


# ---------------------------------------------------------------------------
# Thermal model parameters
# ---------------------------------------------------------------------------

@dataclass
class ThermalParams:
    """
    Lumped-parameter thermal model inputs (per NREL 64641 §Thermal Model).

    PySAM BatteryStateful uses a single-mass energy balance:
        m·Cp·dT/dt = h·A·(T_room − T_batt) + I²·R

    Thermal management is represented by a fixed room temperature.
    For systems with active HVAC, set ``room_temperature_c`` to the
    setpoint of the cooling/heating system.
    """

    mass_kg: float = 30_000.0
    """Total battery mass (kg).  Approximate from system energy and
    gravimetric energy density (e.g. ~150 Wh/kg for NMC)."""

    surface_area_m2: float = 100.0
    """Effective heat transfer surface area (m²)."""

    specific_heat_j_per_kg_k: float = 1000.0
    """Specific heat capacity of battery cells (J/(kg·K)).
    Typical Li-ion: 800–1100 J/(kg·K)."""

    heat_transfer_coeff_w_per_m2_k: float = 10.0
    """Convective heat transfer coefficient (W/(m²·K)).
    Natural convection ~5–10; forced air ~20–50; liquid ~100–500."""

    room_temperature_c: float = 25.0
    """Conditioned room / ambient temperature (°C).
    PySAM treats this as constant for the full simulation."""


# ---------------------------------------------------------------------------
# Operating constraints
# ---------------------------------------------------------------------------

@dataclass
class ConstraintParams:
    """
    Operational constraints enforced by the simulation engine.

    These map to SAM's SOC controller and current controller layers
    (NREL 64641 §Dispatch Controller).  The engine clips or rejects
    dispatch commands that would violate these limits.
    """

    soc_min_pct: float = 10.0
    """Minimum allowed state of charge (%).  Dispatch commands that would
    push SOC below this are clipped."""

    soc_max_pct: float = 90.0
    """Maximum allowed state of charge (%).  Charging commands that would
    push SOC above this are clipped."""

    # NOTE: C-rate limits also exist on CellParams (max_charge_rate,
    # max_discharge_rate).  Those are cell-level physical limits.
    # These SOC limits are operational / warranty-driven limits.

    min_temperature_c: float = 0.0
    """Minimum battery temperature for operation (°C).
    Below this, charging is blocked (lithium plating risk)."""

    max_temperature_c: float = 45.0
    """Maximum battery temperature for operation (°C).
    Above this, all operations are curtailed."""

    eol_capacity_pct: float = 80.0
    """End-of-life capacity threshold (% of nameplate).
    When SOH drops below this, the battery is considered at EOL.
    Configurable per NREL 67102 guidance (70 % or 80 % common)."""


# ---------------------------------------------------------------------------
# Top-level configuration
# ---------------------------------------------------------------------------

@dataclass
class BESSConfig:
    """
    Complete BESS configuration — aggregates all sub-configs.

    This is the single object passed to ``BESSEngine``.  It is
    JSON-serialisable via ``dataclasses.asdict`` for reproducibility.

    Usage
    -----
    >>> cfg = BESSConfig.from_defaults("NMC")
    >>> cfg.cell.nominal_capacity_ah = 100.0  # override from datasheet
    >>> cfg.pack.cells_in_series = 250
    """

    cell: CellParams = field(default_factory=CellParams)
    pack: PackParams = field(default_factory=PackParams)
    inverter: InverterParams = field(default_factory=InverterParams)
    thermal: ThermalParams = field(default_factory=ThermalParams)
    constraints: ConstraintParams = field(default_factory=ConstraintParams)

    simulation_timestep_s: int = 60
    """Simulation timestep in seconds.  Must match the dispatch schedule
    resolution.  Default 60 s = 1-minute resolution."""

    initial_soc_pct: float = 50.0
    """Initial state of charge at simulation start (%)."""

    # --- Derived / convenience -------------------------------------------

    @property
    def nameplate_energy_kwh(self) -> float:
        """System-level nameplate energy (kWh), before derating."""
        cell_energy_wh = (
            self.cell.nominal_capacity_ah * self.cell.nominal_voltage
        )
        n_cells = self.pack.cells_in_series * self.pack.strings_in_parallel
        return cell_energy_wh * n_cells / 1_000.0

    @property
    def nameplate_capacity_ah(self) -> float:
        """System-level nameplate capacity (Ah) at pack voltage."""
        return self.cell.nominal_capacity_ah * self.pack.strings_in_parallel

    @property
    def nominal_pack_voltage_v(self) -> float:
        """Nominal pack voltage (V) = cells_in_series × cell voltage."""
        return self.pack.cells_in_series * self.cell.nominal_voltage

    def to_dict(self) -> dict:
        """Serialise to a plain dict (for JSON logging / reproducibility)."""
        d = asdict(self)
        # Convert enum to string for JSON compatibility
        d["cell"]["chemistry"] = self.cell.chemistry.value
        return d

    # --- Factory methods --------------------------------------------------

    @classmethod
    def from_defaults(cls, chemistry: str | CellChemistry) -> BESSConfig:
        """
        Create a config with sensible defaults for a given chemistry.

        Parameters
        ----------
        chemistry : str or CellChemistry
            One of "NMC", "LFP", "LTO", "NCA".

        Returns
        -------
        BESSConfig
            Populated with typical datasheet values.  Override individual
            fields as needed before passing to BESSEngine.

        Notes
        -----
        Default values represent a ~27 MWh / 10 MW utility-scale system
        (200s × 100p × 75 Ah × 3.6 V nominal).  Scale pack.cells_in_series
        and pack.strings_in_parallel for your actual system size.
        """
        if isinstance(chemistry, str):
            chemistry = CellChemistry(chemistry.upper())

        cfg = cls()

        if chemistry == CellChemistry.NMC:
            cfg.cell = CellParams(
                chemistry=CellChemistry.NMC,
                nominal_capacity_ah=75.0,
                nominal_voltage=3.6,
                voltage_full=4.2,
                voltage_exp=4.05,
                voltage_nom=3.4,
                capacity_exp_pct=8.0,
                capacity_nom_pct=97.0,
                internal_resistance_ohm=0.001,
                max_charge_rate=1.0,
                max_discharge_rate=1.0,
            )
            cfg.constraints.soc_min_pct = 10.0
            cfg.constraints.soc_max_pct = 90.0

        elif chemistry == CellChemistry.LFP:
            cfg.cell = CellParams(
                chemistry=CellChemistry.LFP,
                nominal_capacity_ah=100.0,
                nominal_voltage=3.2,
                voltage_full=3.65,
                voltage_exp=3.35,
                voltage_nom=3.10,
                capacity_exp_pct=5.0,
                capacity_nom_pct=95.0,
                internal_resistance_ohm=0.0008,
                max_charge_rate=1.0,
                max_discharge_rate=1.0,
            )
            # LFP is more tolerant of wide SOC windows
            cfg.constraints.soc_min_pct = 5.0
            cfg.constraints.soc_max_pct = 95.0

        elif chemistry == CellChemistry.LTO:
            cfg.cell = CellParams(
                chemistry=CellChemistry.LTO,
                nominal_capacity_ah=40.0,
                nominal_voltage=2.3,
                voltage_full=2.8,
                voltage_exp=2.5,
                voltage_nom=2.2,
                capacity_exp_pct=10.0,
                capacity_nom_pct=90.0,
                internal_resistance_ohm=0.0005,
                max_charge_rate=5.0,   # LTO supports very high C-rates
                max_discharge_rate=5.0,
            )
            cfg.constraints.soc_min_pct = 5.0
            cfg.constraints.soc_max_pct = 95.0
            cfg.constraints.min_temperature_c = -30.0  # LTO is cold-tolerant

        elif chemistry == CellChemistry.NCA:
            cfg.cell = CellParams(
                chemistry=CellChemistry.NCA,
                nominal_capacity_ah=50.0,
                nominal_voltage=3.6,
                voltage_full=4.2,
                voltage_exp=4.0,
                voltage_nom=3.3,
                capacity_exp_pct=7.0,
                capacity_nom_pct=95.0,
                internal_resistance_ohm=0.0012,
                max_charge_rate=0.7,
                max_discharge_rate=1.0,
            )
            cfg.constraints.soc_min_pct = 15.0
            cfg.constraints.soc_max_pct = 85.0

        else:
            raise ValueError(f"Unknown chemistry: {chemistry}")

        return cfg
