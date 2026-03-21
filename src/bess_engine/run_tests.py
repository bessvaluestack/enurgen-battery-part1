"""
Standalone test runner for bess_engine — no pytest required.

Run with:  python3 tests/run_tests.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from bess_engine.config import BESSConfig, CellChemistry
from bess_engine.dispatch import (
    load_dispatch,
    make_constant_dispatch,
    make_cycling_dispatch,
)
from bess_engine.results import SimulationResults
from bess_engine.engine import BESSEngine, DegradationState


class TestConfig(unittest.TestCase):

    def test_from_defaults_nmc(self):
        cfg = BESSConfig.from_defaults("NMC")
        self.assertEqual(cfg.cell.chemistry, CellChemistry.NMC)
        self.assertAlmostEqual(cfg.cell.voltage_full, 4.2)

    def test_from_defaults_lfp(self):
        cfg = BESSConfig.from_defaults("LFP")
        self.assertEqual(cfg.cell.chemistry, CellChemistry.LFP)

    def test_from_defaults_lto(self):
        cfg = BESSConfig.from_defaults("LTO")
        self.assertEqual(cfg.cell.max_charge_rate, 5.0)

    def test_from_defaults_invalid(self):
        with self.assertRaises(ValueError):
            BESSConfig.from_defaults("INVALID")

    def test_nameplate_energy(self):
        cfg = BESSConfig.from_defaults("NMC")
        expected = 75.0 * 3.6 * 200 * 100 / 1000.0
        self.assertAlmostEqual(cfg.nameplate_energy_kwh, expected, places=0)

    def test_to_dict(self):
        cfg = BESSConfig.from_defaults("NMC")
        d = cfg.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["cell"]["chemistry"], "NMC")


class TestDispatch(unittest.TestCase):

    def test_constant_dispatch(self):
        d = make_constant_dispatch(power_kw=-5000.0, duration_hours=2.0)
        self.assertEqual(len(d), 120)
        self.assertEqual(d.timestep_s, 60)

    def test_cycling_dispatch(self):
        d = make_cycling_dispatch(
            charge_power_kw=5000, discharge_power_kw=5000,
            charge_hours=1.0, discharge_hours=1.0, n_cycles=3,
        )
        self.assertEqual(len(d), 360)
        self.assertTrue(d.power_kw[0] < 0)  # charging
        self.assertTrue(d.power_kw[60] > 0)  # discharging

    def test_load_from_dataframe(self):
        df = pd.DataFrame({
            "Date/Time": pd.date_range("2025-01-01", periods=60, freq="1min"),
            "pwr_kw": np.full(60, -3000.0),
        })
        d = load_dispatch(df)
        self.assertEqual(len(d), 60)

    def test_dispatch_energy(self):
        d = make_constant_dispatch(power_kw=-6000.0, duration_hours=1.0)
        self.assertAlmostEqual(d.total_charge_energy_kwh, 6000.0, places=0)

    def test_load_csv(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("Date/Time,pwr_kw\n")
            for i in range(10):
                f.write(f"2025-01-01 00:{i:02d}:00,{-5000}\n")
            path = f.name
        try:
            d = load_dispatch(path)
            self.assertEqual(len(d), 10)
        finally:
            os.unlink(path)


def _small_config() -> BESSConfig:
    cfg = BESSConfig.from_defaults("NMC")
    cfg.pack.cells_in_series = 10
    cfg.pack.strings_in_parallel = 10
    cfg.inverter.max_power_kw = 500.0
    cfg.thermal.mass_kg = 500.0
    cfg.thermal.surface_area_m2 = 5.0
    cfg.initial_soc_pct = 50.0
    return cfg


class TestEngine(unittest.TestCase):

    def test_initialises(self):
        engine = BESSEngine(_small_config(), use_pysam=False)
        self.assertEqual(engine.backend, "simple")

    def test_constant_discharge(self):
        engine = BESSEngine(_small_config(), use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=100.0, duration_hours=0.5)
        results = engine.run(dispatch)
        df = results.to_dataframe()
        soc = df["soc_pct"].values
        self.assertTrue(soc[-1] < 50.0)
        # Monotonically decreasing
        self.assertTrue(all(soc[i] >= soc[i+1] for i in range(len(soc)-1)))

    def test_constant_charge(self):
        cfg = _small_config()
        cfg.initial_soc_pct = 30.0
        engine = BESSEngine(cfg, use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=-100.0, duration_hours=0.5)
        results = engine.run(dispatch)
        df = results.to_dataframe()
        soc = df["soc_pct"].values
        self.assertTrue(soc[-1] > 30.0)

    def test_idle(self):
        engine = BESSEngine(_small_config(), use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=0.0, duration_hours=0.5)
        results = engine.run(dispatch)
        df = results.to_dataframe()
        self.assertAlmostEqual(df["soc_pct"].iloc[-1], 50.0, places=1)

    def test_soc_min_constraint(self):
        cfg = _small_config()
        cfg.initial_soc_pct = 15.0
        cfg.constraints.soc_min_pct = 10.0
        engine = BESSEngine(cfg, use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=200.0, duration_hours=1.0)
        results = engine.run(dispatch)
        df = results.to_dataframe()
        self.assertGreaterEqual(df["soc_pct"].min(), 9.0)  # small tolerance

    def test_soc_max_constraint(self):
        cfg = _small_config()
        cfg.initial_soc_pct = 85.0
        cfg.constraints.soc_max_pct = 90.0
        engine = BESSEngine(cfg, use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=-200.0, duration_hours=1.0)
        results = engine.run(dispatch)
        df = results.to_dataframe()
        self.assertLessEqual(df["soc_pct"].max(), 91.0)

    def test_inverter_limit(self):
        cfg = _small_config()
        cfg.inverter.max_power_kw = 100.0
        engine = BESSEngine(cfg, use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=500.0, duration_hours=0.1)
        results = engine.run(dispatch)
        df = results.to_dataframe()
        self.assertLessEqual(df["power_actual_kw"].max(), 100.01)
        self.assertTrue(df["power_clipped"].all())

    def test_temperature_blocks_operations(self):
        cfg = _small_config()
        engine = BESSEngine(cfg, use_pysam=False)
        engine._model.temperature = 50.0  # above 45 °C max
        dispatch = make_constant_dispatch(power_kw=100.0, duration_hours=0.1)
        results = engine.run(dispatch)
        df = results.to_dataframe()
        self.assertTrue((df["power_actual_kw"] == 0.0).all())

    def test_cycling(self):
        engine = BESSEngine(_small_config(), use_pysam=False)
        # Use low power relative to system size (27 kWh) to ensure
        # balanced cycles without hitting SOC limits
        dispatch = make_cycling_dispatch(
            charge_power_kw=5, discharge_power_kw=5,
            charge_hours=0.5, discharge_hours=0.5, n_cycles=2,
        )
        results = engine.run(dispatch)
        kpis = results.kpis
        self.assertGreater(kpis["total_energy_charged_kwh"], 0)
        self.assertGreater(kpis["total_energy_discharged_kwh"], 0)
        self.assertGreater(kpis["round_trip_efficiency_pct"], 0)
        self.assertLess(kpis["round_trip_efficiency_pct"], 100)

    def test_kpi_keys(self):
        engine = BESSEngine(_small_config(), use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=0.5)
        results = engine.run(dispatch)
        kpis = results.kpis
        for key in [
            "total_energy_charged_kwh", "total_energy_discharged_kwh",
            "round_trip_efficiency_pct", "n_timesteps",
            "soc_min_pct", "soc_max_pct", "temperature_min_c",
            "final_soh_capacity_pct", "final_soh_resistance_pct",
        ]:
            self.assertIn(key, kpis)

    def test_results_to_dataframe(self):
        engine = BESSEngine(_small_config(), use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=0.1)
        results = engine.run(dispatch)
        df = results.to_dataframe()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 6)

    def test_results_summary(self):
        engine = BESSEngine(_small_config(), use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=0.1)
        results = engine.run(dispatch)
        self.assertIn("SimulationResults", results.summary())

    def test_empty_results(self):
        results = SimulationResults()
        self.assertEqual(results.kpis, {})


class TestDegradation(unittest.TestCase):

    def test_passthrough(self):
        from degradation.passthrough import PassthroughDegradation
        deg = PassthroughDegradation()
        engine = BESSEngine(_small_config(), degradation_model=deg, use_pysam=False)
        dispatch = make_cycling_dispatch(
            charge_power_kw=50, discharge_power_kw=50,
            charge_hours=0.5, discharge_hours=0.5, n_cycles=1,
        )
        results = engine.run(dispatch)
        self.assertEqual(results.kpis["final_soh_capacity_pct"], 100.0)

    def test_passthrough_logs_extras(self):
        from degradation.passthrough import PassthroughDegradation
        deg = PassthroughDegradation()
        engine = BESSEngine(_small_config(), degradation_model=deg, use_pysam=False)
        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=0.5)
        results = engine.run(dispatch)
        df = results.to_dataframe()
        self.assertIn("x_total_ah_throughput", df.columns)
        self.assertGreater(df["x_total_ah_throughput"].iloc[-1], 0)

    def test_custom_degradation(self):
        class LinearFade:
            def __init__(self):
                self._cap = 1.0
                self._res = 1.0
            def update(self, dt_s, soc_pct, temperature_c,
                       current_a, voltage_v, dod_pct):
                self._cap -= 0.00001
                self._res += 0.000005
                return DegradationState(self._cap, self._res)
            def get_state(self):
                return DegradationState(self._cap, self._res)
            def get_mechanism_breakdown(self):
                return {"model": "linear_fade"}

        engine = BESSEngine(
            _small_config(), degradation_model=LinearFade(), use_pysam=False,
        )
        dispatch = make_constant_dispatch(power_kw=-50.0, duration_hours=1.0)
        results = engine.run(dispatch)
        self.assertLess(results.kpis["final_soh_capacity_pct"], 100.0)
        self.assertGreater(results.kpis["final_soh_resistance_pct"], 100.0)


class TestRTE(unittest.TestCase):

    def test_rte_below_100(self):
        engine = BESSEngine(_small_config(), use_pysam=False)
        # Use low power (5 kW into 27 kWh system ≈ 0.19C) for balanced
        # cycles that stay well within SOC limits
        dispatch = make_cycling_dispatch(
            charge_power_kw=5, discharge_power_kw=5,
            charge_hours=1.0, discharge_hours=1.0, n_cycles=3,
        )
        results = engine.run(dispatch)
        rte = results.kpis["round_trip_efficiency_pct"]
        self.assertGreater(rte, 50.0)
        self.assertLess(rte, 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
