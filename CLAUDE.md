# CLAUDE.md — BESS Valuestack Project

## Project Context

This is a consulting engagement for **Enurgen Inc.** by **Valuestack** to extend their DUET solar digital twin platform with battery energy storage system (BESS) modeling capabilities. DUET is an existing Python-based simulation framework for utility-scale PV power plants, focused on design, commissioning, and operational phases — with a strong model-vs-actual comparison product. **Valuestack** is a contracting party that is building a PoC for Enurgen.

The engagement that will be commited to this repo covers:
- **Task 1** (current): BESS Modeling Landscape & Architecture Design — research and documentation
- **Task 2A** (upcoming): Core BESS Performance Simulation Engine — Python implementation
- **Task 2B** (upcoming): Degradation & State-of-Health Model — Python implementation

Tasks 3 (dispatch optimization) and 4 (financial post-processing) are anticipated follow-on work, out of scope for this contract.

## Key Design Principles

1. **Simulation ≠ Optimization.** The BESS simulator (Task 2A) is a forward model: given a dispatch schedule, it simulates physical behavior, i.e. parameters of a BESS system. The optimizer (Task 3, future) is an inverse problem: given prices/constraints, it produces the best BESS dispatch schedule. These are separate modules with clean interfaces.

2. **Degradation is its own domain.** Calendar aging, cycle-based capacity fade (DoD-dependent), rainflow counting, chemistry-specific parameterization — this is Task 2B, extending the simulator built in 2A.

3. **Actual-vs-predicted is the killer feature.** Enurgen's target customers care most about comparing modeled vs. measured performance (obtained from a real system using SCADA). Every module should be designed with this comparison in mind.

4. **We are NOT building a site optimization platform.** Tools like Gridcog, HOMER, etc. already do multi-tariff, multi-asset site simulation. DUET's value is high-fidelity digital twins. In this engagement we're building PoC algorithms and architecture that Enurgen's team will later integrate into DUET.

5. **Incremental, testable deliverables (only valid for code).** Each module should have a clean Python API, standalone tests (including synthetic dispatch data), and documented assumptions.

## Repository Structure

```
├── CLAUDE.md                  									# This file
├── README.md                  									# Project overview
├── docs/
│   └── task1/
│       ├── landscape/         									# BESS modeling landscape survey & SWOT
│       │   └── landscape_survey.md
│       ├── io_spec/           									# Input/output specification & KPIs
│       │   └── io_spec.md
│       └── architecture/      									# Architecture design document
│           └── architecture.md
├── src/                       									# Python implementation (Tasks 2A, 2B)
└── references/                									# Notes, transcript summaries, datasheets
│   └── sam/				   							# SAM tachnical papers around BESS and degradation modeling
│   └── twaice/				   						# TWAICE webinar transcripts and public technical content
│   └── accure/				   						# ACCURE webinar transcripts and public technical content
│   └── zitara/				   						# Zitara webinar transcripts and public technical content
│   └── enurgen/			   						# DUET reference, data models, data points, etc.
│   └── deep-research-report-on-public-materials.md # Deep research report summary
│   └── INDEX.md 									# List of all documents
│   └── SCOPE.md 									# Valuestack's finalized SoW document
```

## Task 1 Deliverables

All Task 1 output is markdown documentation in `docs/task1/`:

1. **`landscape/landscape_survey.md`** — Expainer on BESS simulation theory and practice, comparative analysis of BESS modeling tools with SWOT. Covers: NREL SAM, PyBaMM, OpenEMS, TWAICE, ACCURE, Zitara. Framed relative to DUET's current capabilities and target position.

2. **`io_spec/io_spec.md`** — Minimum viable input parameters from manufacturer datasheets, chemistry-specific vs. generalizable flags, gap inputs with default sources, and formal KPI definitions (operational + financial).

3. **`architecture/architecture.md`** — Module boundaries, interface contracts, DUET integration points, configuration patterns. This is the blueprint for later implementation of Tasks 2A/2B (simulation).

## Style & Conventions

- Documentation is in markdown, written for a technical audience (Enurgen's engineering team)
- Use tables for structured comparisons
- Use mermaid diagrams for architecture (```mermaid blocks)
- Keep prose concise — these are working engineering documents, not sales materials
- When referencing tools/platforms, cite specific capabilities rather than marketing language
- Python code (Tasks 2A/2B) should use numpy/pandas, type hints, and docstrings

## Reference Material Available

The author has access to the following (organized in appropriate folders)

- NREL SAM battery life and degradation documentation (as 67102 - NREL Life Prediction Model Li-ion BESS.pdf)
- PDF explaining of the logical blocks of Enurgen (cells, strings, blocks, PCS(inverters), transformers)
- TWAICE, ACCURE, Zitara webinar transcripts and public technical content
- Existing Deep research report summary
- Valuestack's finalized SoW document in md