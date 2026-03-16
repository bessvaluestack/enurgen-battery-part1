# Input/Output Specification & KPI Definitions

**Task 1, Deliverable 2** |
**Status:** Draft

## Purpose

Define the data the BESS module needs to consume and produce. This specification serves as the 'contract' between the architecture design (Deliverable 3) and the implementation (Tasks 2A/2B). Every input and output defined here should map to a concrete field in the Python API.

---

## 1. System Configuration Inputs

Parameters that define the physical BESS system. These are set once per system configuration and do not vary with time.

### 1.1 Nameplate / Datasheet Parameters

These are the parameters that a manufacturer datasheet will typically provide.

| Parameter | Symbol | Unit | Typical Source | Chemistry-Specific? | Notes |
|-----------|--------|------|---------------|---------------------|-------|
| Nameplate energy capacity | E_nom | kWh | Datasheet | No | |
| Nameplate power (charge) | P_ch_max | kW | Datasheet | No | |
| Nameplate power (discharge) | P_dis_max | kW | Datasheet | No | May differ from charge |
| Round-trip efficiency (AC) | η_rt | % | Datasheet | Partially | Often quoted at specific C-rate |
| Minimum state of charge | SoC_min | % | Datasheet / config | Yes | Typical: 5-10% LFP, 10-20% NMC |
| Maximum state of charge | SoC_max | % | Datasheet / config | Yes | Typical: 90-95% |
| Cycle life at rated DoD | N_cycles | cycles | Datasheet | Yes | Often at 80% DoD to 80% SoH |
| Calendar life | T_cal | years | Datasheet | Yes | |
| Operating temperature range | T_min, T_max | °C | Datasheet | Yes | |
| Self-discharge rate | σ | %/month | Datasheet / lit. | Yes | Often negligible for Li-ion |

### 1.2 Derived / Configured Parameters

Parameters that are either derived from nameplate specs or configured by the modeler.

| Parameter | Symbol | Unit | Source | Notes |
|-----------|--------|------|--------|-------|
| Charge efficiency | η_ch | % | Derived or config | Split from η_rt |
| Discharge efficiency | η_dis | % | Derived or config | Split from η_rt |
| Inverter efficiency curve | η_inv(P) | % | Separate datasheet | If not flat, function of load |
| Auxiliary power consumption | P_aux | kW | Config / estimate | BMS, HVAC, controls |
| C-rate limits | C_ch, C_dis | 1/h | Derived from P/E | |
| Initial state of charge | SoC_0 | % | Config | Starting condition |
| Initial state of health | SoH_0 | % | Config | 100% for new, <100% for used |

### 1.3 Gap Inputs — Not Typically on Datasheets

These are parameters the model needs but manufacturers don't usually publish. For each, identify a reasonable default or source.

| Parameter | Why Needed | Default Strategy | Notes |
|-----------|-----------|-----------------|-------|
| Efficiency vs. C-rate curve | η varies with power | | |
| Efficiency vs. SoC curve | η varies near full/empty | | |
| SoC-dependent power derating | Power limits near 0%/100% SoC | | |
| Temperature derating curve | Power/capacity vs. temperature | | |
| Ramp rate limits | Rate of power change | | |
| Calendar degradation parameters | Task 2B model inputs | | See SAM documentation |
| Cycle degradation curves (DoD vs. cycles) | Task 2B model inputs | | See SAM documentation |
| Thermal model parameters | If modeling temperature effects | | May be deferred |

### 1.4 System Topology Configuration

| Parameter | Options | Notes |
|-----------|---------|-------|
| Topology | Standalone / AC-coupled / DC-coupled | Affects power flow modeling |
| Inverter configuration | Shared (hybrid) / Separate | DC-coupled shares inverter with PV |
| Inverter clipping behavior | Clip / Curtail / Charge battery | DC-coupled: excess PV can charge |
| Grid connection | BTM / FTM | Affects metering and tariff application |
| Number of units | Integer | For fleet/container modeling |

---

## 2. Time-Series Inputs

Data that varies with time, provided as time-series at the simulation resolution.

| Input | Symbol | Unit | Resolution | Source | Required? |
|-------|--------|------|-----------|--------|-----------|
| Dispatch schedule (charge/discharge) | P_cmd(t) | kW | 5min–1hr | Optimizer or manual | Yes (for simulator) |
| Solar generation profile | P_pv(t) | kW | 5min–1hr | DUET PV model | For hybrid/co-located |
| Site load profile | P_load(t) | kW | 5min–1hr | Measured or modeled | For BTM use cases |
| Ambient temperature | T_amb(t) | °C | Hourly | Weather data | If temperature effects modeled |

---

## 3. Outputs — BESS Simulation (Task 2A)

Time-series outputs from the BESS performance simulator.

### 3.1 Primary Time-Series Outputs

| Output | Symbol | Unit | Notes |
|--------|--------|------|-------|
| State of charge | SoC(t) | % | Primary state variable |
| Battery power (DC) | P_batt_dc(t) | kW | Positive = discharge |
| Battery power (AC / grid-side) | P_batt_ac(t) | kW | After inverter losses |
| Energy charged | E_ch(t) | kWh | Cumulative or per-interval |
| Energy discharged | E_dis(t) | kWh | Cumulative or per-interval |
| Inverter losses | P_inv_loss(t) | kW | |
| Auxiliary consumption | P_aux(t) | kW | |

### 3.2 Summary / Aggregated Outputs (per simulation run)

| Output | Unit | Notes |
|--------|------|-------|
| Total energy throughput | MWh | Sum of energy charged |
| Equivalent full cycles | count | Throughput / (2 × usable capacity) |
| Actual round-trip efficiency | % | Energy out / energy in |
| Capacity utilization factor | % | Actual throughput / max possible |
| Hours of operation | hrs | |
| Availability | % | |

---

## 4. Outputs — Degradation (Task 2B)

### 4.1 Time-Series / Periodic Outputs

| Output | Symbol | Unit | Resolution | Notes |
|--------|--------|------|-----------|-------|
| State of health (capacity) | SoH_cap(t) | % | Daily or per-cycle | Relative to nameplate |
| State of health (power) | SoH_pow(t) | % | Daily or per-cycle | If power fade modeled |
| Calendar degradation component | SoH_cal(t) | % | Daily | |
| Cycle degradation component | SoH_cyc(t) | % | Per-cycle | |
| Usable capacity | E_usable(t) | kWh | Daily | SoH × E_nom × (SoC_max - SoC_min) |
| Available power | P_avail(t) | kW | Daily | SoH_pow × P_nom |

### 4.2 Event Outputs

| Output | Unit | Notes |
|--------|------|-------|
| Replacement trigger date | date | When SoH hits threshold |
| Replacement count | integer | Over project lifetime |
| End-of-life SoH | % | At project end or replacement |

### 4.3 Degradation Diagnostics

| Output | Unit | Notes |
|--------|------|-------|
| Rainflow cycle count distribution | cycles vs. DoD bins | From Task 2B cycle counter |
| Average DoD per cycle | % | |
| Average SoC operating range | % | Mean SoC ± std |
| Temperature stress factor | dimensionless | If temperature modeled |

---

## 5. Key Performance Indicators (KPIs)

Formally defined KPIs for use across all modules. Each must have an unambiguous calculation method.

### 5.1 Operational KPIs

| KPI | Definition | Unit | Calculation |
|-----|-----------|------|-------------|
| Round-trip efficiency (actual) | | % | E_discharged_ac / E_charged_ac × 100 |
| Capacity utilization | | % | Actual throughput / theoretical max throughput |
| Equivalent full cycles (annual) | | cycles/yr | Annual throughput / (2 × usable capacity) |
| State of health | | % | Current usable capacity / nameplate capacity |
| Degradation rate | | %/yr | Annualized SoH decline |
| Availability | | % | Hours operational / hours in period |
| Curtailment captured (DC-coupled) | | MWh | Solar energy stored that would have been clipped |

### 5.2 Financial KPIs (defined here, implemented in Task 4)

| KPI | Definition | Unit | Notes |
|-----|-----------|------|-------|
| Levelized Cost of Storage (LCOS) | Total lifecycle cost / total energy discharged | $/MWh | Includes capex, opex, replacement, degradation |
| Revenue per cycle | | $/cycle | Total revenue / equivalent full cycles |
| Revenue per kWh throughput | | $/kWh | Total revenue / total energy discharged |
| Net Present Value (NPV) | | $ | Discounted cash flows over project life |
| Internal Rate of Return (IRR) | | % | Discount rate at which NPV = 0 |
| Simple payback period | | years | Time to recover initial investment |

---

## 6. Data Resolution & Conventions

| Convention | Value | Notes |
|-----------|-------|-------|
| Default time resolution | 30 min | Configurable: 5, 15, 30, 60 min |
| Minimum data length | 1 year (8,760 hrs) | For annual simulation |
| Sign convention (power) | Positive = discharge to grid/load | Consistent with generation convention |
| Sign convention (SoC) | 0% = empty, 100% = full nameplate | Not usable range |
| Timestamp convention | Start-of-interval | ISO 8601, timezone-aware |
| Energy vs. power | Energy = power × interval duration | Not trapezoidal integration |
