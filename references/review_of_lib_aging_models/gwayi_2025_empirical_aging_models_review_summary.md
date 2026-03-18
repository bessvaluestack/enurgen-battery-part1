# Review — Li-ion Battery Empirical and Semi-Empirical Aging Models for Off-Grid RES

**Source:** Engineering Reports, 2025; 7:e70169 (Open Access)  
**Authors:** Isaac Gwayi, Sarah Paul Ayeng'o, Cuthbert Z. M. Kimambo (University of Dar es Salaam)  
**Published:** 2025 (Received Feb 2025, Accepted April 2025)  
**DOI:** `https://doi.org/10.1002/eng2.70169`  
**File:** `Engineering_Reports_-_2025_-_Gwayi_-_A_Review_of_Lithium_Ion_Battery_Empirical_and_Semi_Empirical_Aging_Models_for_Off_Grid.pdf`  
**Funding:** None (university research)

---

## Paper Summary

This is a **systematic review** of empirical and semi-empirical (EM) aging models for Li-ion batteries, specifically aimed at identifying models suitable for battery management systems (BMS) in off-grid renewable energy systems. The paper extracts 13 distinct model formulations from the literature, categorizes them by structure, and compares them on three axes: computational complexity, whether they capture C-rate effects (current fluctuations), and whether they model capacity fade, resistance increase, or both.

**Key value for DUET:** This paper is a curated catalog of the entire empirical/semi-empirical degradation model landscape as of 2025 — every model is presented with its actual equations, parameter counts, and stress factor coverage. It bridges the gap between the NREL Smith et al. model (which DUET targets for Task 2B) and the broader universe of alternative formulations that Enurgen might encounter from customers or competitors. It also provides a useful taxonomy for classifying model complexity and a comprehensive map of which aging stress factors matter most across the literature.

---

## Model Taxonomy — Four Categories

The paper's most useful contribution is a clean four-category classification of empirical aging models based on how they handle calendar vs. cycle aging:

| Category | Abbreviation | Description | Models Found |
|---|---|---|---|
| Calendar aging only | CAOM | Captures time-dependent degradation only | 1 |
| Cycle aging only | CYAOM | Captures cycling-dependent degradation only | 4 |
| Calendar + cycle (separated) | CCYASM | Separate equations for calendar and cycle, summed or composed | 5 |
| Calendar + cycle (combined) | CCYACM | Single unified equation capturing both aging modes | 3 |

This taxonomy maps directly to a design decision DUET faces: should the degradation model use separated or combined formulations for calendar and cycle aging? The NREL Smith et al. 2017 model (67102) uses a **competing-mechanism (min)** structure, which doesn't fit neatly into any of Gwayi's categories — it's closest to CCYASM but with a `min()` coupling rather than additive coupling.

---

## Aging Mechanism Review

The paper provides a concise but complete review of Li-ion degradation mechanisms, organized by electrode. This is useful as a cross-reference to the more detailed taxonomy in the NREL 64171 paper (Smith et al. 2015).

### Three Degradation Modes

| Mode | Abbreviation | Physical Meaning | Effect |
|---|---|---|---|
| Loss of Lithium Inventory | LLI | Cyclable Li consumed by side reactions (SEI, plating) | Capacity fade |
| Loss of Active Material | LAM | Electrode material structural degradation (cracking, exfoliation) | Capacity fade + resistance increase |
| Conductivity Loss | CL | Degradation of electrical pathways (binder, current collector) | Resistance increase |

### Anode Aging Mechanisms (Graphite)

1. **SEI layer formation** — The dominant mechanism. Continuous electrolyte decomposition at the anode surface. Growth rate depends on temperature (Arrhenius), SOC (lower anode potential → faster decomposition), and cycling (mechanical cracking exposes fresh surface). Produces the characteristic √t fade trajectory.

2. **Lithium plating** — Occurs below ~20°C when diffusion rate drops and anode intercalation potential approaches metallic lithium potential. Also triggered by high C-rates and low SOC. Causes LLI and dendrite growth (safety risk).

3. **Mechanical stress** — Volume changes during (de)intercalation cause phase transitions, cracking (LLI + LAM), structural damage (LAM), and contact loss (CL). Can also reduce electrode porosity.

4. **Transition metal dissolution** — High voltage/temperature forms hydrogen fluoride from electrolyte impurities, corroding cathode metals (Mn, Ni, Co, Fe). Dissolved metals migrate to anode, catalyze SEI growth, and induce dendrite formation.

5. **Other** — Graphite exfoliation (high current), particle cracking (mechanical stress), binder decomposition (high voltage/temperature).

### Cathode Aging Mechanisms

1. **CEI layer formation** — Analogous to SEI but at cathode. Reduces Li-ion conductivity, increases resistance.
2. **Mechanical stress** — Phase transitions during cycling cause volume changes; magnitude is material-dependent.
3. **Transition metal dissolution** — Structural cathode degradation (LAM).

### Mapping to NREL Model States

| Gwayi Mechanism | NREL 67102 State Variable | NREL Model Term |
|---|---|---|
| SEI growth (calendar) | Q_Li (lithium loss) | b₁·t^(1/2) — calendar SEI |
| SEI cracking during cycling | Q_Li (lithium loss) | b₂·N — cycling Li loss |
| Mechanical stress at anode | Q_neg (site loss) | c₂ term — self-reinforcing fatigue |
| Lithium plating | Not explicitly modeled | Partially captured by negative E_a in b₂ and c₂ |
| CEI / cathode surface | Q_pos (minor) | d₃ term — initial wetting |
| Conductivity loss | R (resistance model) | a₁, a₂, a₄ terms |

---

## Literature Survey — Calendar and Cycle Aging Studies

### Calendar Aging Studies (Table 2 in paper)

19 studies surveyed covering LFP and NMC chemistries. Key findings:

- **All 19 studies** use SoC, temperature, and time as stress factors — these are universally accepted calendar aging drivers
- **89%** model capacity fade; **63%** model resistance increase; **53%** model both
- Temperature ranges tested: 0–70°C; SOC ranges: 0–100%
- LFP and NMC are the only chemistries with substantial calendar aging data in the empirical literature

### Cycle Aging Studies (Table 3 in paper)

20 studies surveyed. Key findings:

- **100%** include temperature and C-rate as stress factors
- **85%** include SOC; when ΔSoC/DoD is counted, effectively all do
- **95%** model capacity fade; **50%** model resistance increase; **45%** model both
- Temperature ranges tested: -30°C to 70°C; DoD ranges: 5–100%; C-rates: C/20 to 18C
- Cycle aging data is more diverse in operating conditions than calendar aging data

### Cross-Cutting Observation

The paper quantifies a gap that matters for DUET: **resistance increase is under-modeled** relative to capacity fade. Only 46% of all extracted models capture resistance growth, versus 92% for capacity fade. This is significant because resistance growth determines power capability limits, which are critical for grid BESS dispatch (a battery can still have 90% capacity but fail to deliver rated power if resistance has doubled).

---

## The 13 Extracted Models — Detailed Catalog

This is the paper's core contribution. Each model is presented with its full equation, complexity metrics, and coverage flags. Below is a condensed version with the information most relevant to DUET.

### Complexity Metric

The paper uses two measures: (1) number of variables and parameters, and (2) number of elementary operations (additions, multiplications, exponentials, etc.). The sum gives a "total complexity" score.

### Model Summary Table

| Code | Type | Complexity | C-rate | Cap. Fade | Res. Increase | Chemistry | Key Reference |
|---|---|---|---|---|---|---|---|
| CAOM1 | Calendar only | 18 | No | No | Yes | LFP | Stroe et al. 2018 |
| CYAOM1 | Cycle only | 26 | No | Yes | No | LFP | Sarasketa-Zabala et al. 2015 |
| CYAOM2 | Cycle only | 17 | Yes | Yes | No | LFP | Wang et al. 2011 |
| CYAOM3 | Cycle only | 56 | Yes | Yes | Yes | NMC-LMO | Cordoba-Arenas et al. 2015 |
| CYAOM4 | Cycle only | 67 | Yes | Yes | Yes | LFP & NMC | Motapon et al. 2020 |
| CCYASM1 | Separated | 26 | Yes | Yes | No | NMC | Mauri et al. 2019 |
| CCYASM2 | Separated | 70 | No | Yes | Yes | LFP | Swierczynski et al. 2015 |
| CCYASM3 | Separated | 61 | Yes | Yes | No | NMC-LMO | Wang et al. 2014 |
| CCYASM4 | Separated | 46 | No | Yes | Yes | LFP | Marongiu et al. 2015 |
| CCYASM5 | Separated | 69 | No | Yes | Yes | NMC | Schmalstieg et al. 2014 |
| CCYACM1 | Combined | 42 | Yes | Yes | Yes | NMC-LMO & NCA | Baghdadi et al. 2016 |
| CCYACM2 | Combined | 28 | No | Yes | No | LFP | Lam & Bauer 2013 |
| CCYACM3 | Combined | 83 | Yes | Yes | No | LFP | Schimpe et al. 2018 |

### Notable Model Structures

**CYAOM2 (Wang et al. 2011)** — The simplest model that captures C-rate effects:
```
C_loss = B · exp[(-31700 + 370.3·C_rate) / (R·T)] · Ah^0.55
```
Arrhenius temperature dependence with C-rate modifying the activation energy. Only 9 variables/parameters, 8 operations. Cycle-only, LFP chemistry. The Ah^0.55 exponent (less than the √Ah = 0.5 of pure SEI growth) suggests a mix of mechanisms.

**CCYASM5 (Schmalstieg et al. 2014)** — The "holistic" NMC model that's widely cited:
```
Calendar: C_loss = α_cap · t_d^0.75,  R_i = α_res · t_d^0.75
Cycle:    C_loss = α_cap · t_d^0.75 + β_cap · √Ah,  R_i = α_res · t_d^0.75 + β_res · Ah
```
Uses **additive** calendar + cycle coupling (Hypothesis (i) from NREL 64171). The t^0.75 exponent for calendar aging is notably different from the √t (0.5) used by NREL — Schmalstieg found a better fit at 0.75 for their NMC 18650 cells. The cycle aging uses √Ah for capacity fade but linear Ah for resistance — suggesting different underlying mechanisms. Does NOT capture C-rate.

**CCYACM1 (Baghdadi et al. 2016)** — The only model capturing all three: C-rate, capacity fade, and resistance increase, in a combined formulation:
```
C_loss_rate = exp(p_c · C_rate) · exp(q_c · SoC / p_c) · exp(s_c / p_c) · exp(-m_c / (p_c · T))
R_i_rate   = exp(p_r · C_rate) · exp(q_r · SoC / p_r) · exp(s_r / p_r) · exp(-m_r / (p_r · T))
```
Based on Dakin's degradation theory (originally from polymer insulation aging). Moderate complexity (42). Covers NMC-LMO and NCA. However, no DoD dependence — a significant gap for grid BESS where partial cycling is the norm.

**CCYACM3 (Schimpe et al. 2018)** — The most complex model (83), specifically for LFP:
```
C_loss = k_Cal(T, SoC)·√t_d + k_Cyc,HighT(T)·√Ah_Tot + k_Cyc,LowT(T, C_rate_Ch)·√Ah_Ch + k_Cyc,LowT_HighSoC(T, C_rate_Ch, SoC)·Ah_Ch
```
Four separate degradation pathways: calendar SEI, high-temperature cycling, low-temperature cycling (with C-rate), and low-temperature + high-SOC cycling (lithium plating regime). This is the most mechanistically detailed empirical model in the review. The explicit separation of high-T and low-T cycling mechanisms parallels the NREL model's use of positive and negative activation energies.

---

## Key Findings — Quantitative Summary

The paper's Figure 3 and Table 5 yield these statistics across all 13 models:

| Factor | Models Including It | Percentage |
|---|---|---|
| Capacity fade | 12 / 13 | 92% |
| C-rate / current fluctuation | 7 / 13 | 54% |
| Resistance increase | 6 / 13 | 46% |
| All three (C-rate + cap. fade + res. increase) | 3 / 13 | 23% |

### Complexity vs. Coverage Tradeoff

Models that capture all of C-rate, capacity fade, and resistance increase are systematically more complex:

- Models with only capacity fade: average complexity ~26
- Models with capacity fade + C-rate: average complexity ~42
- Models with all three: average complexity ~55

This is a real engineering tradeoff: every additional stress factor roughly doubles the parameter fitting effort while improving fidelity by an incremental (and diminishing) amount.

---

## Models Recommended for Off-Grid BMS

The paper recommends three models for BMS implementation, selected for current-fluctuation representation and manageable complexity:

| Code | Complexity | C-rate | Cap. Fade | Res. Increase | Use Case |
|---|---|---|---|---|---|
| CYAOM2 | 17 | Yes | Yes | No | Cycle aging only, minimum complexity |
| CCYASM1 | 26 | Yes | Yes | No | Calendar + cycle, moderate complexity |
| CCYACM1 | 42 | Yes | Yes | Yes | Full coverage, highest complexity of the three |

The choice depends on whether calendar aging matters (it does for grid BESS — systems sit idle significant fractions of the time) and whether resistance tracking is needed (it is, for power capability monitoring).

---

## Comparison with NREL Smith et al. 2017 (67102)

The NREL model used as DUET's target for Task 2B is notably absent from this review. This is likely because the NREL model doesn't fit cleanly into the "empirical" category — it's semi-empirical with physics-motivated structure (competing mechanisms, electrode-specific states). Comparing it against the review's models:

| Dimension | NREL 67102 | Best in Gwayi Review |
|---|---|---|
| Calendar aging | Yes (√t SEI + break-in) | CCYACM3 (4-pathway) |
| Cycle aging | Yes (site loss, cycling Li loss) | CYAOM4 (fatigue-based) |
| Calendar-cycle coupling | min(Q_Li, Q_neg, Q_pos) — competing | CCYASM5 — additive; CCYACM1 — combined rate |
| C-rate sensitivity | Indirect (via DOD, temperature) | CYAOM2, CCYACM3 — explicit C-rate terms |
| Capacity fade | Yes | 12/13 models |
| Resistance increase | Yes (5 additive terms) | 6/13 models |
| Temperature dependence | Arrhenius (every term) | Arrhenius (most models) |
| DOD dependence | Yes (DOD^β with β=4.54) | 8/13 models (various forms) |
| State variables | 8 | 0–4 (most are stateless algebraic) |
| Chemistry parameterized | NMC/graphite (Kokam 75Ah) | LFP, NMC, NCA, NMC-LMO |
| Validation | 11 cells, 9 conditions, R²=0.99 | Varies; most single-chemistry |
| Complexity (approx.) | ~60–80 (estimated) | 17–83 range |

### Where the NREL Model Exceeds All Reviewed Models

1. **Mechanism decomposition** — The `min(Q_Li, Q_neg, Q_pos)` structure allows diagnosing *which* mechanism is limiting capacity. No model in the Gwayi review offers this.

2. **State-variable formulation** — The 8-state ODE system can be time-stepped through arbitrary dispatch profiles. Most reviewed models are algebraic (capacity loss as a function of cumulative Ah or time), requiring the full history to be known.

3. **Resistance model completeness** — 5 additive resistance terms with distinct physical origins. Only CCYASM5 (Schmalstieg) comes close with separate calendar and cycle resistance factors.

### Where the Reviewed Models Offer Something NREL Doesn't

1. **Explicit C-rate dependence** — The NREL model has no direct C-rate term. CYAOM2 and CCYACM3 show how C-rate modifies activation energy or degradation rate. For high-power BESS applications (frequency regulation, fast-response ancillary services), this matters.

2. **LFP parameterizations** — The NREL model is parameterized for NMC only. Five of the reviewed models have LFP parameters, which is the dominant grid BESS chemistry. CCYACM3 (Schimpe et al.) is particularly relevant — it's LFP-specific with temperature-dependent cycling mechanisms.

3. **Fatigue-based cycle counting** — CYAOM4 (Motapon et al.) uses a fatigue-theory approach with equivalent cycle counting that naturally handles variable-amplitude cycling. This is conceptually cleaner than rainflow counting + DOD_max for irregular dispatch profiles.

4. **Lower complexity options** — For real-time BMS or rapid screening, the simpler models (CYAOM2 at complexity 17) can run orders of magnitude faster than the full NREL model while still capturing the dominant effects.

---

## Reference Map — Key Papers by Chemistry

The review's bibliography is valuable as a chemistry-specific reference guide for aging data:

### LFP/Graphite Aging Data Sources
- Bloom et al. 2001 [67] — Calendar + cycle, 40–70°C
- Swierczynski et al. 2015 [68] — Calendar + cycle, 25–55°C, 4C cycling
- Wang et al. 2011 [82] — Cycle only, -30 to 60°C, C/2 to 10C
- Schimpe et al. 2018 [65] — Calendar + cycle, 0–55°C, comprehensive temperature decomposition
- Sarasketa-Zabala et al. 2015 [84] — Cycle only, 30°C, 1–3.5C, DoD 5–100%
- Marongiu et al. 2015 [80] — Calendar + cycle, 40–70°C, V2G focus

### NMC/Graphite Aging Data Sources
- Schmalstieg et al. 2014 [29] — Calendar + cycle, 35–50°C, "holistic" model
- Ecker et al. 2014 [77] — Calendar + cycle, 35–50°C, 18650 format
- Käbitz et al. 2013 [76] — Calendar + cycle, 25–60°C
- de Hoog et al. 2017 [72] — Calendar + cycle, 10–50°C, real-life profile validation
- Wang et al. 2014 [64] — Calendar + cycle, NMC-LMO blend, 10–46°C
- Yoshida et al. 2010 [75] — Space application, 0–60°C, wide SOC range

### NCA Aging Data Sources
- Baghdadi et al. 2016 [73] — Calendar + cycle, 30–60°C (NMC-LMO & NCA)

---

## Implications for DUET BESS Module

### For Task 1 — Landscape Survey

This review paper should be cited as the **most comprehensive recent catalog of empirical degradation models** (2025). It complements the NREL papers by providing:

1. A taxonomy (CAOM/CYAOM/CCYASM/CCYACM) for classifying any degradation model DUET encounters
2. Quantitative evidence that capacity fade is the primary focus of the field (92% of models) while resistance increase is under-addressed (46%) — which positions DUET's inclusion of resistance modeling (per the NREL model) as a differentiator
3. A complexity benchmark: the simplest useful cycle aging model has 17 total operations, the most complete has 83. DUET's target (NREL 67102) falls in the upper range but delivers mechanism decomposition that none of the simpler models can match

### For Task 1 — I/O Spec

The review confirms the universal stress factors across the literature:

**Calendar aging inputs (unanimous across 19 studies):** Temperature, SOC, time

**Cycle aging inputs (near-unanimous across 20 studies):** Temperature, C-rate, SOC/DOD

**The gap:** Only 54% of models explicitly include C-rate. For DUET's I/O spec, C-rate should be flagged as a "gap input" — not always available from simple dispatch schedules (which specify power, not current), but derivable from the voltage model. This is another argument for the sub-model pipeline architecture (dispatch → voltage → current → degradation).

### For Task 2B — Degradation Model Design

Key design decisions informed by this review:

1. **The NREL model is the right choice for DUET's core** — it's more complete than any single model in this review, with mechanism decomposition that enables model-vs-actual diagnostics. But DUET's architecture should allow swapping in simpler models (e.g., CYAOM2-class) for rapid screening or when full parameterization isn't available.

2. **C-rate sensitivity needs a plan** — The NREL model lacks an explicit C-rate term, which 54% of the literature considers important. Two options: (a) add a C-rate modification factor to the b₂ or c₂ terms in the NREL model, informed by CCYACM3's approach; or (b) acknowledge C-rate as captured indirectly through temperature (higher C-rate → more I²R heating → higher cell temperature → faster degradation via Arrhenius terms). Option (b) is valid if the thermal model is accurate.

3. **Calendar-cycle coupling is chemistry-dependent** — This review shows additive coupling (Schmalstieg, CCYASM5) used for NMC, while the NREL model uses competing-mechanism coupling (min). Gwayi doesn't resolve this — the review doesn't compare coupling approaches. DUET should support pluggable coupling modes, as recommended in the NREL 64171 summary.

4. **LFP needs its own parameter set** — 8 of the 13 models have LFP parameterizations. The NREL model structure is generalizable, but its published parameters are NMC-only. For DUET to support LFP (dominant in grid BESS), the Schimpe et al. 2018 (CCYACM3) parameterization is the most detailed open reference — it explicitly models the low-temperature lithium plating pathway that is particularly important for LFP.

5. **Resistance modeling is a differentiator** — With only 46% of the field modeling resistance increase, DUET's inclusion of the NREL 5-term resistance model is a genuine competitive advantage for power-limited applications (ancillary services, frequency regulation). The I/O spec should include resistance-derived KPIs (power capability, voltage sag under load).

### For Task 2B — Fallback / Simplified Models

DUET should consider implementing a simplified fallback degradation model for cases where full NREL-style parameterization isn't available (e.g., customer provides only a warranty-style cycle count curve). The review suggests a hierarchy:

| Tier | Model Class | Inputs Needed | When to Use |
|---|---|---|---|
| Full | NREL 67102-type | 20+ Arrhenius parameters, voltage curves | Full parameterization available (lab data or published params for chemistry) |
| Standard | CCYASM5-type (Schmalstieg) | Calendar + cycle aging factors, voltage-based | Manufacturer provides calendar + cycle aging curves |
| Basic | SAM lookup table (per 64641) | DoD vs. cycle count table | Only warranty-sheet data available |
| Minimal | CYAOM2-type | Single Arrhenius + Ah throughput | Only basic cycle life rating available |

This tiered approach aligns with the "datasheet-parameterizable" principle from SAM while allowing graceful degradation when less data is available.

---

## Relationship to Other Papers in This Repo

```
[NREL 64171, 2015]                    →  Degradation mechanism taxonomy + coupling hypotheses
    ↓
[NREL 67102, 2017]                    →  Fitted semi-empirical model for NMC/graphite
    ↓
[NREL 64641, 2015]                    →  SAM simulation architecture using these models
    ↓
[Gwayi et al. 2025, this paper]      →  Catalog of alternative empirical models across the field
                                          (validates NREL approach as state-of-art; identifies gaps in C-rate and LFP coverage)
```

This paper sits "beside" the NREL lineage rather than extending it — it surveys the broader field and provides context for why the NREL model's choices (mechanism decomposition, competing-mechanism coupling, 8 state variables) represent a specific and defensible point in the model design space.
