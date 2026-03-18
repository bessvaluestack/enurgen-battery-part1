# TWAICE — Battery Analytics for ESS Failure Prediction & Preventative Maintenance

**Source:** 2023 ESSRF (Energy Storage Safety Research Forum), Session 2.5  
**Presenter:** Ryan Franks, Senior Technical Solution Engineer, TWAICE  
**Date:** June 5, 2023  
**File:** `2023ESSRF_Session2_5_Franks_Ryan.pdf`

---

## Company Profile

TWAICE is a Munich-based battery analytics company offering a cloud-based SaaS platform for monitoring, diagnosing, and predicting battery behavior in energy storage systems. They position themselves as a **pure analytics layer** — no additional hardware required, sitting on top of existing BMS/EMS data streams.

- 120+ battery & software engineers / data scientists
- 30+ patents
- 5 GWh+ connected battery capacity
- Offices: Munich (HQ), Chicago, Paris
- Partners include Munich RE and TÜV Rheinland (insurance + certification angles)

## Platform Architecture

TWAICE operates as a three-tier stack:

1. **Data Integration** — ingests BMS/EMS data via three methods:
   - API push (customer pushes to TWAICE endpoint)
   - CSV upload to TWAICE SFTP server
   - Pull stack (TWAICE pulls from customer's API or database)

2. **Battery Analytics Engine** — core processing layer (proprietary)

3. **Dashboard / API / Reporting** — outputs including:
   - Health analytics (SoH tracking + predicted end-of-life)
   - Warranty tracking (capacity vs. time with warranty curve overlay)
   - Safety monitoring (risk detection with threshold alarming)

## Data Requirements (Key for io_spec)

TWAICE specifies the following **minimum operational data** for their analytics:

| Signal | Ideal Resolution | Ideal Time Resolution |
|---|---|---|
| Current (I) | 0.5 A | 2 s |
| Voltage (V) | 0.5 V | 2 s |
| Temperature (Tmin, Tmax) | 1°C | 60 s |
| State of Charge (SoC) | 1% | 30 s |
| Cell Voltages (Vmin, Vmax) | 0.01 V | 2 s |

Required **metadata**:
- Complete system hierarchy (serial/parallel connections)
- Initial energy capacity and maximum power of the whole system
- Battery specifications: manufacturer, type, and chemistry

### Relevance to DUET io_spec
These are the inputs a commercial analytics platform requires from SCADA/BMS for **operational monitoring**. DUET's simulation model (Task 2A) needs a different but overlapping input set — the simulation needs datasheet parameters to *predict* these values, while TWAICE consumes *measured* values to diagnose. The overlap is exactly the model-vs-actual comparison surface.

---

## Key Industry Data Points

### Risk #1: Early-Life Failure Concentration

Per EPRI Failure Database:

| System Age (years) | % of Failure Events |
|---|---|
| 0–1 | 38% |
| 1–2 | 20% |
| 2–3 | 15% |
| 3–4 | 5% |
| 4–5 | 4% |
| 5–6 | 2% |
| 6–7 | 4% |
| Unknown | 13% |

**58% of BESS failures occur within the first two years.** This is a critical data point — it suggests manufacturing defects and commissioning issues dominate over aging/degradation failures. Implies that DUET's value in the commissioning phase (model-vs-actual at day zero) is potentially even more important than long-horizon degradation modeling.

### Risk #2: Low Availability in Mature Systems

- Average BESS availability cited at ~90% (TWAICE internal data)
- UK storage availability in 2022 was 82% (per Modo Energy)
- US asset owner quote: fleet-wide average availability of only 84% due to unplanned downtime

**Implication for DUET KPIs:** Availability (and its inverse, downtime) should be a first-class KPI. The gap between nameplate availability and actual availability is a key metric for model-vs-actual.

### Risk #3: Thermal Runaway / Fire Events

Presentation references two incidents:
- Tesla Victorian Big Battery fire (Australia, investigated 2022)
- AES thermal runaway at Arizona site (2022)

These are reputational and financial risks that drive insurance and safety monitoring demand. TWAICE's partnership with Munich RE and TÜV Rheinland positions analytics as risk mitigation for insurability.

---

## Case Studies — Diagnostic Patterns

The presentation includes several case studies demonstrating TWAICE's diagnostic approach. These are relevant to Task 2B (degradation modeling) and to understanding what "model-vs-actual" looks like in practice for BESS.

### 1. Temperature Spread Analysis

- Heatmap of temperature spread across inverters × strings
- Used to diagnose **system design or HVAC control failures**
- Identified weak cells through KPI deviations
- Modules/strings not behaving per datasheet → triggers investigation

**Pattern:** Compare observed temperature distribution against expected (datasheet-based) thermal behavior. Deviations indicate design, installation, or manufacturing issues.

### 2. DC Resistance as Failure Predictor

- Plotted DCR (DC resistance) at 30% SoC across all strings of an inverter
- DCR measured at multiple time points after a current pulse (2s through 9s)
- Identified 5 modules with faulty cells (likely manufacturing defects)
- Provides a benchmarkable metric that can be tracked over time

**Pattern:** DCR is a key health indicator. Rising DCR = increased internal resistance = capacity fade and power fade. This is directly relevant to the equivalent circuit model in Task 2A (R_internal as a function of SoC, temperature, and aging state).

### 3. Voltage Spread at Low SoC

- Voltage spread (mV) across strings plotted against SoC
- Spread becomes pronounced at low SoC ranges
- 2% of modules contained defective cells
- Flags cells that should be replaced before cascading failure

**Pattern:** Voltage dispersion at SoC extremes is an early indicator of cell imbalance. A simulation model that predicts expected voltage spread (from cell-to-cell parameter variation) could flag deviations automatically.

### 4. Power Set Point Mismatch

- Compared BESS active power vs. external active power setpoint vs. BESS SoC
- Found discrepancy between what the energy management system commands and what the battery delivers
- Analyzed at inverter level, then drilled to string level

**Pattern:** This is a pure model-vs-actual use case. If the simulator predicts the system should be able to deliver X MW at the current SoC/temperature, and SCADA shows it delivered Y MW, the delta is diagnostic.

### 5. Faulty Cell Replacement Workflow

- Voltage spread exceeded two threshold levels
- Negative trend persisted even after balancing attempt
- Root cause: single cell responsible for the spread
- TWAICE issued notifications → cell replacement → voltage spread resolved

**Pattern:** Two-tier alarming (warning → critical) with automated notification. The "after balancing" check is important — if voltage spread doesn't resolve post-balancing, the root cause is cell-level, not just SoC imbalance.

### 6. Temperature-Triggered Shutdown

- Whole-system shutdown triggered by temperature alarm in one section
- System was offline for 7 days
- Root cause isolated to specific container/string
- Fix: reprogrammed shutdown procedures to isolate affected section rather than shutting down entire system

**Pattern:** Availability loss from overly conservative protection logic. Granular monitoring → granular response. Relevant to availability KPI definition — distinguishing between necessary safety shutdowns and avoidable ones.

---

## Extracted KPIs Tracked by TWAICE

From the dashboard screenshots and case studies, TWAICE monitors at minimum:

| KPI | Level | Notes |
|---|---|---|
| State of Health (SoH) | String | Actual vs. predicted EOL |
| Cycle Count | String | Cumulative full equivalent cycles |
| DC Resistance (DCR) | String/Module | Absolute value + trend |
| Voltage Spread | String | Max–min cell voltage delta |
| Temperature Spread | Inverter/String | Max–min module temperature delta |
| Availability | System | % time online and dispatchable |
| Safety Risk Score | System | Categorized: thermal, electrochemical, BMS, sensors |
| Power Setpoint Compliance | Inverter | Commanded vs. delivered power |

---

## Implications for DUET BESS Module

### For Task 1 — Landscape Survey

TWAICE occupies a specific niche: **operational analytics and diagnostics** on live systems. They are not a simulation/design tool. Their value is in:
- Ingesting high-frequency SCADA data
- Computing derived health indicators (DCR, voltage spread, temperature spread)
- Comparing actual behavior against expected (datasheet) behavior
- Predictive alarming (trending toward failure)

DUET's positioning vs. TWAICE: DUET aims to be the **digital twin / simulation side** — predicting what the battery *should* do given design parameters and a dispatch schedule. TWAICE is the **monitoring side** — analyzing what the battery *actually does*. These are complementary, not competing. DUET could eventually feed predicted baselines into a TWAICE-like monitoring layer, or DUET could build its own lighter-weight model-vs-actual comparison.

### For Task 1 — I/O Spec

TWAICE's data requirements table (current, voltage, temperature, SoC, cell voltages) represents the **minimum viable SCADA interface** for operational analytics. DUET's simulator needs to be able to:
1. Accept these signals as "actual" inputs for comparison
2. Produce predicted equivalents from the forward model
3. Define meaningful tolerance bands / deviation thresholds

### For Task 2A — Simulation Engine

The case studies reveal the physical quantities that matter most for diagnostics:
- **Internal resistance** (DCR) as a function of SoC, temperature, aging
- **Voltage response** under load (V = OCV - I×R_internal)
- **Thermal behavior** (temperature distribution across the system hierarchy)
- **Power capability** (what can the system actually deliver at current state?)

These should be first-class outputs of the simulation engine.

### For Task 2B — Degradation

TWAICE's SoH tracking and predicted EOL curves imply they maintain an internal degradation model (likely semi-empirical). The key insight from their case studies is that **cell-to-cell variation and manufacturing defects** dominate early-life issues, while **calendar + cycle aging** dominate later life. DUET's degradation model (Task 2B) should handle both regimes, but the PoC can reasonably focus on the aging regime first and treat manufacturing defects as outliers.
