# The ROM physical chain: what is measured, what is chosen, and what is still assumed

Three runs in this repository produce every physical ROM number the model has.
They are meant to be read as one chain, because each one consumes the one before
it and each one has a different amount of measurement in it.

| # | Run | Produces | Feeds |
|---|---|---|---|
| 1 | `tools/run_ihp_bitcell_density.py` | the drawn mask-ROM bitcell pitch, the foundry 6T SRAM bitcell pitch, and their ratio, at 130 nm | `rom.cell_to_sram_cell_area_ratio` |
| 2 | `tools/run_ihp_rom_macro_route.py` | the drawn macro footprint and the routed die area of a ROM macro with a synthesised periphery | `rom.array_efficiency` |
| 3 | `tools/run_ihp_rom_read_energy.py` | extracted bitline capacitance, read energy over PVT, read energy against column height, and the wordline load | `energy.rom_read_j_per_byte` |

Every one of them runs in **IHP SG13G2, a 130 nm open foundry PDK**. The program
targets N6/N5. **Nothing in this chain is a leading-node number, and §5 is the
reason that matters more than it looks.**

This document exists so that a reader can tell, at every step, which side of the
line a number is on. The runs' own `REPORT.md` files state their results; this
states their *epistemics*.

---

## 1. The line, stated once

A number in this chain is in exactly one of four states.

**Measured** — a tool read it off a drawn layout, an extracted netlist or a
simulation, under the PDK's own shipped deck, and the runner refuses to record a
result if the measurement did not happen. Example: the ROM bitcell pitch.

**Measured, with a proved floor** — measured, *and* the runner separately
demonstrates that the value cannot be smaller, by regenerating the thing one step
smaller and requiring a named failure. This is strictly stronger than "measured",
and this chain is careful about which of its numbers have it. Example: every
dimension of the ROM bitcell, each of which is re-drawn 10 nm smaller and must
produce a named DRC violation.

**Chosen** — a constant somebody wrote in a contract or, worse, in a runner's
source, which the flow then obeys. A result computed from a chosen constant
inherits its arbitrariness. The die utilization and the placer's target density
are both of these, and §3 is about what was done to each.

**Assumed** — no measurement anywhere, at any node. The chain has fewer of these
than it did, and §6 lists the ones that remain.

The failure this repository keeps finding is a number that *looks* like the first
and is actually the third or fourth. §8 lists every one found in this chain,
including one the chain's own fix for that failure introduced: the die-floor
probe removed a chosen constant and replaced it with a different chosen constant,
and the report called the result measured (§3).

---

## 2. Step 1 — the bitcell area ratio, at 130 nm

`results/spice/ihp_sg13g2_bitcell/` · `tools/run_ihp_bitcell_density.py`

### What is measured

| Quantity | Value | How |
|---|---:|---|
| Mask-ROM bitcell pitch | 510 × 765 nm | drawn here on the public deck, DRC clean under `drc(full)` <!-- figure: 510 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#rom_bitcell.column_pitch_nm" name="ROM column pitch" --> |
| Mask-ROM bitcell area | 0.390150 µm² | pitch product <!-- figure: 0.390150 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#rom_bitcell.cell_area_um2" name="ROM bitcell area" --> |
| Foundry 6T SRAM bitcell area | 3.006700 µm² | placement pitch extracted from the shipped `sg13g2_sram` macro GDS <!-- figure: 3.006700 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#sram_bitcell.1P.cell_area_um2" name="IHP 6T bitcell area" --> |
| **Ratio, ROM ÷ SRAM, same PDK** | **0.1298** | <!-- figure: 0.1298 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#ratio.measured" name="IHP 130 nm ROM/SRAM cell ratio" --> |

The ROM cell has a **proved floor**: six drawn dimensions are each re-drawn 10 nm
smaller and each produces a named violation of the installed deck. The SRAM cell
is not drawn at all — it is the foundry's own cell, cross-checked by requiring the
bitcell instance count to equal the datasheet bit count in every shipped macro.

### What is *not* measured, and which way it pushes

- **The two cells are not drawn under the same rules.** The foundry SRAM bitcell
  carries the PDK's `SRAM` recognition layer and is illegal under the public logic
  deck by 29 violations. <!-- figure: 29 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#sram_bitcell_drc.single_port_bitcell_drc_errors" name="foundry 6T bitcell DRC errors under the logic deck" -->
  A ROM given the same relief would be smaller, so
  **0.1298 is an upper bound** on the single-rule-set ratio. It is not a floor.
- This is a **130 nm** ratio. §5.

---

## 3. Step 2 — the macro, at 130 nm

`results/spice/ihp_sg13g2_rom_macro/` · `tools/run_ihp_rom_macro_route.py`

### What routing found that bitcell geometry could not

**A minimum-pitch ROM array is not legal without periodic substrate taps.** The
run draws the same array with the tap bands removed and the installed public deck
returns 6,897 DRC errors, all of them the latch-up rule `LU.b`. <!-- figure: 6897 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].tapless_control.drc_errors" name="tapless control DRC errors" -->
That is a **control**, not an assertion: the runner refuses to record a result
unless the tapless array actually fails, and fails on a latch-up rule
specifically. Tap bands are real area, they scale with array height, and a density
number taken from bitcell pitch alone does not contain them.

### The two efficiencies, and why the constant is ambiguous

Two boundaries are measured, and they are not the same number.

| | `rom_128x32_c2` (4,096 bits) | `rom_512x32_c4` (16,384 bits) |
|---|---:|---:|
| bit-array area | 1598.1 µm² <!-- figure: 1598.1 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_128x32_c2].bit_array_area_um2" name="c2 bit-array area" --> | 6392.2 µm² <!-- figure: 6392.2 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].bit_array_area_um2" name="c4 bit-array area" --> |
| drawn macro, with tap bands, wordline strap and bitline escape | 2012.1 µm² <!-- figure: 2012.1 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_128x32_c2].drawn.macro_area_um2" name="c2 drawn macro area" --> | 7415.8 µm² <!-- figure: 7415.8 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].drawn.macro_area_um2" name="c4 drawn macro area" --> |
| **macro-internal efficiency** | **79.42%** <!-- figure: 79.42 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_128x32_c2].macro_internal_efficiency" scale="100" name="c2 macro-internal efficiency" --> | **86.20%** <!-- figure: 86.20 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].macro_internal_efficiency" scale="100" name="c4 macro-internal efficiency" --> |
| synthesised standard-cell periphery | 4369.1 µm² <!-- figure: 4369.1 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_128x32_c2].synthesis.standard_cell_area_um2" name="c2 periphery area" --> | 6561.5 µm² <!-- figure: 6561.5 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].synthesis.standard_cell_area_um2" name="c4 periphery area" --> |
| routed die at the contract's utilization | 13402.9 µm² <!-- figure: 13402.9 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_128x32_c2].route.die_area_um2" name="c2 nominal die area" --> | 24395.2 µm² <!-- figure: 24395.2 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].route.die_area_um2" name="c4 nominal die area" --> |
| **whole-macro efficiency** | **11.92%** <!-- figure: 11.92 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_128x32_c2].array_efficiency" scale="100" name="c2 whole-macro efficiency" --> | **26.20%** <!-- figure: 26.20 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].array_efficiency" scale="100" name="c4 whole-macro efficiency" --> |

Both routed with zero detailed-route violations.

The constant `rom.array_efficiency` does not say which boundary it means, and the
two differ by more than a factor of two. **That ambiguity, not the value, is the
defect**, and it is the finding this run contributes.

### What is chosen rather than measured here

The nominal die is **sized from the contract's requested `utilization`**, so
`bit array ÷ die` is partly a restatement of a constant somebody chose. Nothing
in the flow refused that, and an efficiency that moves when you edit one number
in a contract is not a measurement.

So the run squeezes. The identical netlist is re-routed on progressively smaller
dies, and the tightest one that still closes with zero violations is a **measured
floor**; the first one that does not brackets it.

| Macro | Tightest die that closes | Efficiency there | Next step down |
|---|---:|---:|---|
| `rom_128x32_c2` | 11081.9 µm² <!-- figure: 11081.9 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_128x32_c2].die_floor_probe.tightest_closing.die_area_um2" name="c2 measured die floor" --> | 14.42% <!-- figure: 14.42 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_128x32_c2].array_efficiency_at_measured_floor" scale="100" name="c2 efficiency at the measured floor" --> | refused, `DPL-0036` |
| `rom_512x32_c4` | 20691.0 µm² <!-- figure: 20691.0 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].die_floor_probe.tightest_closing.die_area_um2" name="c4 measured die floor" --> | 30.89% <!-- figure: 30.89 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].array_efficiency_at_measured_floor" scale="100" name="c4 efficiency at the measured floor" --> | refused, `DPL-0036` |

So the whole-macro efficiency is **not** an artefact of the utilization constant:
each macro's die can be squeezed one rung and no further before the flow refuses.

**But read the stage the refusals come from.** Every one is a *placement* stage —
`GPL-0301` where the floorplan cannot hold the cells at all, `DPL-0036` where the
legaliser cannot place them — and none is a routing failure. So what is measured
is a **cell-area floor for this periphery**, not a routability floor: a custom
periphery with fewer cells would move it, and that is precisely the difference
between this and a memory compiler.

### And read what the refusal actually named — the second constant

The subsection above is the *corrected* version. The first one stopped at "the
standard cells stopped fitting", and the way that went wrong is worth more than
the number it got.

The probe exists to take one chosen constant out of the reported efficiency. It
sized the die from `utilization` and then refused smaller dies — but the die it
refused was refused *at a placement density of
0.85*, <!-- figure: 0.85 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.place_density_nominal_cap" name="the runner's placement-density cap" -->
`min(0.85, utilization + 0.15)`, a formula written in
`tools/run_ihp_rom_macro_route.py` and in no contract. And OpenROAD said so, in the diagnostic the report was quoting:

> `[ERROR GPL-0302] Use a higher -density or re-floorplan with a larger core area.`

The global placer was naming the runner's own constant as the remedy, the runner
recorded the refusal, and the report called it a **measured cell-area floor**. It
was a floor at 0.85. Nothing was out of range, nothing crashed, and the sentence
a reader took away — *the standard cells stopped fitting* — was one qualifier
short of true.

What refuses it now:

- the contract must carry `die_floor_probe_place_densities`, an **ascending
  ladder whose every rung is above the runner's own cap**, or the run does not
  start;
- a probe that fails with a diagnostic naming the density is **re-tried at each
  rung** before it counts as a refusal, and every attempt is recorded;
- a refusal that survives the top rung *still blaming the density* is recorded as
  `floor_limited_by_place_density` and the report is required to say the floor is
  conditional on the ladder rather than a property of the design.

The claim boundary carries it too, so the caveat cannot be dropped from the
contract without the run refusing to start.

**And it changed the answer, which is how we know it was not a hypothetical.**
Before the escalation, the larger macro's die floor was reported as the nominal
die itself — *no tighter die of this netlist closes*, on a `GPL-0302` that named
the runner's density. Re-tried one rung up that ladder, the tighter die at
utilization 0.55 closes with zero detailed-route violations at
20691.0 µm², <!-- figure: 20691.0 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].die_floor_probe.tightest_closing.die_area_um2" name="c4 die floor after escalation" -->
against the nominal
24395.2 µm² <!-- figure: 24395.2 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].route.die_area_um2" name="c4 nominal die, §3 escalation" -->
the first version had called the floor. The efficiency there is
30.89% <!-- figure: 30.89 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[name=rom_512x32_c4].array_efficiency_at_measured_floor" scale="100" name="c4 efficiency after escalation" -->
rather than the 26.20% the first version reported. The published sentence was
wrong in the direction that made the floor look tighter than it was, and no gate
anywhere would have caught it: the run exited zero, the diagnostic was real, and
the number was inside every declared bound.

Every refusal that survives now names something else — `DPL-0036` from the
legaliser, or `GPL-0301` where the floorplan cannot hold the cells at all — and
the run records
`die_floor_limited_by_place_density = False` <!-- figure: "False" src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.die_floor_limited_by_place_density" name="whether the floor is still the runner's" -->
so a reader does not have to take that on trust.

### What is not in the die area at all

- **No power distribution network.** This flow runs no `pdngen`, no
  `global_connect` and lays no straps. The macro's `VSS` pin is declared in the
  LEF, and in the netlist that gets routed it is tied to a logic constant by
  `insert_tiecells`, not to a rail — recorded, not asserted, at
  `results/spice/ihp_sg13g2_rom_macro/macro_route.json#macros[].synthesis.array_vss_connected_to`.
  Every die area here is **signal routing only**.
- **No sense amplifier.** The bitline is captured by an ordinary standard-cell
  flip-flop, which is the optimistic end of what a real macro needs.
- **No redundancy, repair or BIST.**

All three push the same way: the reported whole-macro efficiency is a **lower
bound** on what a ROM product would achieve, and it must never be quoted as the
efficiency a product would have.

---

## 4. Step 3 — the read energy, at 130 nm

`results/spice/ihp_sg13g2_rom_read_energy/` · `tools/run_ihp_rom_read_energy.py`

### What is measured

A 64-row × 8-column array is drawn at the measured minimum pitch, extracted with
parasitics, and simulated over a 33-case PVT grid with the pinned official PSP103
models. Every capacitance the read drives is extracted; only the precharge
transistor is a model instance rather than drawn layout.

| Quantity | Value |
|---|---:|
| Extracted bitline capacitance | 0.5032 fF per row of column height <!-- figure: 0.5032 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#capacitance_model.slope_ff_per_row" name="bitline capacitance per row" --> |
| Read energy, nominal (tt, 1.2 V, 27 °C) | 135.11 fJ per 8-bit access <!-- figure: 135.11 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#energy.nominal.read_energy_fj" name="nominal read energy" --> |
| The same, per byte | 1.351e-13 J/B <!-- figure: 1.351e-13 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#energy.nominal.read_energy_j_per_byte" name="nominal read energy per byte" --> |
| Across the PVT grid | 107.10 fJ <!-- figure: 107.10 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#energy.min.read_energy_fj" name="min read energy" --> to 188.75 fJ <!-- figure: 188.75 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#energy.max.read_energy_fj" name="max read energy" --> |

Every case is gated: the programmed bitline must discharge, the read margin must
clear a declared floor, and an **idle cycle** is simulated separately and must be
negligible against the read, so that what is measured is the access and not the
background.

**One gate was widened to let this run happen, and it is named here rather than
buried in a diff.** The runner allows exactly two ngspice warnings and fails a
case on anything else. Those two patterns were written with a doubled backslash
inside a raw string, so they matched nothing: the allowlist was inert and every
case would have failed on the PSP103 subcircuit-multiplier note, which is the
only warning any of the 33 cases actually emits. Fixing the escaping made two
named warnings benign again. That is a widening, it was made to let a run pass,
and the honest defence is not that it was harmless but that it is **auditable**:
the allowed patterns are written into the artifact as
`benign_warnings_allowed`, they are anchored whole rather than by prefix, and
every warning every case emitted is recorded per case under `all_warnings`
whether it was suppressed or not. A reader can check the filter against what
happened rather than against what the source claims.

### The finding: the constant's *shape* is wrong, not just its value

Read energy per bit is not a technology constant. It is affine in column height,
because a read discharges a whole bitline whatever the array stores. Over a
16-to-128-row sweep the slope is 1.7464 fJ per row of column height. <!-- figure: 1.7464 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#height_fit.slope_fj_per_row" name="read energy slope per row" -->

A single scalar per byte therefore names a column height without saying so. At
this node and at the measured stored-one density, the model's
8e-14 J/B <!-- figure: 8e-14 src="configs/hardware/technology.json#energy.rom_read_j_per_byte.value" name="assumed ROM read energy per byte, §4" -->
corresponds to a column of about 36 rows. <!-- figure: 36 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#implied_column_height_rows" name="column height the assumed scalar implies" -->
The array measured here is 64 rows and the column heights of IHP's own shipped
single-port memories run to 512 — measured, in
`results/spice/ihp_sg13g2_bitcell/bitcell.json#sram_bitcell.macros[].physical_rows`
— so the height a single scalar silently names is at the very short end of what a
real memory is built at. **The model needs a column-height term, not a better
scalar** — and so does the SRAM side, for the same reason (§7).

### Which way the boundary pushes

The measured boundary is **bit array only**: wordline, cell, bitline and precharge
device. It excludes address decode, sense amplification and the macro output
latch — all three of which `energy.rom_read_j_per_byte`'s own stated boundary
*includes*. So the measured number is a **lower bound** on the quantity the
constant names, and at 64 rows it is already
1.69× <!-- figure: 1.69 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#reference.measured_over_assumed_at_this_column_height" name="measured over assumed read energy at 64 rows" -->
the constant. The direction is
unambiguous and it is against the ROM. It is still a 130 nm number and §5 forbids
moving a leading-node constant with it.

### A second finding, about area rather than energy

At the minimum legal column pitch, 75.5% of a bitline's extracted capacitance is coupling to its two neighbours. <!-- figure: 75.5 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#capacitance_model.neighbour_coupled_fraction" scale="100" name="neighbour-coupled fraction of bitline capacitance" -->
A stored one on both neighbours drags an unselected bitline down with them; the
read still resolves, but a manufacturable array would spend area on shielding, a
wider pitch, or twisted bitlines. **That area is not in the bitcell pitch.** A
density number taken from bitcell geometry alone does not carry this cost, which
is a caveat on §2 that only the simulation could produce.

### The wordline load, and a trap it walked into

The macro flow (§3) needs the bit array's wordline load to size its wordline
drivers. Two windows are measured.

  | Window | Effective capacitance |
  |---|---:|
  | the wordline transition alone | 0.5578 fF/column | <!-- figure: 0.5578 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#wordline_capacitance.ff_per_column_transition_only" name="wordline transition capacitance" -->
  | that, plus the bitline discharge that follows it | 0.6340 fF/column | <!-- figure: 0.6340 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#wordline_capacitance.ff_per_column" name="wordline capacitance given to the macro flow" -->

The **larger** is handed to the macro flow: it sizes the drivers up, makes the
periphery larger and makes the array efficiency this chain reports *lower*.

The trap worth naming: the extracted interconnect capacitance on the same nets is
only 0.0510 fF/column. <!-- figure: 0.0510 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#wordline_capacitance.extracted_interconnect_only_ff_per_column" name="wordline interconnect-only capacitance" -->
`ext2spice` writes wiring parasitics, and the row transistors' gate capacitance
lives inside the device model rather than in a `C` element. Counting the wordline
load out of the parasitic netlist — the obvious thing to do — understates it by
**more than an order of magnitude**, in the direction that flatters the macro
area. The two annotated numbers above are the whole of that claim; it is not a
third number computed here.

---

## 5. The node wall

This is the part of the methodology that constrains every other part, and it is
the one thing in this document that is not about IHP at all.

`docs/ROM_DENSITY_NODE_TRANSFER.md` tested whether the cell-area ratio transfers
between nodes, by measuring the same question at a predictive 7 nm-class FinFET
PDK. **It does not transfer.**
0.1298 <!-- figure: 0.1298 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#ratio.measured" name="130 nm ratio, §5" -->
at 130 nm against
0.2500 <!-- figure: 0.2500 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#node_sensitivity.ratio" name="predictive FinFET ratio, §5" -->
at ASAP7,
92.7% apart, <!-- figure: 92.7 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#node_sensitivity.relative_disagreement" scale="100" name="cross-node disagreement" -->
and the mechanism is understood: at the FinFET node the one-transistor ROM
cell is nothing but quantisation floor while the 6T cell still has spacing rules
with usable granularity, and the memory-cell rule relief that shrinks the 6T cell
buys the ROM exactly nothing.

Three consequences bind this chain:

1. **No number in `results/spice/ihp_sg13g2_*` may be presented as an N6/N5/N7/N4
   value.** Each run's contract encodes this as
   `target_node_scaling_status: "prohibited"` and each runner refuses to start if
   its claim boundary does not carry it.
2. **The 130 nm and 7 nm-class ratios are never averaged, blended or
   interpolated.** They are two measurements of the same question at two nodes.
3. **At a FinFET node the ratio is quantised and cannot be swept continuously.**
   Both cells land on integer multiples of one CPP × one fin pitch, so the ratio
   is a quotient of small integers. The admissible ladder is generated from the
   sibling's own recorded quanta and archived at
   `results/spice/ihp_sg13g2_bitcell/bitcell.json#node_sensitivity.admissible_ratio_ladder`.
   The step down one SRAM quantum is 0.0147; <!-- figure: 0.0147 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#node_sensitivity.admissible_ratio_ladder.gap_to_next_rung_down" name="ladder gap down" -->
   the step up is 0.0167. <!-- figure: 0.0167 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#node_sensitivity.admissible_ratio_ladder.gap_to_next_rung_up" name="ladder gap up" -->
   They are not equal, which is why an evenly-spaced sweep gets both the values
   and their spacing wrong.

---

## 6. What is still assumed after all three runs

Being explicit about this is the point of the document. Every item below is
something a reader might reasonably think this chain established, and it did not.

**About the target node — everything.** No number here is an N6/N5/N7/N4 value.
The bitcell ratio, the macro efficiency, the read energy, the bitline
capacitance, the read margin: all 130 nm. The only cross-node evidence is the
*falsification* in §5, and falsifying node-stability is not the same as measuring
the target node.

**The 130 nm ROM/SRAM ratio's own floor.**
0.1298 <!-- figure: 0.1298 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#ratio.measured" name="130 nm ratio, §6" -->
is an upper bound because the
SRAM cell gets rule relief the ROM does not. How much smaller a relieved ROM
would be was not measured at 130 nm. (It was measured at the predictive node,
where the answer is "not at all", but that does not transfer either.)

**A ROM macro with a real periphery.** Every whole-macro efficiency here is built
on a synthesised standard-cell periphery with a flip-flop where a sense amplifier
belongs, no redundancy, no repair, no BIST and no power distribution network. The
difference between that and a memory compiler is the difference between
14.4% <!-- figure: 14.4 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.whole_macro_range_at_measured_floor[0]" scale="100" name="ROM macro efficiency at the measured floor, §6" -->
and the
24.4 <!-- figure: 24.4 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#sram_array_efficiency.single_port_min.array_efficiency" scale="100" name="foundry SRAM efficiency floor, §6" -->
–61.8% <!-- figure: 61.8 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.foundry_sram[macro=RM_IHPSG13_1P_1024x16_c2_bm_bist].array_efficiency" scale="100" name="foundry SRAM efficiency at 16k bits, §6" -->
IHP's own SRAM macros reach at the same capacities, and this chain
measured the gap without closing it.

**A die floor that owes nothing to a constant in the runner.** §3 fixed the worst
of it: a probe's refusal is now escalated up the contract's placement-density
ladder before it counts. But the top rung of that ladder is still a number
somebody chose
(`results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.place_density_ladder`),
and a floor that survives to the top rung is a floor *conditional on the ladder*.
The run says which case it is on every invocation; it does not remove the
dependence.

**Whether a ROM array is manufacturable at the minimum pitch it was drawn at.**
The read simulation shows
75.5% <!-- figure: 75.5 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#capacitance_model.neighbour_coupled_fraction" scale="100" name="neighbour-coupled fraction, §6" -->
of a bitline's capacitance is coupling to its
neighbours and the unselected bitline never reaches the rail. The read resolves in
simulation across the whole PVT grid. It does not follow that a product would ship
this pitch, and the shielding or twisting that would fix it is area this chain has
not costed.

**Anything statistical.** No mismatch, no sense offset, no yield, no aging, no
electromigration. The PVT grid is corner models, not a Monte Carlo.

**The wordline load's effect on area.** The wordline pin capacitance is measured
and is now traceable, but `abc` is handed the standard-cell Liberty only and the
bit array is a blackbox by then, so that number cannot move the synthesised
periphery area or the floorplanned die. It reaches OpenROAD's `repair_design` and
nothing else. The fix to its provenance was worth making; it is not load-bearing
for any area reported here, and this document does not pretend otherwise.

**That the wordline load extrapolates linearly from 8 columns to 128.** It is
measured on an 8-column array and the macro Liberty declares it as
`ff_per_column × cols`, a 16× extrapolation on the wider macro. The gate term is
exactly linear in columns; the wiring term is linear plus end effects that an
8-column array carries a disproportionate share of, so the extrapolation is
approximate in the direction of overstating the load per column. It was not
measured at 128 columns. Because of the paragraph above it changes no area
reported here either way, but the number itself is an extrapolation and is
labelled one.

**Silicon.** Nothing in this chain has been fabricated or correlated to anything
that has.

---

## 7. What each constant should carry

This chain touches three entries in `configs/hardware/technology.json`, and one
more that it insists is inseparable from the third. **It asks for no value change
to any of them**, and the reason is the same in all three
cases: every number here is 130 nm and §5 forbids moving a leading-node constant
with a 130 nm measurement. What it asks for is that each entry carry what has now
been measured, and that two of the notes be corrected.

### `rom.cell_to_sram_cell_area_ratio`

The entry already cites this chain's
0.1298 <!-- figure: 0.1298 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#ratio.measured" name="130 nm ratio, §7" -->
and already has a band-containment
audit in `tools/run_roofline_studies.py` that refuses a band excluding it. Two
things are still open.

**The band is continuous and the constant is not.** At a FinFET node both cells
land on integer multiples of one contacted poly pitch by one fin pitch, so the
ratio is a quotient of small integers and cannot take a value between two adjacent
rungs. Containment is the right check for a band; **enumeration** is the right
shape for a sweep. The admissible ladder, and the unequal spacing that makes an
even sweep wrong, are archived at
`results/spice/ihp_sg13g2_bitcell/bitcell.json#node_sensitivity.admissible_ratio_ladder`.
The rungs there are a property of the predictive PDK they were drawn in; the
*shape* claim — that there are rungs — holds at any FinFET node.

**One node-free ratio is still applied at N6 and at N5**, which both of this
repository's measurements say is wrong. That is not something this chain can fix;
it needs `rom_bits_per_mm2` to take the node it is already passed.

### `rom.array_efficiency`

The entry is now `derived` from a published compiler figure at one instance depth.
This chain adds an independent 130 nm cross-check and one correction to how the
constant is read.

**The 130 nm cross-check.** Measured the same way (bitcell pitch area ÷ macro
footprint), IHP's own foundry SRAM macros at this node reach
24.4% at 4,096 bits <!-- figure: 24.4 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#sram_array_efficiency.single_port_min.array_efficiency" scale="100" name="foundry SRAM efficiency floor at 130 nm" -->
and 61.8% at 16,384 bits, <!-- figure: 61.8 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.foundry_sram[macro=RM_IHPSG13_1P_1024x16_c2_bm_bist].array_efficiency" scale="100" name="foundry SRAM efficiency at 16k bits" -->
rising to 83.9% at 262,144 bits. <!-- figure: 83.9 src="results/spice/ihp_sg13g2_bitcell/bitcell.json#sram_array_efficiency.single_port_max.array_efficiency" scale="100" name="foundry SRAM efficiency ceiling at 130 nm" -->
This ROM macro with a synthesised standard-cell periphery reaches
14.4% <!-- figure: 14.4 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.whole_macro_range_at_measured_floor[0]" scale="100" name="ROM macro efficiency at the measured floor, low" -->
and 30.9% <!-- figure: 30.9 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.whole_macro_range_at_measured_floor[1]" scale="100" name="ROM macro efficiency at the measured floor, high" -->
at the same two capacities. At both depths the foundry macro is the higher of the
two by a wide margin, and that gap is what a memory compiler's custom periphery
buys. A published
0.52 <!-- figure: 0.52 src="configs/hardware/technology.json#rom.array_efficiency.value" name="live ROM array efficiency, §7" -->
at one compiler's deepest instance is consistent with that picture; nothing here refutes it and nothing here supports transporting it to a
shallow macro.

**The correction to how the constant is read.** `rom.array_efficiency` does not
say which boundary it means, and the two boundaries this run measures differ by
more than a factor of two —
79.4% <!-- figure: 79.4 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.macro_internal_range[0]" scale="100" name="macro-internal efficiency low, §7" -->
–86.2% <!-- figure: 86.2 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.macro_internal_range[1]" scale="100" name="macro-internal efficiency high, §7" -->
macro-internal against
11.9% <!-- figure: 11.9 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.whole_macro_range[0]" scale="100" name="whole-macro efficiency low, §7" -->
–26.2% <!-- figure: 26.2 src="results/spice/ihp_sg13g2_rom_macro/macro_route.json#comparison.whole_macro_range[1]" scale="100" name="whole-macro efficiency high, §7" -->
whole-macro at the contract's utilization. The entry's own source is a whole-macro
figure, so the note should say so explicitly, and it should record the **instance
depth of the ROM macros the model actually builds**: at 130 nm, the foundry's own
memories move from the 24.4% and the 83.9% quoted above across a 64-fold capacity
range, on depth alone. A scalar array efficiency with no stated depth is
under-specified in exactly the way the read-energy scalar is.

### `energy.rom_read_j_per_byte` — and `energy.sram_read_j_per_byte`

This is the entry where the recommendation is strongest and it is a recommendation
**not to move the number**.

The measurement says the 130 nm value is
1.69× <!-- figure: 1.69 src="results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#reference.measured_over_assumed_at_this_column_height" name="measured over assumed read energy, §7" -->
the constant at 64 rows, on a boundary that *excludes* three things the
constant's own boundary includes. That
is a real result and it points against the ROM. It still must not move the
constant, for two independent reasons, and either one alone would be sufficient:

1. **It is 130 nm.** §5.
2. **Identical treatment.** `energy.sram_read_j_per_byte` is
   2.6e-12 J/B, <!-- figure: 2.6e-12 src="configs/hardware/technology.json#energy.sram_read_j_per_byte.value" name="assumed SRAM read energy per byte" -->
   graded `assumed`. <!-- figure: "assumed" src="configs/hardware/technology.json#energy.sram_read_j_per_byte.grade" name="SRAM read energy grade" -->
   It is a plane split of one published GPU L1 measurement, and it has *exactly*
   the same physics as the ROM side — a read discharges a whole bitline whatever
   the array stores — and therefore exactly the same defect: it is a scalar where
   the quantity is affine in column height, and no measurement anywhere in this
   repository has resolved that for either side. Replacing the ROM side with a
   130 nm measurement while the SRAM side stays a scalar prices one side of the
   comparison and not the other. This repository has already shipped that failure
   once, across 430 comparisons.

   *This paragraph was itself an instance of the defect it describes.* It said
   "1 pJ/B, graded `assumed`, with no measurement behind it" — true when it was
   written and stale by the time it was committed, because another agent moved
   the constant to 2.6e-12 against an SC'25 measurement. Nothing refused it: an
   unannotated number in prose is invisible to `tools/check_prose_figures.py`.
   The two annotations above are the fix; they now fail the checker if either the
   value or the grade moves again.

**What should change instead: both notes.** Each should record that the quantity
is affine in column height, that a scalar per byte silently names a column height,
and that the model needs a column-height term rather than a better scalar. Any
future fix is one edit that moves both sides or it is not made at all.

---

## 8. The traps, and what each one would have refused

A finding in this repository is only closed when the thing that should have
caught it does catch it. Every check below is run on every invocation and every
one of them has been demonstrated to fire.

| The defect | What now refuses it | Where |
|---|---|---|
| A layout label that misses its conductor produces no port, magic writes a shorter `.subckt` without complaint, and the array simulates with its ground rail floating | the extracted port list is compared against the port list the generator drew, name by name and in order | `run_ihp_bitcell_density.check_ports` |
| The same trap one step further on: the ground pad is drawn and labelled, its via lands on nothing, and the port keeps its name while the transistors sit on a different node — a name check passes that netlist | every row transistor is required to touch the `VSS` port electrically, not just for the port to exist | `run_ihp_bitcell_density.check_ports` |
| The same omission reaching the macro flow, where the LEF simply declares one fewer pin and the router has nothing to complain about | the macro LEF's `PIN` records are compared against the same expected list | `run_ihp_rom_macro_route.draw_array` |
| A bitcell area transcribed by hand into another runner's source, so that re-measuring the bitcell silently leaves the macro quoting the old cell | the area is read from `bitcell.json`, and refused unless that measurement used the same revision of the layout generator this run draws with | `run_ihp_rom_macro_route.measured_bitcell_area_um2` |
| A constant in a governed contract citing an artifact that does not contain it | the wordline load is read from the read-energy artifact, and a contract value that the artifact does not support is refused | `run_ihp_rom_macro_route.measured_wordline_capacitance` |
| The macro array drawn on the generator's *default* dimensions while the bitcell area came from the contract's *nominal* dimensions — two independent number sets that happen to agree | the pitch the generator reports for the macro array is compared with the pitch that was measured | `run_ihp_rom_macro_route.draw_array` |
| A recorded artifact hash that looks like a determinism check and can never be reproduced, because the tool stamps a clock into the file | the array is drawn and extracted **twice** and the canonical, clock- and order-independent digests must match; the raw hashes are labelled archival identity only | `run_ihp_bitcell_density.canonical_digests` |
| The same defect in the read-energy runner, where every simulation deck carries the absolute path of that run's temporary build directory in its `.include` and `.lib` lines | a `canonical_deck_sha256` with every absolute path reduced to its file name is recorded alongside, and is refused unless the canonicalisation removed every absolute path; the raw hashes are labelled archival identity only | `run_ihp_rom_read_energy.canonical_deck_digest` |
| A die area that is really a restatement of a chosen utilization, reported as a measured array efficiency | the same netlist is re-routed on progressively smaller dies and the tightest that closes cleanly is reported as the measured floor; a contract with no probe ladder is refused | `run_ihp_rom_macro_route.die_floor_probe` |
| The fix above replacing that constant with a *second* one: the die floor was found at a placement density the runner chose, and the placer's own diagnostic named that constant as the remedy | a refusal whose diagnostic blames the target density is re-tried up the contract's density ladder before it counts, and one that survives the top rung still blaming it is recorded as conditional on the ladder, not as a floor | `run_ihp_rom_macro_route.die_floor_probe`, `validate_contract` |
| A model constant moving under a committed artifact, leaving its report comparing against a value the model no longer holds | every `assumed`/`assumed_grade` an artifact records is compared with the live entry at the `configs/hardware/technology.json` path it cites | `tests/test_rom_physical_chain.py` |
| A number in one of these documents drifting away from the artifact it came from | the load-bearing figures carry machine-resolvable provenance annotations and `tools/check_prose_figures.py` re-reads the artifact | `docs/ROM_PHYSICAL_METHODOLOGY.md`, `docs/ROM_DENSITY_NODE_TRANSFER.md` |
| A previous run's probe report left in the results directory after the probe was renamed or removed, indistinguishable from evidence this run produced, and simply absent from the manifest | every file this macro left behind and does not produce now is deleted before the manifest is written | `run_ihp_rom_macro_route.main` |
| Tap bands justified by assertion | the tapless control must actually fail, on a latch-up rule specifically, or the run refuses to record | `run_ihp_rom_macro_route.tapless_control` |
| A bitcell dimension asserted to be minimal | every probed dimension must produce a named DRC violation one step smaller | `run_ihp_bitcell_density.measure_rom_bitcell` |

---

## 9. Reproduction

```bash
python3 tools/run_ihp_bitcell_density.py      # ~1 min, draws the array twice
python3 tools/run_ihp_rom_read_energy.py      # ~40 min, 38 ngspice transients
python3 tools/run_ihp_rom_macro_route.py      # ~1 h, OpenROAD routes plus the
                                              #   density-escalated die probes
python3 -m pytest tests/test_rom_physical_chain.py
```

The order matters: the macro run reads the other two artifacts and refuses to
start without them.

The test file is not a smoke test. It reads the three committed artifacts back
and refuses the failures this chain has actually had: an `assumed` reference
drifting away from the live constant it cites, a generator edited after the runs
that quote it, a wordline load quietly swapped for the smaller of its two
windows, a die floor that is really a floor at a constant in the runner, and a
findings-erasing regression in any of the three results the chain exists to
state. Four of its cases construct broken contracts and require the runner to
refuse them, because a check nobody has seen fire is a check nobody has.

**What "reproducible" means here.** Each of the three runs above was executed
more than once in the course of writing this document, and every figure any of
their reports prints came back identical to every digit printed. Below that, two
things move and neither is a measurement: the archival file hashes (see the last
paragraph), and the last bits of a handful of floating-point accumulations over
the extracted parasitics, whose summation order `ext2spice` does not fix. The
second is a real non-determinism, it is bounded far below any reported precision,
and it is named rather than rounded away.

The drawn geometry and the extracted netlists are byte-identical across runs
*after canonicalisation*, and the bitcell runner proves it on every invocation by
drawing the array twice. The read-energy decks are byte-identical after their own
canonicalisation, which reduces every absolute path to its file name; the raw
files are not:
Magic stamps a wall-clock `timestamp` into the `.mag` and into the GDS header, and
`ext2spice` does not emit the extracted parasitics in a stable order. The
per-file `sha256` values recorded under `artifacts` are therefore **archival
identity only** and are labelled as such in the JSON.
