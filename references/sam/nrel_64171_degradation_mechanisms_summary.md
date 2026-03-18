# NREL — Degradation Mechanisms and Lifetime Prediction for Li-ion Batteries: A Control Perspective

**Source:** NREL/CP-5400-64171, Conference Paper (Preprint)  
**Authors:** Kandler Smith, Ying Shi, Shriram Santhanagopalan (NREL)  
**Presented:** 2015 American Control Conference, Chicago, IL, July 1–3, 2015  
**File:** `64171_-_Degradation_Mechanisms_and_Lifetime_Prediction_for_LithiumIon_Batteries.pdf`  
**Funding:** U.S. DOE Vehicle Technologies Office + ARPA-E (AMPED Program)

---

## Paper Summary

This is the **theoretical precursor** to Smith et al. 2017 (NREL/CP-5400-67102). Where the 2017 paper presents the fitted model and parameter values for a specific NMC/graphite cell, this 2015 paper lays out the **generalized framework** — the degradation mechanism taxonomy, the model selection methodology, and the control applications that motivate the work. It's a shorter, more conceptual paper (extended abstract with references), but contains critical framing that the 2017 paper assumes.

Read this paper for *why* the model is structured the way it is. Read the 2017 paper for *how* to implement it.

---

## Degradation Mechanism Taxonomy

The paper's Table I provides a classification of Li-ion failure modes by their underlying physics. This is the most useful artifact from the paper — it maps the territory of what a degradation model needs to capture.

### Five Categories of Degradation Physics

| Category | Description | Stress Factors | How to Characterize |
|---|---|---|---|
| **Mechanical** | Failure of cell structures and packaging | Deformation, vibration | Mechanical tests, accelerated with magnitude and cycle count |
| **Chemical** | Side reactions occurring during rest (calendar aging) | Temperature, chemical state (SOC) | Storage tests at various temperatures and SOC levels |
| **Electrochemical** | Side reactions driven by charge/discharge rate | Current rate, temperature, potential window | Accelerated cycling at various C-rates and temperatures |
| **Electrochemo-mechanical** | Degradation from material expansion/contraction during cycling | Material properties, phase changes, DOD, C-rate, temperature, mechanical damage state | Accelerated cycling across a matrix of duty cycles |
| **Thermal coupling** | Accelerates all of the above | Temperature (high accelerates reactions, low impedes transport and causes mechanical stress) | Aging tests at 3–5 temperatures including cold and hot extremes |

### Key Insight: Thermal Coupling Is Everywhere

Temperature doesn't have its own degradation mechanism — it *modulates* every other mechanism. High temperature accelerates chemical and electrochemical side reactions (Arrhenius). Low temperature impedes normal transport (increasing overpotentials) and causes mechanical stress (thermal contraction). This is why the 2017 model uses Arrhenius temperature dependence in every rate coefficient, with some having negative activation energies (worse at cold temperatures).

---

## The SEI Growth Dominance Argument

For Li-ion chemistries with graphitic negative electrodes (which covers NMC/graphite, LFP/graphite, NCA/graphite — essentially all mainstream grid storage chemistries), **SEI layer growth is usually the dominant degradation mechanism**. The paper explains:

1. SEI growth increases cell impedance (resistance growth)
2. SEI growth consumes cyclable lithium (capacity fade)
3. The rate-limiting step is electrolyte solvent diffusion through the existing SEI layer
4. This diffusion-limited process produces the characteristic **√t trajectory** — rapid fade at BOL that gradually decelerates

The √t trajectory is the single most important pattern in Li-ion degradation modeling. If you see capacity fade that follows √t, you're looking at calendar-dominated SEI growth. If fade is faster than √t or accelerates, another mechanism is contributing.

---

## Calendar vs. Cycling Degradation: Three Coupling Hypotheses

The paper identifies a critical open question in degradation modeling: how do calendar (storage) and cycling contributions combine? Three plausible couplings exist:

### Hypothesis (i): Additive

```
Fade_total = Fade_calendar + Fade_cycling
```

Used by Schmalstieg et al. (2014) for NMC. Calendar and cycling degradation are independent and sum linearly. Simple, but may over-predict for mixed conditions.

### Hypothesis (ii): Maximum (Competing Mechanisms)

```
Fade_total = max(Fade_calendar, Fade_cycling)
```

Used by Smith et al. (2013) and later in the 2017 paper as `Q = min(Q_Li, Q_neg, Q_pos)`. Calendar and cycling mechanisms compete — whichever causes more fade at a given point in time controls the observed capacity. This is the approach adopted in the 2017 fitted model.

### Hypothesis (iii): Multiplicative

```
Fade_total = Fade_calendar × Fade_cycling
```

Based on the Deshpande et al. (2012) model of coupled chemical degradation and fatigue mechanics. Cycling-induced microcracks in the SEI expose fresh electrode surface, accelerating calendar-like SEI formation on the new surface. This creates a coupled, accelerating degradation path.

### Model Selection Approach

The paper proposes a **statistical model selection procedure**: fit multiple hypothesis models to the same aging dataset, evaluate goodness-of-fit statistics, and down-select the best model. The framework treats each hypothesis as a set of trial functions that are regressed to cell-level aging data. This is how they arrived at the `min(Q_Li, Q_neg, Q_pos)` structure in the 2017 paper — it was the hypothesis that best fit the Kokam NMC data.

**Implication for DUET:** The coupling hypothesis may need to change for different cell chemistries. LFP/graphite may be better described by additive coupling (Schmalstieg-type) while NMC/graphite may favor the competing-mechanism (min) approach. The model framework should support pluggable coupling modes.

---

## Degradation Mechanism Details

### What Degrades: Two Quantities

1. **Capacity fade** — measured Ah capacity decreases over time
2. **Resistance growth** — measured impedance increases over time

Both are tracked independently because they have different implications: capacity fade limits energy, resistance growth limits power.

### What Causes Degradation: Two Physical Processes

1. **Lithium loss** — cyclable Li consumed by side reactions (primarily SEI growth). Reduces capacity.
2. **Active site loss** — electrode material damage/isolation. Reduces both capacity and increases resistance.

These map directly to the 2017 model's Q_Li (lithium-limited capacity) and Q_neg (negative electrode site-limited capacity).

### The Electrochemo-Mechanical Fatigue Story

The paper highlights the Deshpande et al. model as a particularly interesting degradation pathway:

1. Graphite expands/contracts during cycling (up to 8% volume change)
2. This mechanical strain causes microcracks in the SEI layer
3. Fresh graphite surface is exposed
4. New SEI forms on the exposed surface, consuming more lithium
5. As more sites are damaged, remaining sites bear more stress → self-reinforcing

This produces three distinct lifetime phases:
- **BOL:** Rapid fade (initial SEI formation + break-in cracking)
- **MOL:** Decelerating fade (SEI growth is diffusion-limited, cracking rate stabilizes)
- **EOL:** Accelerating fade (accumulated damage creates a cascade — the "knee" in capacity curves)

The 2017 model captures the BOL and MOL phases well. The EOL acceleration ("knee") is harder to predict and is acknowledged as needing further work.

---

## Control Applications

The paper briefly describes two control applications using degradation models — these are relevant to DUET's future Task 3 (dispatch optimization):

### HEV Supervisory Control

Goal: downsize battery by 50% while meeting 10-year lifetime. The controller uses the degradation model in real-time to adjust the power split between engine and battery, avoiding operating conditions that would accelerate degradation.

### PHEV Active Cell Balancing

Goal: extend battery life by 20%. Cell-to-cell variation within a pack means some cells degrade faster. An active balancing controller uses per-cell degradation models to equalize aging rather than just equalizing SOC.

**Implication for DUET:** The cell balancing application connects directly to TWAICE's diagnostic case studies (cell imbalance detection, voltage spread analysis). DUET's model-vs-actual comparison could flag when cell-to-cell variation exceeds model predictions, indicating a need for rebalancing or cell replacement.

---

## Practical Guidance for Aging Test Design

The paper offers implicit guidance on how many aging tests are needed to parameterize a degradation model:

- **~5 different degradation mechanisms** must be included in a model to faithfully reproduce resistance and capacity fade
- **20–30 aging test conditions** are needed to cover the parameter space
- **6–12 months of accelerated aging data** are needed to extrapolate to 10–15 year lifetime
- **3–5 temperature levels** including cold and hot extremes
- Storage tests at various SOC levels (calendar aging characterization)
- Cycling tests across DOD, C-rate, and temperature (cycle aging characterization)

For DUET's PoC, this means relying on published aging datasets (like the Kokam data from the 2017 paper) rather than generating new test data. The model structure should be chemistry-pluggable so that when Enurgen's customers provide cell-specific aging data, the parameters can be re-fitted.

---

## Relationship to Other NREL Papers in This Repo

This paper is the **theoretical foundation** that connects two other references:

```
[This paper, 2015]           →  Theory, framework, mechanism taxonomy
    ↓
[Smith et al. 2017, 67102]   →  Fitted model with parameters for NMC/graphite
    ↓
[DiOrio et al. 2015, 64641]  →  Full SAM simulation architecture using these models
```

Together, these three papers document the complete intellectual lineage of SAM's battery degradation modeling, from theory → parameterization → system integration.

---

## Implications for DUET BESS Module

### For Task 1 — Landscape Survey

This paper should be cited as the theoretical basis for NREL's degradation modeling approach. The failure mode taxonomy (Table I) is directly reusable in the landscape survey as a framework for comparing how different tools handle different degradation mechanisms:

| Mechanism | SAM/NREL | TWAICE | PyBaMM | DUET (Target) |
|---|---|---|---|---|
| Chemical (calendar SEI) | Yes (√t model) | Yes (monitoring) | Yes (physics-based) | Yes (Task 2B) |
| Electrochemo-mechanical (cycling) | Yes (site loss model) | Yes (monitoring) | Yes (physics-based) | Yes (Task 2B) |
| Thermal coupling | Yes (Arrhenius) | Yes (temperature spread analytics) | Yes (thermal-electrochemical coupling) | Yes (Task 2A thermal model) |
| Cell-to-cell variation | No | Yes (core competency) | Limited | Future extension |

### For Task 1 — I/O Spec

The paper's aging test matrix (20–30 conditions, 3–5 temperatures, multiple SOC/DOD levels) defines what manufacturer-supplied data would be needed to fully parameterize a chemistry-specific degradation model. For the PoC, DUET can use published parameters. For production use, Enurgen would need either manufacturer-provided aging curves or access to published aging datasets for the target cell chemistry.

### For Task 2B — Degradation Model

Key design decisions informed by this paper:

1. **Support multiple coupling hypotheses** — additive, competing (min), and multiplicative coupling between calendar and cycle aging. Different chemistries may favor different couplings.

2. **The √t trajectory is the baseline** — any deviation from √t capacity fade indicates a non-SEI mechanism is active. This is diagnostically valuable for model-vs-actual comparison.

3. **Plan for the "knee"** — the EOL acceleration phase where degradation suddenly speeds up is not well-captured by the 2017 model. DUET should at minimum flag when predicted degradation trajectories approach conditions where knee behavior is expected.

4. **Temperature is not a separate mechanism — it modulates everything.** Every degradation rate coefficient needs Arrhenius temperature dependence. Don't model "thermal degradation" as a separate pathway.

5. **The model needs 8+ state variables** — capacity and resistance each need multiple states tracking different mechanisms. The state-variable formulation enables time-stepping through arbitrary dispatch profiles, which is essential for DUET's simulation use case.
