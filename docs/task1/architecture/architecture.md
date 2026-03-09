# Architecture Design — DUET BESS Module

**Task 1, Deliverable 3** | Est. 8 hrs
**Status:** Draft

## Purpose

Blueprint for integrating BESS modeling into the DUET platform. This document defines module boundaries, interface contracts, and integration points so that Enurgen's engineering team can take the PoC code from Tasks 2A/2B and integrate it into the DUET production codebase.

**Audience:** Enurgen CTO and engineering team.

---

## 1. Module Overview

The BESS capability is decomposed into four modules with clear boundaries. This engagement implements the first two; the others are architected but deferred.

```
┌─────────────────────────────────────────────────────────┐
│                    DUET Platform                         │
│                                                         │
│  ┌──────────────┐    ┌──────────────────────────────┐   │
│  │   PV Model   │    │        BESS Module            │   │
│  │  (existing)  │    │                              │   │
│  │              │    │  ┌────────┐   ┌───────────┐  │   │
│  │  Generation  │───▶│  │ SoC    │   │Degradation│  │   │
│  │  Profiles    │    │  │Simulator│──▶│  Engine   │  │   │
│  │              │    │  │(Task 2A)│   │ (Task 2B) │  │   │
│  └──────────────┘    │  └────┬───┘   └─────┬─────┘  │   │
│                      │       │             │        │   │
│                      │       ▼             ▼        │   │
│                      │  ┌────────┐   ┌───────────┐  │   │
│                      │  │Dispatch│   │ Financial  │  │   │
│                      │  │Optimizer│  │   Layer    │  │   │
│                      │  │(Task 3)│   │ (Task 4)  │  │   │
│                      │  └────────┘   └───────────┘  │   │
│                      └──────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Model vs. Actual Comparison              │   │
│  │              (existing + extended)                 │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Module Responsibilities

| Module | Scope | Input | Output | This Contract? |
|--------|-------|-------|--------|---------------|
| **SoC Simulator** | Forward simulation of battery physical behavior for one time period | Dispatch schedule + system config | SoC, power flows, losses, throughput time-series | ✅ Task 2A |
| **Degradation Engine** | State-of-health projection over system lifetime | Operating history (from simulator) + chemistry params | SoH trajectory, replacement timing, capacity/power fade | ✅ Task 2B |
| **Dispatch Optimizer** | Produce optimal charge/discharge schedules | Prices, load, solar, constraints, battery state | Dispatch schedule time-series | ⏳ Task 3 |
| **Financial Layer** | Lifetime economics from simulated + degraded results | Simulator outputs, SoH trajectory, cost assumptions | NPV, IRR, LCOS, cash flows | ⏳ Task 4 |

---

## 2. SoC Simulator (Task 2A)

### 2.1 Responsibility

Given a dispatch schedule and system parameters, simulate the physical behavior of the BESS at each time step. This is a **stateless-per-call, stateful-per-timestep** model: you pass in the full dispatch schedule and get back the full time-series result.

### 2.2 Interface

```python
class BESSSimulator:
    """Forward simulation of BESS physical behavior."""

    def __init__(self, config: BESSConfig):
        """Initialize with system configuration."""
        ...

    def simulate(
        self,
        dispatch: pd.DataFrame,      # columns: timestamp, p_cmd_kw
        solar: pd.DataFrame = None,   # columns: timestamp, p_pv_kw (for hybrid)
        load: pd.DataFrame = None,    # columns: timestamp, p_load_kw (for BTM)
        ambient_temp: pd.Series = None,
    ) -> SimulationResult:
        """Run forward simulation over the dispatch schedule."""
        ...
```

### 2.3 Configuration Object

```python
@dataclass
class BESSConfig:
    # Nameplate
    energy_capacity_kwh: float
    power_charge_kw: float
    power_discharge_kw: float
    rte_pct: float                    # Round-trip efficiency (AC-AC)

    # Operating limits
    soc_min_pct: float = 5.0
    soc_max_pct: float = 95.0
    soc_initial_pct: float = 50.0

    # Efficiency (optional refinement)
    charge_efficiency_pct: float = None   # Derived from rte if not set
    discharge_efficiency_pct: float = None
    inverter_efficiency_pct: float = None  # Flat or curve
    aux_power_kw: float = 0.0

    # Topology
    topology: Topology = Topology.STANDALONE  # STANDALONE | AC_COUPLED | DC_COUPLED
    inverter_capacity_kw: float = None        # For DC-coupled shared inverter

    # Time resolution
    interval_minutes: int = 30

    # Chemistry (used by degradation engine)
    chemistry: Chemistry = Chemistry.LFP  # LFP | NMC | GENERIC
```

### 2.4 Result Object

```python
@dataclass
class SimulationResult:
    timeseries: pd.DataFrame
    # Columns: timestamp, soc_pct, p_batt_dc_kw, p_batt_ac_kw,
    #          p_inv_loss_kw, p_aux_kw, e_charged_kwh, e_discharged_kwh,
    #          p_import_kw, p_export_kw, p_clipped_captured_kw

    summary: dict
    # Keys: total_throughput_mwh, equivalent_full_cycles, actual_rte_pct,
    #        capacity_utilization_pct, hours_of_operation

    # Validation
    warnings: list[str]               # Constraint violations, clipping events
    dispatch_fidelity: pd.DataFrame   # Commanded vs. actual dispatch
```

### 2.5 State Transition Logic

<!-- Describe the per-timestep SoC update equation -->
<!-- SoC(t+1) = SoC(t) + (P_ch * η_ch - P_dis / η_dis) * Δt / E_nom -->
<!-- Constraint enforcement: SoC bounds, power limits, ramp rates -->
<!-- Derating logic: SoC-dependent, temperature-dependent -->

### 2.6 Topology Variants

<!-- How DC-coupled differs from AC-coupled in the simulation -->
<!-- Inverter clipping capture logic -->
<!-- Shared vs. separate inverter modeling -->

---

## 3. Degradation Engine (Task 2B)

### 3.1 Responsibility

Given an operating history (from the simulator), project the battery's state-of-health over time. Can run in two modes:
1. **Post-hoc analysis:** Given a completed simulation, compute degradation
2. **Coupled multi-year:** Step through year-by-year, updating usable capacity between years

### 3.2 Interface

```python
class DegradationEngine:
    """Battery degradation and state-of-health tracking."""

    def __init__(self, config: DegradationConfig):
        ...

    def compute_degradation(
        self,
        operating_history: SimulationResult,
        duration_years: float = 1.0,
    ) -> DegradationResult:
        """Compute degradation from an operating history."""
        ...

    def project_lifetime(
        self,
        simulator: BESSSimulator,
        dispatch: pd.DataFrame,
        project_years: int = 25,
        replacement_threshold_pct: float = 70.0,
    ) -> LifetimeResult:
        """Multi-year projection coupling simulation and degradation."""
        ...
```

### 3.3 Configuration

```python
@dataclass
class DegradationConfig:
    chemistry: Chemistry
    model_type: DegradationModel = DegradationModel.EMPIRICAL
    # EMPIRICAL (calendar + cycle tables, SAM-style)
    # NMC_BUILTIN (SAM's Li-ion NMC/Graphite model)
    # LFP_BUILTIN (adapted LFP model)

    # Calendar degradation
    calendar_model: CalendarModel = CalendarModel.EMPIRICAL
    # NONE | EMPIRICAL (time + temp + SoC) | CUSTOM_TABLE

    # Cycle degradation
    cycle_model: CycleModel = CycleModel.RAINFLOW
    # RAINFLOW (DoD-dependent) | SIMPLE_COUNTING

    # Chemistry-specific parameter sets loaded from config files
    calendar_params: dict = None
    cycle_fade_table: pd.DataFrame = None  # DoD vs. cycles vs. capacity
```

### 3.4 Degradation Combination Logic

<!-- SAM approach: min(calendar, cycle) for generic; sum for NMC/LFP built-in -->
<!-- Configurable per chemistry -->
<!-- Reference the SAM battery life documentation -->

### 3.5 Rainflow Counting

<!-- Brief description of rainflow algorithm for cycle extraction -->
<!-- DoD binning approach -->
<!-- Mapping to capacity fade curves -->

---

## 4. Dispatch Optimizer (Task 3 — Architecture Only)

### 4.1 Responsibility

Given prices, constraints, and current battery state, produce an optimal dispatch schedule. Formulated as LP/MILP/convex optimization.

### 4.2 Proposed Interface

```python
class DispatchOptimizer:
    """Optimal dispatch schedule generation."""

    def __init__(self, config: OptimizerConfig):
        ...

    def optimize(
        self,
        prices: pd.DataFrame,        # Energy prices or tariff signals
        solar: pd.DataFrame = None,
        load: pd.DataFrame = None,
        battery_state: BatteryState = None,  # Current SoC, SoH
        horizon_hours: int = 24,
    ) -> DispatchSchedule:
        ...
```

### 4.3 Optimization Formulation (Sketch)

<!-- Objective: minimize cost or maximize revenue -->
<!-- Decision variables: P_ch(t), P_dis(t), SoC(t) -->
<!-- Constraints: SoC continuity, power limits, SoC bounds, energy balance -->
<!-- Degradation-aware: throughput limits, DoD penalties -->
<!-- Solver: cvxpy or Pyomo -->

### 4.4 Use Cases

<!-- BTM: TOU tariff + demand charges + solar + load -->
<!-- FTM: Wholesale price arbitrage -->

---

## 5. Financial Layer (Task 4 — Architecture Only)

### 5.1 Responsibility

Post-processing wrapper that takes simulator + degradation outputs and applies financial assumptions to produce lifetime economics.

### 5.2 Proposed Interface

```python
class FinancialModel:
    """Lifetime financial analysis for BESS / solar+BESS."""

    def __init__(self, config: FinancialConfig):
        ...

    def analyze(
        self,
        lifetime_result: LifetimeResult,
        cost_assumptions: CostAssumptions,
    ) -> FinancialResult:
        ...
```

### 5.3 Key Capabilities (Deferred)

<!-- NPV, IRR, LCOS, LCOE, payback -->
<!-- Revenue stacking -->
<!-- Replacement cost modeling -->
<!-- Rate escalation, discount rate sensitivity -->
<!-- Actual-vs-predicted financial comparison -->

---

## 6. DUET Integration Points

### 6.1 PV Generation Pipeline

<!-- How the BESS module receives solar generation profiles from DUET -->
<!-- Time-series format alignment -->
<!-- Resolution matching -->

### 6.2 Model-vs-Actual Extension

<!-- How DUET's existing comparison framework extends to storage -->
<!-- Measured BESS data ingestion (SoC, power, energy) -->
<!-- Comparison metrics for storage: SoC trajectory error, throughput error, degradation tracking -->

**Pending:** DUET entity-relationship diagram / data model (requested from Enurgen)

### 6.3 Configuration Management

<!-- How battery system configurations are stored and versioned -->
<!-- Chemistry parameter sets -->
<!-- Relationship to DUET's existing project/site/scenario hierarchy -->

---

## 7. Data Contracts

### 7.1 Dispatch Schedule Format

```
timestamp (ISO 8601, tz-aware) | p_cmd_kw (float, + = discharge)
```

### 7.2 Simulation Output Format

<!-- Reference io_spec.md Section 3 -->

### 7.3 Degradation Output Format

<!-- Reference io_spec.md Section 4 -->

### 7.4 Time-Series Conventions

| Convention | Value |
|-----------|-------|
| Index | DatetimeIndex, tz-aware |
| Interval semantics | Start-of-interval |
| Resolution | Configurable (5/15/30/60 min) |
| Missing data handling | Raise error (don't interpolate silently) |

---

## 8. Configuration Patterns

### 8.1 Chemistry Parameterization

<!-- How different chemistries (LFP, NMC) are configured -->
<!-- Parameter files / config objects -->
<!-- Extensibility to new chemistries -->

### 8.2 System Topologies

<!-- Standalone, AC-coupled, DC-coupled -->
<!-- How topology choice affects simulation flow -->

### 8.3 Use Case Presets

<!-- Common configurations: utility-scale FTM, C&I BTM, residential, hybrid solar+BESS -->
<!-- Sensible defaults for each -->

---

## 9. Technology Stack

| Component | Recommendation | Notes |
|-----------|---------------|-------|
| Core simulation | numpy, pandas | Performance-critical inner loops in numpy |
| Degradation | numpy, scipy (rainflow) | Rainflow counting may use `rainflow` package |
| Optimization (Task 3) | cvxpy | Convex optimization; LP/MILP via CBC or HiGHS |
| Data serialization | Parquet / CSV | Parquet for large time-series, CSV for config |
| Configuration | dataclasses + YAML | System configs in YAML, loaded into dataclasses |
| Testing | pytest | |
| Documentation | Markdown + docstrings | |

---

## 10. Open Questions

<!-- Track decisions that need input from Enurgen -->

| # | Question | Status | Notes |
|---|----------|--------|-------|
| 1 | DUET data model / ERD | Requested | Need to understand existing entity structure |
| 2 | Time resolution in DUET | TBD | What resolution does DUET's PV model use? |
| 3 | Measured BESS data format | TBD | What format do Enurgen's partners provide field data in? |
| 4 | Python version / dependency constraints | TBD | Any DUET platform constraints? |
| 5 | Preferred config format | TBD | YAML? JSON? Python dataclasses? |
