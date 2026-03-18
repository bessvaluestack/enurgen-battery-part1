# PyBaMM Continuum Models & LiionDB — Physics-Based Battery Modeling Layer

**Primary Source:** Internal analysis of PyBaMM GitHub repository (`pybamm-team/PyBaMM`) and LiionDB (`ndrewwang/liiondb`)  
**Companion Paper:** Wang, A.A., O'Kane, S.E.J., Brosa Planella, F., et al. "Review of parameterisation and a novel database (LiionDB) for continuum Li-ion battery models." *Progress in Energy*, vol. 4, 032004, 2022. DOI: `10.1088/2516-1083/ac692c`
**PyBaMM Repo:** `https://github.com/pybamm-team/PyBaMM` (active, commits through Feb 2026)  
**LiionDB Repo:** `https://github.com/ndrewwang/liiondb` (last activity Jan 2024)

---

## Why This Matters for DUET

DUET's BESS module needs a **multi-model degradation framework** — not a single model commitment. The NREL semi-empirical approach (Smith et al. 2017, summarized in `nrel_67102_life_prediction_summary.md`) and the broader empirical model landscape (Gwayi et al. 2025, summarized in `gwayi_2025_empirical_aging_models_review_summary.md`) represent the system-level, computationally efficient end of the modeling spectrum. PyBaMM and its physics-based continuum models represent the **other end**: first-principles electrochemical simulation that can serve as a validation reference, a parameter-sensitivity tool, and potentially a higher-fidelity option for customers who need cell-level physics.

This summary documents what PyBaMM offers, how its model hierarchy works, and where it connects to (or conflicts with) DUET's architecture. It is written to inform the landscape survey's PyBaMM section and the architecture document's model-abstraction layer.

---

## The DFN Model Hierarchy — Three Levels of Fidelity

PyBaMM implements three progressively simplified versions of the Doyle–Fuller–Newman (DFN) porous-electrode framework. Understanding this hierarchy is important because it maps directly to a **fidelity-vs-speed tradeoff** that DUET's architecture must accommodate.

### Level 1: Full DFN (P2D — Pseudo-Two-Dimensional)

The DFN is the canonical continuum electrochemical model for Li-ion cells. It treats the cell as three macroscopic regions (negative electrode, separator, positive electrode) with particle-scale diffusion coupled at each point through the electrode thickness.

**Physical submodels encoded in PyBaMM's `basic_dfn.py`:**

**Solid-phase (particle) diffusion** — Fickian diffusion in spherical particles, separately in each electrode:
- Flux: N_s,k = −D_k(c_s,k, T) ∇c_s,k
- Conservation: ∂c_s,k/∂t = −∇·N_s,k
- Boundary condition at particle surface couples to interfacial reaction flux j_k (Neumann condition)

**Interfacial reaction kinetics** — Butler–Volmer in symmetric sinh form:
- Exchange current densities j_0,k computed from surface concentration
- Overpotential: η_k = φ_s,k − φ_e,k − U_k(stoichiometry, T)
- Reaction flux: j_k ∝ 2·j_0,k·sinh(...)

**Solid-phase charge conservation** — Ohm's law with reaction source:
- i_s,k = −σ_k,eff ∇φ_s,k
- ∇·i_s,k + a_k·j_k = 0 (algebraic constraint)

**Electrolyte transport** — Concentrated-solution-theory conductivity + diffusion:
- Electrolyte current: i_e = κ_e(c_e,T)·τ·(χ·∇c_e/c_e − ∇φ_e)
- Current conservation: ∇·i_e − a·j = 0
- Mass conservation: ∂c_e/∂t = (1/ε)(−∇·N_e + (1−t₊)·a·j/F)

**State variables:** c_e(x,t), φ_e(x,t), φ_s,n(x,t), φ_s,p(x,t), c_s,n(x,r,t), c_s,p(x,r,t), plus throughput Q(t).

**Key assumption in the readable baseline:** Isothermal (constant temperature). Thermal coupling is available through separate thermal submodels but not included in the self-contained `basic_dfn.py`.

**Computational cost:** High-dimensional stiff PDE/DAE system after spatial discretization. PyBaMM uses `CasadiSolver` for practical execution. Typical solve times are seconds-to-minutes for a single charge/discharge cycle — orders of magnitude slower than semi-empirical models but tractable for validation studies.

### Level 2: SPMe (Single Particle Model with Electrolyte)

SPMe retains continuum electrolyte dynamics but collapses the particle-scale to a single representative particle per electrode (x-averaged).

**What it keeps from DFN:** Full electrolyte diffusion and potential (evolves c_e as a PDE). Particle diffusion in spherical coordinates.

**What it simplifies:** Instead of resolving particle behavior at every point through the electrode thickness, SPMe uses x-averaged particle states — one representative particle per electrode.

**Implementation:** Inherits from SPM class, sets `self.x_average = True`, and configures electrolyte diffusion to "Full" (as opposed to SPM's constant-concentration treatment).

**State variables:** x-averaged particle concentrations c̄_s,n(r,t), c̄_s,p(r,t), plus electrolyte field(s).

**When to use:** When electrolyte dynamics matter (high C-rates, thick electrodes, low-conductivity electrolytes) but full through-electrode particle resolution isn't needed.

### Level 3: SPM (Single Particle Model)

The most reduced continuum model. Collapses both electrolyte and spatial resolution.

**What it keeps:** Particle diffusion and reaction kinetics (Butler-Volmer).

**What it simplifies:** Electrolyte concentration set to constant (no transport dynamics). X-averaged particles.

**State variables:** c̄_s,n(r,t), c̄_s,p(r,t), Q(t), plus a voltage expression from electrode OCPs + kinetic terms (asinh form).

**When to use:** Fast screening, parameter sensitivity studies, or situations where electrolyte transport is not rate-limiting (moderate C-rates, thin electrodes).

### Fidelity Hierarchy Summary

| Model | Electrolyte | Particle Spatial Resolution | Thermal | Typical Solve Time | Use Case |
|---|---|---|---|---|---|
| DFN | Full PDE (c_e, φ_e) | Through-thickness resolved | Optional coupling | Seconds–minutes per cycle | Full validation, electrode design |
| SPMe | Full PDE (c_e) | X-averaged (1 particle/electrode) | Optional | Sub-second–seconds | Rate studies, degradation coupling |
| SPM | Constant | X-averaged (1 particle/electrode) | Optional | Milliseconds | Fast screening, parameter sweeps |

---

## Degradation Physics in PyBaMM

PyBaMM exposes degradation through a **model options infrastructure** — configuration flags that activate submodel code paths. This is architecturally significant: degradation isn't hardcoded into the core electrochemical model but composed via options.

### Available Degradation Mechanisms (GitHub-Evidenced)

| Mechanism | PyBaMM Option Key | Physical Basis | Connects To |
|---|---|---|---|
| SEI growth | `"SEI"` | Solid-electrolyte interface formation on graphite | LLI (capacity fade), impedance growth |
| SEI on cracks | `"SEI on cracks"` | SEI regrowth on mechanically exposed surface | Coupled mechanical-chemical degradation |
| Lithium plating | (available in model options) | Metallic Li deposition at low T / high rate | LLI, safety |
| Particle mechanics | `"particle mechanics"` | Stress-driven cracking from volume changes | LAM, SEI-on-cracks trigger |
| Loss of active material | `"loss of active material"` | Electrode material isolation/degradation | LAM (capacity + power fade) |

### Mapping PyBaMM Degradation to NREL Semi-Empirical States

| NREL 67102 State | Physical Mechanism | PyBaMM Equivalent |
|---|---|---|
| Q_Li (lithium loss — calendar SEI) | SEI growth consuming cyclable Li | `"SEI"` submodel (calendar component) |
| Q_Li (lithium loss — cycling) | SEI cracking + regrowth during cycling | `"SEI on cracks"` + `"particle mechanics"` |
| Q_neg (negative site loss) | Mechanical fatigue of graphite | `"particle mechanics"` + `"loss of active material"` |
| Q_pos (positive site gain) | Initial cathode wetting | Not directly modeled (minor effect) |
| R (resistance — SEI film) | SEI thickness → impedance | `"SEI"` submodel resistance contribution |
| R (resistance — site loss) | Reduced active surface area | `"loss of active material"` → surface area reduction |

This mapping is imperfect — the NREL model captures mechanisms as lumped empirical terms fitted to aging data, while PyBaMM models the underlying physics. But the correspondence shows that **the same physical phenomena are being described at different levels of abstraction**, which is exactly the multi-model framework insight.

---

## LiionDB — Parameter Database for Continuum Models

### What It Is

LiionDB (Wang et al. 2022) is a **searchable relational database** aggregating published DFN model parameters. It is both a web interface (`liiondb.com`) and a GitHub repo with SQL-queryable notebooks.

### Database Schema

The implementation uses four core tables: `material`, `paper`, `parameter`, `data`. Notebooks demonstrate programmatic SQL queries and plotting workflows for parameter retrieval and comparison.

### What It Contains

The database collects parameters needed for DFN-family models, organized by material and source paper:

- **Electrode geometry:** particle radii (distributions available), electrode thicknesses, porosities, volume fractions
- **Solid-phase transport:** diffusion coefficients D_s(c_s, T) as functions or scalars
- **Electrolyte transport:** conductivity κ_e(c_e, T), diffusion D_e(c_e, T), transference number t₊, thermodynamic factor
- **Kinetics:** exchange current density parameters, OCV curves (with stoichiometric limits)
- **Thermal:** specific heat, thermal conductivity (where available)

### Relevance to DUET

LiionDB's parameter catalog is useful in two ways:

1. **Validation reference** — When DUET's semi-empirical model predicts degradation behavior for a given chemistry, LiionDB provides the underlying physical parameters (D_s, κ_e, particle radii) that could explain *why* the empirical parameters take the values they do. This supports the model-vs-actual diagnostic story.

2. **Physics-based model parameterization** — If DUET's framework eventually supports a PyBaMM-backed physics mode (even as a validation tool, not a production simulator), LiionDB is the parameter source. The Wang et al. paper documents the measurement methods, their limitations, and the scatter in published values — critical for understanding parameter uncertainty.

### LiionDB Status

The GitHub repo shows last activity in January 2024. The web interface at liiondb.com is the primary access point. The repo is smaller in footprint than PyBaMM and shows fewer software maturity signals (test coverage, CI), but this is appropriate — it's a data product, not a simulation engine.

---

## Key Insights from the Parameterization Review (Wang et al. 2022)

The companion paper provides a critical review of DFN parameter measurement methods:

### Parameter Measurement Is Hard and Uncertain

The paper documents significant scatter in published parameter values for the same materials. For example, reported particle radii for the same electrode chemistry can vary by an order of magnitude across different measurement techniques and different research groups. This uncertainty propagates through continuum models and is a fundamental limitation of physics-based approaches.

**Implication for DUET:** This is a structural argument *for* semi-empirical models at the system level. The NREL model's parameters are fitted to cell-level aging data, implicitly integrating over all the microscopic uncertainties. A physics-based model requires getting each parameter right individually.

### The DFN Parameter Count Is Large

A full isothermal DFN parameterization requires values for approximately 30+ distinct parameters (geometric, transport, kinetic, thermodynamic) across three domains (negative, separator, positive), plus electrolyte properties. Adding thermal coupling adds another ~5-10 parameters. Adding degradation submodels adds further parameters per mechanism.

**Implication for DUET:** The "datasheet-parameterizable" design principle from SAM (see `nrel_64641_sam_technoeconomic_summary.md`) is validated by contrast — DFN models are fundamentally *not* datasheet-parameterizable. They require specialized characterization data that most battery system integrators don't have access to. This positions the semi-empirical approach as the right default for DUET's PoC, with physics-based models as an expert-mode validation layer.

### OCV Curves Are the Most Reliably Available Parameter

Of all DFN parameters, open-circuit voltage (OCV) curves are the most commonly published and most consistently measured. Both half-cell and full-cell OCV data are available for major chemistries (NMC, LFP, NCA, graphite, LTO) across multiple sources.

**Implication for DUET:** OCV curves are already part of SAM's voltage model inputs (see `nrel_64641_sam_technoeconomic_summary.md`). They bridge the semi-empirical and physics-based worlds — used directly in the NREL degradation model (via U₋(SOC) terms in the Arrhenius coefficients) and as a fundamental input to DFN simulations. DUET's I/O spec should treat OCV data as a first-class input regardless of which model tier is active.

### Electrolyte Parameterization Is Chemistry-Specific but Transferable

Unlike electrode parameters (which vary by manufacturer, coating process, and cell design), electrolyte transport properties are more transferable across cells using the same electrolyte formulation. LiionDB collects full electrolyte parameterizations as functional relationships (κ_e(c_e, T), D_e(c_e, T)).

**Implication for DUET:** For the PoC, electrolyte effects can be captured through the round-trip efficiency and internal resistance terms in the semi-empirical model. But if a future physics-based validation mode is added, electrolyte parameterization from LiionDB is the most portable starting point.

---

## Model Spectrum — Positioning for DUET's Multi-Model Framework

The full picture across all reference summaries in this repo now covers a spectrum of modeling approaches. This table is designed to inform the landscape survey and architecture documents:

| Approach | Representative | Fidelity | Speed | Parameterization | DUET Role |
|---|---|---|---|---|---|
| **Empirical (algebraic)** | Gwayi CYAOM2 (Wang 2011) | Low | Very fast (μs) | Minimal (1–2 Arrhenius + Ah throughput) | Fallback / rapid screening |
| **Semi-empirical (state-variable)** | NREL Smith et al. 2017 | Medium | Fast (ms per timestep) | Moderate (20+ fitted parameters from aging data) | **Core PoC engine** |
| **Semi-empirical (lookup + rainflow)** | SAM BattWatts (DiOrio 2015) | Medium-low | Fast | Manufacturer DoD-cycle curves | Compatibility layer for datasheet-only inputs |
| **Reduced physics (SPM)** | PyBaMM `SPM` | Medium | Moderate (ms–s per cycle) | High (30+ physical parameters) | Fast physics check |
| **Reduced physics + electrolyte (SPMe)** | PyBaMM `SPMe` | Medium-high | Moderate (s per cycle) | High | Validation / sensitivity studies |
| **Full physics (DFN/P2D)** | PyBaMM `DFN` | High | Slow (s–min per cycle) | Very high (30+ with full characterization) | Reference validation, electrode-level analysis |

### Architectural Implication: The Model Interface Contract

All of these models, despite their vastly different internals, share a common **interface contract** at the simulation engine level:

**Inputs per timestep:**
- Current or power command (from dispatch schedule)
- Cell temperature (from thermal model or measurement)
- Current state (SOC, SOH, internal states)

**Outputs per timestep:**
- Terminal voltage
- Updated SOC
- Updated degradation states (capacity remaining, resistance)
- Constraint violations (if any)

DUET's architecture should define this interface cleanly so that the core simulator can swap between model tiers without changing the dispatch logic, thermal model, or post-processing. The semi-empirical NREL model and a PyBaMM SPMe wrapper would both implement the same interface — they just differ in what happens inside the timestep.

This is why committing to a single model prematurely would be a mistake. The framework should support:

1. **Semi-empirical mode** (NREL-type) as the default — fast, datasheet-parameterizable, proven for multi-year simulations
2. **Empirical fallback** (Gwayi-catalog models) when only warranty-sheet data is available
3. **Physics-based validation mode** (PyBaMM SPMe/DFN) for customers who have full cell characterization data and need electrode-level diagnostics

---

## PyBaMM — Software Assessment for Landscape Survey

### Maturity Signals

- **Repository:** `pybamm-team/PyBaMM` on GitHub
- **Activity:** Active commits through February 2026 (confirmed in analysis)
- **Documentation:** Full `docs/` directory
- **Testing:** `tests/` directory present, CI infrastructure
- **Community:** Large contributor base, issue tracker, discussions active
- **License:** Open source (BSD 3-Clause)
- **Language:** Python, with C/C++ solver backends

### What PyBaMM Is Good At

- **Model flexibility** — DFN/SPMe/SPM selectable at runtime, degradation mechanisms composable via options
- **Symbolic equation representation** — Models defined symbolically, discretized and solved automatically
- **Solver infrastructure** — CasadiSolver for stiff systems, configurable discretization
- **Parameter sets** — Ships with default parameter sets for common chemistries (Chen 2020 NMC, Marquis 2019 SPM, etc.)
- **Research tool** — Designed for academic battery researchers doing single-cell studies

### What PyBaMM Is Not

- **Not a system simulator** — No pack-level modeling, no BMS logic, no dispatch scheduling, no financial analysis
- **Not datasheet-parameterizable** — Requires specialized characterization data (see Wang et al. 2022 discussion above)
- **Not optimized for multi-year simulation** — Designed for individual cycles or short duty profiles, not 25-year lifetime projections at minute resolution (~13M timesteps)
- **Not a degradation prediction tool out of the box** — Degradation submodels exist but require careful configuration, parameterization, and validation for each cell type

### SWOT Summary for Landscape Survey

| | |
|---|---|
| **Strengths** | Most complete open-source physics-based Li-ion model; active development; composable degradation mechanisms; symbolic equation framework enables custom extensions |
| **Weaknesses** | High parameterization burden; not designed for system-level multi-year simulation; computational cost prohibitive for dispatch optimization loops; no pack/string modeling |
| **Opportunities** | Could serve as DUET's physics-based validation engine for high-fidelity customers; parameter sensitivity studies to validate semi-empirical model assumptions; LiionDB integration for parameterization |
| **Threats** | Complexity may deter Enurgen's engineering team from maintaining a PyBaMM integration; rapid development pace means API changes; academic focus may diverge from industrial BESS needs |

---

## Relationship to Other Reference Summaries

```
MODELING SPECTRUM (cell-level degradation)
═══════════════════════════════════════════

Physics-based (this summary)                Semi-empirical                         Empirical
─────────────────────────────              ──────────────────                     ──────────
PyBaMM DFN (full continuum)         ←→     NREL 67102 (Smith 2017)          ←→   Gwayi catalog
PyBaMM SPMe (reduced + electrolyte)         8 state variables                     (13 models, 17–83 complexity)
PyBaMM SPM (minimal continuum)              Mechanism decomposition               Algebraic, no state tracking
                                            min(Q_Li, Q_neg, Q_pos)
  ↑                                           ↑                                     ↑
  |                                           |                                     |
  Parameters from LiionDB/Wang 2022    Parameters from aging tests            Parameters from curve fits
  (30+ physical params per cell)       (20+ Arrhenius coefficients)           (3–15 empirical coefficients)
                                              ↑
                                              |
                                    NREL 64171 (Smith 2015)
                                    Mechanism taxonomy & coupling hypotheses

SYSTEM-LEVEL SIMULATION (SAM reference)
═══════════════════════════════════════
NREL 64641 (DiOrio 2015)
SAM's battery model architecture:
  Dispatch → Capacity → Voltage → Thermal → Lifetime → Economics
  Validated against hardware (<9% SOC RMSE)
  Datasheet-parameterizable (key design principle for DUET)
```

### How This Feeds Into the Landscape Survey

The landscape survey (`docs/task1/landscape/landscape_survey.md`) needs a PyBaMM section. This summary provides:

1. **The three-model hierarchy** (DFN → SPMe → SPM) with clear fidelity/speed tradeoffs — Table ready for inclusion
2. **Degradation mechanism coverage** mapped to NREL model states — Shows physics-to-empirical correspondence
3. **SWOT assessment** — Ready for the comparative analysis section
4. **Architectural insight** — The model interface contract concept that feeds directly into the architecture document
5. **LiionDB as a data resource** — Documented for the I/O spec's discussion of parameter sources

The landscape survey should position PyBaMM as "the physics-based reference point" in DUET's model spectrum, not as a competing approach to the semi-empirical core. The value proposition is: DUET uses semi-empirical models for production simulation (fast, datasheet-parameterizable, proven for multi-year projections) and can optionally invoke physics-based models (PyBaMM) for validation, sensitivity analysis, or customers with full characterization data.
