"""
BESS simulation engine — PySAM BatteryStateful wrapper.

This is the core of Task 2A.  It wraps NREL's ``PySAM.BatteryStateful``
module to provide:

1. **Dispatch ingestion** — accepts a power-vs-time schedule and feeds it
   to the battery model one timestep at a time.
2. **Constraint enforcement** — clips or rejects commands that violate
   SOC, temperature, C-rate, or inverter limits *before* passing to PySAM.
3. **Full-resolution logging** — records every intermediate quantity at
   every timestep for downstream analysis.
4. **Degradation hook** — a pluggable interface for Task 2B's degradation
   model to update capacity and resistance each step/cycle.

Architecture
------------
The engine uses PySAM's ``BatteryStateful`` in "manual dispatch" mode:
each timestep, we set ``Controls.input_power`` and call ``execute(dt)``.
PySAM handles the voltage model (Tremblay-Dessaint), thermal model
(lumped-parameter), and SOC tracking (coulomb counting) internally.

If PySAM is not installed, the engine falls back to a simplified internal
model (``SimpleBatteryModel``) that implements basic coulomb counting and
ohmic losses.  This fallback is intended for testing and development only
— it does NOT replicate PySAM's validated voltage or thermal models.

Degradation integration (Task 2B)
---------------------------------
The engine accepts an optional ``degradation_model`` that conforms to the
``DegradationModelProtocol``.  If provided, it is called after each
timestep with the current operating conditions and returns updated SOH
values that feed back into the next timestep's capacity and resistance.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

import numpy as np

from bess_engine.config import BESSConfig, CellChemistry
from bess_engine.dispatch import DispatchSchedule
from bess_engine.results import TimestepRecord, SimulationResults


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Degradation model protocol (Task 2B interface contract)
# ---------------------------------------------------------------------------

@runtime_checkable
class DegradationModelProtocol(Protocol):
    """
    Interface contract for pluggable degradation models (Task 2B).

    Any degradation model must implement this protocol.  The engine calls
    ``update()`` after each timestep and reads back the updated SOH values.
    """

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
        Advance degradation state by one timestep.

        Parameters
        ----------
        dt_s : float
            Timestep duration (seconds).
        soc_pct : float
            State of charge at end of step (%).
        temperature_c : float
            Battery temperature (°C).
        current_a : float
            Current during step (A).  Negative=charge.
        voltage_v : float
            Terminal voltage (V).
        dod_pct : float
            Depth of discharge since last full charge (%).

        Returns
        -------
        DegradationState
            Updated capacity and resistance fractions.
        """
        ...

    def get_state(self) -> DegradationState:
        """Return the current degradation state."""
        ...

    def get_mechanism_breakdown(self) -> dict:
        """Return per-mechanism state for logging (extras dict)."""
        ...


@dataclass
class DegradationState:
    """
    Degradation state returned by the degradation model.

    Attributes
    ----------
    capacity_fraction : float
        Remaining capacity as fraction of nameplate (0–1).
        1.0 = no fade, 0.8 = 20% capacity lost.
    resistance_fraction : float
        Current resistance as fraction of BOL resistance (≥1.0).
        1.0 = no growth, 1.5 = 50% resistance increase.
    """
    capacity_fraction: float = 1.0
    resistance_fraction: float = 1.0


# ---------------------------------------------------------------------------
# Simple fallback battery model (no PySAM dependency)
# ---------------------------------------------------------------------------

class SimpleBatteryModel:
    """
    Minimal battery model for testing without PySAM.

    Implements:
    - Coulomb counting for SOC
    - Ohmic voltage model: V = V_oc(SOC) - I × R
    - Simple thermal model: dT/dt ∝ I²R - cooling

    This is NOT a substitute for PySAM's validated models.  It exists so
    that the engine's dispatch logic, constraint enforcement, and logging
    can be tested independently of the PySAM installation.
    """

    def __init__(self, config: BESSConfig):
        self.config = config
        cell = config.cell
        pack = config.pack

        # Pack-level derived quantities
        self.n_series = pack.cells_in_series
        self.n_parallel = pack.strings_in_parallel
        self.cell_capacity_ah = cell.nominal_capacity_ah
        self.pack_capacity_ah = cell.nominal_capacity_ah * self.n_parallel

        # Voltage model: simple linear OCV approximation
        # V_oc(SOC) = V_min + SOC_fraction × (V_max - V_min)
        self.v_cell_min = cell.voltage_nom  # voltage at low SOC
        self.v_cell_max = cell.voltage_full  # voltage at full SOC

        # Resistance (pack-level): series adds, parallel divides
        self.r_cell = cell.internal_resistance_ohm
        self.r_pack_bol = (
            cell.internal_resistance_ohm * self.n_series / self.n_parallel
        )

        # Thermal model parameters
        self.mass = config.thermal.mass_kg
        self.cp = config.thermal.specific_heat_j_per_kg_k
        self.h_a = (
            config.thermal.heat_transfer_coeff_w_per_m2_k
            * config.thermal.surface_area_m2
        )
        self.t_room = config.thermal.room_temperature_c

        # State
        self.soc = config.initial_soc_pct / 100.0  # fraction [0, 1]
        self.temperature = self.t_room
        self.capacity_fraction = 1.0  # from degradation model
        self.resistance_fraction = 1.0  # from degradation model

    @property
    def effective_capacity_ah(self) -> float:
        """Pack capacity adjusted for degradation."""
        return self.pack_capacity_ah * self.capacity_fraction

    @property
    def effective_resistance(self) -> float:
        """Pack resistance adjusted for degradation."""
        return self.r_pack_bol * self.resistance_fraction

    def ocv_pack(self, soc_frac: float) -> float:
        """Open-circuit voltage at given SOC fraction (pack-level, V)."""
        v_cell = self.v_cell_min + soc_frac * (self.v_cell_max - self.v_cell_min)
        return v_cell * self.n_series

    def step(self, power_kw: float, dt_s: float) -> dict:
        """
        Execute one timestep at the given power.

        Parameters
        ----------
        power_kw : float
            AC power command (kW).  Negative=charge, positive=discharge.
        dt_s : float
            Timestep duration (seconds).

        Returns
        -------
        dict
            State snapshot with keys: soc_pct, voltage_v, current_a,
            temperature_c, heat_generated_w, energy_charged_kwh,
            energy_discharged_kwh, power_actual_kw.
        """
        inv = self.config.inverter

        # Convert AC power to DC power (apply inverter efficiency)
        if power_kw < 0:
            # Charging: AC → DC, losses reduce power reaching battery
            dc_power_kw = power_kw * inv.ac_dc_efficiency
        elif power_kw > 0:
            # Discharging: DC → AC, battery must supply more than AC output
            dc_power_kw = power_kw / inv.dc_ac_efficiency
        else:
            dc_power_kw = 0.0

        # DC power in watts
        dc_power_w = dc_power_kw * 1000.0

        # Estimate current from power and OCV (iterative would be better,
        # but single-step Newton is fine for this simple model)
        v_oc = self.ocv_pack(self.soc)
        r = self.effective_resistance

        if abs(dc_power_w) < 1e-3:
            current_a = 0.0
            voltage_v = v_oc
        else:
            # P = V × I = (V_oc - I×R) × I  → quadratic in I
            # I² × R - I × V_oc + P = 0
            # For discharge (P > 0): I = (V_oc - sqrt(V_oc² - 4RP)) / (2R)
            # For charge (P < 0):    I = (V_oc - sqrt(V_oc² - 4RP)) / (2R)
            discriminant = v_oc ** 2 - 4 * r * dc_power_w
            if discriminant < 0:
                # Power exceeds what the battery can deliver/absorb
                # Fall back to max current estimate
                current_a = dc_power_w / v_oc
            else:
                # Take the solution with smaller |I| (physical solution)
                current_a = (v_oc - np.sqrt(discriminant)) / (2 * r)

            voltage_v = v_oc - current_a * r

        # Update SOC via coulomb counting
        # Current sign: positive = discharge (SOC decreases)
        d_soc = -current_a * dt_s / (self.effective_capacity_ah * 3600.0)
        self.soc = np.clip(self.soc + d_soc, 0.0, 1.0)

        # Thermal model: simple Euler step
        heat_w = current_a ** 2 * r
        cooling_w = self.h_a * (self.temperature - self.t_room)
        if self.mass > 0 and self.cp > 0:
            d_temp = (heat_w - cooling_w) * dt_s / (self.mass * self.cp)
            self.temperature += d_temp

        # Energy accounting — AC-side (what the grid meter sees).
        # This is the standard for revenue calculation.  Round-trip
        # efficiency is computed in the KPIs with a SOC-correction term
        # to account for net energy stored/released from the battery.
        dt_h = dt_s / 3600.0

        if power_kw < 0:
            energy_charged_kwh = abs(power_kw) * dt_h
            energy_discharged_kwh = 0.0
        elif power_kw > 0:
            energy_charged_kwh = 0.0
            energy_discharged_kwh = abs(power_kw) * dt_h
        else:
            energy_charged_kwh = 0.0
            energy_discharged_kwh = 0.0

        return {
            "soc_pct": self.soc * 100.0,
            "voltage_v": voltage_v,
            "current_a": current_a,
            "temperature_c": self.temperature,
            "heat_generated_w": heat_w,
            "energy_charged_kwh": energy_charged_kwh,
            "energy_discharged_kwh": energy_discharged_kwh,
            "power_actual_kw": power_kw,  # pre-constraint; engine handles clipping
        }


# ---------------------------------------------------------------------------
# PySAM BatteryStateful wrapper
# ---------------------------------------------------------------------------

def _try_import_pysam():
    """Attempt to import PySAM.  Returns module or None."""
    try:
        import PySAM.BatteryStateful as batt_module
        return batt_module
    except ImportError:
        return None


class PySAMBatteryModel:
    """
    Wrapper around PySAM.BatteryStateful for timestep-by-timestep simulation.

    Handles:
    - Configuration from BESSConfig → PySAM parameter groups
    - Per-timestep execution via ``Controls.input_power`` + ``execute(dt)``
    - State readback (SOC, voltage, current, temperature)
    """

    def __init__(self, config: BESSConfig):
        batt_module = _try_import_pysam()
        if batt_module is None:
            raise ImportError(
                "PySAM is required for PySAMBatteryModel. "
                "Install with: pip install nrel-pysam"
            )

        self.config = config
        self._batt = batt_module.default("GenericBatteryStateful")
        self._configure(config)

    def _configure(self, cfg: BESSConfig) -> None:
        """
        Map BESSConfig fields to PySAM BatteryStateful parameter groups.

        PySAM BatteryStateful parameter groups:
        - ParamsCell: cell-level electrochemical parameters
        - ParamsPack: pack topology (series/parallel)
        - Controls:   dispatch control mode and power commands
        - StatePack:  initial state (SOC, temperature)

        Reference: NREL SAM SDK documentation + BatteryStateful_CustomLifeModel
        notebook from NatLabRockies/pysam.
        """
        b = self._batt

        # --- Chemistry selection ------------------------------------------
        # PySAM chem codes: 0=LeadAcid, 1=Li-ion
        b.ParamsCell.chem = 1  # Li-ion for all supported chemistries

        # --- Cell voltage model (Tremblay-Dessaint) -----------------------
        cell = cfg.cell
        b.ParamsCell.Vnom_default = cell.nominal_voltage
        b.ParamsCell.Vfull = cell.voltage_full
        b.ParamsCell.Vexp = cell.voltage_exp
        b.ParamsCell.Vnom = cell.voltage_nom
        b.ParamsCell.Qfull = cell.nominal_capacity_ah
        b.ParamsCell.Qexp = cell.nominal_capacity_ah * cell.capacity_exp_pct / 100.0
        b.ParamsCell.Qnom = cell.nominal_capacity_ah * cell.capacity_nom_pct / 100.0
        b.ParamsCell.resistance = cell.internal_resistance_ohm

        # C-rate limits
        b.ParamsCell.C_rate = cell.max_discharge_rate
        b.ParamsCell.maximum_SOC = cfg.constraints.soc_max_pct
        b.ParamsCell.minimum_SOC = cfg.constraints.soc_min_pct

        # --- Pack topology ------------------------------------------------
        b.ParamsPack.Cp = cfg.pack.cells_in_series
        b.ParamsPack.Cs = cfg.pack.strings_in_parallel
        # NOTE: PySAM naming can be confusing — Cp and Cs may be swapped
        # depending on PySAM version.  Verify against SAM SDK docs.

        # --- Thermal model ------------------------------------------------
        b.ParamsCell.mass = cfg.thermal.mass_kg
        b.ParamsCell.surface_area = cfg.thermal.surface_area_m2
        b.ParamsCell.Cp_cell = cfg.thermal.specific_heat_j_per_kg_k
        b.ParamsCell.h = cfg.thermal.heat_transfer_coeff_w_per_m2_k
        b.ParamsCell.T_room_init = cfg.thermal.room_temperature_c

        # --- Initial state ------------------------------------------------
        b.StatePack.SOC_init = cfg.initial_soc_pct
        b.StatePack.T_batt = cfg.thermal.room_temperature_c

        # --- Control mode: manual power dispatch --------------------------
        # 0 = dispatch off, 1 = manual power, 2 = manual current
        b.Controls.control_mode = 1
        b.Controls.dt_hr = cfg.simulation_timestep_s / 3600.0

        # --- Lifetime model: disabled (we use our own in Task 2B) ---------
        # 0 = None, 1 = capacity model, 2 = voltage model
        b.ParamsCell.life_model = 0  # disabled — Task 2B handles this

    def step(self, power_kw: float, dt_s: float) -> dict:
        """
        Execute one PySAM timestep.

        Parameters
        ----------
        power_kw : float
            AC power command (kW).  Negative=charge, positive=discharge.
        dt_s : float
            Timestep duration (seconds).

        Returns
        -------
        dict
            State snapshot matching SimpleBatteryModel.step() output format.
        """
        b = self._batt

        # Set dispatch command
        # PySAM convention: positive = discharge, negative = charge
        # (same as our convention)
        b.Controls.input_power = power_kw

        # Execute one timestep
        b.execute(int(dt_s))

        # Read state
        soc_pct = b.StatePack.SOC
        voltage_v = b.StatePack.V
        current_a = b.StatePack.I
        temperature_c = b.StatePack.T_batt
        heat_w = current_a ** 2 * (
            self.config.cell.internal_resistance_ohm
            * self.config.pack.cells_in_series
            / self.config.pack.strings_in_parallel
        )

        # AC-side energy accounting (consistent with SimpleBatteryModel)
        dt_h = dt_s / 3600.0
        if power_kw < 0:
            energy_charged_kwh = abs(power_kw) * dt_h
            energy_discharged_kwh = 0.0
        elif power_kw > 0:
            energy_charged_kwh = 0.0
            energy_discharged_kwh = abs(power_kw) * dt_h
        else:
            energy_charged_kwh = 0.0
            energy_discharged_kwh = 0.0

        return {
            "soc_pct": soc_pct,
            "voltage_v": voltage_v,
            "current_a": current_a,
            "temperature_c": temperature_c,
            "heat_generated_w": heat_w,
            "energy_charged_kwh": energy_charged_kwh,
            "energy_discharged_kwh": energy_discharged_kwh,
            "power_actual_kw": power_kw,
        }


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class BESSEngine:
    """
    BESS simulation engine — the primary public API for Task 2A.

    Given a ``BESSConfig`` and a ``DispatchSchedule``, the engine:
    1. Initialises the battery model (PySAM or fallback)
    2. Steps through the dispatch schedule one timestep at a time
    3. Enforces operational constraints at each step
    4. Optionally calls a degradation model (Task 2B)
    5. Logs every quantity at every timestep

    Parameters
    ----------
    config : BESSConfig
        Complete system configuration.
    degradation_model : DegradationModelProtocol, optional
        Pluggable degradation model (Task 2B).  If None, SOH stays at 100 %.
    use_pysam : bool or None
        If True, requires PySAM.  If False, uses SimpleBatteryModel.
        If None (default), uses PySAM if available, else falls back.

    Examples
    --------
    >>> cfg = BESSConfig.from_defaults("NMC")
    >>> dispatch = load_dispatch("dispatch.csv")
    >>> engine = BESSEngine(cfg)
    >>> results = engine.run(dispatch)
    >>> print(results.summary())
    """

    def __init__(
        self,
        config: BESSConfig,
        degradation_model: Optional[DegradationModelProtocol] = None,
        use_pysam: Optional[bool] = None,
    ):
        self.config = config
        self.degradation_model = degradation_model

        # --- Select battery model backend ---------------------------------
        if use_pysam is True:
            self._model = PySAMBatteryModel(config)
            self._backend = "pysam"
        elif use_pysam is False:
            self._model = SimpleBatteryModel(config)
            self._backend = "simple"
        else:
            # Auto-detect
            pysam = _try_import_pysam()
            if pysam is not None:
                try:
                    self._model = PySAMBatteryModel(config)
                    self._backend = "pysam"
                except Exception as e:
                    logger.warning(
                        "PySAM available but BatteryStateful init failed: %s. "
                        "Falling back to SimpleBatteryModel.", e
                    )
                    self._model = SimpleBatteryModel(config)
                    self._backend = "simple"
            else:
                logger.info(
                    "PySAM not installed. Using SimpleBatteryModel fallback. "
                    "Install PySAM for validated simulation: pip install nrel-pysam"
                )
                self._model = SimpleBatteryModel(config)
                self._backend = "simple"

        # Track peak DOD for degradation model
        self._soc_max_since_charge = config.initial_soc_pct
        self._soc_min_since_charge = config.initial_soc_pct

    @property
    def backend(self) -> str:
        """Which battery model backend is active: 'pysam' or 'simple'."""
        return self._backend

    def run(
        self,
        dispatch: DispatchSchedule,
        progress_interval: int = 10_000,
    ) -> SimulationResults:
        """
        Run the full simulation over a dispatch schedule.

        Parameters
        ----------
        dispatch : DispatchSchedule
            Validated dispatch schedule.
        progress_interval : int
            Log progress every N timesteps.

        Returns
        -------
        SimulationResults
            Complete per-timestep results with aggregate KPIs.
        """
        logger.info(
            "Starting BESS simulation: %d timesteps, backend=%s",
            len(dispatch), self._backend,
        )
        t_start = time.monotonic()

        results = SimulationResults(config_snapshot=self.config.to_dict())
        dt_s = float(dispatch.timestep_s)

        for i in range(len(dispatch)):
            # --- 1. Get commanded power -----------------------------------
            power_cmd_kw = float(dispatch.power_kw[i])
            timestamp = dispatch.timestamps[i]

            # --- 2. Enforce constraints (pre-model) -----------------------
            power_actual_kw, clipped, clip_reason = self._enforce_constraints(
                power_cmd_kw, dt_s
            )

            # --- 3. Execute battery model timestep ------------------------
            state = self._model.step(power_actual_kw, dt_s)

            # --- 4. Track DOD for degradation model -----------------------
            soc_pct = state["soc_pct"]
            self._update_dod_tracking(soc_pct, power_actual_kw)
            current_dod = self._soc_max_since_charge - soc_pct

            # --- 5. Run degradation model (if attached) -------------------
            soh_cap_pct = 100.0
            soh_res_pct = 100.0
            extras = {}

            if self.degradation_model is not None:
                deg_state = self.degradation_model.update(
                    dt_s=dt_s,
                    soc_pct=soc_pct,
                    temperature_c=state["temperature_c"],
                    current_a=state["current_a"],
                    voltage_v=state["voltage_v"],
                    dod_pct=current_dod,
                )
                soh_cap_pct = deg_state.capacity_fraction * 100.0
                soh_res_pct = deg_state.resistance_fraction * 100.0
                extras = self.degradation_model.get_mechanism_breakdown()

                # Feed back to battery model if it supports it
                if isinstance(self._model, SimpleBatteryModel):
                    self._model.capacity_fraction = deg_state.capacity_fraction
                    self._model.resistance_fraction = deg_state.resistance_fraction

            # --- 6. Log everything ----------------------------------------
            record = TimestepRecord(
                timestamp=timestamp,
                step_index=i,
                power_commanded_kw=power_cmd_kw,
                power_actual_kw=power_actual_kw,
                soc_pct=soc_pct,
                voltage_v=state["voltage_v"],
                current_a=state["current_a"],
                temperature_c=state["temperature_c"],
                heat_generated_w=state["heat_generated_w"],
                energy_charged_kwh=state["energy_charged_kwh"],
                energy_discharged_kwh=state["energy_discharged_kwh"],
                power_clipped=clipped,
                clip_reason=clip_reason,
                soh_capacity_pct=soh_cap_pct,
                soh_resistance_pct=soh_res_pct,
                extras=extras,
            )
            results.append(record)

            # --- Progress logging -----------------------------------------
            if progress_interval > 0 and (i + 1) % progress_interval == 0:
                elapsed = time.monotonic() - t_start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                logger.info(
                    "  Step %d / %d (%.0f steps/s) — SOC=%.1f%%, T=%.1f°C",
                    i + 1, len(dispatch), rate, soc_pct,
                    state["temperature_c"],
                )

        elapsed = time.monotonic() - t_start
        logger.info(
            "Simulation complete: %d steps in %.1f s (%.0f steps/s)",
            len(dispatch), elapsed,
            len(dispatch) / elapsed if elapsed > 0 else 0,
        )

        return results

    # --- Constraint enforcement -------------------------------------------

    def _enforce_constraints(
        self,
        power_kw: float,
        dt_s: float,
    ) -> tuple[float, bool, str]:
        """
        Enforce operational constraints on a dispatch command.

        Applies constraints in priority order:
        1. Temperature limits (block all operations if out of range)
        2. SOC limits (clip power to prevent over/under-charge)
        3. C-rate limits (clip to max charge/discharge rate)
        4. Inverter power limits (clip to PCS rating)

        Parameters
        ----------
        power_kw : float
            Commanded power (kW).  Negative=charge, positive=discharge.
        dt_s : float
            Timestep duration (seconds).

        Returns
        -------
        tuple of (adjusted_power_kw, was_clipped, clip_reason)
        """
        cfg = self.config
        cell = cfg.cell
        constraints = cfg.constraints

        original_power = power_kw
        reasons: list[str] = []

        # Get current state from model
        if isinstance(self._model, SimpleBatteryModel):
            current_soc = self._model.soc * 100.0
            current_temp = self._model.temperature
        else:
            # PySAM: read from StatePack
            current_soc = self._model._batt.StatePack.SOC
            current_temp = self._model._batt.StatePack.T_batt

        # --- 1. Temperature limits ----------------------------------------
        if current_temp < constraints.min_temperature_c:
            # Block charging at low temperatures (lithium plating risk)
            if power_kw < 0:
                power_kw = 0.0
                reasons.append("temperature_low")
        if current_temp > constraints.max_temperature_c:
            # Block all operations at high temperature
            power_kw = 0.0
            reasons.append("temperature_high")

        # --- 2. SOC limits ------------------------------------------------
        if power_kw < 0:
            # Charging — check SOC upper limit
            if current_soc >= constraints.soc_max_pct:
                power_kw = 0.0
                reasons.append("soc_max")
            else:
                # Estimate energy headroom to max SOC
                soc_headroom_frac = (constraints.soc_max_pct - current_soc) / 100.0
                energy_headroom_kwh = (
                    soc_headroom_frac
                    * cfg.nameplate_energy_kwh
                    * (self._model.capacity_fraction
                       if isinstance(self._model, SimpleBatteryModel)
                       else 1.0)
                )
                max_charge_kw = energy_headroom_kwh / (dt_s / 3600.0)
                if abs(power_kw) > max_charge_kw and max_charge_kw > 0:
                    power_kw = -max_charge_kw
                    reasons.append("soc_max")

        elif power_kw > 0:
            # Discharging — check SOC lower limit
            if current_soc <= constraints.soc_min_pct:
                power_kw = 0.0
                reasons.append("soc_min")
            else:
                soc_available_frac = (current_soc - constraints.soc_min_pct) / 100.0
                energy_available_kwh = (
                    soc_available_frac
                    * cfg.nameplate_energy_kwh
                    * (self._model.capacity_fraction
                       if isinstance(self._model, SimpleBatteryModel)
                       else 1.0)
                )
                max_discharge_kw = energy_available_kwh / (dt_s / 3600.0)
                if power_kw > max_discharge_kw and max_discharge_kw > 0:
                    power_kw = max_discharge_kw
                    reasons.append("soc_min")

        # --- 3. C-rate limits ---------------------------------------------
        # Max power from C-rate: P = C_rate × E_nameplate
        nameplate_kwh = cfg.nameplate_energy_kwh
        if power_kw < 0:
            max_charge_power = cell.max_charge_rate * nameplate_kwh
            if abs(power_kw) > max_charge_power:
                power_kw = -max_charge_power
                reasons.append("c_rate")
        elif power_kw > 0:
            max_discharge_power = cell.max_discharge_rate * nameplate_kwh
            if power_kw > max_discharge_power:
                power_kw = max_discharge_power
                reasons.append("c_rate")

        # --- 4. Inverter / PCS power limits -------------------------------
        max_pcs = cfg.inverter.max_power_kw
        if abs(power_kw) > max_pcs:
            power_kw = np.sign(power_kw) * max_pcs
            reasons.append("inverter_limit")

        # --- Build result -------------------------------------------------
        clipped = abs(power_kw - original_power) > 0.01  # 10 W tolerance
        clip_reason = ",".join(reasons) if reasons else ""

        return power_kw, clipped, clip_reason

    # --- DOD tracking for degradation model -------------------------------

    def _update_dod_tracking(self, soc_pct: float, power_kw: float) -> None:
        """
        Track SOC excursions for depth-of-discharge calculation.

        Maintains running max/min SOC since last direction change.
        The degradation model uses this to compute per-cycle DOD.
        """
        if power_kw < 0:
            # Charging — SOC is rising; track the peak
            self._soc_max_since_charge = max(self._soc_max_since_charge, soc_pct)
        elif power_kw > 0:
            # Discharging — SOC is falling; track the trough
            self._soc_min_since_charge = min(self._soc_min_since_charge, soc_pct)
        # When direction changes, the DOD of the half-cycle is the excursion.
        # Full rainflow counting (Task 2B) will handle this properly;
        # this simple tracking provides an approximate DOD for per-timestep use.
