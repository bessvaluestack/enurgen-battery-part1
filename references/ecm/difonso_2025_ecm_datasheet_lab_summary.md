# Data-Driven ECM Modeling from Manufacturer Specifications and Laboratory Measurements

**Source:** IEEE Transactions on Industry Applications, Vol. 61, No. 2, March/April 2025  
**Authors:** Roberta Di Fonso, Carlo Cecati, Remus Teodorescu, Daniel-Ioan Stroe, Pallavi Bharadwaj  
**Published:** 21 January 2025  
**DOI:** `10.1109/TIA.2025.3532572`  
**File:** `Fonso2025-Data-Driven_Modeling_of_Li-Ion_Battery_Based_on_the_Manufacturer_Specifications_and_Laboratory_Measurements.pdf`  
**Funding:** Villum Foundation (SMART BATTERY project, Grant 222860)

---

## Paper Summary

This paper presents a **step-by-step methodology for building equivalent circuit models (ECMs) of Li-ion batteries at three escalating tiers of data availability**: (1) from manufacturer datasheets alone, (2) from customized laboratory measurements, and (3) with aging-state awareness using publicly available degradation datasets (NASA, Oxford). The approach uses Matlab/Simulink's Datasheet Battery Block and Equivalent Circuit Battery Block as implementation platforms, but the parameterization methodology is general.

**Key value for DUET:** This is the most explicit published treatment of the *process* of going from a manufacturer datasheet to a working battery simulation model — exactly the workflow DUET's "datasheet-parameterizable by default" principle requires. It also demonstrates how the same ECM framework can be progressively enhanced as more data becomes available (lab measurements, aging data), which maps directly onto DUET's model tiering strategy. The aging-aware ECM variant (Tier 3 in the paper) shows how ECM parameters (OCV, R₀, R₁–R₃, C₁–C₃) evolve as functions of SOC, temperature, *and SOH* — making it the closest published reference for an ECM that tracks degradation effects on instantaneous performance.

---

## ECM Structure

The paper uses a first-order RC equivalent circuit (Fig. 1 in the paper) as the baseline model:

```
V(t) = OCV(SOC, T) − I(t)·R₀(SOC, T) − V_RC(t)
```

Where V_RC is the voltage across the parallel R₁–C₁ branch, representing charge-transfer and double-layer dynamics. All parameters depend on SOC and temperature:

| Element | Physical Interpretation |
|---|---|
| OCV(SOC, T) | Open-circuit voltage — main nonlinear element |
| R₀(SOC, T) | Electrolyte (Ohmic) resistance — immediate voltage drop |
| R₁(SOC, T) | Charge-transfer resistance at electrode-electrolyte interface |
| C₁(SOC, T) | Double-layer capacitance at electrode surface |

For the advanced model, N = 3 RC pairs are used (R₁C₁, R₂C₂, R₃C₃), capturing multiple time constants from fast electrode kinetics to slow diffusion processes. The paper shows that R₃ and C₃ (the slowest pair) have the largest impact on voltage output accuracy.

---

## Three-Tier Parameterization Methodology

### Tier 1: Datasheet-Only Model

**Data source:** Manufacturer-published discharge curves (voltage vs. capacity at different C-rates and temperatures).

**Procedure:**

1. **Import raw data** from datasheets using semi-automatic digitization (WebPlotDigitizer or equivalent).
2. **Resample and synchronize** curves to 101 uniformly-spaced points using interpolation (Matlab `interp1`). Raw digitized curves have non-uniform sampling and are not synchronous across C-rates.
3. **Extract OCV curve** by fitting a voltage surface over (DoD, C-rate) and extrapolating to zero current. The surface is built from curves at multiple C-rates at a single temperature (23°C in the paper's example with A123 LFP cells at 1C, 5C, 20C). Extrapolation uses spline method (`interp2` with spline extrapolation).
4. **Compute internal resistance** from the difference between OCV and loaded voltage at each SOC point:

```
R₀(SOC, T) = [OCV(SOC) − V(SOC, T)] / I_discharge
```

5. **Populate look-up tables** for OCV(SOC, T) and R₀(SOC, T) as the block's configuration.

**Limitations of Tier 1:**

- OCV can only be computed at the single temperature where multiple C-rate curves are provided (23°C in the A123 example). Temperature dependence of OCV is not captured — only R₀ varies with T.
- At very low SOC (< 10%) and low temperatures, the computed R₀ shows anomalous behavior (can go negative) because the OCV extrapolation is inaccurate in the steep end-of-discharge region. Workaround: hold R₀ constant for SOC ≤ 10%.
- The C-rate range in manufacturer datasheets may not cover the operating range of interest (datasheets often show only 2–3 C-rates).
- No standard procedure exists across manufacturers — every company's datasheet uses different C-rates, temperatures, and presentation formats.

**Accuracy:** Relative error ≤ 2.8% for 10% ≤ SOC ≤ 100%.

### Tier 2: Laboratory-Enhanced Model

**Data source:** Controlled laboratory discharge tests at a wider matrix of conditions than the datasheet provides.

**Test matrix (A123 LFP cells):**
- C-rates: 0.25C, 0.5C, 1C, 2C, 3C, 4C (vs. only 1C, 5C, 20C from the datasheet)
- Temperatures: 15°C, 25°C, 35°C, 45°C (vs. only 0°C, 23°C, 45°C from the datasheet)
- CC-CV charge protocol, CC discharge, with 1-hour OCV rest period before each test
- Cell temperature measured via thermocouple in a climate chamber

**Advantages over Tier 1:**
1. Data specific to the selected battery cell (not manufacturer averages)
2. C-rates and temperatures customizable to the application's operating range
3. Finer resolution: 6 C-rates × 4 temperatures = 24 operating points vs. ~6 from the datasheet
4. Can include dynamic behavior and cycling aging tests

**Parameterization procedure:** Same as Tier 1 (surface fitting, OCV extraction, R₀ computation), but with denser data.

**Key finding:** The internal resistance surface from lab data (Fig. 10 in the paper) is much smoother and more physically consistent than from datasheet data (Fig. 9), especially at temperature extremes. Both show the expected trend: resistance increases as temperature decreases.

**Accuracy:** Relative error ≤ 1.0% for 10% ≤ SOC ≤ 100%. A 2.8× improvement over Tier 1.

### Tier 3: Aging-Aware ECM

**Data source:** Pulsed discharge sequences at multiple SOH levels.

**Procedure:**
1. Use pulsed discharge data (current pulse + relaxation period at each SOC level).
2. For each SOH level, fit the N-RC ECM parameters by performing curve fitting on the pulse relaxation intervals.
3. Build three-dimensional look-up tables: each ECM parameter as a function of (SOC, SOH). Example: OCV(SOC, SOH), R₀(SOC, SOH), R₃(SOC, SOH), C₃(SOC, SOH).
4. SOH becomes an additional input to the battery model. The model can either simulate a battery at a fixed age or accept a degradation curve as a time-varying input.

**Data requirements for pulse identification:**
- Sample rate: minimum 1 Hz (ideal: 10 Hz)
- Voltage accuracy: ±5 mV (ideal: ±1 mV)
- Current accuracy: ±100 mA (ideal: ±10 mA)
- SOC change per pulse: ≤ 5%
- Sufficient relaxation time after each pulse (steady-state approach)

**Datasets used:**
- NASA Ames Prognostics Data Repository: 21 pulsed discharge sequences at different aging states for Li-ion cells (1A pulse for 10 min, 20 min rest, sampled at 1 Hz)
- Oxford University dataset (Raj 2021): Panasonic NCR18650BD NCA cells, pulse power characterization at SOH = 90%

**Key observations on parameter evolution with aging (Figs. 11–12):**
- OCV(SOC, SOH): the OCV curve shape is relatively stable across SOH values but shifts downward and compresses as capacity fades. The characteristic flat region (especially in LFP) shrinks.
- R₀(SOC, SOH): internal resistance increases with decreasing SOH — the expected trend. The increase is nonlinear, accelerating as SOH drops below ~0.6.
- R₃(SOC, SOH): the slowest RC pair's resistance shows the most dramatic increase with aging, particularly at low SOC. This captures the increasing difficulty of diffusion processes as electrode surfaces degrade.
- C₃(SOC, SOH): capacitance changes are less systematic than resistance changes, reflecting the complex interplay of surface area loss and film formation.

**Accuracy:** Relative error ≤ 0.4% for 10% ≤ SOC ≤ 100%. A 7× improvement over Tier 1.

---

## Validation on Alternative Datasets

The paper validates the Tier 3 procedure on Panasonic NCR18650BD NCA cells (3 Ah, widely used in EV packs) using the Oxford University dataset. Results confirm:

- OCV curve shape is consistent with published NCA characterization data
- R₀ profile matches experimental tests from the literature
- Relative error ≤ 0.4% — same accuracy as the NASA LFP dataset results

This cross-chemistry validation (LFP via NASA, NCA via Oxford) demonstrates the methodology is chemistry-agnostic, supporting DUET's chemistry-pluggable design principle.

---

## Accuracy Progression Summary

| Model Tier | Data Source | ECM Complexity | Relative Error | Improvement |
|---|---|---|---|---|
| 1 — Datasheet | Manufacturer curves | OCV + R₀ | ≤ 2.8% | Baseline |
| 2 — Lab enhanced | Controlled discharge tests | OCV + R₀ (denser) | ≤ 1.0% | 2.8× over Tier 1 |
| 3 — Aging-aware | Pulsed discharge at multiple SOH | OCV + R₀ + 3×RC, all f(SOH) | ≤ 0.4% | 7× over Tier 1 |

---

## Relationship to Other Models in the Repo

The ECM approach sits in a distinct position on the modeling spectrum:

| Dimension | Di Fonso ECM (this paper) | SAM Tremblay-Dessaint (64641) | NREL Semi-Empirical (67102) | PyBaMM DFN |
|---|---|---|---|---|
| **What it models** | Instantaneous voltage response | Instantaneous voltage response | Long-term degradation trajectory | Full electrochemical state |
| **Parameters from** | Datasheet / lab / aging data | Datasheet (6 values) | Aging test data (20+ Arrhenius) | Full characterization (30+) |
| **Tracks aging?** | Yes (Tier 3: ECM params as f(SOH)) | No (parameters fixed at BoL) | Yes (8 state variables for capacity + resistance over time) | Yes (degradation submodels) |
| **Time resolution** | Sub-second dynamics (RC transients) | Steady-state per timestep | Per-cycle or per-day | Sub-second (PDE solver) |
| **Predicts future aging?** | No — requires SOH as input | Only via lookup table | Yes — projects capacity and resistance trajectory | Yes — from first principles |

**The critical distinction:** The Di Fonso ECM captures how a battery *behaves at a given health state* with high accuracy (<0.4%), but does not predict *how that health state evolves over time*. The NREL model does the opposite: it predicts how capacity and resistance change over years, but uses simpler voltage/power relationships within each timestep. These are complementary, not competing.

### How They Compose in a Simulation Framework

```
                    ┌─────────────────────────────┐
                    │  Degradation Model           │
                    │  (NREL 67102 or equivalent)  │
                    │                              │
                    │  Inputs: T, SOC, DOD, N, t   │
                    │  Outputs: SOH_C, SOH_R       │
                    │  (capacity fade, R growth)    │
                    └──────────────┬────────────────┘
                                   │ SOH_C, SOH_R
                                   ▼
                    ┌─────────────────────────────┐
                    │  Performance Model (ECM)     │
                    │  (Di Fonso or SAM voltage)   │
                    │                              │
                    │  Inputs: I(t), T, SOC, SOH   │
                    │  Outputs: V(t), P(t), losses │
                    └─────────────────────────────┘
```

The degradation model updates SOH periodically (per cycle or per day). The ECM uses the current SOH to select the right parameter values for instantaneous voltage/power calculation at each sub-second or per-minute timestep. This is exactly the sub-model pipeline architecture described in SAM (DiOrio 2015) and targeted for DUET.

---

## Implications for DUET BESS Module

### For Task 1 — Landscape Survey

This paper fills a specific gap in the landscape survey: it documents the **parameterization workflow** rather than just the model equations. Where the NREL papers describe *what* equations to use and *what* parameters they need, Di Fonso describes *how* to actually get those parameters from real-world data sources.

The paper should be cited in:

- **Section 2.1 (Electrochemical Core):** as the most explicit published procedure for ECM parameterization from datasheets
- **Section 3.5 (SAM Architecture):** as evidence that the Tremblay-Dessaint voltage model (SAM) and ECM (Di Fonso) represent two approaches to the same sub-problem, with ECM offering higher accuracy when aging data is available
- **Section 4.3 (Model Tiering):** the paper's own three-tier progression (datasheet → lab → aging-aware) directly validates DUET's tiered model framework concept

### For Task 1 — I/O Spec

The paper provides concrete data requirements at each tier:

**Tier 1 (datasheet) minimum inputs:**
- Rated capacity (Ah) at nominal temperature
- Voltage vs. capacity curves at 2+ C-rates at a single temperature
- Voltage vs. capacity curves at 1 C-rate at 2+ temperatures

**Tier 2 (lab) recommended test matrix:**
- 4–6 C-rates spanning 0.25C to 4C
- 3–4 temperatures spanning 15°C to 45°C
- CC-CV charge protocol, CC discharge
- 1-hour OCV rest before each measurement

**Tier 3 (aging-aware) requirements:**
- Pulsed discharge sequences at multiple SOH levels
- ≥ 1 Hz sampling (10 Hz ideal)
- Voltage accuracy ± 5 mV
- Current accuracy ± 100 mA
- SOC step per pulse ≤ 5%

### For Task 2A — Simulation Engine

Key design decisions informed by this paper:

1. **The ECM is the right voltage model for DUET's PoC** — it bridges datasheets and lab data with a single parameterization framework. The 2.8% accuracy from datasheets alone is sufficient for system-level simulation; the < 0.4% accuracy with aging awareness is competitive with any commercial tool.

2. **Support three-dimensional parameter lookup: f(SOC, T, SOH).** The paper shows that ECM parameters change meaningfully with aging state. A voltage model that only uses f(SOC, T) parameters from BoL data will become increasingly inaccurate as the battery ages. The architecture should support the SOH dimension from Day 1, even if the PoC only populates it for one aging state.

3. **The OCV extraction procedure (surface fitting + zero-current extrapolation) is reusable.** DUET could implement this as a utility function: given a set of discharge curves at different C-rates, automatically extract the OCV curve. This is useful both for parameterization from datasheets and for processing lab data.

4. **R₀ behavior at SOC extremes needs special handling.** The paper documents anomalous R₀ values at SOC < 10% when computed from datasheet data. The recommended fix (hold R₀ constant below 10% SOC) should be implemented as a default, with the option to use lab-measured values when available.

### For Task 2B — Degradation Model

The paper does **not** provide a degradation prediction model — it requires SOH as an input rather than predicting it. However, the aging-aware ECM framework (Tier 3) is directly useful for Task 2B in two ways:

1. **Validation:** The aging-aware ECM provides ground-truth for how voltage response should change at a given SOH. If DUET's degradation model (NREL or alternative) predicts SOH_C = 85% and SOH_R = 120% (of BoL), the ECM parameterized at those health states should match the observed voltage behavior. Discrepancies indicate either the degradation model or the ECM is miscalibrated.

2. **Closing the loop:** The NREL degradation model outputs capacity fade (equivalent to SOH_C) and resistance growth (equivalent to SOH_R). The aging-aware ECM needs SOH as input to select the right parameter set. Together, they form a complete time-stepping simulation: degradation model updates SOH → ECM uses updated SOH for voltage calculation → voltage feeds back into dispatch constraints and thermal model.

### For Model-vs-Actual Comparison

The paper's accuracy numbers provide a useful **noise floor** for model-vs-actual comparison:

- If the model's voltage error is < 1% against lab data, then any observed mismatch > 2–3% against field SCADA data is likely a real physical anomaly (cell degradation, thermal issue, BMS error), not model error.
- The paper's clear progression (2.8% → 1.0% → 0.4%) shows that much of the model error at Tier 1 is systematic (incomplete parameterization), not random. This means model-vs-actual deviations that are spatially or temporally correlated are more likely to be real issues than random noise.

---

## Relationship to Other Reference Summaries

```
PARAMETERIZATION METHODOLOGY
═════════════════════════════

  Datasheet → ECM (this paper, Tier 1)          Datasheet → Voltage model (SAM/DiOrio 2015)
       ↓                                              ↓
  Lab data → ECM (this paper, Tier 2)           Aging tests → Degradation params (Smith 2017)
       ↓                                              ↓
  Aging data → ECM (this paper, Tier 3)         Physics characterization → DFN params (LiionDB/Wang 2022)
       ↓                                              ↓
  Result: instantaneous V(I, SOC, T, SOH)       Result: SOH trajectory over years
```

Both columns are needed for a complete simulation. This paper provides the left column; the NREL papers provide the right column. DUET's architecture must compose them.

### Cross-References Within the Repo

- **NREL 64641 (DiOrio 2015):** SAM's Tremblay-Dessaint voltage model is an alternative to the ECM for the same purpose (instantaneous voltage calculation). The ECM is more accurate when pulse data is available; the Tremblay-Dessaint model is simpler and parameterizable from fewer datasheet values. Both should be supported as voltage model options in DUET's framework.

- **NREL 67102 (Smith 2017):** The semi-empirical degradation model provides the SOH trajectory that the aging-aware ECM consumes. The 5-term resistance model in Smith 2017 predicts R growth; the ECM shows how that R growth manifests in terminal voltage at each operating point.

- **Gwayi 2025:** The 13-model empirical catalog covers degradation models (predicting capacity/resistance fade over time). The Di Fonso ECM is orthogonal — it models instantaneous electrical behavior, not long-term fade. But the empirical models' output (SOH over time) feeds the ECM's SOH input.

- **TWAICE (ESSRF 2023):** TWAICE's diagnostic approach (DCR measurement from current pulses at specific SOC levels) is precisely what generates the Tier 3 parameterization data. The pulse power characterization test (Fig. 14 in Di Fonso) is the same physical test that TWAICE uses for DCR trending. DUET could use periodic SCADA-derived pulse responses to update ECM parameters in the field — closing the model-vs-actual loop.

- **PyBaMM / LiionDB:** The DFN's 30+ parameters include solid-phase diffusion and electrolyte transport that the ECM implicitly lumps into its R and C elements. If DUET implements a PyBaMM validation mode, the ECM parameters can be derived from PyBaMM simulations rather than from lab data — this is a parameterization pathway worth noting in the architecture.
