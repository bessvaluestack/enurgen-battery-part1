# NREL — Life Prediction Model for Grid-Connected Li-ion Battery Energy Storage System

**Source:** NREL/CP-5400-67102, Conference Paper (Preprint)  
**Authors:** Kandler Smith, Aron Saxon, Matthew Keyser, Blake Lundstrom (NREL); Ziwei Cao, Albert Roc (SunPower Corp.)  
**Presented:** 2017 American Control Conference, Seattle, WA, May 24–26, 2017  
**File:** `67102_-_NREL_Life_Prediction_Model_Li-ion_BESS.pdf`  
**Funding:** U.S. DOE + SunPower Corporation CRADA

---

## Paper Summary

This paper presents a semi-empirical lifetime prognostic model for grid-connected Li-ion BESS, developed from accelerated aging tests on commercial graphite/NMC cells (Kokam 75-Ah pouch cells). The model predicts both **capacity fade** and **resistance growth** as functions of temperature, SOC, DOD, calendar time, and cycle count. It is the foundational degradation model used in NREL's System Advisor Model (SAM) for battery storage.

**Key result:** Across 9 aging conditions (0°C to 55°C), the model achieves 1.4% RMS error on capacity fade and 15% RMS error on resistance growth. It uses 8 internal state variables representing separate degradation mechanisms.

---

## Experimental Setup

11 Kokam 75-Ah NMC/graphite pouch cells tested under 9 conditions:

### Cycling Tests

| Test # | Temperature | DOD | Dis./Charge Rate | Duty Cycle | Cells |
|---|---|---|---|---|---|
| 1, 2 | 23°C | 80% | 1C/1C | 100% | 2 |
| 3 | 30°C | 100% | 1C/1C | 100% | 1 |
| 4 | 30°C | 80% | 1C/1C | 50% | 1 |
| 6, 7 | 0°C | 80% | 1C/0.3C | 100% | 2 |
| 9 | 45°C | 80% | 1C/1C | 100% | 1 |

### Storage (Calendar Aging) Tests

| Test # | Temperature | SOC | Cells |
|---|---|---|---|
| 5 | 30°C | 100% | 1 |
| 8 | 45°C | 65% | 1 |
| 10 | 45°C | 100% | 1 |
| 11 | 55°C | 100% | 1 |

Protocol details: full charge to 4.2 V (CC-CV, taper to C/10), full discharge to 3.0 V. For 80% DOD tests, voltage window narrowed to 4.1 V / 3.4 V. Monthly reference performance tests (RPT) at C/5 rate + HPPC resistance measurement.

**Replicate cell observations:** At 23°C (mild fade), replicate cells aged nearly identically. At 0°C (severe fade), replicates showed ~10% difference in fade rate — a useful data point for uncertainty quantification.

---

## Capacity Fade Model — Three Competing Mechanisms

The core modeling insight: measured capacity Q is the **minimum** of three independently-tracked limiting mechanisms:

```
Q = min(Q_Li, Q_neg, Q_pos)
```

### Mechanism 1: Lithium Loss (Q_Li) — SEI Growth + Cycling Coupling

**Dominates under:** normal operating conditions, storage, mild-to-moderate cycling.

Cyclable lithium is consumed by solid-electrolyte interface (SEI) growth — a side reaction at the graphite negative electrode surface. SEI growth is diffusion-limited, so capacity fade follows a **√t trajectory** (square root of time). Three sub-mechanisms contribute to Li loss:

1. **Calendar SEI growth** — proportional to √t, accelerated by high temperature and high SOC
2. **Cycling-driven Li loss** — proportional to cycle count N, representing mechanical disturbance of SEI that exposes fresh electrode surface
3. **Break-in mechanism** — small initial Li loss at BOL as the cell is conditioned

The Li-loss equation (Eq. 4 in the paper):

```
Q_Li = d₀ × [b₀ - b₁·t^(1/2) - b₂·N - b₃·(1 - exp(-t/τ_b3))]
```

Where coefficients b₁, b₂, b₃ are Arrhenius-type functions of temperature, SOC, and DOD:

- **b₁** (calendar SEI rate): depends on T, average negative electrode potential U₋(SOC), and DOD_max. Higher T, higher SOC, and deeper cycling all accelerate fade.
- **b₂** (cycling Li loss rate): depends on T only. Negative activation energy means this mechanism is **worse at low temperatures**.
- **b₃** (break-in rate): depends on T, open-circuit voltage V_OC(SOC), and DOD_max.

**Fit quality (Li-loss model alone, excluding 0°C):** R² = 0.97, RMSE = 0.77 Ah (1.0% of nameplate).

### Mechanism 2: Negative Electrode Site Loss (Q_neg) — Mechanical Fatigue

**Dominates under:** low temperature, high DOD, high C-rate, frequent cycling (>4 cycles/day).

Active sites on the graphite anode are lost due to mechanical stress from volume expansion/contraction during cycling (graphite expands ~8% during full lithiation). The model assumes a **self-reinforcing degradation** — as sites are lost, remaining sites bear more stress:

```
dQ_neg/dN = -(c₂/Q_neg)²
```

Analytical solution: `Q_neg = [c₀² - 2·c₂·c₀·N]^(1/2)`

The rate constant c₂ depends on temperature and DOD:

```
c₂ = c₂,ref × exp[-E_a/(R·(1/T - 1/T_ref))] × DOD^β_c2
```

With β_c2 = 4.54, DOD has a very strong effect — doubling DOD increases site loss rate by roughly 2^4.5 ≈ 23×.

**Negative activation energy** (E_a,c2 = −48260 J/mol): this mechanism is **accelerated by low temperature**, which is physically consistent with the graphite becoming more brittle and prone to fracture at cold temperatures.

### Mechanism 3: Positive Electrode Site Gain (Q_pos) — Initial Wetting

**Dominates:** only at BOL, very small effect (~0.5% capacity increase).

Initial cycling causes electrolyte wetting of the NMC positive electrode, slightly increasing accessible capacity. Modeled as a saturating exponential with cumulative Ah discharged.

### Final Capacity Model Fit

Combining all three mechanisms: **R² = 0.99, RMSE = 1.05 Ah (1.4% of nameplate)**. All cells predicted within ±5% error bounds. Largest errors on the most severely degraded cells (0°C cycling, 55°C storage).

---

## Resistance Growth Model — Five Additive Mechanisms

Unlike capacity (minimum of competing mechanisms), resistance is modeled as the **sum of additive contributions**:

```
R = R₀ × [a₀ + a₁·t^(1/2) + a₂/Q_neg + a₃·(1-exp(-t/τ)) + a₄·t]
```

| Term | Mechanism | Dependence |
|---|---|---|
| R₀ | BOL temperature response | Arrhenius in T |
| a₀ | Base resistance | Arrhenius (two-term) in T |
| a₁·t^(1/2) | SEI film resistance growth | T, SOC (via U₋), DOD_max |
| a₂/Q_neg | Negative electrode site loss → less surface area | T, DOD (from capacity model) |
| a₃·(1-exp) | Break-in mechanism (resistance decrease at BOL) | T |
| a₄·t | Secondary calendar aging (positive electrode surface?) | T, SOC (via V_OC) |

**Fit quality (all data):** R² = 0.98, RMSE = 0.15 mΩ (15% of nameplate 1 mΩ). Excluding 0°C and 55°C extreme cases: RMSE = 0.044 mΩ (4.4% of nameplate).

---

## State-Variable Formulation

For time-stepping simulation of real-world dispatch profiles, the model is recast with **8 state variables**:

- 1 state from Q_pos (Eq. 2) — positive electrode site capacity
- 3 states from Q_Li (Eq. 4) — SEI growth, cycling Li loss, break-in
- 1 state from Q_neg (Eq. 8) — negative electrode site loss
- 4 states from R (Eq. 12, though partially sharing Q_neg) — resistance sub-mechanisms

This formulation allows the model to be driven by a time series of operating conditions (T, SOC, current, DOD) at each timestep, rather than requiring constant aging conditions. This is what makes it usable for dispatch simulation in SAM and, by extension, in DUET's Task 2B.

---

## Application Example: PV + Battery Self-Consumption

The paper demonstrates the model on a PV-battery system operating in self-consumption mode (minimize grid exchange). Key scenario parameters:

- Ambient temperature: 28°C (constant) or seasonal variation (18/28/12/5°C for spring/summer/fall/winter)
- Average battery temperature: ~32°C
- Average SOC: 45%
- Maximum DOD: 74%
- Daily Ah throughput: 69 Ah (discharge direction)

### Lifetime Results

| Scenario | Years to 70% Remaining Capacity |
|---|---|
| Constant 28°C ambient, 74% DOD | 7.3 years |
| Seasonal temp variation, 74% DOD, no thermal management | 4.9 years |
| Seasonal temp, 74% DOD, with thermal management (20–30°C) | 7.0 years |
| Seasonal temp, 54% DOD, with thermal management | 10 years |
| Seasonal temp, 47% DOD, no thermal management | 7 years |

### Key Insight: Oversizing vs. Thermal Management

The paper's Figure 9 is the money chart — it shows the tradeoff between battery oversizing (restricting DOD) and adding thermal management (constraining cell temperature to 20–30°C):

- **Without thermal management** (5°C < T_cell < 35°C): maximum achievable life is ~7 years at 47% DOD. Going beyond 65% DOD drops life below 5 years.
- **With thermal management** (20°C < T_cell < 30°C): 10 years achievable at 54% DOD. Even at 74% DOD, life reaches 7 years.

The cold-temperature penalty is severe — winter operation accelerates the negative electrode site loss mechanism, which is the mechanism with negative activation energy.

---

## Fitted Parameter Catalogue

All parameters are provided in the paper for the Kokam 75-Ah NMC/graphite cell. These are **chemistry-specific** and would need to be re-fitted for different cell chemistries (LFP, NCA, etc.), but the **model structure** is generalizable.

### Capacity Model Parameters

| Parameter | Value | Units | Mechanism |
|---|---|---|---|
| d₀,ref | 75.10 | Ah | BOL capacity |
| d₃ | 0.46 | Ah | BOL capacity increase |
| E_a,d0,1 | 34,300 | J/mol | Capacity temperature dependence |
| E_a,d0,2 | 74,860 | J/mol | Capacity temperature dependence (quadratic) |
| b₁,ref | 3.503e-3 | day^-0.5 | SEI growth rate |
| E_a,b1 | 35,392 | J/mol | SEI growth activation energy |
| α_b1 | 1.0 | — | SEI voltage sensitivity |
| γ | 2.472 | — | DOD exponent for SEI |
| β_b1 | 2.157 | — | DOD coefficient for SEI |
| b₂,ref | 1.541e-5 | — | Cycling Li loss rate |
| E_a,b2 | −42,800 | J/mol | Cycling Li loss activation (negative → worse cold) |
| b₃,ref | 2.805e-2 | — | Break-in rate |
| E_a,b3 | 42,800 | J/mol | Break-in activation energy |
| α_b3 | 0.0066 | — | Break-in voltage sensitivity |
| τ_b3 | 5 | days | Break-in time constant |
| θ | 0.135 | — | DOD coupling for break-in |
| c₀,ref | 75.64 | Ah | Initial negative electrode capacity |
| E_a,c0 | 2,224 | J/mol | Neg. electrode capacity temp. dependence |
| c₂,ref | 3.9193e-3 | Ah/cycle | Neg. electrode site loss rate |
| β_c2 | 4.54 | — | DOD exponent for site loss |
| E_a,c2 | −48,260 | J/mol | Site loss activation (negative → worse cold) |

### Resistance Model Parameters

| Parameter | Value | Units |
|---|---|---|
| R₀,ref | 1.155e-3 | Ω |
| E_a,R0 | −28,640 | J/mol |
| a₁,ref | 0.0134 | day^-0.5 |
| E_a,a1 | 36,100 | J/mol |
| α_a1 | −1.0 | — |
| γ_a1 | 2.433 | — |
| β_a1 | 1.870 | — |
| a₂,ref | 46.05 | Ah |
| E_a,a2 | −29,360 | J/mol |
| a₃,ref | 0.145 | — |
| E_a,a3 | −29,360 | J/mol |
| τ_a3 | 100 | days |
| a₄,ref | 5.357e-4 | day^-1 |
| E_a,a4 | 77,470 | J/mol |
| α_a4 | −1.0 | — |

---

## Implications for DUET BESS Module

### For Task 1 — Landscape Survey

This paper represents the **gold standard open-source degradation model** for grid BESS. It is the model implemented in SAM's BattWatts module. Strengths and limitations to note in the survey:

**Strengths:**
- Physically-motivated semi-empirical structure (each term maps to a known degradation mechanism)
- Separates calendar aging from cycle aging with proper coupling
- State-variable formulation enables time-stepping through arbitrary dispatch profiles
- All parameters published — fully reproducible
- Validated against real accelerated aging data

**Limitations:**
- Parameterized for a single cell chemistry (Kokam NMC/graphite). Applying to LFP, NCA, or other chemistries requires new aging test data and re-fitting.
- No rainflow cycle counting — uses DOD_max as a scalar, not a cycle-by-cycle DoD distribution. For complex dispatch profiles with partial cycles, this is a significant simplification.
- 11 cells / 9 conditions is a modest dataset. The paper itself notes that uncertainty quantification and further validation are needed.
- Does not model cell-to-cell variation within a pack/string (acknowledged in the paper).
- 0°C and 55°C extremes show the largest model error — exactly the conditions where prediction matters most for thermal management design.

### For Task 1 — I/O Spec

The model's **input requirements** define what DUET's simulation engine needs:

**From manufacturer datasheets / cell characterization:**
- BOL capacity (Ah) at reference temperature
- BOL resistance (Ω) at reference temperature and 50% SOC
- Voltage limits (charge/discharge cutoff)
- Chemistry type (to select parameter set)

**From dispatch simulation (time series):**
- Cell temperature T(t)
- State of charge SOC(t)
- Current I(t) → to derive cumulative Ah, cycle count N, DOD per cycle
- Calendar time t

**Model outputs (KPIs):**
- Remaining capacity Q(t) as fraction of nameplate
- Internal resistance R(t) as fraction of BOL
- Decomposed fade: how much is calendar vs. cycle-driven vs. site loss
- Predicted years to end-of-life (e.g., 70% or 80% remaining capacity)

### For Task 2A — Simulation Engine

The simulation engine needs to provide the degradation model with the right inputs at each timestep. Specifically, the state-variable formulation requires that the simulator track and pass through:

- Average SOC over each cycle or timestep → feeds b₁ via U₋(SOC)
- Maximum DOD over the current duty period → feeds b₁ and c₂ via DOD_max^β
- Cell temperature → feeds all Arrhenius terms
- Cumulative cycle count N → feeds b₂ and Q_neg
- Cumulative Ah discharged → feeds Q_pos (minor)

The `min(Q_Li, Q_neg, Q_pos)` structure means the simulator should track all three mechanisms in parallel and report which one is currently limiting — this is critical for understanding *why* a battery is fading and what operational changes would help.

### For Task 2B — Degradation Model

This paper is essentially the **reference implementation spec** for Task 2B. The model can be implemented directly for NMC/graphite cells using the published parameters. Key design decisions for DUET:

1. **Start with the NREL model structure** — it's proven, well-documented, and the parameter values are published. Good PoC starting point.
2. **Add rainflow counting** — the paper uses DOD_max as a scalar input, but real dispatch profiles have partial cycles at varying depths. A rainflow cycle counter (per ASTM E1049) would decompose an arbitrary SOC time series into individual cycles with specific DoD values, feeding c₂ more accurately.
3. **Make it chemistry-pluggable** — the model structure (3 capacity mechanisms + 5 resistance mechanisms) is generalizable, but all Arrhenius parameters are chemistry-specific. Design the API so that a `ChemistryParams` object can be swapped in for different cell types.
4. **Track mechanism decomposition** — always output all three Q mechanisms separately, not just the min. This enables the model-vs-actual diagnostic: "your battery is fading faster than predicted, and it's dominated by site loss rather than SEI growth, which suggests a thermal management issue."

### Specific Numbers Worth Remembering

- **DOD exponent for site loss: β_c2 = 4.54** — this is why depth-of-discharge management matters so much. Restricting DOD from 80% to 60% reduces cycle-driven site loss rate by (0.6/0.8)^4.54 ≈ 0.27× — nearly 4× reduction.
- **SEI growth follows √t** — capacity fade decelerates over time under calendar aging. This means the first year of life shows the most fade per unit time. Important for warranty curve interpretation.
- **Cold temperature accelerates mechanical degradation** (negative E_a for c₂ and b₂) while **hot temperature accelerates chemical degradation** (positive E_a for b₁). Optimal operating temperature is a compromise, roughly 20–30°C.
- **End-of-life definition: 70% remaining capacity** is used in this paper. Industry also commonly uses 80%. DUET should make this configurable.
