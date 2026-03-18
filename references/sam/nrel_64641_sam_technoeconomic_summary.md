# NREL — Technoeconomic Modeling of Battery Energy Storage in SAM

**Source:** NREL/TP-6A20-64641, Technical Report  
**Authors:** Nicholas DiOrio, Aron Dobos, Steven Janzou, Austin Nelson, Blake Lundstrom (NREL)  
**Date:** September 2015  
**File:** `64641_-_Technoeconomic_Modeling_of_Battery_Energy_Storage_in_SAM.pdf`

---

## Paper Summary

This is the **reference manual for SAM's battery storage model** — the software architecture document that describes how SAM simulates battery performance coupled with PV systems. Where the companion paper (NREL/CP-5400-67102, Smith et al. 2017) covers the degradation model specifically, this report covers the full simulation stack: capacity model, voltage model, thermal model, lifetime/cycle-counting model, dispatch controller, and economic analysis. It also includes hardware validation results.

This is the most directly relevant architectural reference for DUET's Task 2A (simulation engine) because it documents a complete, validated, open-source BESS simulation pipeline — from cell-level electrochemistry to system-level financial outputs.

---

## SAM Battery Model Architecture

SAM's battery model is structured as a pipeline of coupled sub-models. The key design choice is that **all inputs should be derivable from manufacturer datasheets** — no lab characterization required for basic use.

### System Configuration

SAM assumes an **AC-coupled** battery connected through a bidirectional power converter, in parallel with the load, grid, and PV system. Power conversion is modeled as two single-point efficiencies:

```
I_in  = I × η_ACDC    (charging: AC→DC efficiency)
I_out = I × η_DCAC    (discharging: DC→AC efficiency)
```

The battery bank is built from cells: series connections increase voltage, parallel strings increase capacity. The user specifies either desired bank capacity/voltage or explicit series/parallel cell counts.

### Sub-Model Pipeline

```
Dispatch Controller → Capacity Model → Voltage Model → Thermal Model → Lifetime Model → Economics
         ↑                                                    |
         └────────────────── feedback ─────────────────────────┘
```

Each sub-model feeds the next, with the lifetime model feeding back to modify maximum capacity over time, and the thermal model feeding back to modify instantaneous capacity.

---

## 1. Voltage Model (Generic, Both Chemistries)

Based on the Tremblay-Dessaint dynamic voltage model — a generalized Shepherd equation applicable to both lead-acid and Li-ion:

```
V = V₀ - K·(q_max/(q_max - q_removed)) + a·exp(-B·q_removed) - R·I
```

| Parameter | Description | Source |
|---|---|---|
| V₀ | Battery constant voltage | Computed from datasheet |
| K | Polarization voltage | Computed from datasheet |
| a | Exponential zone amplitude (V) | V_full - V_exp |
| B | Exponential zone time constant inverse (Ah⁻¹) | 3/q_exp |
| R | Internal resistance (Ω) | From datasheet |
| I | Battery current (A) | From dispatch controller |

### Parameter Determination from Datasheets

All voltage model parameters are extracted from a single **voltage-vs-discharge curve** at a known C-rate. Required data points:

- q_full: fully charged cell capacity (Ah)
- V_full: fully charged voltage (V)
- V_exp: voltage at end of exponential zone (V)
- V_nom: voltage at end of nominal zone (V)
- q_exp,%: percent capacity removed at end of exponential zone
- q_nom,%: percent capacity removed at end of nominal zone

This is a critical design decision for DUET — the voltage model can be parameterized from standard datasheet information without specialized testing.

### Voltage Losses and Round-Trip Efficiency

The model naturally captures voltage-based losses: during charging, terminal voltage rises (requiring more power input); during discharging, terminal voltage drops (delivering less power output). Round-trip efficiency is computed as:

```
η = 100 × (E_discharged / E_charged)
```

The report shows an example Li-ion cell achieving **97.4% DC-side round-trip efficiency** at moderate C-rates (Figure 4). This is the voltage-only efficiency; total system RTE includes converter losses (η_ACDC × η_DCAC).

### Model Limitations

- Becomes undefined at very low SOC (<1%) — returns half nominal voltage as fallback
- Overcharge capped at 125% of full cell voltage
- Does not directly model temperature effects on voltage (temperature impacts are handled indirectly through capacity)

---

## 2. Thermal Model

A lumped-parameter energy balance:

```
m·Cp·(dT_batt/dt) = h·A·(T_room - T_batt) + I²·R
```

| Input | Units | Description |
|---|---|---|
| m | kg | Battery mass |
| Cp | J/(kg·K) | Specific heat capacity |
| h | W/(m²·K) | Heat transfer coefficient |
| A | m² | Battery surface area |
| T_room | K | Storage room temperature (user-specified, fixed) |
| R | Ω | Internal resistance |

Solved using the **trapezoidal method** (unconditionally stable, second-order).

The thermal model's output (battery temperature) modifies capacity via a user-provided **capacity-vs-temperature lookup table**. This lookup table is a percentage modifier applied to the charge in the battery.

**Key limitation:** The thermal model assumes a **conditioned room at fixed temperature** — no ambient weather exposure. The report acknowledges this as a simplification; real outdoor installations would need a more detailed thermal model.

### Relevance to DUET

The thermal model is deliberately simple — a single lumped mass with convective heat transfer to a fixed-temperature room. For DUET's PoC this is probably sufficient, but the architecture should allow swapping in a more detailed thermal model later (e.g., multi-node with HVAC system modeling, ambient weather coupling).

---

## 3. Capacity Models (Chemistry-Specific)

### Lead-Acid: Kinetic Battery Model (KiBaM)

Lead-acid batteries have rate-dependent capacity due to bound vs. available charge. SAM uses the Manwell-McGowan KiBaM, which tracks two charge pools:

- **Available charge** (q₁): immediately usable
- **Bound charge** (q₂): must become available through diffusion before use
- Rate constant k and capacity ratio c determine the interplay

KiBaM requires capacities at three different discharge rates (typically 1h, 10h, 20h) to parameterize. SAM provides defaults based on chemistry sub-type (Flooded, VRLA-Gel, VRLA-AGM) from the HOMER database.

**Not relevant to DUET** — Enurgen's BESS targets are Li-ion, not lead-acid. But the KiBaM architecture shows how SAM handles chemistry-specific capacity sub-models behind a common interface.

### Lithium-Ion: Simple Tank-of-Charge

Li-ion batteries can charge/discharge rapidly enough that rate-dependent capacity effects are negligible for system-level simulation. SAM uses a simple coulomb-counting model:

```
q(t+Δt) = q(t) - I·Δt
```

Constrained by user-specified minimum and maximum SOC limits and maximum charge/discharge C-rates. Capacity relates to energy through voltage (E = q × V), and power through time (P = E/Δt).

**Default Li-ion chemistries** provided in SAM with pre-populated voltage curve and lifetime defaults:
- NMC (Nickel Manganese Cobalt) / graphite
- NCA (Nickel Cobalt Aluminum) / graphite
- LMO (Lithium Manganese Oxide) / graphite
- LFP (Lithium Iron Phosphate) / graphite
- LCO (Lithium Cobalt Oxide) / graphite
- LMO / LTO (Lithium Titanate)

Changing chemistry type only changes default parameter values — the underlying equations remain the same. This is exactly the pattern DUET should follow.

---

## 4. Lifetime Model (Rainflow Cycle Counting)

SAM uses a **rainflow counting algorithm** (Downing-Socie method, per ASTM E1049) to distill complex, irregular charge/discharge histories into a series of constant-amplitude cycles. This is coupled with manufacturer-provided degradation curves.

### User Inputs

The user provides a table mapping (DoD, cycle count) → remaining capacity %. Example:

| DoD (%) | Cycles Elapsed | Remaining Capacity (%) |
|---|---|---|
| 20 | 0 | 100 |
| 20 | 650 | 96 |
| 20 | 1500 | 87 |
| 80 | 0 | 100 |
| 80 | 150 | 96 |
| 80 | 300 | 87 |

At each completed cycle (identified by rainflow counting), the model interpolates this table at the current cycle count and average DoD to determine the new maximum capacity.

### Handling Sparse Data

The report acknowledges that many datasheets only report degradation at a single DoD. It suggests a rule-of-thumb: if only one DoD curve is available (assumed to be 80%), generate a second data point at 20% DoD by multiplying the cycle count by 5 for the same capacity degradation. This is explicitly called out as an approximation.

### Key Design Decisions

- **Lifetime losses only applied when a new cycle completes** — not continuously
- **End-of-life threshold** is configurable (default 80% remaining capacity, consistent with academic literature)
- **Calendar aging is NOT modeled** in this version of SAM's lifetime model — only cycle-based degradation

### Relevance to DUET

This is where SAM's 2015 model is weakest compared to the Smith et al. 2017 degradation model (which was added to SAM later). The 2015 version:
- Uses manufacturer curves as lookup tables rather than physics-based equations
- Has no calendar aging — major gap for systems that sit idle
- Relies on the user to provide degradation data at multiple DoD levels

DUET's Task 2B should implement the Smith et al. semi-empirical model (from the companion paper) rather than this simpler lookup approach. However, the **rainflow counting** component from this paper is valuable and should be integrated — the Smith model uses DOD_max as a scalar, whereas rainflow counting gives per-cycle DoD values.

---

## 5. Dispatch Controller

SAM implements a **manual dispatch strategy** with user-configurable profiles scheduled by month and hour-of-day. Each profile specifies:

- Whether to allow charging from PV
- Whether to allow charging from grid
- Whether to allow discharging
- Percent of available capacity to discharge per timestep

### Dispatch Algorithm Logic

```
1. Compute battery energy available and needed
2. Compare PV power vs. Load
3. If PV > Load:
   - If charging from PV allowed → dump excess to battery
   - If grid charging allowed → draw additional from grid to fill
4. If Load > PV:
   - If discharging allowed → discharge to meet deficit
   - If grid charging allowed → recharge from grid after reaching min SOC
5. Apply constraints:
   - SOC limits (min/max)
   - Oscillation prevention (minimum time at charge state before switching)
   - Current limits (max charge/discharge C-rate)
6. Dispatch battery at computed power
```

### Controllers Stack

Three constraint controllers layer on top of the dispatch decision:

1. **SOC Controller** — enforces min/max SOC limits, computes max energy per timestep
2. **Switching Controller** — prevents rapid charge/discharge oscillation at sub-hourly timesteps (user-specified minimum dwell time)
3. **Current Controller** — enforces max charge/discharge C-rates

### Relevance to DUET

DUET's Task 2A simulator takes a dispatch schedule as input (simulation ≠ optimization, per CLAUDE.md design principle #1). SAM's dispatch controller is the inverse: it decides what to do. But the **constraint enforcement logic** (SOC limits, C-rate limits, switching protection) is exactly what DUET's simulator needs to validate dispatch schedules against physical limits. The simulator should reject or clip dispatch commands that violate these constraints.

---

## 6. Battery Economics

SAM runs a **multi-year simulation** (typically 25 years) rather than extrapolating from year 1. This captures:

- Variable battery replacement timing (depends on cycling behavior)
- Replacement costs (user-specified $/kWh, with escalation schedule)
- Battery capacity resets to 100% upon replacement

The financial model computes NPV across three scenarios: No System, PV Only, PV+Battery. Key cost categories: energy charges, demand charges (TOU), capital + replacement costs, O&M.

### Example Result (from the paper)

Over 25 years with a Li-ion battery fading to 20% capacity by year ~10:
- Battery replaced twice over the analysis period
- PV+Battery reduces energy charges vs. PV-only
- But capital + replacement costs ($20,309 vs. $12,747 for PV-only) make the system economically unfavorable in the example scenario

### Relevance to DUET

Financial post-processing is Task 4 (out of scope for current contract), but the architecture insight matters: the simulation engine (Task 2A) must be able to run multi-year simulations efficiently. If each timestep is 1-minute resolution over 25 years, that's ~13M timesteps. The state-variable formulation from Smith et al. enables this — but DUET's engine should be designed with this computational scale in mind.

---

## 7. Validation Results

### Software Comparison: SAM vs. HOMER

| Metric | SAM (Full) | SAM (Reduced) | HOMER |
|---|---|---|---|
| Energy to charge (kWh) | 297.20 | 393.17 | 383.59 |
| Energy discharged (kWh) | 260.90 | 347.88 | 338.56 |
| Battery efficiency (%) | 87.79 | 88.48 | 88.26 |

The full SAM model predicts ~23% less energy throughput than HOMER due to SAM's more detailed loss models (thermal, lifetime). When thermal and lifetime models are disabled ("reduced"), SAM comes within 3% of HOMER. SOC RMSE between models: 8.62%.

### Software Comparison: SAM vs. PV*SOL

Key energy quantities differ by <5% between models. Net battery energy to load differs by only 0.3%. Minor differences attributed to charge controller behavior at SOC extremes.

### Hardware Validation: Lead-Acid (OutBack Radian + EnergyCell 200RE)

Tested against three 4-hour profiles (steady oscillation, high variability, afternoon peak):

| Test | SOC RMSE (%) | Current RMSE (A) | Voltage RMSE (V) | Power RMSE (W) | Temp RMSE (°C) |
|---|---|---|---|---|---|
| Steady | 3.76 | 6.12 | 3.78 | 249.86 | 7.85 |
| Variability | 0.82 | 7.74 | 2.65 | 397.53 | 1.97 |
| Afternoon | 1.47 | 7.05 | 3.76 | 325.36 | 0.52 |

SOC predicted within 4% RMSE across all tests.

### Hardware Validation: Li-ion (OutBack Radian + Enerdel EC4S6P)

| Test | SOC RMSE (%) | Current RMSE (A) | Voltage RMSE (V) | Power RMSE (W) | Temp RMSE (°C) |
|---|---|---|---|---|---|
| Steady | 3.93 | 20.91 | 2.29 | 1119.75 | 2.08 |
| Variability | 2.80 | 9.04 | 2.30 | 526.15 | 1.32 |
| Peak | 8.89 | 9.43 | 3.31 | 460.25 | 1.04 |

SOC within 9% RMSE. Higher current/power RMSE in steady oscillation test due to timing differences in recharge cycle initiation — a dispatch controller alignment issue, not a battery model issue.

### Standalone Discharge Tests

Both lead-acid (3300 W) and Li-ion (3200 W) constant-power discharge tests showed **<1% SOC RMSE** — validating that the core capacity and voltage models track well when dispatch controller differences are eliminated.

---

## Implications for DUET BESS Module

### For Task 1 — Landscape Survey (SAM Section)

SAM's battery model should be characterized in the survey as:

**What it is:** A complete, open-source, validated technoeconomic simulation framework coupling battery performance models (voltage, thermal, capacity, lifetime) with dispatch controllers and financial analysis. AC-coupled PV+storage focus.

**What it does well:**
- Parameterizable from manufacturer datasheets (no lab testing needed)
- Multiple Li-ion chemistry defaults (NMC, NCA, LFP, LMO, LCO, LMO/LTO)
- Rainflow cycle counting for realistic dispatch profiles
- Validated against hardware (<4% SOC RMSE for lead-acid, <9% for Li-ion)
- Multi-year simulation with battery replacement economics
- Open-source (C++/Python via PySAM)

**What it doesn't do well (as of 2015 report):**
- No calendar aging in the lifetime model (added later via Smith et al. 2017)
- Thermal model is very simple (single lumped mass, fixed room temperature)
- Voltage model doesn't directly capture temperature effects
- No cell-to-cell variation / string imbalance modeling
- Dispatch is manual schedules only (no optimization)

### For Task 1 — I/O Spec

SAM's input requirements define a useful baseline for "minimum viable datasheet inputs":

**Battery Cell Parameters (from datasheet):**
- Nominal capacity (Ah) at a known C-rate
- Voltage discharge curve: V_full, V_exp, V_nom, q_exp,%, q_nom,%
- Internal resistance (Ω)
- Max charge/discharge C-rates

**Battery Bank Configuration:**
- Cells in series, strings in parallel (or desired bank voltage/capacity)
- AC/DC and DC/AC converter efficiencies

**Thermal Properties:**
- Mass per kWh, surface area per kWh
- Specific heat capacity
- Heat transfer coefficient
- Room/ambient temperature

**Lifetime Data:**
- Capacity vs. cycles at one or more DoD levels
- Replacement threshold (% remaining capacity)

**Dispatch Schedule:**
- Hourly/monthly profile: charge from PV, charge from grid, allow discharge, % capacity per timestep
- Min/max SOC limits
- Min dwell time (switching protection)

### For Task 2A — Simulation Engine Architecture

SAM's architecture provides a validated reference for DUET's simulation engine design:

1. **Sub-model pipeline with feedback** — capacity → voltage → thermal → lifetime, with lifetime feeding back to capacity. DUET should follow this pattern.

2. **Chemistry abstraction** — changing chemistry changes defaults, not equations. DUET should implement a `CellChemistry` configuration object that populates model parameters.

3. **Constraint enforcement layer** — SOC limits, C-rate limits, oscillation protection applied after dispatch decision. DUET's simulator should validate/clip dispatch commands against these constraints before simulating each timestep.

4. **Datasheet-parameterizable** — SAM's explicit design goal. DUET should adopt the same principle: all required inputs should be available from a standard battery datasheet + system configuration spec.

5. **Simple Li-ion capacity model (coulomb counting)** is sufficient for system-level simulation. The complex capacity models (KiBaM) are only needed for lead-acid.

### For Task 2B — Degradation

SAM's 2015 lifetime model (lookup table + rainflow counting) is simpler than the Smith et al. 2017 model. DUET should implement the Smith model for physics-based degradation prediction, but **use SAM's rainflow counting approach** to properly handle partial cycles in real dispatch profiles. The combination — Smith's degradation equations driven by rainflow-extracted cycle parameters — is stronger than either alone.

### Key Validation Numbers to Reference

- SAM vs. HOMER: within 3% on energy throughput (with matched features)
- SAM vs. PV*SOL: within 5% on energy quantities, <1% on net battery-to-load
- SAM vs. hardware (Li-ion discharge): <1% SOC RMSE
- SAM vs. hardware (Li-ion dispatch): <9% SOC RMSE (dominated by controller mismatch)
- DC-side round-trip efficiency example: 97.4% at moderate C-rate
