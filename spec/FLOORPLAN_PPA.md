# Floorplan, PPA, and proxy methodology

**Document:** SPEC-PPA 1.0  
**Status:** frozen public-reference proxy and measurement plan; no target-node signoff

This document turns the legacy public-reference interface proxy into explicit
physical-design budgets. It does not define the current N7 or N4 product envelope.
Values marked `assumed` are proxy design-entry constraints, not evidence that a
wafer, package, or product can meet them. Open tools and an open PDK may test
methodology and scaling behavior, but cannot close the external gates.

Current comparison inputs and derivations are controlled by
`configs/hardware/technology_inputs.json`, `docs/METHODOLOGY.md`, and
`results/iso-node/`. The numbers below must never be averaged with those envelopes
or quoted as selected product targets.

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

| Item | Public proxy | Class | Acceptance artifact |
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

The public proxy's 184 GB raw hypothesis is partitioned into 160 GB logical image capacity plus a
13.0435% visible reserve for row/column repair, CRC/signature regions, alignment,
fragmentation, and service metadata. Capacity is checked per indivisible tensor and
layer partition. The compiler emits raw, reserve, logical, and free-byte totals for
every stage; aggregate bytes alone are insufficient.

### PPA-3.2 HBM and beachfront

The 384 GB HBM number is a public-proxy per-stage physical hypothesis. At most 90% is available
to session/KV state; the remainder is reserved for runtime, queues, communication,
ECC, diagnostics, and safety. The physical plan must show stack count, channels,
PHY/IO area, thermal path, power delivery, and usable capacity after package
constraints. The analytical capacity result is not a beachfront measurement.

## PPA-4 Service budgets

| ID | Budget | Public proxy | Class | Required proof |
|---|---|---:|---|---|
| PPA-4.1 | exposed ROM read bandwidth/stage | 100 TB/s | assumed | ROM macro/sense characterization plus sustained traffic test |
| PPA-4.2 | MXFP4-weight × FP8-activation / FP8×FP8 / BF16×BF16 arithmetic | 0.5 / 0.5 / 0.25 POP/s | assumed | format-specific post-synthesis/placement throughput and power |
| PPA-4.3 | bidirectional HBM payload bandwidth/stage | 8 TB/s | assumed | PHY/controller traffic and thermal test |
| PPA-4.4 | NoC floor plus payload | 100 ns/layer + 128 GB/s | simulated/assumed | cycle model, RTL timing, and post-layout network analysis |
| PPA-4.5 | stage-link payload / one-way latency | 128 GB/s / 0.5 µs | assumed | link wrapper timing and package SI/latency study |

The budgets are independent roofs. The service model reports memory, compute,
collective, pipeline, HBM capacity, and thermal constraints separately; it must not
replace a binding physical constraint with a peak arithmetic number.

## PPA-5 Power and thermal

### PPA-5.1 Allocation

The public-proxy stage operating hypothesis is 15 kW with a 20 kW cooling limit. The initial
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

### PPA-6.3 Governed public implementation proxy

`implementation_proxy.json` and `tools/rtl_implementation_campaign.py` define the
canonical implementation-methodology campaign. Four arithmetic points vary one to
sixteen experts and four to sixteen lanes; three stage-control points vary reduced,
midpoint, and default control storage. Every point receives generic and Nangate45
mapped synthesis, structural checks, complete 100 MHz proxy constraints, a 1 GHz
core-frequency diagnostic, minimum-delay/reset audit, and exact warning review.
The reduced arithmetic and stage-control representatives additionally run immutable-
digest OpenROAD/ORFS placement, CTS, detailed route, extraction, final reporting,
and GDS generation.

The exact 16-expert × 16-lane arithmetic endpoint is retained rather than
resized. Because the pinned default delay-oriented ABC recipe previously ran for
more than 64 minutes without emitting a mapped netlist, that scaling-only,
non-equivalence, non-physical point uses the separately identified bounded
structural Liberty profile `strash; &get -n; &nf; &put` with a 300-second outer
timeout. It must still produce only pinned-Liberty cells, no latches, blackboxes,
internal cells, or structural errors, and complete STA constraint coverage. Its
cell count, area, and timing are not directly QoR-comparable to default-profile
rows.

A required physical proxy passes only with nonnegative final setup and hold slack,
zero setup/hold, max-slew, max-fanout, max-capacitance, placement, antenna, flow, and
final DRC violations, an exact max-fanout-32 structural audit, zero unexplained
drivers or loads, and independent equivalence from the exact ORFS synthesized
netlist to the final physical netlist. Every final artifact is hashed. The pinned
ORFS image's optional Kepler LEC helper is explicitly disabled because its Naja
Python library raised an illegal-instruction exception on this host; that helper is
not reported as passing. The replacement public gate uses pinned Yosys to expand
Liberty semantics, normalize both netlists to arbitrary-initial-state AIGs, and
audit identical public IO plus latch-index state pairing before pinned ABC `dsec`
inductively proves the sequential networks equivalent. Only a bounded number of
autogenerated private state symbols may be aligned; public state-name differences
are fatal. Qualified diverse product LEC remains external.

OpenSTA and OpenROAD vectorless power have no workload activity, characterized
macros, package loss, calibrated target voltage/frequency, or thermal feedback.
Default-grid IR drop likewise lacks a product floorplan and PDN. Both are retained
as visibly non-gating diagnostics; neither may be used as product power, energy, or
power-integrity evidence. Inferred memories remain flop-mapped and are reported
separately from qualified SRAM/ROM macros.

### PPA-6.4 Governed custom-transistor ROM methodology slice

The selected public custom-circuit vehicle is SKY130A, with IHP SG13G2 reserved
for independent replication. This selection is based on foundry provenance,
primitive models, DRC/LVS/extraction, PVT/statistical collateral, reproducible
releases, and open-tool maturity—not nominal feature size. See
`docs/OPEN_PDK_SELECTION.md` and `configs/pdk/sky130_physical_lock.json`.

`tools/run_sky130_physical.py` now closes zero-error Magic DRC, unique Netgen LVS
including all ten ports, the ten-device/fifteen-net schematic contract, exactly
one physical via1 programming delta, and base capacitance extraction for a
deliberately roomy two-column slice. `tools/run_sky130_extracted_pvt.py` closes
33/33 deterministic extracted-layout process/voltage/temperature/output-load
cases. `tools/run_sky130_extracted_mismatch.py` additionally closes 256/256
fixed-seed, mismatch-only nominal-TT local cases, exact same-seed replay, and
cross-seed variation detection. Exact artifacts and hashes are under
`results/spice/sky130_physical/`, `results/spice/sky130_extracted_pvt.json`, and
`results/spice/sky130_extracted_mismatch.json`. A complementary integrated
detailed-resistance campaign closes five semantic extraction replays and
165/165 deterministic cases over five RC styles; its governed result is
`results/spice/sky130_resistance/resistance.json`.

The independent IHP chain is also governed. The exact public SG13G2 `v0.3.0`
checkout and submodules are recursively content-locked; all four official
Verilog-A/OSDI models compile twice byte-identically for a generic CPU target;
and the official 1.2-V NMOS/PMOS wrappers pass a deterministic TT DC/transient
smoke deck. An independently generated controlled-via slice then closes zero-
error full DRC, unique ten-port LVS, the ten-device/fifteen-net topology, the
exact six-versus-five via1 invariant, base capacitance extraction, and 33/33
official-PSP103 PVT/load cases. A complementary five-style detailed-RC campaign
closes 5/5 semantic extraction replays, preserves 10 MOS/41 resistor/68
capacitor elements and all six NMOS body-resistance paths per style, and passes
165/165 electrical cases. The governed records are under
`results/spice/ihp_device_smoke/`, `results/spice/ihp_sg13g2_physical/`,
`results/spice/ihp_sg13g2_extracted_pvt.json`, and
`results/spice/ihp_sg13g2_resistance/`.

This gate tests local topology and methodology only. Its 373.75-µm² footprint
is not a ROM-bit density; its delay and energy are not array or product values.
No SKY130 or IHP result may be feature-size-scaled into N7/N4. Distributed wire
resistance for a compact/full array, full decoder/row/column organization,
silicon mismatch/sense yield, simultaneous activity, repair, target-foundry
macro characterization, and reticle-silicon correlation remain required.

## PPA-7 Entry and exit criteria

Physical proxy work begins only after RTL static and functional verification for the
selected baseline. A proxy result is acceptable for methodology only when the
machine-readable PPA-6.3 gates pass, all warnings have exact dispositions, no black
box is silently inferred, and area/timing/power uncertainty is reported. Raw
prelayout stage timing is diagnostic because inferred memories and high-fanout
controls lack product macros and trees; required stage timing closes only on the
buffered postroute proxy. Product PPA remains blocked until characterized
ROM/HBM/PHY/package, reset/clock trees, yield/repair, SI/PI, thermal, reliability,
and commercial evidence are available.
