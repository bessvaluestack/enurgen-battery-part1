# BESS Modeling Landscape Survey + Architecture Recommendations

**Task 1, Deliverable 1** | Status: Outline+Summary
**Audience:** Enurgen engineering team
**Feeds into:** `io_spec/io_spec.md`, `architecture/architecture.md`

---

## Glossary

- **Ah** — Ampere-hour
- **ASTM** — ASTM International
- **BESS** — Battery Energy Storage System
- **BMS** — Battery Management System
- **BoL** — Beginning of Life
- **C-rate** — Charge/discharge rate normalized by nominal capacity
- **CAOM / CYAOM / CCYASM / CCYACM** — Taxonomy labels used in the cited battery aging literature for classes of empirical and semi-empirical aging models
- **Cp** — Specific heat capacity
- **DCR** — Direct current resistance
- **DoD** — Depth of discharge
- **EKF** — Extended Kalman Filter
- **EMS** — Energy Management System
- **EOL** — End of life
- **EPC** — Engineering, Procurement, and Construction
- **FEC** — Full equivalent cycles
- **DFN / P2D** — Doyle-Fuller-Newman / pseudo-two-dimensional electrochemical model
- **HPPC** — Hybrid Pulse Power Characterization
- **I/O** — Input/output
- **LAM** — Loss of active material
- **LAM_NE** — Loss of active material in the negative electrode
- **LAM_PE** — Loss of active material in the positive electrode
- **LCO** — Lithium cobalt oxide
- **LFP** — Lithium iron phosphate
- **Li plating** — Metallic lithium plating on the anode during charge under adverse conditions
- **LLI** — Loss of lithium inventory
- **LMO** — Lithium manganese oxide
- **LTO** — Lithium titanate
- **ML** — Machine learning
- **MV** — Medium voltage
- **NCA** — Nickel cobalt aluminum oxide
- **NMC** — Nickel manganese cobalt oxide
- **NPV** — Net present value
- **OCV** — Open-circuit voltage
- **ODE** — Ordinary differential equation
- **PCS** — Power conversion system
- **PDE** — Partial differential equation
- **PyBaMM** — Python Battery Mathematical Modelling
- **Q_neg / Q_pos / Q_Li** — State variables in the NREL semi-empirical model representing negative-electrode capacity, positive-electrode capacity, and lithium inventory related capacity
- **R** — Resistance
- **RES** — Renewable energy system(s)
- **RMSE** — Root mean square error
- **RTE** — Round-trip efficiency
- **SAM** — System Advisor Model
- **SEI** — Solid electrolyte interphase
- **SOC** — State of charge
- **SOH** — State of health
- **SOH_C** — Capacity-based state of health
- **SOH_R** — Resistance-based state of health
- **SPM** — Single Particle Model
- **SPMe** — Single Particle Model with electrolyte
- **TMS** — Thermal management system

---

## Document Purpose and Scope

This document provides (1) a technical primer on Li-ion BESS physics and system architecture, (2) a catalog of functional requirements every BESS model must implement, (3) a comparative review of energy flow and degradation modeling approaches, and (4) a proposed design approach for DUET's BESS PoC module grounded in that review.

Goals:

1. Provide a shared technical frame of reference before architecture design and implementation begin.
2. Outline and choose which modeling choices are appropriate for DUET's BESS PoC.

---

## 1. Li-ion BESS Primer: Physics, Components, and System Architecture

**Purpose of this section:** Ground-level technical context. Establishes terminology and physical intuitions that the rest of the document assumes.

---

### 1.1 Cell Electrochemistry Fundamentals

- Li-ion cell operating principle: intercalation mechanism, anode (graphite), cathode (NMC/LFP/NCA), electrolyte, separator
- Charge/discharge as lithium-ion transport between electrodes; electrons flow through external circuit
- Key cell quantities: nominal capacity (Ah), open-circuit voltage (OCV), terminal voltage under load, internal resistance (DCR), state of charge (SOC)
- How cells differ from capacitors: voltage is relatively flat over SOC range (especially LFP), not proportional to stored charge
- Brief intro to degradation modes — LLI and LAM (LAM_NE, LAM_PE); observable consequences: capacity fade and resistance growth (more detail in Section 3)
- Characteristic aging trajectory: capacity fade under calendar aging (SEI growth is diffusion-limited); deviation from signals

**Reference sources:**

- `nrel_64171_degradation_mechanisms_summary.md` — mechanism taxonomy, SEI growth dominance argument, √t trajectory
- `zitara_lithium_ion_battery_degradation.md` — accessible primer on degradation causes and effects
- `dubarry_2023_mechanistic_modeling_accure_summary.md` — three-mode (LLI/LAM) framework introduction

---

### 1.2 BESS System Hierarchy: Cell to Grid

- Physical hierarchy: Cell -> Module -> String -> Rack/Block -> PCS (bidirectional inverter) -> MV transformer -> HV transformer -> grid connection
- Electrical rules: series connections add voltage; parallel connections add current capacity
- Annotated diagram of a utility-scale BESS container showing hierarchy levels
- Map to Enurgen's existing DUET solar hierarchy (Panel->String->Block->System) — show the analogy and highlight BESS-specific differences:
  - PCS is bidirectional (vs. unidirectional solar inverter)
  - BMS layer sits across all BESS levels (no PV equivalent)
  - BESS has internal state (SOC, SOH) that PV panels do not
- Module-level and string-level monitoring: what SCADA typically exposes at each level (current, voltage, temperature, SOC)
- Why hierarchy matters for digital twins: failures are localized; granular monitoring enables granular isolation

**Reference sources:**

- `solar_plant_hierarchy_annotated.md` — Enurgen's existing DUET hierarchy as the analog
- `nrel_64641_sam_technoeconomic_summary.md` — SAM's cells-in-series/parallel bank model and AC-coupled architecture

---

### 1.3 Energy Conversion Chain and Efficiency Budget

- Full power flow diagram: Grid AC (charge) -> PCS (AC->DC) -> Battery DC -> PCS (DC->AC) -> Grid AC (discharge) — the round trip
- Identify and quantify all loss sources:
  - DC-side round-trip: internal resistance losses (Ohmic, I²R); voltage-curve losses (polarization)
  - PCS conversion: typical AC-DC and DC-AC single-point efficiencies (95–98%); combined round-trip impact
  - Transformer losses: typically 0.5–1% per transformer stage
  - Auxiliary loads: BMS power draw, HVAC/TMS parasitics (can be 1–3% of throughput energy in extreme climates)
- Round-Trip Efficiency (RTE): `η_RT = E_discharged_AC / E_charged_AC`
- Show how RTE depends on operating point: C-rate (higher C-rate is more I²R loss), temperature (cold leads to higher resistance = more loss), SOC extremes
- Note: SAM models AC-coupled topology with two single-point efficiencies (η_ACDC, η_DCAC); DUET should follow same pattern

**Reference sources:**

- `nrel_64641_sam_technoeconomic_summary.md` — voltage model, PCS efficiency model

---

### 1.4 Li-ion Chemistries for Grid-Scale BESS

- Comparison table of the three chemistries dominant in large-scale BESS — NMC, LFP, NCA:
  - Energy density (Wh/kg, Wh/L)
  - Cycle life at 80% DoD (typical manufacturer ratings)
  - Thermal stability / safety profile
  - Operating temperature range
  - Dominant grid use cases
- Why LFP has become the dominant chemistry in new utility-scale deployments despite lower energy density: cycle life, thermal safety, cost, absence of cobalt/nickel
- NMC relevance: still common in existing installed base, higher energy density for space-constrained applications
- Modeling implications by chemistry:
  - LFP: flat OCV curve means structural SOC estimation difficulty; hysteresis effect; different calendar/cycle aging coupling vs. NMC
  - NMC/NCA: more sloped OCV (easier SOC estimation); LAM_PE from layered oxide degradation is a real concern; higher temperature sensitivity
- Chemistry determines: which degradation model parameters to use, whether hysteresis OCV model is needed, appropriate SOC confidence levels

**Reference sources:**

- `accure_2024_soc_lfp_whitepaper_summary.md` — LFP flat OCV, hysteresis, SOC estimation challenge (primary for LFP)
- `nrel_67102_life_prediction_summary.md` — NMC/graphite parameterized model; notes on chemistry-specificity
- `gwayi_2025_empirical_aging_models_review_summary.md` — 19 calendar + 20 cycle aging studies; LFP vs. NMC coverage

---

### 1.5 Degradation: The High-Level Picture

- The two observable outcomes of degradation: (1) capacity fade — battery stores less energy; (2) resistance growth — battery delivers/accepts less power and generates more heat
- The three root degradation modes (introduce the LLI/LAM framework without going into model equations — Section 3 covers that):
  - LLI (Loss of Lithium Inventory): cyclable Li consumed by SEI growth and side reactions; primary cause of capacity fade in most conditions
  - LAM_NE (Loss of Active Material, Negative): graphite anode structural damage from mechanical stress; self-reinforcing at low temperatures and high DoD
  - LAM_PE (Loss of Active Material, Positive): cathode structural degradation; particularly relevant for NMC/NCA layered oxides
- Calendar vs. cycle aging: calendar = time + temperature + SOC, even at rest; cycle = DoD + C-rate + temperature per cycle
- Characteristic trajectories: √t for calendar SEI (decelerating fade); accelerating fade at end-of-life (the characteristic "knee")
- Operational factors that accelerate degradation:
  - High temperature (chemical aging: SEI, cathode decomposition)
  - Low temperature (mechanical aging: graphite cracking; Li plating at high rates)
  - Deep cycling (nonlinear acceleration)
  - High C-rate (I²R heating, Li plating risk at cold)
  - High resting SOC (accelerates calendar SEI)
- Key design insight: thermal management is more effective at extending life than battery oversizing (restricting DoD), especially in moderate climates; in cold climates, mechanical degradation dominates regardless

**Reference sources:**

- `nrel_64171_degradation_mechanisms_summary.md` — mechanism taxonomy, SEI dominance, √t trajectory, coupling hypotheses
- `nrel_67102_life_prediction_summary.md` — oversizing vs. thermal management tradeoff
- `zitara_lithium_ion_battery_degradation.md` — six causes of degradation (accessible framing)

---

## 2. What BESS Models Should Implement: A Functional Requirements Catalog

**Purpose of this section:** Define the complete set of functional building blocks that any serious BESS simulation or digital twin tool must address — independent of any specific implementation. This serves as the evaluation framework for Section 3's degradation model comparison and as the specification basis for DUET BESS PoC module design in Section 4.

---

### 2.1 Electrochemical Core: Capacity and Voltage Model

- The minimum battery model: coulomb counting for SOC tracking (`SOC(t+Δt) = SOC(t) − I·Δt / C_usable`)
- Voltage model: terminal voltage as a function of OCV(SOC), internal resistance, and current (`V = OCV(SOC) − I·R_internal`)
- More complete: Tremblay-Dessaint generalized Shepherd model (SAM's approach) — captures exponential and nominal voltage zones from datasheet
- Most complete: DFN/SPMe electrochemical model (PyBaMM) — resolves solid-phase diffusion, Butler-Volmer kinetics, electrolyte transport
- The "datasheet-parameterizable" principle: SAM's voltage model parameterized from 6 datasheet values (`V_full, V_exp, V_nom, q_exp, q_nom, R`); DFN needs 30+ characterization parameters
- Chemistry-specific voltage behavior: LFP flat OCV with hysteresis; NMC monotonically sloped OCV

**Reference sources:**

- `nrel_64641_sam_technoeconomic_summary.md` — Tremblay-Dessaint model, datasheet parameter extraction
- `pybamm_continuum_models_liiondb_summary.md` — DFN model structure

---

### 2.2 Thermal Model

- Heat generation: Ohmic (`I²·R_internal`) + entropic heat (minor; often neglected at system level)
- Heat removal: HVAC/TMS coupling, convective and conductive losses to ambient
- Lumped-parameter thermal model (SAM's approach): `m·Cp·(dT/dt) = h·A·(T_room − T_battery) + I²·R`
- Temperature effects that feed back into other models:
  - Capacity: lookup table modifier (SAM); at cold temperatures capacity is reduced
  - Resistance: Arrhenius (higher R at low T, lower R at high T up to a point)
  - Degradation rates: every aging rate coefficient is temperature-dependent via Arrhenius
- SAM thermal model limitations: fixed room temperature, single lumped mass, no HVAC modeling (a simplification)
- Required inputs: battery mass, specific heat capacity, surface area, heat transfer coefficient, TMS setpoint temperature

**Reference sources:**

- `nrel_64641_sam_technoeconomic_summary.md` — lumped thermal model equations, trapezoidal solver
- `nrel_67102_life_prediction_summary.md` — temperature effects on degradation (thermal management impact)

---

### 2.3 Degradation / Aging Model

- Required features of a production-grade degradation model (used as evaluation criteria in Section 3):
  - Captures both calendar AND cycle aging
  - Tracks both capacity fade AND resistance growth
  - Temperature dependence (Arrhenius)
  - DoD dependence
  - Time-steppable through arbitrary dispatch profiles (not just end-of-life formula)
  - Mechanism decomposition enables model-vs-actual diagnostics
- The 4-tier model spectrum introduced here as the organizing framework (detailed in Section 3):
  - Empirical
  - Semi-empirical
  - Mechanistic
  - Physics-based
- Required outputs (where supported by the chosen model tier): remaining capacity (% of BoL), remaining resistance (% of BoL), EOL trajectory, and, for higher-fidelity tiers, degradation mode attribution

**Reference sources:**

- `nrel_64171_degradation_mechanisms_summary.md` — mechanism taxonomy, coupling hypotheses
- `gwayi_2025_empirical_aging_models_review_summary.md` — 13-model catalog, 46% resistance gap finding
- `dubarry_2023_mechanistic_modeling_accure_summary.md` — 4-tier taxonomy

---

### 2.4 State of Charge (SOC) Estimation

- SOC as the central operational state variable: everything depends on it — dispatch decisions, degradation rates, power capability estimates, financial projections
- Two fundamental methods:
  - Coulomb counting: integrates measured current; drifts over time due to sensor offsets, unmeasured parasitics, capacity uncertainty
  - OCV lookup: maps measured (or estimated) open-circuit voltage to SOC; requires rest periods; fails for LFP flat curve
- BMS sophistication tiers (Rudimentary / Standard / Advanced-EKF) and their accuracy implications
- SOC source trust hierarchy: BMS-reported (±10–20% LFP), cloud-corrected (±2–3%), model-estimated (depends on model), full charge calibration (±1–2%)
- Chemistry-specific flag: LFP SOC from BMS is structurally less reliable than NMC — this affects confidence intervals on all downstream KPIs
- For DUET BESS: simulator should track its own SOC via coulomb counting with model-derived capacity (not BMS-reported capacity); BMS SOC used for comparison, not as ground truth

**Reference sources:**

- `accure_2024_soc_lfp_whitepaper_summary.md` — primary reference; complete treatment of LFP SOC problem, BMS tiers, cloud analytics

---

### 2.5 State of Health (SOH) Tracking and Lifetime Prediction

- SOH definitions: SOH_C (capacity relative to BoL: `C_current / C_BoL`) and SOH_R (resistance relative to BoL: `R_current / R_BoL`) — why a single SOH number is insufficient; the two metrics tell different stories
- Cycle counting for degradation accumulation:
  - Simple full-equivalent-cycle (FEC) counting: total Ah discharged / nominal capacity — misses partial cycle depth effects
  - Rainflow counting (Downing-Socie, ASTM E1049): decomposes arbitrary SOC history into individual cycles with specific DoD values; correct approach for variable dispatch profiles (SAM uses this)
- Calendar aging accumulation: cumulative time × f(T, SOC)
- Predicting EOL trajectory: given current degradation state, project when battery will reach 70% or 80% remaining capacity
- EOL threshold: configurable (industry uses 70–80%); must match warranty terms

**Reference sources:**

- `nrel_64641_sam_technoeconomic_summary.md` — rainflow counting methodology, SAM lookup table lifetime model, EOL threshold
- `nrel_67102_life_prediction_summary.md` — state-variable model for EOL projection; 70% capacity threshold in paper

---

### 2.6 Dispatch Interface and Physical Constraint Enforcement

- Forward model role limitations: accepts a dispatch schedule (P(t) time series from EMS/optimizer), simulates what the battery does (simulation ≠ optimization)
- Required constraint checks the simulator must apply before executing each timestep:
  - SOC limits (min/max — typically 5–95% or 10–90% for grid BESS; hard limits defined by BMS)
  - Max charge/discharge power (C-rate limits — typically 0.5C to 2C for energy storage; different for power BESS)
  - Switching protection: prevent rapid charge/discharge oscillation at sub-hourly timesteps
  - Thermal limits: optional — flag dispatch that would push battery above/below thermal safety bounds
- Violation handling: clip-and-flag (execute at constraint boundary, log violation) vs. reject-and-raise (return error, caller must adjust) — both modes needed
- SAM's constraint controller stack as the reference: SOC Controller; Switching Controller; Current Controller (layered)
- Output: what the battery actually does given the constrained dispatch command, including energy delivered/absorbed and any clipping

**Reference sources:**

- `nrel_64641_sam_technoeconomic_summary.md` — dispatch algorithm logic, constraint controller stack

---

### 2.7 System Hierarchy Aggregation

- From cell-level physics to system-level behavior
- Series strings: voltage adds; failure/degradation of one cell limits the whole string (weakest-cell constraint)
- Parallel strings: capacity adds; string imbalance causes unequal loading leading to differential aging
- Cell-to-cell variation: manufacturing tolerances cause spread in capacity, resistance, SOC at assembly; BMS balancing mitigates but doesn't eliminate spread
- Key diagnostic patterns from this:
  - Voltage spread at low SOC: early indicator of cell imbalance (2% of modules had defective cells flagged by this)
  - Temperature spread across strings: indicates HVAC design flaw or failing cell
  - DCR spread: identifies aging outliers before capacity failure
- What system models must represent vs. what can be lumped: at PoC level, use lumped cell model; architect so cell-level variation can be added later as a plug-in

**Reference sources:**

- `nrel_64641_sam_technoeconomic_summary.md` — cells-in-series/parallel bank model

---

### 2.8 Model-vs-Actual Comparison Layer

- SCADA/BMS signals as "actual" inputs: current, voltage, temperature, SOC, cell voltages at configurable time resolution
- Simulated equivalents as "predicted" outputs: the same physical quantities predicted by the forward model
- Comparison surface: define the primary comparison pairs and their diagnostic meaning:
  - `SOC_predicted vs. SOC_BMS` (or SCADA-reported SOC): persistent offset = BMS calibration issue
  - `V_terminal_predicted vs. V_SCADA`: offset = resistance model error; shape mismatch = OCV curve error
  - `DCR_predicted vs. DCR_measured`: rising DCR faster than predicted = accelerated aging; flag for investigation
  - `Power_delivered vs. Power_setpoint`: underdelivery = C-rate limit violation or resistance growth
  - `SOH_predicted vs. SOH_estimated`: trajectory divergence = wrong degradation mechanism dominating
- Tolerance bands and anomaly thresholds: how to define "within model uncertainty" vs. "diagnostic signal"

**Target for eventual DUET BESS product: simulate what the battery *should* do. SCADA shows what it *actually does* and maps to the model at the right fidelity. Analyze 'deltas', as DUET's current PV product.**

**Reference sources:**

- `accure_2024_soc_lfp_whitepaper_summary.md` — BMS SOC vs. corrected SOC as the comparison layer

---

## 3. Degradation Modeling Approaches: Review and Comparison

**Purpose of this section:** Review the full modeling landscape (both for degradation and for energy flow simulation) comparing models, approaches and tools.

---

### 3.1 The Four-Tier Degradation Modeling Spectrum

| Tier | Model | Tracks | Parameters | Insight Level |
|---|---|---|---|---|
| Empirical / data-driven | Wang 2011 (CYAOM2), Schmalstieg 2014 | Aggregate capacity / resistance | Large datasets or curve fits (3–15 parameters) | Black box — correlations only |
| Semi-empirical (state-variable) | NREL Smith 2017 | Q_Li, Q_neg, Q_pos, R (8 states) | Aging test data + Arrhenius (20+ parameters) | Aggregate mechanisms (LLI-equivalent, LAM-equivalent) |
| Mechanistic | ACCURE / Dubarry 2023 | LLI, LAM_NE, LAM_PE from voltage curves | Half-cell OCV data + full-cell cycling | Electrode-level — *which* mode dominates |
| Physical-chemical | PyBaMM DFN, SPMe, SPM | Full electrochemical state | 30+ physical parameters (DFN characterization) | Mechanism-level — *why* degradation occurs |

- Key insight: mechanistic models are the minimum complexity level that provides electrode-level diagnostic decomposition; semi-empirical models track aggregate health but cannot attribute fade to a specific electrode
- No tier is universally superior: right choice depends on data available, required fidelity, and computational context (real-time BMS vs. cloud simulation vs. validation)
- Spectrum diagram showing the models positioned on the spectrum

**Reference sources:**

- `dubarry_2023_mechanistic_modeling_accure_summary.md` — 4-tier table (primary)
- `mechanistic_modeling_in_batteries.md` — ACCURE blog explanation of tiers
- `pybamm_continuum_models_liiondb_summary.md` — full spectrum summary table with DUET roles

---

### 3.2 Empirical and Semi-Empirical Models

- The CAOM/CYAOM/CCYASM/CCYACM taxonomy with model counts per category
- Summary table of all 13 models: code, type, complexity score, C-rate sensitivity, capacity fade, resistance increase, chemistry
- Deep look at four model structures selected for illustrative contrast:
  1. **CYAOM2 (Wang 2011)** — Simplest C-rate-capable model; single Arrhenius with C-rate modifying activation energy; LFP; complexity 17
  2. **CCYASM5 (Schmalstieg 2014)** — "Holistic" NMC; additive calendar + cycle (t^0.75 + √Ah); capacity and resistance; complexity 70; no C-rate
  3. **CCYACM1 (Baghdadi 2016)** — Combined formulation, all three: C-rate + capacity fade + resistance; NMC/NCA; complexity 42; no DoD term
  4. **CCYACM3 (Schimpe 2018)** — Most complete LFP model; four explicit pathways (calendar, high-T cycling, low-T cycling, low-T + high-SOC plating); complexity 83
- Field-wide statistics: 92% of models capture capacity fade; only 46% capture resistance increase; 54% include C-rate; only 23% capture all three
- Calendar-cycle coupling options: additive (Schmalstieg), competing/min (NREL Smith), multiplicative/combined rate (Baghdadi) — different coupling may be optimal for different chemistries

**Reference sources:**

- `gwayi_2025_empirical_aging_models_review_summary.md` — primary; all 13 models, statistics, key equations

#### 3.2.1 The NREL Semi-Empirical Model (Smith et al. 2017)

- Context: a later NREL state-variable degradation model and the reference implementation for DUET Task 2B. It is conceptually aligned with the NREL/SAM lineage, but distinct from BattWatts' original 2015 lookup-table lifetime model described in Section 3.5
- Experimental basis: 11 Kokam 75-Ah NMC/graphite cells, 9 conditions (0°C to 55°C); cycling and storage tests
- Capacity model: three competing mechanisms, `Q = min(Q_Li, Q_neg, Q_pos)`:
  - Q_Li: lithium loss from calendar SEI (√t), cycling-driven SEI cracking (×N), break-in (saturating exponential)
  - Q_neg: graphite site loss from mechanical fatigue (self-reinforcing ODE)
  - Q_pos: initial positive electrode wetting (minor; saturating at BoL)
- Resistance model: five additive mechanisms covering SEI film, site loss, break-in, calendar secondary, temperature base
- Arrhenius temperature dependence in every rate coefficient; some with negative activation energy (worse at cold for mechanical mechanism)
- State-variable formulation: enables time-stepping through arbitrary dispatch profiles
- Fit quality: R²=0.99, RMSE=1.4% on capacity across all conditions
- Limitations: NMC/graphite only (no LFP parameters); no explicit C-rate term; no LAM_PE for layered oxides; 11-cell dataset; 0°C and 55°C show largest residuals

**Reference sources:**

- `nrel_67102_life_prediction_summary.md` — primary; full parameter catalog, model equations, validation results
- `nrel_64171_degradation_mechanisms_summary.md` — theoretical foundation; competing-mechanism coupling choice; SEI dominance argument

---

### 3.3 Mechanistic Modeling: LLI/LAM Decomposition

Summary: mechanistic is the minimum complexity level for root-cause diagnostics; positioned as "compromise" between semi-empirical and physics-based.

- What mechanistic models do that semi-empirical models cannot: attribute observed degradation to a specific electrode and a specific degradation mode
- Core principle: full-cell voltage = `V_PE(Q) − V_NE(Q)`; by adjusting how electrode curves are aligned/scaled, the model emulates LLI/LAM_NE/LAM_PE effects on the observable voltage profile
- Two framework families: Q/SOC-based (fewer parameters, faster) vs. lithiation-based (more physically intuitive); over 37 published implementations
- The inaccessible lithium correction (Dubarry 2023): layered oxide cathodes (NMC, NCA, LCO) are never fully delithiated at normal cutoffs; models that ignore this systematically overestimate LLI and underestimate LAM_PE; the correction equations
- ACCURE's production use: non-invasive electrode-level diagnostics from operational charge/discharge voltage data (SCADA already collects this)
- LLI/LAM ratio as safety indicator: acceleration in this ratio is a leading indicator for the capacity "knee" and potential unsafe events
- Mapping to NREL model: LLI <-> Q_Li, LAM_NE <-> Q_neg, LAM_PE not in NREL

**Reference sources:**

- `dubarry_2023_mechanistic_modeling_accure_summary.md` — primary; model framework, inaccessible lithium problem, correction equations, mapping to NREL states
- `mechanistic_modeling_in_batteries.md` — ACCURE's plain-language positioning statement

---

### 3.4 Physics-Based Models: PyBaMM and the DFN Hierarchy

- The DFN (Doyle-Fuller-Newman) framework as the canonical continuum model: three regions (NE, separator, PE), particle-scale diffusion coupled through electrode thickness
- Three fidelity tiers in PyBaMM:

| Model | Electrolyte | Particle resolution | Typical solve time | Use case |
|---|---|---|---|---|
| SPM | Constant | X-averaged (1 per electrode) | Milliseconds | Fast screening, parameter sweeps |
| SPMe | Full PDE | X-averaged | Sub-second to seconds | Rate studies, degradation coupling |
| DFN (P2D) | Full PDE | Through-thickness resolved | Seconds to minutes | Full validation, electrode design |

- Degradation options in PyBaMM: SEI growth, SEI on cracks, lithium plating, particle mechanics, loss of active material — composable via model options
- Mapping PyBaMM degradation to NREL semi-empirical states
- Parameterization challenge: 30+ physical parameters per cell; NOT datasheet-parameterizable; published values show order-of-magnitude scatter
- LiionDB (Wang et al. 2022): searchable database of DFN parameters; useful as validation reference

**Reference sources:**

- `pybamm_continuum_models_liiondb_summary.md` — primary; model hierarchy, degradation options, SWOT, interface contract concept
- `dubarry_2023_mechanistic_modeling_accure_summary.md` — positioning PyBaMM in tier 4

---

### 3.5 Energy Flow and System-Level Simulation: SAM BattWatts Architecture

Key design principle for DUET: "all inputs should be derivable from manufacturer datasheets"

- SAM BattWatts is a complete, open-source, hardware-validated system-level BESS simulation pipeline; the reference architecture for DUET
- Sub-model pipeline with feedback: Dispatch, Capacity, Voltage, Thermal, Lifetime, Economics
- Voltage model (Tremblay-Dessaint): parameterizable from 6 datasheet values; 97.4% DC RTE at moderate C-rates; doesn't handle LFP hysteresis
- Thermal model (lumped): single mass, convective to fixed room temperature; trapezoidal solver; feeds capacity modifier table
- Capacity model: coulomb counting for Li-ion (simple tank-of-charge)
- Lifetime model (BattWatts 2015 version): rainflow counting + manufacturer DoD-cycle lookup table; no calendar aging. This is distinct from the later Smith 2017 state-variable degradation model proposed for DUET
- Dispatch controller: constraint stack (SOC, switching, current); manual monthly/hourly schedule dispatch
- Economics: multi-year simulation with replacement logic; NPV across three scenarios
- Validation results: SAM vs. HOMER within 3% (feature-matched); SAM vs. hardware Li-ion <9% SOC RMSE (dispatch-mode), <1% SOC RMSE (discharge-only)
- Chemistry defaults: NMC, NCA, LFP, LMO, LCO, LMO/LTO — changing chemistry changes parameter defaults, not model equations

**Reference sources:**

- `nrel_64641_sam_technoeconomic_summary.md` — primary; full architecture, sub-models, validation results

---

### 3.6 Commercial Platforms: TWAICE, ACCURE, Zitara

A side-by-side review of the three commercial analytics/digital twin platforms.

**TWAICE:**

- Pure analytics overlay: no hardware, sits on BMS/EMS data streams (API push / CSV upload / pull stack)
- Three-tier stack: data integration -> battery analytics engine -> dashboard/API/reporting
- Key capabilities: SoH tracking + EOL prediction, warranty tracking (vs. warranty curve), safety risk scoring, power setpoint compliance monitoring
- Data requirements: V (0.5V, 2s), I (0.5A, 2s), T (1°C, 60s), SOC (1%, 30s), cell V_min/V_max (0.01V, 2s) + system metadata
- 5+ GWh connected; partnerships: Munich RE (insurance), TÜV Rheinland (certification)
- Diagnostic case studies: temperature spread (HVAC failure), DCR spread (faulty cells), voltage spread at low SOC (cell imbalance), power setpoint mismatch, faulty cell replacement workflow
- 58% of BESS failures in first 2 years (EPRI data) — commissioning-phase monitoring is their top use case

**ACCURE:**

- Two complementary product layers:
  1. SOC correction: cloud analytics overlay fixing BMS SOC errors, especially for LFP; fleet benchmarking; hysteresis models; historical drift correction; claims ±2–3% accuracy
  2. Degradation diagnostics: mechanistic modeling (LLI/LAM decomposition) from operational voltage data; joint research with HNEI/Dubarry
- 3+ GWh connected; partnership with Munich RE
- SOC problem quantified: 20%+ field errors common in LFP; 50% in documented case; 35pp ambiguity from hysteresis alone
- Positioning: diagnostic depth + state accuracy; LFP specialization

**Zitara:**

- Model-based BMS algorithms: physics-based predictive algorithms for onboard or cloud deployment
- Focus on degradation-resilient controls: BMS adapts behavior as battery ages; not just monitoring but adaptive management
- Cloud-ready battery management software; works across chemistries
- Advanced predictive algorithms: predict energy, power, heat generation now and into the future with full state visibility
- Key differentiation from TWAICE/ACCURE: Zitara's algorithms can run onboard (embedded BMS level) not just cloud; combines monitoring with adaptive control

**Reference sources:**

- `accure_2024_soc_lfp_whitepaper_summary.md` — ACCURE SOC correction product
- `dubarry_2023_mechanistic_modeling_accure_summary.md` — ACCURE degradation diagnostics product
- `zitara_lithium_ion_battery_degradation.md` — Zitara's approach and positioning

---

## 4. Design Approach for DUET's BESS Module

**Purpose of this section:** Translate the landscape survey findings into concrete design recommendations for DUET's BESS module. This section flows directly into the **architecture document** and **I/O specification** (TBA).

---

### 4.1 DUET BESS Position in the Landscape

- DUET BESS PoC is not:
  - A sizing/technoeconomic tool (Xendee, GridCog, EnergyToolBase, etc.)
  - An EMS/dispatch optimizer (OpenEMS, GELI, others)
  - A commercial monitoring overlay (TWAICE, ACCURE)
  - A cell-level physics engine (PyBaMM)
- DUET BESS' position: **simulation-driven digital twin for actual-vs-predicted comparison** at the system level, parameterized from datasheets, integrated with the existing PV digital twin infrastructure
- What to build for PoC:
  - Forward simulation engine + semi-empirical degradation model
  - Model-vs-actual comparison framework: how to translate real BMS/SCADA data from an actual BESS and compare it to the digital twin model at the correct fidelity

---

### 4.2 Design Principles

The following principles govern all PoC design decisions and carry forward into production. They are ordered by priority.

**Principle 1: Extensible toward failure prediction and preventative maintenance.** The PoC builds a forward simulation engine and a model-vs-actual comparison layer. These two capabilities together are the foundation for future failure prediction and preventative maintenance modules. The architecture must be designed so that:

- Every sub-model (voltage, thermal, degradation) exposes **intermediate states**, not just final outputs. Internal resistance decomposition, mechanism-specific degradation rates, thermal headroom, and constraint-violation logs are all first-class outputs available to downstream consumers. A future anomaly detection module should be able to subscribe to any of these signals without modifying the simulator.
- The model-vs-actual comparison layer produces **structured deviation signals**. Each comparison pair (SOC, voltage, DCR, power, SOH) generates a typed deviation record that includes the magnitude, direction, persistence, and which sub-model is affected. These deviation records are the input that a potential future failure prediction engine would consume.
- The system hierarchy supports **drill-down granularity**. The PoC uses a lumped cell model at the rack/block level, but the hierarchy (Cell -> String -> Rack -> System) must be represented in the data model. A future preventative maintenance module might need to localize faults to specific strings or modules: e.g. voltage spread helps identify a specific faulty cell, or temperature spread - a specific cooling system zone.
- **Diagnostic patterns are catalogued, not hardcoded.** The PoC will include an initial deviation-to-root-cause mapping (e.g., "DCR rising faster than predicted -> accelerated aging"; "power underdelivery at normal SOC -> resistance growth"). This mapping should be a configurable lookup, so it can be extended with new patterns encountered in the field. This is the seed of a rule-based failure prediction system that can later be augmented with statistical or ML-based approaches.

**Principle 2: Datasheet-parameterizable by default.** Every required input should be derivable from a standard manufacturer datasheet and system configuration specification. This is the SAM design philosophy, and it is the right one for a tool targeting asset owners and EPCs who do not have cell characterization labs. Where richer data is available (aging test curves, half-cell OCV data, full DFN parameterization), the model tiering strategy (see 4.3 below) should allow higher-fidelity modes. The default path must work with datasheets alone.

**Principle 3: Actual-vs-predicted comparison is a key feature.** Target customers care most about comparing modeled vs. measured performance. Every module should be designed with this comparison in mind. The simulator's outputs must be directly comparable to the signals that SCADA/BMS systems produce: same physical quantities, same units, same temporal resolution (or cleanly resampleable). The comparison layer is not an afterthought — it is the primary value delivery mechanism.

**Principle 4: Chemistry-pluggable, not chemistry-locked.** The PoC targets NMC (published parameters available from NREL) with LFP as the immediate follow-on. The architecture must ensure that chemistry-specific behavior is isolated behind stable interfaces rather than scattered through the codebase. A proposed `CellChemistry` configuration object encapsulates chemistry-dependent parameters (OCV curves, Arrhenius coefficients, degradation coupling mode, SOC confidence bounds), while chemistry-specific sub-model selection remains internal to the battery-model package. This extends to voltage model selection: NMC may use a single-curve OCV model; LFP may require a hysteresis-aware OCV implementation — both exposed through the same external interface.

**Principle 5: Applicable to both hybrid PV+BESS and standalone BESS.** DUET already has a PV plant digital twin. The BESS module must work in three configurations: standalone BESS, PV+BESS (AC-coupled, sharing transformers and grid connection), or multi-asset sites. The site topology model is shared between PV and BESS. The BESS module plugs into this topology at the same level as a PV block — both produce/consume AC power through inverters/PCS into a shared MV bus. The dispatch interface should be topology-agnostic: the simulator receives a power command and doesn't care whether an optimizer, an EMS, or a manual schedule generated it.

**Principle 6: Degradation is its own domain.** Calendar aging, cycle-based capacity fade (DoD-dependent), rainflow counting, chemistry-specific parameterization, and resistance growth are complex enough to warrant a dedicated module with its own state, interface, and test suite. The degradation model receives operating conditions from the simulation engine and returns updated capacity and resistance — it does not reach into the voltage or thermal model internals. This clean boundary also makes it straightforward to swap degradation model (see 4.3 below) without touching the rest of the stack.

---

### 4.3 Model Tiering Strategy

We propose DUET BESS PoC implements a tiered degradation model framework so that model fidelity can be matched to available cell/module/rack technical specs and parameterization data. The common interface across all tiers is the key architectural commitment.

**Interface contract all tiers should implement:**

- Inputs per timestep: current/power command, cell temperature, current state (SOC, internal model states)
- Outputs per timestep: terminal voltage, updated SOC, updated degradation states, constraint violations

**Tier definitions:**

(The model selection below is not final, shown to illustrate fidelity)

| Tier | Model Class | Data Required | When to Use |
|---|---|---|---|
| 1 — Default | NREL Smith 2017 semi-empirical | 20+ Arrhenius parameters (published for NMC; LFP would require a separate parameter set or model variant) | Full parameterization available; Task 2B PoC |
| 2 — Datasheet fallback | SAM-style DoD-cycle lookup + rainflow | Manufacturer cycle-count vs. DoD curves | Customer provides warranty sheet only |
| 3 — Minimal | CYAOM2-class (single Arrhenius + Ah) | Nominal cycle life at one DoD | Only basic cycle rating available |
| 4 — Physics validation | PyBaMM SPMe wrapper | 30+ cell characterization parameters | Expert mode; validation studies |

A well specified interface contract means the dispatch engine and post-processing don't change when the tier changes.

**Reference sources:**

- `pybamm_continuum_models_liiondb_summary.md` — interface contract concept, spectrum table
- `gwayi_2025_empirical_aging_models_review_summary.md` — tiered fallback table (last section)

---

### 4.4 Chemistry Strategy

- Priority chemistries: LFP (dominant new deployments) and NMC (dominant installed base)
- NMC for PoC (Task 2B): NREL Smith 2017 parameters are published, validated, directly usable
- LFP roadmap:
  - Voltage model: requires separate charge/discharge OCV curves and a hysteresis convergence sub-model; Tremblay-Dessaint (single curve) is insufficient
  - Degradation model: Schimpe 2018 (CCYACM3) is the most detailed open LFP empirical reference; explicitly models low-temperature plating pathway that matters for LFP
  - SOC uncertainty: wider confidence bands; flag LFP BMS SOC as less reliable than NMC
- API design requirement from Day 1: `CellChemistry` configuration object that populates all model parameters; swapping chemistries should not require code changes, only config changes
- Future chemistries (NCA, LFP+LTO): plug in via chemistry config once structure is established

**Reference sources:**

- `accure_2024_soc_lfp_whitepaper_summary.md` — LFP voltage/SOC model requirements
- `gwayi_2025_empirical_aging_models_review_summary.md` — LFP parameterizations across catalog; CCYACM3 recommendation

---

### 4.5 Integration with DUET's Existing Architecture

- DUET's existing PV hierarchy: Panel -> String -> Block (strings + inverters + MV transformer) -> System (blocks + HV transformer + grid connection)
- BESS analog hierarchy: Cell -> String (cells in series/parallel) -> Rack/Block (strings + BMS + PCS/inverter) -> System (racks + MV/HV transformers + grid connection)
- Shared levels: Block and System levels share the same transformer/grid connection model with PV — BESS plugs into the same site topology
- Shared dispatch interface: PV system receives AC output; BESS receives AC dispatch command; both managed by the same site-level EMS
- Key additions for BESS vs. PV:
  - Internal state (SOC, SOH) — PV panels are stateless
  - Bidirectional power flow — PV is unidirectional
  - BMS layer — no PV equivalent
  - Degradation model — PV has degradation too but different model
- Integration point for SCADA comparison: same SCADA data model that handles PV actual-vs-predicted should be extended to accept BESS signals (I, V, T, SOC, cell voltages)

**Reference sources:**

- `solar_plant_hierarchy_annotated.md` — Enurgen's existing DUET hierarchy (the structure to match and extend)

---

### 4.6 Model-vs-Actual Comparison: Key Design Decisions

- Comparison surface priorities (ranked by diagnostic value for Enurgen's customers):
  1. **SOC tracking**: `SOC_model vs. SOC_BMS` — most operationally critical; persistent offset flags calibration issues
  2. **Terminal voltage under load**: `V_model vs. V_SCADA` — shape and level mismatch identifies resistance or OCV errors
  3. **DC resistance**: `DCR_model vs. DCR_measured` (via HPPC or current-pulse method) — key health indicator
  4. **Power capability**: `P_max_model vs. P_actual at given SOC/T` — rising gap flags resistance growth before capacity fade is visible
  5. **SOH trajectory**: `SOH_model vs. SOH_estimated` — long-horizon comparison; requires degradation model to be running
- Diagnostic inference: which deviation pattern -> which root cause (a taxonomy table for engineers to use in the field)
- Tolerance bands: how to set them (model uncertainty from parameter uncertainty + known measurement noise); chemistry-specific (wider for LFP)
- Cadence: some comparisons are continuous (SOC, voltage); others are periodic (DCR from reference pulses, SOH updates from capacity tests)
- Architecture extensibility: the model-vs-actual comparison layer and its deviation signals are the foundation for future failure prediction and preventative maintenance modules

**Reference sources:**

- `accure_2024_soc_lfp_whitepaper_summary.md` — SOC comparison layer design; chemistry-specific confidence levels
