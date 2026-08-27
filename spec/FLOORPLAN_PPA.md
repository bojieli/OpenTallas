# Floorplan, PPA, and proxy methodology

**Document:** SPEC-PPA 1.0  
**Status:** frozen hypothesis and measurement plan; no target-node signoff

This document turns the analytical midpoint into explicit physical-design
budgets. Values marked `assumed` are design-entry constraints, not evidence that a
wafer, package, or product can meet them. Open tools and an open PDK may be used
to test methodology and scaling behavior, but cannot close the external gates.

## PPA-1 Scope and accounting

### PPA-1.1 Hierarchy and ownership

The physical planning unit is one stage: 8 × 8 reticle fields, 64 service tiles
per field, and 4,096 tiles total. The logical stage boundary includes ROM/sense,
scale ROM, tile arithmetic and SRAM, local/mesh NoC, HBM wrappers, link wrappers,
clock/reset, RAS/DFT, and power delivery keep-outs. Package HBM, PHY analog, PLL,
IO/ESD, thermal structures, and security macros are separate black-box line items.

### PPA-1.2 Evidence and claim hygiene

Every PPA table carries an evidence class (`measured`, `published`, `derived`,
`assumed`, `simulated`, or `synthetic`) and a replacement artifact. RTL synthesis
counts are measured for the selected generic library and parameters. They are not
silicon area or frequency. Analytical throughput is simulated/derived, not a
measured product result. A report may not multiply a reduced proxy linearly into a
leading-node wafer claim without a stated scaling model and uncertainty.

## PPA-2 Floorplan contract

| Item | Midpoint | Class | Acceptance artifact |
|---|---:|---|---|
| reticle fields/stage | 64 | assumed architectural limit | floorplan database and connectivity check |
| service tiles/stage | 4,096 | derived from hierarchy | elaboration and placement inventory |
| gross reticle area | 718.75 mm² | assumed | open-PDK proxy floorplan; target-node macro view |
| stitched logical silicon | 46,000 mm² | assumed | package/wafer feasibility study |
| tile gross area budget | 11.2305 mm² | derived | tile macro inventory and utilization report |
| ROM raw / usable bytes | 184 / 160 GB | assumed | characterized ROM macro and repair/layout report |
| HBM physical / usable fraction | 384 GB / 90% | assumed | OSAT/package and allocator measurement |

The floorplan reserves explicit channels for 12 logical HBM ports, two stage-link
directions, AON access, clock/power straps, scan/BIST, and repair spares. No route
may cross a declared macro keep-out. A reticle boundary includes spare link lanes
and a test-observable break point; a stitched-stage estimate must not hide those
overheads in the tile line.

## PPA-3 Capacity and physical feasibility

### PPA-3.1 Immutable ROM capacity

The 184 GB raw hypothesis is partitioned into 160 GB logical image capacity plus a
13.0435% visible reserve for row/column repair, CRC/signature regions, alignment,
fragmentation, and service metadata. Capacity is checked per indivisible tensor and
layer partition. The compiler emits raw, reserve, logical, and free-byte totals for
every stage; aggregate bytes alone are insufficient.

### PPA-3.2 HBM and beachfront

The 384 GB HBM number is a per-stage physical hypothesis. At most 90% is available
to session/KV state; the remainder is reserved for runtime, queues, communication,
ECC, diagnostics, and safety. The physical plan must show stack count, channels,
PHY/IO area, thermal path, power delivery, and usable capacity after package
constraints. The analytical capacity result is not a beachfront measurement.

## PPA-4 Service budgets

| ID | Budget | Midpoint | Class | Required proof |
|---|---|---:|---|---|
| PPA-4.1 | exposed ROM read bandwidth/stage | 100 TB/s | assumed | ROM macro/sense characterization plus sustained traffic test |
| PPA-4.2 | routed low-precision / dense high-precision arithmetic | 1 / 0.5 POP/s | assumed | post-synthesis/placement throughput and power |
| PPA-4.3 | bidirectional HBM payload bandwidth/stage | 8 TB/s | assumed | PHY/controller traffic and thermal test |
| PPA-4.4 | NoC floor plus payload | 100 ns/layer + 128 GB/s | simulated/assumed | cycle model, RTL timing, and post-layout network analysis |
| PPA-4.5 | stage-link payload / one-way latency | 128 GB/s / 0.5 µs | assumed | link wrapper timing and package SI/latency study |

The budgets are independent roofs. The service model reports memory, compute,
collective, pipeline, HBM capacity, and thermal constraints separately; it must not
replace a binding physical constraint with a peak arithmetic number.

## PPA-5 Power and thermal

### PPA-5.1 Allocation

The stage operating hypothesis is 15 kW with a 20 kW cooling limit. The initial
allocation is: ROM/sense 3.0 kW, MAC/vector 5.0 kW, HBM/PHY 2.2 kW, NoC/SRAM
movement 3.3 kW, clock/control 0.8 kW, and 0.7 kW contingency. These are budget
partitions, not measured rail power. Dynamic estimates must include clock,
leakage, repair-disabled resources, ECC, retries, and test modes where applicable.

### PPA-5.2 Thermal and reliability closure

The plan shall model steady state, burst, thermal gradients, emergency throttle,
power sequencing, and sensor uncertainty. A target package study must provide
junction/stack temperatures, hotspot maps, IR drop, EM lifetime, cooling pressure,
and safe-trip hysteresis. Public RTL can verify throttle protocol only; it cannot
close package or reliability requirements.

## PPA-6 Clock, area, and proxy methodology

### PPA-6.1 Clock and frequency

Architectural core frequency is 1.0 GHz with legal 0.8–1.2 GHz hypotheses; the
public open-PDK proxy target is 100 MHz. Timing constraints include macro latency,
CDC synchronizers, NoC wire delay, repair muxes, CRC/ECC, and clock-gate insertion.
Frequency claims require unconstrained-path review, generated-clock coverage, and
separate setup/hold, skew, and duty-cycle results. A proxy meeting 100 MHz does not
imply 1 GHz silicon.

### PPA-6.2 Scaling and reporting

Reports separate synthesized standard-cell area, inferred/specified memories,
black-box area, wire/clock estimates, power model, and unmodeled keep-outs. Every
run records tool versions, library/PDK identity, parameters, constraints, seeds,
and input hashes. Results are compared at equal architectural work, not merely
equal RTL line count. No public-PDK result is promoted to a target-node claim.

## PPA-7 Entry and exit criteria

Physical proxy work begins only after RTL static and functional verification for the
selected baseline. A proxy result is acceptable for methodology when constraints
are covered, no black box is silently inferred, and area/timing/power uncertainty
is reported. Product PPA remains blocked until characterized ROM/HBM/PHY/package,
yield/repair, SI/PI, thermal, reliability, and commercial evidence are available.
