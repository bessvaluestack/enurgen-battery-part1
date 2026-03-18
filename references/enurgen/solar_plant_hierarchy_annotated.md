# Solar Power Plant Electrical Interconnection Hierarchy

A hierarchical structure for a solar photovoltaic (PV) digital twin tool, organizing electrical components from the smallest individual units to the complete grid-connected system.

---

## Hierarchy Levels (Bottom-Up)

### Level 1: **Panel**
```
Panel: x × y cells
```

**Description:**
- The basic unit of the solar installation
- Comprises a rectangular array of photovoltaic cells
- Dimensions defined as `x` (columns) × `y` (rows) of individual solar cells
- Each cell generates DC voltage under sunlight
- Cells are electrically interconnected to produce a combined voltage output

**Role in System:** Primary energy conversion unit from solar radiation to electrical current

---

### Level 2: **String**
```
String: z panels
```

**Description:**
- Multiple panels connected in series
- Contains `z` panels wired end-to-end
- Series connection increases voltage output (voltages add)
- Each panel in the string operates at the same current (limited by the lowest-performing panel)

**Electrical Characteristics:**
- Total voltage = sum of individual panel voltages
- Current = current of a single panel
- Vulnerable to shading on any single panel (affects entire string)

**Role in System:** Intermediate aggregation unit; provides voltage suitable for inverter input

---

### Level 3: **Block**
```
Block: v strings, w inverters, 1 MV transformer
```

**Description:**
- Collection of `v` strings wired in parallel
- Serves `w` inverters (DC/AC conversion units)
- Includes 1 medium-voltage (MV) transformer for voltage step-up
- Represents a functional production unit within the plant

**Electrical Characteristics:**
- Parallel connection of strings increases current capacity
- Total current = sum of individual string currents
- Total voltage = voltage of a single string
- Inverters convert DC power to AC grid-frequency power
- MV transformer steps up voltage to medium-voltage levels (typically 10–35 kV)

**Role in System:** Functional subarray with DC/AC conversion and voltage transformation; primary unit for plant operation and monitoring

---

### Level 4: **System**
```
System: q blocks, 1 HV transformer, 1 grid connection
```

**Description:**
- Complete solar power plant installation
- Comprises `q` blocks connected together
- Single high-voltage (HV) transformer for final voltage step-up
- One grid connection point (Point of Common Coupling, PCC) to the electrical grid

**Electrical Characteristics:**
- Aggregates all power from `q` blocks
- HV transformer steps voltage to high-voltage transmission levels (typically 69 kV, 138 kV, or higher)
- Single point of grid interconnection for metering, control, and dispatch

**Role in System:** Complete power plant; operational unit managed as a single entity by the utility

---

## Power Flow Summary

**Direction:** Solar radiation → Electrical power (DC) → Grid (AC)

| Level | Input | Output | Function |
|-------|-------|--------|----------|
| **Cell** | Solar radiation | DC voltage (~0.5–0.7 V/cell) | Energy conversion |
| **Panel** | x × y cells in parallel/series | DC voltage (~20–50 V typical) | Module aggregation |
| **String** | z panels in series | DC voltage (~500–1000 V) | Voltage buildup |
| **Block** | v strings in parallel + inverters | AC power (3-phase) | DC-to-AC conversion |
| **System** | q blocks + HV transformer | AC power at grid voltage | Grid injection |

---

## Digital Twin Implications

This hierarchy enables modular monitoring and control at each level:

- **Cell/Panel level:** Individual performance tracking, fault detection
- **String level:** Imbalance detection, shading analysis
- **Block level:** Inverter status, local power factor correction, MV transformer monitoring
- **System level:** Total plant output, grid compliance (frequency, voltage), revenue metering

Each aggregation level reduces data volume while maintaining critical operational visibility.

---

## Key Design Parameters

- `x, y`: Panel cell matrix dimensions
- `z`: Number of panels per string
- `v`: Number of strings per block (parallel strings)
- `w`: Number of inverters per block
- `q`: Number of blocks in the system

These parameters define the total plant capacity:
```
Total Power = (x × y cells/panel) × (z panels/string) × (v strings) × (q blocks) × power_per_cell
```
