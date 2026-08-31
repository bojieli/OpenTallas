# Does the mask-ROM to SRAM bitcell area ratio transfer between nodes?

**Answer: no. It moves by +93% between 130 nm planar and a 7 nm-class FinFET
node, and it moves against the ROM.** `rom.cell_to_sram_cell_area_ratio` needs a
per-node treatment, exactly as `links.on_wafer` was split into `links.on_wafer`
and `links.on_wafer_n5` when the same question was asked of it.

---

## 1. Why this had to be tested

`rom.cell_to_sram_cell_area_ratio = 0.2` is graded `assumed` in
`configs/hardware/technology.json`, and its own note calls it *"the single most
load-bearing assumption in the ROM capacity chain"*. It decides how much weight
fits per mm², which decides how many devices a model needs, which decides mesh
diameter, which is over half the step time at batch 1.

A sibling experiment measured that ratio at **IHP SG13G2**, the only open PDK in
this repository with real foundry collateral. IHP SG13G2 is a **130 nm** process.
The program targets **N6/N5**. The transfer from one to the other rests on a
premise nobody had tested: **that the ratio is node-stable.**

A ratio of two structures drawn in one process does travel further than either
absolute area — contact size, contact-to-gate clearance, diffusion spacing and
gate length all enter both cells and partly cancel. But "further" is not
"unchanged". This document tests the premise at a 7 nm-class node.

## 2. What ASAP7 is, and the line this document does not cross

`docs/OPEN_PDK_SELECTION.md` is binding:

> **ASAP7** — Published as a 7-nm FinFET *predictive* PDK. Research FinFET
> assumptions. Research decks and cell libraries, not a foundry manufacturing
> kit. **Excluded as transistor/manufacturing evidence.** May be used only for
> explicitly predictive digital experiments.

Accordingly:

- **No number in this document is a TSMC N7, N6, N5 or N4 figure**, and none may
  be labelled one.
- **The ASAP7 and IHP results are never averaged, blended or interpolated.** They
  are two measurements at two nodes and one comparison between them.
- **No ASAP7 FakeRAM collateral was read or used.** The platform's `ram/`
  directory contains only `cva6.cfg`, and `fakeram.cfg` is a generator config;
  neither holds a bitcell. Both are present in the verified tree and both are
  recorded as unused. Every shape measured here was drawn from the ASAP7 design
  rules.
- What ASAP7 *can* support is a predictive statement about **how a ratio behaves
  between nodes**. That is the only claim made.

## 3. Where ASAP7 is installed

The Liberty-only tree at `/home/ubuntu/.local/opentallas-pdk-asap7` (5 NLDM
`.lib` files, no layers, no rules) is **not** sufficient for layout. The complete
ASAP7 v1.7 platform lives inside the pinned OpenROAD-flow-scripts container that
the existing `tools/run_asap7_physical.py` campaign already uses, at
`/OpenROAD-flow-scripts/flow/platforms/asap7`.

It was extracted read-only to:

```
/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7
```

from image `openroad/orfs` digest
`sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`.

Every file used is hash-verified against `configs/pdk/asap7_physical_lock.json`
on each run, and the run aborts on any mismatch:

| File | SHA-256 (from the governed lock) |
|---|---|
| `lef/asap7_tech_1x_201209.lef` | `7694bf4f…4ca41` |
| `gds/asap7sc7p5t_28_R_220121a.gds` | `f43d5b33…b9263` |
| `drc/asap7.lydrc` | `dc78ccd8…c7765d` |
| `KLayout/asap7.lyt` | `c0d9587a…6d8fba2` |
| `config.mk` | `c5c868f3…42507c` |

DRC is the platform's **own** shipped KLayout deck, `drc/asap7.lydrc`, coded from
`asap7_drm_201207a.pdf`, run under KLayout 0.30.7 inside that same pinned
container.

## 4. Method

The measured quantity is **the smallest array lattice pitch at which a DRC-clean
array can be drawn**. Arrays, not isolated cells — a single cell in isolation
does not exercise the abutment rules that actually set a bitcell pitch.

Both cells were drawn from scratch on ASAP7's own layers by
`tools/asap7_bitcell_density.py`, using the drawn conventions taken directly from
ASAP7's shipped `INVx1_ASAP7_75t_R` (uniform 27 nm fin sea, 20 nm gates on an
exact 54 nm pitch, one-fin actives 27 nm tall, 24 nm SDT/LISD bars overhanging
the active by 4 nm, GCUT only in the gap between actives).

Process constants, all read from the deck rather than assumed:

| Constant | Value | Deck rule |
|---|---:|---|
| Contacted poly pitch (CPP) | 54 nm | `GATE.S.1` "Exact horizontal GATE pitch" |
| Fin pitch | 27 nm | `FIN.S.1` "Exact vertical FIN pitch" |
| Gate width | 20 nm | `GATE.W.1` "Exact horizontal width of GATE" |
| Min active height | 27 nm, quantised to 27 nm | `ACTIVE.W.1`, `ACTIVE.W.2` |
| Min active vertical spacing | 27 nm | `ACTIVE.S.1` |
| Min S/D active horizontal spacing | 92 nm | `ACTIVE.S.2A` |
| Min n-well vertical spacing | 108 nm | `WELL.S.1` |

**Minimality is proved, not asserted.** For each pitch dimension the array is
regenerated one lattice quantum smaller and must *fail* DRC on a named rule. At a
FinFET node the smallest legal step is a whole quantum — a whole fin pitch or a
whole CPP — which is itself part of the finding (§7).

## 5. The two cells

### 5.1 NOR mask-ROM, via-programmed — 108 × 54 nm = 5,832 nm²

One nMOS per bit. Bits are laid out as mirrored **D-G-S-G-D** islands: two bits
share a source, each bit keeps a **private drain with its own programming via**,
and islands are separated by an active break. This is the program's own topology,
from `spice/ihp_sg13g2/rom_slice/schematic.spice` — *"the row transistor drain is
connected to `BL_PRESENT`"* versus *"`ROM_DRAIN_ABSENT` has no via to
`BL_ABSENT`"* — and it is the same topology the sibling drew at IHP.

The array is drawn complete through the back end: horizontal M2 bitline per row,
vertical M1 source column, V0/M1/V1 drain stack per bit, and the programming V1
present or absent. The generated array carries programmed and unprogrammed bits
so the via delta is exercised, matching the sibling's present/absent column
method.

Why the pitch cannot shrink:

| Dimension | Pitch | Probe | Result |
|---|---:|---|---|
| x (bitline direction) | 108 nm = 2 CPP | rebuild at 162 nm period | **60 violations**: `ACTIVE.S.2A` (92 nm S/D spacing), `GATE.S.1` |
| y (wordline direction) | 54 nm = 2 fin pitches | rebuild at 45 nm row pitch | **149 violations**: `ACTIVE.S.1` (27 nm), `ACTIVE.FIN.EX.1`, `LISD.S.3-4`, `M1.S.2` |

### 5.2 6T SRAM thin cell — 108 × 216 nm = 23,328 nm²

Two CPP wide, four one-fin device bands tall, in the canonical thin-cell order
NMOS-A (PG1, PD1) / PMOS-A (PU1) / PMOS-B (PU2) / NMOS-B (PG2, PD2). The wordline
is a vertical gate line running the full array height; the cross-coupled gates are
cut by GCUT in the gap between PMOS-A and PMOS-B and again between vertically
adjacent cells. The cell carries ASAP7's `SRAMDRC` recognition layer and therefore
gets the PDK's memory-cell rule relief.

**ASAP7 ships no SRAM bitcell.** Its standard-cell GDS holds 212 cells and not one
of them is a memory cell; the platform's only memory collateral is FakeRAM, which
is forbidden here and was not used. The cell therefore had to be drawn. Three
independent checks say the drawn pitch is the right one:

1. **Seven SRAM-specific ASAP7 rules are satisfied with exact equality** at this
   pitch — `WELL.S.1` = 108 nm, `ACTIVE.S.1` = 27 nm, `SRAM.ACTIVE.WELL.S.5` =
   13.5 nm, `SRAM.*SELECT.ACTIVE.EN.3-4` = 13.5 nm, `GATE.ACTIVE.S.4` = 9 nm,
   `ACTIVE.S.2A` = 92 nm, `GCUT.GATE.S.2` = 17 nm. Seven rules landing
   simultaneously on their minimum is strong evidence that this is the cell those
   rules were dimensioned for.
2. **Shrinking the cell height by one fin-pitch quantum fails DRC** on `WELL.S.1`
   — the n-well spacing between mirrored cell rows is exactly at its 108 nm floor.
3. **The metal fits inside the front-end pitch with room to spare.** At 216 nm
   height and 36 nm M2 pitch the cell has 6 horizontal M2 tracks and needs 5 (BL,
   BLB, VDD, two VSS). At 108 nm width and 36 nm M1 pitch it has 3 vertical M1
   tracks and needs 2 (the Q and QB cross-couple straps). The wordline is the gate
   line itself and costs no metal. The cell is front-end limited, which is the
   normal situation for an SRAM bitcell.

Point 3 is an argument, not a measurement — the internal cross-couple metal was
not drawn. §8 states the direction of that gap.

### 5.3 The unprogrammable floor — 54 × 54 nm = 2,916 nm²

For reference only. If every source/drain region is shared between the two
transistors flanking it, a 1T NOR ROM reaches 1 CPP × 2 fin pitches and is
DRC-clean. But no node in that array is private to one bit, so **a contact or via
cannot program a single bit**; such an array is reachable only by implant/Vt
programming, which is not the program's mechanism and not what the sibling
measured. It is quoted as a floor, never as the comparator.

## 6. The comparison

| Node | ROM bitcell | 6T SRAM bitcell | **Ratio** | 6T ÷ ROM |
|---|---:|---:|---:|---:|
| **IHP SG13G2**, 130 nm planar, real foundry PDK (sibling) | 0.390150 µm² | 3.0067 µm² | **0.1298** | 7.71× |
| **ASAP7**, predictive 7 nm FinFET (this run) | 0.005832 µm² | 0.023328 µm² | **0.2500** | 4.00× |

**They do not agree. The ASAP7 ratio is +92.7% higher — a factor of 1.93.**

In absolute terms the ratio moves from 0.1298 to 0.2500, +12.0 percentage points.
Put the other way: at 130 nm a 6T SRAM bitcell costs **7.71×** a mask-ROM bitcell;
at a 7 nm-class FinFET node it costs only **4.00×**. **The mask ROM loses roughly
half of its relative density advantage over SRAM in the move from planar 130 nm to
FinFET 7 nm.**

Against the assumption:

| | Value | vs assumed 0.20 | vs assumed bracket 1/6 – 1/4 |
|---|---:|---|---|
| IHP SG13G2, 130 nm | 0.1298 | 0.65× | **below** the 0.1667 floor |
| ASAP7, 7 nm-class | 0.2500 | 1.25× | exactly **at** the 0.2500 ceiling |

The stated bracket does not contain both measurements, and the two nodes span
1.93× — wider than the bracket's own 1.5× span. The point value 0.20 happens to
sit between the two, but it sits there by accident, not by derivation, and it is
not node-stable.

**A sharper way to see it:** even the ASAP7 ROM's *unprogrammable* floor (0.1250,
§5.3) does not beat the 130 nm *programmable, measured* ratio (0.1298). At a 7 nm
FinFET node, a mask ROM cannot do better against SRAM than a 130 nm mask ROM
already does — even after throwing away per-bit programmability.

## 7. Why they differ — the mechanism, which is the real finding

The trap in this exercise was that a ROM bitcell in a FinFET process is not a
smaller version of a planar one. That is exactly what happened, and it has two
compounding parts.

### 7.1 Fin and CPP quantisation: the ROM cell is *entirely* quantisation-limited

At ASAP7 both cells land on exact integer multiples of CPP × fin pitch
(54 × 27 nm = 1,458 nm²):

| Cell | Area | In CPP × fin-pitch units |
|---|---:|---:|
| 6T SRAM | 23,328 nm² | **16** |
| Via-programmed mask ROM | 5,832 nm² | **4** |
| Shared-S/D ROM floor | 2,916 nm² | **2** |

The ratio is therefore a ratio of *small integers*, 4/16, and it can only take
discrete values. There is no 4.3 and no 3.7.

That quantisation is not symmetric in its effect. The sibling's 130 nm ROM cell
is 510 × 765 nm, built by summing independent continuous minimum dimensions —
device width 300, diffusion gap 210, contact-to-poly 380, diffusion overlap 340,
poly width 130 — and their minimality probes shrink each by **10 nm**, roughly 2%
of the cell. At ASAP7 no such probe exists. The smallest legal change to the ROM
cell is a whole fin pitch (27 nm, a **50%** change in its row pitch) or a whole
CPP (54 nm, a **50%** change in its column pitch). **A single-transistor cell at
7 nm is already so small that it is nothing but quantisation floor; there is no
10 nm left to give back.** The 6T cell, at sixteen quanta, is large enough that
its dimensions are still being set by real spacing rules with useful granularity,
and the industry has spent two decades of dedicated co-optimisation spending that
granularity.

### 7.2 The memory-cell rule relief helps the 6T cell and does nothing for the ROM

Both PDKs give the SRAM bitcell its own rule set. The sibling measured this at IHP
and found the foundry 6T cell carries the `SRAM` recognition layer (GDS 25/0) and
is **illegal** under the public logic deck by 29 violations. ASAP7 does the same
thing explicitly: a `SRAMDRC` layer (GDS 99/0) switches on relaxed rules —
select and well enclosure of active drop from 46/27 nm to **13.5 nm**, SDT
vertical width from 27 nm to **17 nm**, minimum active area from 864 nm² to
**432 nm²**, LIG-to-gate overlap from 320 nm² to **240 nm²**, and the
`GATE.S.2` isolated-gate rule is waived entirely.

The sibling correctly flagged this as making their 0.1298 an **upper bound**: a
ROM given the same relief would be smaller, so the true single-rule-set ratio at
130 nm is ≤ 0.1298.

**This run tested that same question directly at ASAP7 and the answer is
different.** Case `rom_via_sram_rules` redraws the via-programmed ROM array with
the `SRAMDRC` layer covering it, granting it every memory-cell relaxation ASAP7
offers. Result: **DRC-clean at exactly the same 108 × 54 nm pitch, and still
failing at 162 nm period on `ACTIVE.S.2A` and `GATE.S.1`.** The relief buys the
ROM **zero** area, because the ROM's pitch is pinned by rules that have no SRAM
variant — the 92 nm source/drain spacing, the 27 nm active spacing, and the exact
54 nm gate pitch.

So the asymmetry runs one way at each node, and it runs in opposite directions
for the *bound*: at 130 nm the true same-rules ratio is at most 0.1298; at ASAP7
it is exactly 0.2500. **The 93% gap is a lower bound on the disagreement, not an
upper one.**

## 8. Direction, and how hard this was scrutinised

**A smaller ROM cell relative to SRAM favours the ROM side. This result points
the other way: it makes the ROM cell relatively larger, and it moves the headline
against the ROM.** It therefore gets the lighter scrutiny burden, and it is
recorded as one more correction in the same direction as the last three days'
worth. The places where this measurement could still be wrong, and which way each
one pushes:

| Gap | Direction |
|---|---|
| The ASAP7 SRAM cell had to be hand-drawn — ASAP7 ships no bitcell and FakeRAM is forbidden. The sibling's SRAM is a real foundry cell cross-checked against 28 shipped macros' datasheet bit counts. **This is the largest methodological difference and it is unavoidable.** | If the drawn SRAM is too small, the ratio is too high — **against ROM**. Robustness: even if the SRAM were a full fin pitch taller (26,244 nm²) the ratio would be 0.2222, still **+71%** over IHP; two fin pitches taller (29,160 nm²) gives 0.2000, still **+54%**. The conclusion survives a large SRAM error. |
| The SRAM's internal cross-couple metal was not drawn; the ROM's back end was drawn complete through M2. | If metal forced the SRAM larger the ratio would fall — **towards ROM**. §5.2 point 3 shows the track budget has spare capacity on both M1 and M2, so this is unlikely to bind, but it is not measured. |
| The ROM is the *more* completely drawn of the two cells. | Ensures the ROM is **not understated** — the conservative direction. |
| ASAP7 is predictive, with no calibrated error bar against any real 7 nm process. | Unknown sign. This is why the result is a statement about **node transfer**, not an N6 value. |

## 9. Where the methodology matched the sibling, and where it could not

Two ratios measured two different ways are not comparable, so this is stated
explicitly.

**Matched:**

- Same question, same definition: minimum DRC-legal drawn **bitcell pitch area**,
  ratio taken **within one PDK**.
- Same ROM topology: via-programmed NOR mask ROM, one nMOS per bit, **two bits per
  diffusion island sharing a source, each bit with its own private programming
  via**. Confirmed against the sibling's drawn `ihp_rom_bitarray.mag`: their
  channels sit on a 510 nm column pitch with 210 nm diffusion isolation and
  alternating 1020/510 nm row steps, i.e. mirrored source-sharing pairs — the same
  D-G-S-G-D island as drawn here.
- Same standard of proof for minimality: shrink one dimension, name the rule that
  breaks.
- Same use of the PDK's **own shipped deck** as the arbiter.
- Same rule-set-asymmetry question asked and answered rather than assumed away.
- Same claim boundary: no scaling to N7/N6/N5/N4, no silicon claim.

**Could not be matched:**

1. **SRAM provenance.** Theirs is a foundry-shipped bitcell. Mine is hand-drawn,
   because ASAP7 has no foundry SRAM and its only memory collateral is the
   forbidden FakeRAM. Unavoidable; §8 gives the direction and the robustness.
2. **DRC engine.** Theirs is Magic `drc(full)` with the IHP deck; mine is KLayout
   with `asap7.lydrc`. Each is the PDK's own deck; ASAP7 ships no Magic rule file.
3. **Minimality probe granularity.** Theirs shrinks by 10 nm (~2% of a cell
   dimension). Mine shrinks by one lattice quantum (~50%). This is not a choice —
   it is forced by FinFET quantisation, and §7.1 makes it part of the finding.
4. **Extraction.** Their existing IHP pipeline also does LVS and PEX. This run is
   geometry and DRC only; no netlist, no parasitics, no read margin.

## 10. What grade this can honestly carry

| Claim | Grade | Reason |
|---|---|---|
| ASAP7 ROM and 6T bitcell pitch areas, and their ratio 0.2500 | **measured** (evidence class: *predictive open-PDK drawn geometry*) | Drawn, DRC-clean under the PDK's own hash-verified deck, minimality proved by named-rule failure one quantum down. |
| "The ratio is **not** node-stable" | **measured** | Falsification needs only that two same-question measurements differ by more than methodological wobble. 93% is far outside any plausible wobble (§8 shows it survives a two-quantum SRAM error). Falsification is far more robust than either point value. |
| `rom.cell_to_sram_cell_area_ratio` at N6/N5 | **still `assumed`** | Nothing here measures a real 7 nm foundry process. ASAP7 is predictive and excluded as manufacturing evidence. |

The honest summary of the state of this constant: it has gone from *one assumed
number with no measurement behind it* to *one assumed number bracketed by two
measurements at two nodes that disagree by 93%, with a mechanism that explains the
disagreement and predicts its sign*. That is a real improvement in evidence, and
it is not a measurement of the target node.

## 11. What this licenses, and what it forbids

**Forbidden, from this point on:**

- Presenting the IHP SG13G2 **0.1298** as evidence for an N6/N5 constant. It is a
  130 nm measurement, and the node-transfer premise it depended on has now been
  tested and failed. It remains excellent evidence for **130 nm** and excellent
  evidence that *a ratio measurement is possible*; it is not evidence for a
  leading-node value.
- Presenting **0.2500** as a TSMC N7/N6/N5 number. It is ASAP7, predictive.
- Averaging, blending or interpolating the two.
- Quoting either without naming its node.

**Required:**

- **Split `rom.cell_to_sram_cell_area_ratio` into per-node entries**, on the
  `links.on_wafer` / `links.on_wafer_n5` precedent — a 130 nm entry carrying the
  measured 0.1298, and N6/N5 entries whose value is chosen against the ASAP7
  measurement rather than against the 130 nm one, still graded `assumed` and
  carrying the predictive caveat. The single node-free scalar is no longer
  defensible: this repository has now measured it twice and got two answers.
- **Widen the swept bracket.** The current 1/6 – 1/4 does not contain the 130 nm
  measurement. The measured span across the two nodes is 0.1298 – 0.2500; any
  sweep that claims to bound this constant must at least cover it.

**The stake, in the model's own primitives.** Using the numbers already in
`results/roofline/*/analytical.json` — 24.07 Mbit/mm² usable SRAM,
`rom.array_efficiency` 0.70 against `sram.array_efficiency` 0.65:

| Ratio used | ROM density | vs the assumed 0.20 |
|---|---:|---|
| 0.1298 (IHP, 130 nm) | ~200 Mbit/mm² | +54% |
| **0.20 (currently assumed)** | ~130 Mbit/mm² | — |
| **0.2500 (ASAP7, node-appropriate)** | ~104 Mbit/mm² | **−20%** |

Moving from the assumed 0.20 to the node-appropriate 0.25 costs **20% of ROM
capacity per mm²**, which needs **25% more devices** for the same model, which —
if mesh diameter scales as √N as the 2-D mesh model implies — lengthens the mesh
diameter by about **12%**, on a term that is over half the step time at batch 1.
Choosing the 130 nm number instead would have moved the same lever **the other
way by 54%**. That factor-of-two swing on a load-bearing constant, decided purely
by which node you measured at, is the reason this test was worth running.

## 12. Reproduction

```bash
python3 tools/asap7_bitcell_density.py
```

Requires Docker and the pinned ORFS image, plus the ASAP7 platform extracted to
`~/.local/opentallas-pdk-asap7-platform` (or `--platform`). Every ASAP7 file is
hash-checked against `configs/pdk/asap7_physical_lock.json` before anything runs.

Outputs: `results/asap7_physical/bitcell_density/bitcell_density.json` and
`REPORT.md`. Runs are deterministic: the drawn geometry and every DRC result are
byte-identical across repeat runs, recorded per case as `geometry_sha256`. The
companion `gds_sha256` is archival identity only — KLayout stamps its write time
into the GDS header, so that hash is not stable and is not used as a determinism
check. The sibling's 130 nm counterpart is
`results/spice/ihp_sg13g2_bitcell/` via `tools/run_ihp_bitcell_density.py`; this
run reads that result read-only for the comparison in §6 and modifies nothing
under `results/spice/`.
