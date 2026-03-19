# CLAUDE.md — BESS Valuestack Project

## Project Context

This is a consulting engagement for **Enurgen Inc.** by **Valuestack** to extend their DUET solar digital twin platform with battery energy storage system (BESS) modeling capabilities. DUET is an existing Python-based simulation framework for utility-scale PV power plants, focused on design, commissioning, and operational phases — with a strong model-vs-actual comparison product. **Valuestack** is a contracting party that is building a PoC for Enurgen.

The engagement that will be committed to this repo covers:
- **Task 1** (in progress): BESS Modeling Landscape & Architecture Design — research and documentation
- **Task 2A** (upcoming): Core BESS Performance Simulation Engine — Python implementation
- **Task 2B** (upcoming): Degradation & State-of-Health Model — Python implementation

Tasks 3 (dispatch optimization) and 4 (financial post-processing) are anticipated follow-on work, out of scope for this contract.

## Key Design Principles

1. **Simulation ≠ Optimization.** The BESS simulator (Task 2A) is a forward model: given a dispatch schedule, it simulates physical behavior, i.e. parameters of a BESS system. The optimizer (Task 3, future) is an inverse problem: given prices/constraints, it produces the best BESS dispatch schedule. These are separate modules with clean interfaces.

2. **Extensible toward failure prediction and preventative maintenance.** The PoC builds simulation + model-vs-actual comparison. The architecture must expose intermediate state from every sub-model, produce structured deviation signals (not just residuals), support hierarchy drill-down to string/module level, and catalog diagnostic patterns as configurable lookups. These are the foundations that future failure prediction and preventative maintenance modules will consume. Design for this extensibility now; build those modules later.

3. **Datasheet-parameterizable by default.** Every required input should be derivable from a standard manufacturer datasheet and system configuration spec. Where richer data is available, the model tiering strategy allows higher-fidelity modes — but the default path works with datasheets alone.

4. **Actual-vs-predicted is the killer feature.** Enurgen's target customers care most about comparing modeled vs. measured performance (obtained from a real system using SCADA). Every module should be designed with this comparison in mind.

5. **Chemistry-pluggable, not chemistry-locked.** Changing chemistry changes parameter values and configuration, never model code. A `CellChemistry` configuration object encapsulates all chemistry-dependent parameters.

6. **Applicable to hybrid PV+BESS and standalone BESS.** The BESS module plugs into DUET's existing site topology at the same level as a PV block. The dispatch interface is topology-agnostic.

7. **Degradation is its own domain.** Calendar aging, cycle-based capacity fade (DoD-dependent), rainflow counting, chemistry-specific parameterization — this is Task 2B, extending the simulator built in 2A. Clean boundary: degradation model receives operating conditions, returns updated capacity and resistance.

8. **We are NOT building a site optimization platform.** Tools like Gridcog, HOMER, etc. already do multi-tariff, multi-asset site simulation. DUET's value is high-fidelity digital twins. In this engagement we're building PoC algorithms and architecture that Enurgen's team will later integrate into DUET.

9. **Log everything the future needs.** The simulation engine logs all intermediate quantities at every timestep — per-mechanism degradation increments, constraint violations, thermal headroom, full degradation state vector. Storage is cheap; reconstructing state from sparse logs is not.

10. **Incremental, testable deliverables (only valid for code).** Each module should have a clean Python API, standalone tests (including synthetic dispatch data), and documented assumptions.

## Repository Structure

```
├── CLAUDE.md                  # This file
├── README.md                  # Project overview
├── docs/
│   └── task1/
│       ├── landscape/         # BESS modeling landscape survey & SWOT
│       │   └── landscape_survey.md
│       ├── io_spec/           # Input/output specification & KPIs
│       │   └── io_spec.md
│       └── architecture/      # Architecture design document
│           └── architecture.md
├── src/                       # Python implementation (Tasks 2A, 2B)
└── references/                # Notes, transcript summaries, datasheets
    ├── sam/                   # SAM technical papers around BESS and degradation modeling
    ├── twaice/                # TWAICE webinar transcripts and public technical content
    ├── accure/                # ACCURE webinar transcripts and public technical content
    ├── zitara/                # Zitara webinar transcripts and public technical content
    ├── enurgen/               # DUET reference, data models, data points, etc.
    ├── deep-research-report-on-public-materials.md
    ├── INDEX.md               # List of all documents
    └── SCOPE.md               # Valuestack's finalized SoW document
```

## Task 1 Deliverables

All Task 1 output is markdown documentation in `docs/task1/`:

1. **`landscape/landscape_survey.md`** — Explainer on BESS simulation theory and practice, comparative analysis of BESS modeling tools with SWOT. Covers: NREL SAM, PyBaMM, OpenEMS, TWAICE, ACCURE, Zitara. Framed relative to DUET's current capabilities and target position. Structure:
   - Section 1: Li-ion BESS primer (electrochemistry, hierarchy, efficiency, chemistries, degradation overview)
   - Section 2: Functional requirements catalog (voltage, thermal, degradation, SOC, SOH, dispatch, hierarchy, model-vs-actual)
   - Section 3: Degradation modeling review (4-tier spectrum, empirical catalog, NREL deep dive, mechanistic/ACCURE, PyBaMM/DFN, SAM architecture, commercial platforms)
   - Section 4: DUET design approach (positioning, design principles, model tiering, chemistry strategy, integration, model-vs-actual decisions)

2. **`io_spec/io_spec.md`** — Minimum viable input parameters from manufacturer datasheets, chemistry-specific vs. generalizable flags, gap inputs with default sources, and formal KPI definitions (operational + financial).

3. **`architecture/architecture.md`** — Module boundaries, interface contracts, DUET integration points, configuration patterns. This is the blueprint for later implementation of Tasks 2A/2B (simulation). Must explicitly address extensibility toward failure prediction and preventative maintenance.

## Task 1 Progress

- [x] Reference material surveyed and summarized (NREL 64171, 64641, 67102; Gwayi 2025; Dubarry/ACCURE 2023; PyBaMM/LiionDB; TWAICE ESSRF 2023; Zitara)
- [x] Landscape survey outline complete (all 4 sections structured with bullet-point content and reference mapping)
- [ ] Landscape survey prose — in progress
- [ ] I/O specification — not started
- [ ] Architecture document — not started

## Style & Conventions

- Documentation is in markdown, written for a technical audience (Enurgen's engineering team)
- Use tables for structured comparisons
- Use mermaid diagrams for architecture (```mermaid blocks)
- Keep prose concise — these are working engineering documents, not sales materials
- When referencing tools/platforms, cite specific capabilities rather than marketing language
- Python code (Tasks 2A/2B) should use numpy/pandas, type hints, and docstrings

## Reference Material Available

The author has access to the following (organized in `references/` subdirectories):

- NREL SAM battery life and degradation documentation (64171, 64641, 67102)
- PDF explaining of the logical blocks of Enurgen (cells, strings, blocks, PCS/inverters, transformers)
- TWAICE, ACCURE, Zitara webinar transcripts and public technical content
- Gwayi et al. 2025 empirical aging model review
- Dubarry et al. 2023 mechanistic modeling paper
- PyBaMM repository analysis and Wang et al. 2022 LiionDB parameterization review
- Existing deep research report summary
- Valuestack's finalized SoW document in md

## Key Reference Papers

| Short Name | Full Citation | Relevance |
|---|---|---|
| NREL 64171 | Smith et al. 2015, NREL/CP-5400-64171 | Degradation mechanism taxonomy, coupling hypotheses |
| NREL 64641 | DiOrio et al. 2015, NREL/TP-6A20-64641 | SAM battery model architecture, validation |
| NREL 67102 | Smith et al. 2017, NREL/CP-5400-67102 | Semi-empirical degradation model with NMC parameters |
| Gwayi 2025 | Gwayi et al. 2025, Eng. Reports 7:e70169 | Catalog of 13 empirical/semi-empirical aging models |
| Dubarry 2023 | Dubarry et al. 2023, J. Electrochem. Soc. 170:070503 | Mechanistic LLI/LAM decomposition, ACCURE approach |
| Wang/LiionDB 2022 | Wang et al. 2022, Prog. Energy 4:032004 | DFN parameterization review and database |
| TWAICE ESSRF | Franks 2023, ESSRF Session 2.5 | Commercial BESS analytics, diagnostic case studies |
