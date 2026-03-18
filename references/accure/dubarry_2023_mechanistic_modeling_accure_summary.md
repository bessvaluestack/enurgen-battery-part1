# Mechanistic Degradation Modeling — Dubarry et al. 2023 & ACCURE Approach

**Paper:** Dubarry, M., Agrawal, V., Hüske, M., Kuipers, M. "Accurate LLI and LAM_PE Estimation Using the Mechanistic Modeling Approach with Layered Oxides." *J. Electrochem. Soc.*, 170, 070503, 2023. (Open Access, CC BY 4.0)  
**DOI:** `10.1149/1945-7111/ace21c`  
**Authors:** Matthieu Dubarry (Hawai'i Natural Energy Institute, UH Mānoa), Vishal Agrawal, Martin Hüske, Matthias Kuipers (ACCURE Battery Intelligence GmbH, Aachen)  
**Companion Blog:** ACCURE, "Mechanistic Modeling Battery Aging" (`accure.net/blogs/mechanistic-modeling-battery-aging`)  
**File:** `Dubarry_2023_J__Electrochem__Soc__170_070503.pdf`  
**Funding:** U.S. Office of Naval Research + ACCURE Battery Intelligence

---

## Paper Summary

This paper identifies and fixes a systematic error in how most mechanistic degradation models handle **loss of active material on the positive electrode (LAM_PE)** for layered oxide cathodes (NMC, NCA, LCO) — materials where the cathode is never fully delithiated during normal operation. The error causes lithiation-based models to underestimate LAM_PE and overestimate LLI, and causes Q/SOC-based models to overestimate LLI. The paper proposes corrected equations for both model families and proves that total LAM_PE is invariant regardless of which lithiation range is used.

**Why this matters for DUET:** This paper sits at a modeling layer between the semi-empirical approach (NREL Smith et al.) and full physics-based models (PyBaMM DFN). Mechanistic models are what ACCURE — one of the commercial tools in the landscape survey — actually uses in production. Understanding this approach clarifies where mechanistic modeling fits in DUET's multi-model framework and reveals a diagnostic capability (LLI/LAM decomposition from voltage curves) that is directly relevant to DUET's model-vs-actual comparison feature.

---

## The Four-Tier Model Taxonomy (from ACCURE Blog)

The ACCURE blog post provides a clean four-category taxonomy that is useful for the landscape survey because it explicitly positions their approach relative to the alternatives. This taxonomy maps onto (and extends) the model categories already documented in this repo:

| Tier | Description | Parameterization | Insight Level | DUET Repo Mapping |
|---|---|---|---|---|
| **Empirical / Data-driven** | Purely statistical correlations from large datasets; no battery physics assumed | Large operational datasets | Black box — correlations only | Gwayi catalog (CYAOM, CCYACM models) |
| **Semi-empirical** | Empirical models guided by domain expertise; known stress factors (T, SOC, DOD) used as inputs | Aging test data + expert selection of stress factors | Aggregate health (capacity, resistance) | NREL Smith et al. 2017 (67102); Schmalstieg et al. 2014 |
| **Mechanistic** | Tracks electrode-level degradation modes: LLI, LAM_NE, LAM_PE; derived from voltage curve analysis | Half-cell OCV data + full-cell cycling data | Electrode-level — *which* degradation mode dominates | **This paper**; ACCURE's production approach; Dubarry 'alawa toolbox |
| **Physical-chemical** | First-principles electrochemical models (DFN, SPMe) with degradation submodels | Extensive cell characterization (30+ physical parameters) | Mechanism-level — *why* degradation occurs | PyBaMM DFN + degradation options |

The key positioning insight: mechanistic models are the **minimum complexity level that provides electrode-level diagnostic decomposition** (LLI vs LAM_NE vs LAM_PE). Semi-empirical models (like NREL's) track aggregate capacity and resistance but can't attribute fade to specific electrodes. Physics-based models can do everything mechanistic models do and more, but at much higher parameterization cost.

---

## What Mechanistic Models Are

### Core Principle

A mechanistic model reconstructs a full cell's voltage response by matching (overlaying) the voltage curves of the positive and negative electrodes measured separately against lithium metal (half-cell data). The full cell voltage is simply:

```
V_FC(Q) = V_PE(Q) − V_NE(Q)
```

By adjusting how the two electrode curves are aligned, stretched, and shifted relative to each other, the model can emulate the effects of different degradation modes on the full cell voltage profile.

### The Three Degradation Modes

| Mode | Abbreviation | Physical Meaning | Effect on Electrode Matching |
|---|---|---|---|
| Loss of Lithium Inventory | LLI | Cyclable Li consumed by side reactions (SEI, plating) | Shifts the relative alignment (offset/slippage) between PE and NE curves |
| Loss of Active Material — Negative Electrode | LAM_NE | Graphite anode material lost (cracking, isolation) | Shrinks the NE capacity window |
| Loss of Active Material — Positive Electrode | LAM_PE | Cathode material lost (structural degradation) | Shrinks the PE capacity window |

### Two Framework Families

The paper identifies two families of mechanistic model implementations:

**Q/SOC-based models** (pioneered by Bloom et al. 2005, Dubarry et al. 2012):
- Match electrodes using capacity (Q) or state of charge (SOC) as the x-axis
- Require minimum two parameters: loading ratio (LR) between PE and NE capacity, and their offset (OFS)
- Fewer parameters → faster for large-scale synthetic dataset generation
- The 'alawa toolbox (Dubarry) uses this approach

**Lithiation-based models** (Ge et al. 2017, Birkl et al. 2015, and many others):
- Match electrodes using lithiation (stoichiometry θ) as the x-axis
- Require minimum four parameters: min and max lithiation for each electrode
- More physically intuitive but more parameters to fit or scan

The paper cites over 37 published mechanistic model frameworks, indicating this is a mature and active field.

---

## The Inaccessible Lithium Problem

### The Issue

For layered oxide cathodes (NMC, NCA, LCO), the cathode is **never fully delithiated** during normal operation. At standard cutoff voltages, significant lithium remains in the cathode:

| Cathode Material | Cutoff Voltage | Lithiation at Cutoff (x_cutoff) | % Lithium Remaining |
|---|---|---|---|
| NMC111 | 4.2 V | ~0.42 | 42% |
| NMC111 | 4.3 V | ~0.33 | 33% |
| LCO | 4.2 V | ~0.50 | 50% |
| NCA | 4.2 V | ~0.40 | 40% |
| NMC811 | 4.4 V | Minimal | ~0% |

This "inaccessible lithium" creates a subtle but important modeling error. When cathode active material is lost (LAM_PE), it's lost *with the lithium still inside it*. This lithium isn't available for cycling anymore, but it also isn't consumed by a side reaction — it's trapped in the degraded material.

### How the Error Manifests

**In lithiation-based models:** Most implementations assume LAM_PE means losing fully delithiated electrode material. But real LAM_PE always includes lithium at x_cutoff concentration. This causes:
- Incorrect voltage response prediction (artificial SOC shift at end of charge)
- Underestimation of total LAM_PE (only counting the delithiated portion)
- Overestimation of LLI (lithium trapped in lost material is misattributed to LLI)
- False prediction of "PE-induced lithium plating" (an artifact, not a real risk)

**In Q/SOC-based models:** These handle the voltage response correctly by default (they only work with usable capacity), but still overestimate LLI because the electrode size used as the reference is smaller than the true electrode.

### The Paper's Key Insight: Decomposing LAM_PE

The lost active material can be decomposed into two components:

```
LAM_PE = LAM_dePE + LAM_liPE                                    [Eq. 1]
```

Where LAM_dePE is the delithiated portion and LAM_liPE is the portion still containing lithium. For the "true" (full-delithiation) scale:

```
LAM_liPE_True = (x_cutoff / (1 − x_cutoff)) · LAM_dePE_True    [Eq. 2]
```

The relationship between true and usable scales:

```
LAM_dePE_True = (1 − x_cutoff) · LAM_dePE_Usable               [Eq. 3]
LAM_liPE_True = x_cutoff · LAM_dePE_Usable                      [Eq. 4]
```

And the proof that total LAM_PE is invariant:

```
LAM_PE_True = (1 − x_cutoff) · LAM_dePE_Usable + x_cutoff · LAM_dePE_Usable
            = LAM_dePE_Usable = LAM_PE_Usable                    [Eq. 5]
```

This proves that total LAM_PE is the same regardless of which lithiation range is considered, but the decomposition into LLI and LAM changes.

### Practical Consequence

The corrected model ensures that when the PE voltage response is "shrunk" to emulate LAM_PE, it is shrunk from **both sides** (accounting for both delithiated and lithiated losses). The shrunken electrode curve always crosses the pristine curve at the cutoff voltage, negating any risk of artificial excess capacity.

For NMC111 at 4.3 V (x_cutoff ≈ 0.33), a reported 20% LAM_PE in a Q/SOC model corresponds to only 13.33% "true" LAM_PE if full delithiation were considered (20 × 100/150 = 13.33). The remaining 6.67% is lithium trapped in the lost material (x_cutoff × LAM_PE = 0.33 × 20 = 6.67).

---

## Mapping to NREL Model States

The mechanistic model's degradation modes map directly onto the NREL Smith et al. 2017 state variables, but at a different level of granularity:

| Mechanistic Mode | NREL 67102 State(s) | Relationship |
|---|---|---|
| LLI | Q_Li (lithium loss) | Direct — both track cyclable lithium consumed by side reactions. NREL decomposes further into calendar SEI (b₁·√t), cycling Li loss (b₂·N), and break-in (b₃). Mechanistic models report aggregate LLI. |
| LAM_NE | Q_neg (negative site loss) | Direct — both track graphite active material degradation. NREL models this as self-reinforcing fatigue (c₂ term). |
| LAM_PE | Not explicitly tracked in NREL model | Gap — the NREL model has Q_pos but treats it as a minor initial wetting effect. Mechanistic models show LAM_PE can be significant for layered oxides. |
| Kinetic limitations | R (resistance model) | Indirect — NREL tracks resistance growth through 5 additive terms. Mechanistic models detect kinetic limitations through voltage curve distortion rather than resistance measurement. |

### Key Gap Identified

The NREL model essentially assumes Q_pos is negligible (only a small initial wetting effect). Dubarry et al. show that for layered oxide cathodes (NMC, NCA, LCO), **LAM_PE can be significant and must be tracked properly**. Moreover, the ratio of LLI to LAM is an important safety indicator — the paper cites work showing that an acceleration in the LLI/LAM ratio can signal impending rapid capacity loss ("knee" behavior).

**Implication for DUET:** If DUET's degradation model (Task 2B) tracks only Q_Li and Q_neg (per the NREL model), it will miss LAM_PE-driven degradation. For NMC and NCA chemistries — which are common in grid BESS — this could be a blind spot. The architecture should at minimum allow adding a LAM_PE state variable, even if the PoC uses only the NREL two-mechanism (Q_Li, Q_neg) structure.

---

## ACCURE's Production Approach

The blog post reveals how ACCURE uses mechanistic modeling in their commercial product:

**What they do:** Track LLI, LAM_NE, and LAM_PE from operational voltage data. The mechanistic model reconstructs the degradation mode decomposition from full-cell charge/discharge curves without requiring disassembly or half-cell measurements.

**Why it matters:** This is a **non-invasive diagnostic** technique. Given operational charge/discharge data (which SCADA systems already collect), the mechanistic model can identify which electrode is limiting and which degradation mode is dominant. This is exactly the kind of model-vs-actual diagnostic that DUET's architecture should support.

**Their collaboration with Dubarry:** The paper itself is a joint ACCURE + HNEI publication, indicating that ACCURE's production models are informed by academic state-of-the-art mechanistic modeling. The 'alawa toolbox (Dubarry's open-source MATLAB code) is the reference implementation for the Q/SOC-based framework.

**ACCURE's positioning:** They explicitly position mechanistic modeling as a "compromise" — more insight than semi-empirical models (can identify *which electrode* is degrading and *which mode* dominates), less parameterization burden than physics-based models (doesn't need DFN-level characterization). They also note that they select the right modeling approach for the right conditions, implying a multi-model strategy similar to what DUET should adopt.

---

## Implications for DUET BESS Module

### For Task 1 — Landscape Survey (ACCURE Section)

ACCURE should be characterized in the landscape survey as using a **mechanistic modeling approach** for degradation diagnostics. Key points:

- Tracks three degradation modes (LLI, LAM_NE, LAM_PE) from operational voltage data
- Non-invasive — works with standard charge/discharge curves from SCADA
- Published correction for LAM_PE estimation on layered oxides (this paper)
- Positions between semi-empirical (NREL) and physics-based (PyBaMM) on the fidelity spectrum
- Joint academic research with HNEI demonstrates technical depth

### For Task 1 — I/O Spec

The mechanistic approach reveals additional input requirements and KPI possibilities:

**Inputs needed for mechanistic diagnostics:**
- Half-cell OCV curves for both electrodes (PE and NE vs Li metal) — these are chemistry-specific reference data, not operational measurements
- Full-cell charge/discharge voltage curves at low C-rate (C/10 to C/25) — periodic reference tests
- Cutoff voltages (charge and discharge limits)
- For layered oxides: the lithiation at cutoff (x_cutoff) — derivable from published data

**Additional KPIs enabled:**
- LLI (%) — fraction of cyclable lithium consumed
- LAM_NE (%) — fraction of negative electrode active material lost
- LAM_PE (%) — fraction of positive electrode active material lost
- LLI / LAM ratio — safety indicator for accelerating degradation ("knee" detection)
- Electrode utilization window — identifies how close each electrode operates to its limits

### For Task 1 — Architecture

The mechanistic modeling approach informs DUET's architecture in several ways:

1. **Voltage curve analysis as a diagnostic layer.** DUET's model-vs-actual comparison should include a mechanism for analyzing periodic reference charge curves (low-rate characterization tests) to extract LLI/LAM decomposition. This is independent of the core simulation engine — it's a post-hoc diagnostic applied to measured data.

2. **Three-state degradation tracking.** Even if the core simulation uses the NREL two-mechanism model (Q_Li + Q_neg), the architecture should support an optional third state (LAM_PE) for chemistries where cathode degradation is significant. This future-proofs for NMC and NCA systems.

3. **The x_cutoff correction matters.** If DUET ever implements lithiation-based degradation tracking, the Dubarry correction (Equations 1–5 in the paper) must be applied to avoid systematic LLI overestimation. This is a known error in "most state-of-the-art mechanistic models" per the paper.

### For Task 2B — Degradation Model Design

Key design decisions informed by this paper:

1. **Track LAM_PE explicitly for layered oxides.** The NREL model's Q_pos term is only an initial wetting effect. For NMC/NCA BESS systems, cathode degradation (structural, transition metal dissolution) can be significant. The degradation module should have a placeholder for LAM_PE even in the PoC.

2. **Support voltage-curve-based diagnostics.** The mechanistic approach works on measured voltage profiles, not on predicted degradation curves. DUET should provide a pathway for comparing simulated vs. measured voltage profiles and extracting degradation mode decomposition from the residuals.

3. **LLI/LAM ratio as a safety KPI.** The paper cites work (Dubarry et al. 2018, Attia et al. 2022) showing that the ratio of LLI to LAM is a leading indicator of accelerating degradation and potential safety events. DUET should compute and report this ratio as a KPI.

4. **Chemistry-specific x_cutoff data.** The paper provides x_cutoff values for NMC111, LCO, NCA, and NMC811 at standard cutoff voltages. These should be included in DUET's chemistry parameter sets as they affect how LAM_PE is interpreted.

---

## Reference Map — Key Papers Cited

The paper's 54 references are a near-complete bibliography of the mechanistic modeling field. The most relevant for DUET:

| Reference | Contribution | DUET Relevance |
|---|---|---|
| Bloom et al. 2005 [2] | Pioneering Q/SOC-based mechanistic framework | Historical — first electrode matching model |
| Dubarry et al. 2012 [5] | 'alawa toolbox — reference Q/SOC implementation | Open-source reference implementation |
| Birkl et al. 2015, 2017 [28–30] | Lithiation-based framework with degradation diagnostics | Frequently cited diagnostic methodology |
| Lee et al. 2019, 2020 [26, 27] | Lithiation-based model with NMC111 parameterization | Example of models affected by the x_cutoff issue |
| Lu et al. 2021 [38] | Prior identification of inaccessible lithium correction | Equations for lithiation-based model correction |
| Weng et al. 2023 [39] | Additional inaccessible lithium analysis | Complementary correction approach |
| Dubarry & Anseán 2022 [50] | PE not usually limiting at end of discharge | Explains why LAM_PE doesn't cause FC capacity loss until threshold |
| Dubarry et al. 2018 [43] | LLI/LAM ratio as degradation acceleration indicator | Safety KPI methodology |
| Attia et al. 2022 [44] | LAM_PE-induced plating pathway | Safety-relevant degradation coupling |

---

## Relationship to Other Reference Summaries

```
DEGRADATION MODEL SPECTRUM
══════════════════════════

                          Insight Level
                    ┌──────────────────────────────┐
                    │                              │
  Empirical ──→ Semi-empirical ──→ Mechanistic ──→ Physics-based
  (Gwayi)      (NREL 67102)       (THIS PAPER)    (PyBaMM DFN)
                    │                   │               │
                    │                   │               │
  Tracks:      Tracks:            Tracks:          Tracks:
  Aggregate    Q_Li, Q_neg, R     LLI, LAM_NE,    Electrochemical
  capacity     (8 state vars)     LAM_PE           state everywhere
  or resistance                   (3 modes from    (continuous PDEs)
                    │              voltage curves)       │
                    │                   │               │
  Params:      Params:            Params:          Params:
  3–15 fitted  20+ Arrhenius      Half-cell OCV    30+ physical
  coefficients coefficients       curves + cutoffs parameters
                    │                   │               │
                    └───────────────────┼───────────────┘
                                       │
                              ACCURE's production
                              approach lives here
                              (mechanistic tier)
```

### Cross-References Within the Repo

- **NREL 64171 summary** — Dubarry's LLI/LAM_NE/LAM_PE maps directly to Smith's degradation mechanism taxonomy (SEI growth → LLI; mechanical fatigue → LAM_NE; positive electrode → LAM_PE). The 64171 paper's Table I classification of degradation physics is the theoretical foundation that mechanistic models operationalize.

- **NREL 67102 summary** — The `min(Q_Li, Q_neg, Q_pos)` structure is essentially a semi-empirical implementation of mechanistic modeling's three degradation modes, with Q_pos treated as negligible. Dubarry's work shows Q_pos (= LAM_PE) is *not* negligible for layered oxides.

- **Gwayi 2025 summary** — Gwayi's taxonomy (CAOM/CYAOM/CCYASM/CCYACM) covers the empirical and semi-empirical tiers. Mechanistic models sit above that taxonomy — they don't fit neatly into any of Gwayi's categories because they operate on voltage curve shape rather than on algebraic stress-factor relationships.

- **PyBaMM summary** — PyBaMM's degradation options (SEI, particle mechanics, LAM) are the physics-based equivalents of the mechanistic model's LLI, LAM_NE, LAM_PE. PyBaMM resolves the spatial and temporal physics; mechanistic models extract the same degradation modes from measured voltage signatures without solving the physics.
