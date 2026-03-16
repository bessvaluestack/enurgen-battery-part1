# Scope of Work — BESS Module for DUET

## Engagement Overview

Extend the DUET solar digital twin platform with BESS modeling. Deliverables are working prototypes, documented architecture, and validated algorithms for Enurgen's team to integrate into DUET. This is not a site optimization platform build — DUET's value is high-fidelity simulation and actual-vs-predicted analysis.

**Core distinction:** simulation (given a dispatch schedule, how does the battery behave?) is architecturally separate from optimization (given prices and constraints, what's the best schedule?). This engagement covers simulation only.

## In Scope

### Task 1: BESS Modeling Landscape & Architecture Design

1. Survey existing BESS modeling tools (SAM, PyBaMM, OpenEMS, HOMER + battery analytics platforms) — simulation vs. optimization capabilities, inputs, degradation treatment
2. Identify minimum viable manufacturer datasheet inputs; flag chemistry-specific vs. generalizable
3. Define operational and financial KPIs (RTE, capacity utilization, SoH, LCOS, etc.)
4. Architecture design: simulation engine, degradation model, and optimizer interfaces + DUET integration points
5. Data model and API contracts (dispatch schedule format, time-series resolution, state vectors)

**Deliverables:** Landscape report with SWOT, I/O specification, architecture design document, build-vs-integrate recommendation

### Task 2A: Core BESS Performance Model

6. SoC tracking model — configurable resolution (5min–1hr), asymmetric charge/discharge efficiency, inverter losses, auxiliary consumption
7. Power constraints — nameplate limits, SoC-dependent derating, temperature derating, ramp rates
8. DC-coupled and AC-coupled solar+BESS configurations, including inverter clipping capture
9. Integration with DUET solar generation profiles
10. Validation harness against measured field data (subject to availability)

**Deliverables:** Python module (numpy/pandas) with documented API, test suite, DUET integration example

### Task 2B: Degradation & State-of-Health Model

11. Calendar degradation — f(time, temperature, average SoC), empirical model following SAM's approach for LFP and NMC
12. Cycle degradation — rainflow counting, DoD-dependent capacity fade curves from manufacturer data or literature
13. Combined degradation (min or additive, configurable by chemistry) → composite SoH trajectory
14. Degradation impact on usable capacity and available power over multi-year simulations
15. Battery replacement logic at configurable SoH threshold (70–80% nameplate)
16. Parameterized for LFP and NMC, extensible to other chemistries

**Deliverables:** Python degradation module, LFP/NMC parameter sets, validation against published curves, assumptions documentation

## Out of Scope

- Dispatch optimization / optimizer engine (future Task 3)
- Financial post-processing / lifetime economics (future Task 4)
- Electrochemical cell-level modeling (suggest SAM/PyBaMM integration)
- Multi-site portfolio optimization or VPP dispatch
- UI/UX development — all deliverables are Python modules with APIs