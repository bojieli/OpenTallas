# Open transistor PDK selection

**Decision:** use SKY130A as the primary public physical-methodology vehicle,
repeat the final topology in IHP SG13G2 when the first campaign is stable, and
retain GF180MCU as a secondary older/high-voltage check.  None of these kits is
an N7 or N4 proxy, and no feature-size scaling from them is permitted.

## What is being selected

The purpose of an open PDK in this program is narrowly defined.  It must let us
draw a legal present/absent-via ROM slice, run DRC and schematic-versus-layout
LVS, extract physical interconnect and device parasitics, and simulate the
extracted read path over documented process/voltage/temperature and statistical
conditions.  It is not being selected to predict target-node density or speed.

The comparison therefore uses the following gates, in this order:

1. foundry/process provenance and a path to fabrication;
2. complete custom-device models rather than only digital timing libraries;
3. public DRC, LVS, and parasitic-extraction support;
4. core-device voltage and geometry appropriate to a dense read array;
5. PVT, mismatch, and Monte Carlo collateral;
6. reproducible releases and an independently usable open-tool flow;
7. enough ecosystem experience to distinguish tool-flow failures from circuit
   failures.

Nominal node name is deliberately not a score.  A predictive 7-nm kit is less
useful for this experiment than a foundry-backed 130-nm kit because it cannot
establish that a drawn structure corresponds to a manufacturable process.

## Evidence matrix

| Candidate | Process status | Core MOS relevant to this experiment | Public custom physical/electrical flow | Role and disposition |
|---|---|---|---|---|
| **SKY130A** | SkyWater/Google state that the kit derives from a commercially used process and can create designs manufacturable at SkyWater, while warning that the open release is still an experimental preview | 1.8-V CMOS, local interconnect, five metal levels; closer to a compact low-voltage ROM read path than the GF180 MCU devices | Complete primitive SPICE models, PVT/statistical collateral, Magic and KLayout technology/decks, Netgen setup, extraction rules, primitive MAG/GDS/SPICE views, and a large open test-chip ecosystem | **Primary methodology PDK.** Best combined fit and flow observability; not selected for performance |
| **IHP SG13G2** | IHP states that SG13G2 is a manufacturable 130-nm BiCMOS process; the public PDK is a preview | 1.2-V thin-oxide and 3.3-V thick-oxide CMOS; the 1.2-V option is a valuable independent low-voltage topology check | Primitive models, KLayout and Magic DRC/extraction, LVS, ngspice/Xyce support, and published process/layout rules | **Independent replication.** Strongest way to detect a SKY130-specific result after the primary flow closes |
| **GF180MCU** | GlobalFoundries/Google state that the kit targets a manufacturable 0.18-um MCU process; the public PDK is an experimental preview | 3.3-V/6-V MCU devices; physically valid but a weaker first analogue for a dense low-voltage ROM array | Primitive models and open physical decks through the same open-PDK ecosystem | **Secondary robustness check.** Useful for topology portability, not the first choice for read-path PPA |
| **ASAP7** | Published as a 7-nm FinFET *predictive* PDK | Research FinFET assumptions | Research decks and cell libraries, not a foundry manufacturing kit | **Excluded as transistor/manufacturing evidence.** May be used only for explicitly predictive digital experiments |
| **FreePDK45 + Nangate45** | The maintainers explicitly state that FreePDK45 is generic, corresponds to no real process, and cannot be fabricated; Nangate45 is a generic standard-cell library built on it | Generic 45-nm assumptions | Useful synthesis/place-route teaching and proxy collateral, not foundry devices | **Excluded as transistor evidence.** Existing RTL implementation results remain methodology proxies only |

Primary sources are registered as `SRC-PDK-*` entries in `docs/SOURCES.md`.
The exact installed PDK and tool identities are machine-readable in
`configs/pdk/sky130_physical_lock.json` and
`configs/pdk/ihp_sg13g2_physical_lock.json`.

## Why SKY130A is first

SKY130A does not win because 130 nm is intrinsically representative of N7 or N4.
It wins because the experiment needs a complete, inspectable path from legal
geometry through extracted devices and wires to a statistical circuit run.  Its
1.8-V core devices are a better first fit than GF180MCU's 3.3/6-V MCU devices,
and its mature Magic/open_pdks/test-chip ecosystem lowers the chance that a deck
integration problem will be mistaken for a ROM problem.  IHP SG13G2 is at least
as important scientifically once the topology is stable: reproducing the result
under an independently developed foundry PDK is stronger evidence than adding
more SKY130 corners.

## Hard claim boundary

A clean DRC/LVS/extracted SKY130 slice can establish that the topology is legal
under this installed public deck and show how physical rows, columns, wires,
contacts, vias, sense devices, and masks affect its extracted behavior.  It
cannot establish any of the following:

- that a target N7/N4 foundry offers a late-via-personalized mask-ROM option;
- target-node ROM cell or peripheral area;
- target-node delay, energy, leakage, sense margin, yield, bandwidth, or cost;
- whole-wafer simultaneous activation, PDN, clock, NoC, thermal, repair, or
  stitching feasibility.

Those quantities stay in evidence-backed uncertainty bands until a target
foundry supplies a characterized macro and a reticle test vehicle correlates the
models.

## Current governed evidence

The primary methodology run is now implemented against the exact locked
SKY130A tree. `tools/run_sky130_physical.py` verifies the complete installed PDK
manifest and pinned tools before generating the layout. Its archived result is
`results/spice/sky130_physical/physical.json` and closes the following local
gates:

- zero Magic DRC errors;
- a unique Netgen LVS match, including all ten top-level pins;
- ten MOS devices and fifteen extracted nets matching the schematic contract;
- six via1 shapes in the programmed half versus five in the unprogrammed half,
  so the only controlled programming delta is one physical via;
- a separate capacitance-preserving PEX netlist with 59 extracted capacitance
  elements.

`tools/run_sky130_extracted_pvt.py` then instantiates two copies of that exact
archived PEX slice and closes 33/33 deterministic SS/TT/FF, supply,
temperature, and output-load cases. Exact measures and model-file hashes are in
`results/spice/sky130_extracted_pvt.json`.

`tools/run_sky130_extracted_mismatch.py` separately enables the installed TT
1V8 per-instance mismatch equations while keeping process variation disabled.
Its 256 fixed contract-derived seeds all satisfy the local functional checks,
the repeated seed matches every parsed measure exactly, and the result confirms
cross-seed electrical variation. Exact seeds, netlist-level seed controls,
model-expression counts, measures, and hashes are in
`results/spice/sky130_extracted_mismatch.json`. This finite public-model sample
is not silicon-yield or sign-off Monte Carlo evidence.

`tools/run_sky130_resistance.py` separately invokes Magic's integrated detailed-
resistance path with zero network/delay/pruning thresholds and simplification
disabled. Five nominal/high/low interconnect styles are each extracted twice;
all five exact semantic replays pass. Every output has ten MOS devices, 630
explicit resistor elements, and 269 capacitors, and the programmed and absent-
via resistor components remain disjoint. The same 33 deterministic electrical
points per style pass, for 165/165 cases. Exact artifacts, case measures, and
full-RC-versus-capacitance-only deltas are in
`results/spice/sky130_resistance/resistance.json`.

This is stronger evidence than a schematic-only smoke test, but it does not
change the claim boundary above. The 32.5 × 11.5-µm demonstration layout is
deliberately roomy and is not a density macro. Compact-array/full-array RC,
silicon/statistical yield, target-node macro correlation, and silicon remain
open gates.

## IHP replication chain now closed locally

The exact IHP Open PDK `v0.3.0` checkout is installed outside the repository and
locked by root commit, all five submodule commits, every tracked regular file,
the tracked symlink target, Git modes, sizes and content hashes. The semantic
identity covers 5,121 payload entries, 812,058,771 payload bytes and five
gitlinks; the checkout is required to remain pristine.

IHP's official MOS models use PSP103 Verilog-A through ngspice's OSDI interface.
The governed tool path therefore pins ngspice 43 built with `--enable-osdi`,
OpenVAF 23.5.0 plus a one-line `--target_cpu generic` CLI type fix, Rust 1.64.0,
and LLVM/Clang/LLD 15.0.7. All four official IHP modules—`psp103`,
`psp103_nqs`, `r3_cmc`, and `mosvar`—compile twice outside the immutable PDK and
the paired outputs are byte-identical. An official `sg13_lv_nmos`/
`sg13_lv_pmos` TT inverter then passes DC and transient checks at 1.2 V and
27 °C.

The device prerequisite is recorded in
`results/spice/ihp_device_smoke/REPORT.md`. The separately implemented IHP
controlled-via slice then closes zero-error full Magic DRC, a unique Netgen LVS
match across all ten ports, ten MOS devices/fifteen nets, and an exact six-
versus-five via1 programming count. Its 59-element capacitance PEX is archived
and hash-bound to the physical result. Exact evidence is in
`results/spice/ihp_sg13g2_physical/`.

`tools/run_ihp_extracted_pvt.py` instantiates that exact PEX with the official
PSP103 SS/TT/FF low-voltage sections and closes 33/33 deterministic
1.08/1.20/1.32-V, -40/27/125-°C, and 5/20/80-fF cases. The only accepted model
warning is recorded exactly. `tools/run_ihp_resistance.py` independently
extracts all five public IHP interconnect styles twice. Each output has ten MOS
devices, 41 explicit resistor elements, and 68 capacitors; all five semantic
replays pass, all six extracted non-ground NMOS body nodes retain
positive-resistance paths to ground, and 165/165 electrical cases pass. The
full-RC report is `results/spice/ihp_sg13g2_resistance/REPORT.md`.

This cross-PDK agreement reduces the chance that topology legality or local
read behavior is a SKY130-deck artifact. It still does not establish a compact
array, statistical yield, a target-foundry late-via option, N7/N4 PPA, wafer
behavior, or silicon correlation, and none of its values enter the iso-node GPU
speedup calculation by feature-size scaling.
