"""
Tests for bess_engine (Task 2A).

All tests use ``use_pysam=False`` to ensure they run without PySAM
installed.  PySAM-specific integration tests will be added separately.

Run with:  pytest tests/test_engine.py -v
"""

import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bess_engine.config import (
    BESSConfig,
    CellChemistry,
    CellParams,
    PackParams,
    InverterParams,
    ThermalParams,
    ConstraintParams,
)
from bess_engine.dispatch import (
    DispatchSchedule,
    load_dispatch,
    make_constant_dispatch,
    make_cycling_dispatch,
)
from bess_engine.results import TimestepRecord, SimulationResults
from bess_engine.engine import BESSEngine, DegradationState


# ======================================================================
# Configuration tests
# ======================================================================

class TestBESSConfig:
    """Tests for BESSConfig and its sub-dataclasses."""

    def test_from_defaults_nmc(self):
        cfg = BESSConfig.from_defaults("NMC")
        assert cfg.cell.chemistry == CellChemistry.NMC
        assert cfg.cell.voltage_full == 4.2
        assert cfg.cell.nominal_capacity_ah == 75.0
        assert cfg.constraints.soc_min_pct == 10.0

    def test_from_defaults_lfp(self):
        cfg = BESSConfig.from_defaults("LFP")
        assert cfg.cell.chemistry == CellChemistry.LFP
        assert cfg.cell.voltage_full == 3.65
        assert cfg.cell.nominal_capacity_ah == 100.0
        # LFP has wider SOC window
        assert cfg.constraints.soc_min_pct < 10.0

    def test_from_defaults_lto(self):
        cfg = BESSConfig.from_defaults("LTO")
        assert cfg.cell.chemistry == CellChemistry.LTO
        assert cfg.cell.max_charge_rate == 5.0  # LTO supports high C-rates
        assert cfg.constraints.min_temperature_c == -30.0  # cold-tolerant

    def test_from_defaults_nca(self):
        cfg = BESSConfig.from_defaults("NCA")
        assert cfg.cell.chemistry == CellChemistry.NCA

    def test_from_defaults_invalid(self):
        with pytest.raises(ValueError):
            BESSConfig.from_defaults("INVALID")

    def test_from_defaults_case_insensitive(self):
        cfg = BESSConfig.from_defaults("nmc")
        assert cfg.cell.chemistry == CellChemistry.NMC

    def test_nameplate_energy(self):
        cfg = BESSConfig.from_defaults("NMC")
        # 75 Ah × 3.6 V = 270 Wh per cell
        # 200 series × 100 parallel = 20,000 cells
        # 270 × 20,000 / 1000 = 5,400 kWh
        expected = 75.0 * 3.6 * 200 * 100 / 1000.0
        assert abs(cfg.nameplate_energy_kwh - expected) < 0.1

    def test_nominal_pack_voltage(self):
        cfg = BESSConfig.from_defaults("NMC")
        expected = 200 * 3.6  # 720 V
        assert abs(cfg.nominal_pack_voltage_v - expected) < 0.1

    def test_to_dict_serialisable(self):
        """Config should serialise to a dict (for JSON logging)."""
        cfg = BESSConfig.from_defaults("NMC")
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert d["cell"]["chemistry"] == "NMC"
        assert isinstance(d["cell"]["nominal_capacity_ah"], float)

    def test_override_fields(self):
        """Users should be able to override individual fields."""
        cfg = BESSConfig.from_defaults("NMC")
        cfg.cell.nominal_capacity_ah = 100.0
        cfg.pack.cells_in_series = 250
        assert cfg.cell.nominal_capacity_ah == 100.0
        assert cfg.pack.cells_in_series == 250


# ======================================================================
# Dispatch tests
# ======================================================================

class TestDispatch:
    """Tests for dispatch loading and validation."""

    def test_make_constant_dispatch(self):
        d = make_constant_dispatch(power_kw=-5000.0, duration_hours=2.0)
        assert len(d) == 120  # 2 hours × 60 steps/hour
        assert d.timestep_s == 60
        assert np.all(d.power_kw == -5000.0)
        assert d.duration_hours == 2.0

    def test_make_cycling_dispatch(self):
        d = make_cycling_dispatch(
            charge_power_kw=5000,
            discharge_power_kw=5000,
            charge_hours=1.0,
            discharge_hours=1.0,
            n_cycles=3,
        )
        # 3 cycles × (60 charge + 60 discharge) = 360 steps
        assert len(d) == 360
        # First step should be charging (negative)
        assert d.power_kw[0] < 0
        # Step 60 should be discharging (positive)
        assert d.power_kw[60] > 0

    def test_make_cycling_with_rest(self):
        d = make_cycling_dispatch(
            charge_power_kw=5000,
            discharge_power_kw=5000,
            charge_hours=1.0,
            discharge_hours=1.0,
            n_cycles=1,
            rest_hours=0.5,
        )
        # 1 cycle: 60 charge + 30 rest + 60 discharge + 30 rest = 180
        assert len(d) == 180

    def test_load_dispatch_csv(self):
        """Test loading from a CSV file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("Date/Time,pwr_kw\n")
            for i in range(10):
                f.write(f"2025-01-01 00:{i:02d}:00,{-5000 + i * 1000}\n")
            csv_path = f.name

        try:
            d = load_dispatch(csv_path)
            assert len(d) == 10
            assert d.timestep_s == 60
            assert d.power_kw[0] == -5000.0
        finally:
            os.unlink(csv_path)

    def test_load_dispatch_missing_column(self):
        df = pd.DataFrame({"time": ["2025-01-01"], "power": [100]})
        with pytest.raises(ValueError, match="Time column"):
            load_dispatch(df)

    def test_load_dispatch_nan_values(self):
        df = pd.DataFrame({
            "Date/Time": pd.date_range("2025-01-01", periods=5, freq="1min"),
            "pwr_kw": [100, 200, np.nan, 400, 500],
        })
        with pytest.raises(ValueError, match="NaN"):
            load_dispatch(df)

    def test_load_dispatch_from_dataframe(self):
        df = pd.DataFrame({
            "Date/Time": pd.date_range("2025-01-01", periods=60, freq="1min"),
            "pwr_kw": np.full(60, -3000.0),
        })
        d = load_dispatch(df)
        assert len(d) == 60
        assert d.timestep_s == 60

    def test_dispatch_summary(self):
        d = make_cycling_dispatch(
            charge_power_kw=5000,
            discharge_power_kw=5000,
            charge_hours=1.0,
            discharge_hours=1.0,
            n_cycles=1,
        )
        summary = d.summary()
        assert "DispatchSchedule" in summary
        assert "Charging" in summary
        assert "Discharging" in summary

    def test_dispatch_energy_properties(self):
        d = make_constant_dispatch(power_kw=-6000.0, duration_hours=1.0)
        # 6000 kW × 1 hour = 6000 kWh charged
        assert abs(d.total_charge_energy_kwh - 6000.0) < 1.0
        assert d.total_discharge_energy_kwh == 0.0


# ======================================================================
# Engine tests (SimpleBatteryModel fallback)
# ======================================================================

class TestBESSEngine:
    """Tests for BESSEngine with SimpleBatteryModel backend."""

    @pytest.fixture
    def small_config(self) -> BESSConfig:
        """A small system config for fast tests."""
        cfg = BESSConfig.from_defaults("NMC")
        # Scale down to a 270 kWh system (10s × 10p × 75 Ah × 3.6 V)
        cfg.pack.cells_in_series = 10
        cfg.pack.strings_in_parallel = 10
        cfg.inverter.max_power_kw = 500.0
        cfg.thermal.mass_kg = 500.0
        cfg.thermal.surface_area_m2 = 5.0
        cfg.initial_soc_pct = 50.0
        return cfg

    def test_engine_initialises(self, small_config):
        engine = BESSEngine(small_config, use_pysam=False)
        assert engine.backend == "simple"

    def test_constant_discharge(self, small_config):
        """Constant discharge should reduce SOC monotonically."""
        engine = BESSEngine(small_config, use_pysam=False)
        dispatch = make_constant_dispatch(
            power_kw=100.0,  # discharge 100 kW
            duration_hours=0.5,
            timestep_s=60,
        )
        results = engine.run(dispatch)

        assert len(results) == 30
        df = results.to_dataframe()

        # SOC should decrease monotonically
        soc = df["soc_pct"].values
        assert soc[0] < 50.0  # started at 50 %, should drop
        assert all(soc[i] >= soc[i + 1] for i in range(len(soc) - 1))

    def test_constant_charge(self, small_config):
        """Constant charge should increase SOC monotonically."""
        small_config.initial_soc_pct = 30.0  # start low
        engine = BESSEngine(small_config, use_pysam=False)
        dispatch = make_constant_dispatch(
            power_kw=-100.0,  # charge 100 kW
            duration_hours=0.5,
            timestep_s=60,
        )
        results = engine.run(dispatch)
        df = results.to_dataframe()

        soc = df["soc_pct"].values
        assert soc[-1] > 30.0  # SOC should have increased
        assert all(soc[i] <= soc[i + 1] for i in range(len(soc) - 1))

    def test_idle_dispatch(self, small_config):
        """Zero power should leave SOC unchanged (within float tolerance)."""
        engine = BESSEngine(small_config, use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=0.0, duration_hours=0.5)
        results = engine.run(dispatch)
        df = results.to_dataframe()

        assert abs(df["soc_pct"].iloc[-1] - 50.0) < 0.01
        assert df["energy_charged_kwh"].sum() == 0.0
        assert df["energy_discharged_kwh"].sum() == 0.0

    def test_soc_min_constraint(self, small_config):
        """Discharging should stop at SOC min limit."""
        small_config.initial_soc_pct = 15.0  # close to 10 % min
        small_config.constraints.soc_min_pct = 10.0
        engine = BESSEngine(small_config, use_pysam=False)

        dispatch = make_constant_dispatch(
            power_kw=200.0,  # aggressive discharge
            duration_hours=1.0,
        )
        results = engine.run(dispatch)
        df = results.to_dataframe()

        # SOC should never go below min
        assert df["soc_pct"].min() >= small_config.constraints.soc_min_pct - 0.5
        # Some steps should have been clipped
        assert df["power_clipped"].any()

    def test_soc_max_constraint(self, small_config):
        """Charging should stop at SOC max limit."""
        small_config.initial_soc_pct = 85.0  # close to 90 % max
        small_config.constraints.soc_max_pct = 90.0
        engine = BESSEngine(small_config, use_pysam=False)

        dispatch = make_constant_dispatch(
            power_kw=-200.0,  # aggressive charge
            duration_hours=1.0,
        )
        results = engine.run(dispatch)
        df = results.to_dataframe()

        # SOC should never exceed max
        assert df["soc_pct"].max() <= small_config.constraints.soc_max_pct + 0.5
        assert df["power_clipped"].any()

    def test_inverter_power_limit(self, small_config):
        """Power should be clipped to inverter rating."""
        small_config.inverter.max_power_kw = 100.0
        engine = BESSEngine(small_config, use_pysam=False)

        dispatch = make_constant_dispatch(
            power_kw=500.0,  # exceeds 100 kW inverter limit
            duration_hours=0.1,
        )
        results = engine.run(dispatch)
        df = results.to_dataframe()

        # Actual power should be clipped to inverter limit
        assert df["power_actual_kw"].max() <= 100.0 + 0.01
        assert df["power_clipped"].all()
        assert "inverter_limit" in df["clip_reason"].iloc[0]

    def test_temperature_constraint_blocks_at_high_temp(self, small_config):
        """Operations should be blocked when temperature exceeds max."""
        # Hack: set model temperature above limit
        engine = BESSEngine(small_config, use_pysam=False)
        engine._model.temperature = 50.0  # above 45 °C default max

        dispatch = make_constant_dispatch(power_kw=100.0, duration_hours=0.1)
        results = engine.run(dispatch)
        df = results.to_dataframe()

        # All power should be blocked
        assert (df["power_actual_kw"] == 0.0).all()
        assert df["power_clipped"].all()

    def test_cycling_dispatch(self, small_config):
        """A full charge/discharge cycle should work end-to-end."""
        small_config.initial_soc_pct = 50.0
        engine = BESSEngine(small_config, use_pysam=False)

        # Use low power relative to system size (27 kWh) to avoid
        # SOC-limit clipping that would distort RTE
        dispatch = make_cycling_dispatch(
            charge_power_kw=5,
            discharge_power_kw=5,
            charge_hours=0.5,
            discharge_hours=0.5,
            n_cycles=2,
        )
        results = engine.run(dispatch)

        assert len(results) == 120  # 2 cycles × (30 + 30)
        kpis = results.kpis
        assert kpis["total_energy_charged_kwh"] > 0
        assert kpis["total_energy_discharged_kwh"] > 0
        assert 0 < kpis["round_trip_efficiency_pct"] <= 100

    def test_results_kpis(self, small_config):
        """KPIs should contain all expected keys."""
        engine = BESSEngine(small_config, use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=0.5)
        results = engine.run(dispatch)

        kpis = results.kpis
        expected_keys = {
            "total_energy_charged_kwh",
            "total_energy_discharged_kwh",
            "round_trip_efficiency_pct",
            "n_timesteps",
            "n_clipped_timesteps",
            "clip_fraction_pct",
            "soc_min_pct",
            "soc_max_pct",
            "soc_mean_pct",
            "temperature_min_c",
            "temperature_max_c",
            "temperature_mean_c",
            "final_soh_capacity_pct",
            "final_soh_resistance_pct",
        }
        assert expected_keys.issubset(set(kpis.keys()))

    def test_results_to_dataframe(self, small_config):
        """Results should convert cleanly to a DataFrame."""
        engine = BESSEngine(small_config, use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=0.1)
        results = engine.run(dispatch)

        df = results.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 6  # 0.1 hours = 6 minutes
        assert "soc_pct" in df.columns
        assert "voltage_v" in df.columns

    def test_results_summary(self, small_config):
        """Summary string should be human-readable."""
        engine = BESSEngine(small_config, use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=0.1)
        results = engine.run(dispatch)
        summary = results.summary()
        assert "SimulationResults" in summary
        assert "SOC range" in summary

    def test_empty_results(self):
        """Empty results should handle gracefully."""
        results = SimulationResults()
        assert results.kpis == {}
        assert "empty" in results.summary()


# ======================================================================
# Degradation model integration tests
# ======================================================================

class TestDegradationIntegration:
    """Tests for the degradation model hook (Task 2B interface)."""

    @pytest.fixture
    def small_config(self) -> BESSConfig:
        cfg = BESSConfig.from_defaults("NMC")
        cfg.pack.cells_in_series = 10
        cfg.pack.strings_in_parallel = 10
        cfg.inverter.max_power_kw = 500.0
        cfg.thermal.mass_kg = 500.0
        cfg.initial_soc_pct = 50.0
        return cfg

    def test_passthrough_degradation_model(self, small_config):
        """PassthroughDegradation should leave SOH at 100 %."""
        from degradation.passthrough import PassthroughDegradation

        deg = PassthroughDegradation()
        engine = BESSEngine(
            small_config,
            degradation_model=deg,
            use_pysam=False,
        )

        dispatch = make_cycling_dispatch(
            charge_power_kw=50,
            discharge_power_kw=50,
            charge_hours=0.5,
            discharge_hours=0.5,
            n_cycles=1,
        )
        results = engine.run(dispatch)

        kpis = results.kpis
        assert kpis["final_soh_capacity_pct"] == 100.0
        assert kpis["final_soh_resistance_pct"] == 100.0

    def test_passthrough_logs_throughput(self, small_config):
        """PassthroughDegradation should track Ah throughput in extras."""
        from degradation.passthrough import PassthroughDegradation

        deg = PassthroughDegradation()
        engine = BESSEngine(
            small_config,
            degradation_model=deg,
            use_pysam=False,
        )

        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=0.5)
        results = engine.run(dispatch)

        df = results.to_dataframe()
        # Extras should be flattened with x_ prefix
        assert "x_total_ah_throughput" in df.columns
        assert df["x_total_ah_throughput"].iloc[-1] > 0

    def test_custom_degradation_model(self, small_config):
        """A custom degradation model that applies fixed fade per step."""

        class LinearFadeModel:
            """Toy model: loses 0.001 % capacity per step."""
            def __init__(self):
                self._cap = 1.0
                self._res = 1.0

            def update(self, dt_s, soc_pct, temperature_c,
                       current_a, voltage_v, dod_pct):
                self._cap -= 0.00001  # 0.001 % per step
                self._res += 0.000005
                return DegradationState(self._cap, self._res)

            def get_state(self):
                return DegradationState(self._cap, self._res)

            def get_mechanism_breakdown(self):
                return {"model": "linear_fade", "cap": self._cap}

        engine = BESSEngine(
            small_config,
            degradation_model=LinearFadeModel(),
            use_pysam=False,
        )
        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=1.0)
        results = engine.run(dispatch)

        kpis = results.kpis
        # 60 steps × 0.001 % = 0.06 % fade → final ~99.94 %
        assert kpis["final_soh_capacity_pct"] < 100.0
        assert kpis["final_soh_resistance_pct"] > 100.0


# ======================================================================
# Round-trip efficiency sanity check
# ======================================================================

class TestRoundTripEfficiency:
    """Verify that the simple model produces physically plausible RTE."""

    def test_rte_below_100_pct(self):
        """RTE should always be < 100 % (losses exist)."""
        cfg = BESSConfig.from_defaults("NMC")
        cfg.pack.cells_in_series = 10
        cfg.pack.strings_in_parallel = 10
        cfg.inverter.max_power_kw = 500.0
        cfg.thermal.mass_kg = 500.0
        cfg.initial_soc_pct = 50.0

        engine = BESSEngine(cfg, use_pysam=False)
        # Use low power (5 kW into 27 kWh ≈ 0.19C) for balanced cycles
        dispatch = make_cycling_dispatch(
            charge_power_kw=5,
            discharge_power_kw=5,
            charge_hours=1.0,
            discharge_hours=1.0,
            n_cycles=3,
        )
        results = engine.run(dispatch)
        rte = results.kpis["round_trip_efficiency_pct"]

        # RTE should be plausible: typically 85–97 % for Li-ion
        assert 50.0 < rte < 100.0, f"RTE={rte}% is out of plausible range"


# ======================================================================
# Entry point
# ======================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
