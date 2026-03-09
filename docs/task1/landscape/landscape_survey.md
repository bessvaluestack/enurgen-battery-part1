# BESS Modeling Landscape Survey

**Task 1, Deliverable 1** | Est. 10 hrs
**Status:** Draft

## Purpose

Comparative analysis of existing BESS modeling tools — how they handle simulation, optimization, and degradation — framed relative to DUET's current capabilities and target position. The goal is to identify where the whitespace is for DUET and inform the build-vs-integrate decisions in the architecture design.

## Tool Categories

We evaluate three categories of tools, each relevant to different aspects of the BESS module:

1. **Simulation & sizing tools** — full system models (SAM, HOMER, OpenEMS)
2. **Electrochemical modeling** — cell-level physics (PyBaMM)
3. **Battery analytics platforms** — BMS-layer degradation prediction and state estimation (TWAICE, ACCURE, Zitara)

---

## 1. NREL SAM (System Advisor Model)

**Category:** Simulation & sizing (open-source, NREL)
**Relevance to DUET:** Primary reference for degradation modeling approach; candidate for future integration (original SoW Task 5)

### Overview

<!-- Brief description of SAM's battery module, what it does, who uses it -->

### Simulation Capabilities

<!-- How SAM simulates battery behavior: dispatch, SoC tracking, efficiency modeling, time resolution -->

### Degradation Treatment

<!-- Calendar vs. cycle degradation, chemistry-specific models (NMC, LFP, LMO/LTO), rainflow counting, capacity fade curves, replacement logic -->
<!-- Reference the SAM battery life documentation we have -->

### Optimization Approach

<!-- What dispatch strategies does SAM support? Rule-based? Optimization? -->

### Required Inputs

<!-- What does SAM need from the user / datasheets? -->

### Key Outputs

<!-- What does SAM produce? -->

### SWOT

| | |
|---|---|
| **Strengths** | |
| **Weaknesses** | |
| **Opportunities** (for DUET) | |
| **Threats** (to DUET) | |

---

## 2. PyBaMM

**Category:** Electrochemical modeling (open-source, Oxford/Faraday Institution)
**Relevance to DUET:** Future phase (cell-level physics); understanding the interface matters now for architecture

### Overview

<!-- What PyBaMM is, what level of fidelity it operates at -->

### Simulation Capabilities

<!-- Electrochemical models available, time resolution, computational cost -->

### Degradation Treatment

<!-- Physics-based degradation: SEI growth, lithium plating, etc. -->

### Optimization Approach

<!-- N/A or limited — PyBaMM is a forward model -->

### Required Inputs

<!-- Cell-level parameters, electrolyte properties, etc. — much more detailed than datasheet-level -->

### Key Outputs

<!-- Voltage profiles, internal states, degradation mechanisms -->

### SWOT

| | |
|---|---|
| **Strengths** | |
| **Weaknesses** | |
| **Opportunities** (for DUET) | |
| **Threats** (to DUET) | |

---

## 3. OpenEMS

**Category:** Energy management system (open-source)
**Relevance to DUET:** Reference for dispatch/EMS architecture patterns

### Overview

<!-- What OpenEMS does, target use cases -->

### Simulation Capabilities

<!-- How it models battery and site behavior -->

### Degradation Treatment

<!-- If any -->

### Optimization Approach

<!-- Rule-based? Optimization? How does it handle dispatch scheduling? -->

### Required Inputs

<!-- -->

### Key Outputs

<!-- -->

### SWOT

| | |
|---|---|
| **Strengths** | |
| **Weaknesses** | |
| **Opportunities** (for DUET) | |
| **Threats** (to DUET) | |

---

## 4. HOMER

**Category:** Microgrid sizing and simulation (commercial, HOMER Energy / UL)
**Relevance to DUET:** Common reference point for customer expectations; sizing methodology

### Overview

<!-- -->

### Simulation Capabilities

<!-- -->

### Degradation Treatment

<!-- -->

### Optimization Approach

<!-- How HOMER searches the design space — exhaustive enumeration? -->

### Required Inputs

<!-- -->

### Key Outputs

<!-- -->

### SWOT

| | |
|---|---|
| **Strengths** | |
| **Weaknesses** | |
| **Opportunities** (for DUET) | |
| **Threats** (to DUET) | |

---

## 5. TWAICE

**Category:** Battery analytics platform (commercial, Munich)
**Relevance to DUET:** Degradation prediction methodology, digital twin positioning in the battery analytics space

### Overview

<!-- What TWAICE does, market positioning, who their customers are -->

### Approach to Degradation / State Estimation

<!-- How do they model SoH, RUL? ML-based? Physics-informed? What data do they need? -->

### Key Differentiators

<!-- What can we learn from their approach? -->

### Relevance to DUET Architecture

<!-- What patterns or ideas should we adopt or avoid? -->

**Sources:** <!-- webinar transcripts, published materials -->

---

## 6. ACCURE

**Category:** Battery analytics platform (commercial, Aachen)
**Relevance to DUET:** Safety monitoring, anomaly detection, fleet-level analytics

### Overview

<!-- -->

### Approach to Degradation / State Estimation

<!-- -->

### Key Differentiators

<!-- -->

### Relevance to DUET Architecture

<!-- -->

**Sources:** <!-- -->

---

## 7. Zitara

**Category:** Battery analytics / modeling platform (commercial)
**Relevance to DUET:** Physics-based battery modeling, digital twin approach at the cell level

### Overview

<!-- -->

### Approach to Degradation / State Estimation

<!-- -->

### Key Differentiators

<!-- -->

### Relevance to DUET Architecture

<!-- -->

**Sources:** <!-- -->

---

## Comparative Summary

| Tool | Simulation | Optimization | Degradation | Fidelity Level | Open Source | DUET Relevance |
|------|-----------|-------------|-------------|---------------|-------------|----------------|
| SAM | | | | System | ✅ | Direct reference |
| PyBaMM | | | | Cell | ✅ | Future phase |
| OpenEMS | | | | System | ✅ | Architecture ref |
| HOMER | | | | System | ❌ | Sizing benchmark |
| TWAICE | | | | Cell→System | ❌ | Degradation methods |
| ACCURE | | | | System | ❌ | Monitoring patterns |
| Zitara | | | | Cell→System | ❌ | Modeling approach |

## Whitespace Analysis

<!-- Where does DUET have a unique position? What should it NOT try to replicate? -->

### DUET's Unique Position

<!-- PV digital twin + actual-vs-predicted + extending to storage -->

### Gaps in Existing Tools

<!-- What do existing tools do poorly that DUET could do better? -->

### What DUET Should NOT Build

<!-- Capabilities better served by integration or partnership -->

## Build-vs-Integrate Recommendations (Summary)

<!-- High-level recommendations — detailed version in architecture doc -->

| Capability | Recommendation | Rationale |
|-----------|---------------|-----------|
| BESS forward simulation | | |
| Degradation modeling | | |
| Dispatch optimization | | |
| Electrochemical modeling | | |
| Market data integration | | |
