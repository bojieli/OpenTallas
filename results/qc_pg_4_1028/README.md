# QC-PG-4 (2026-10-28): A0 clock gating vs 75-um bump field -- estimate for the owner decision

Successor of QC-PG-3 (claude/qc-pg-3-1028@56428859c9). Same deck and method: QC-PG-MAP M9 .672 upper deck, exact linear
class superposition (tools/pg_activity/qc/a0_superpose.py, reproduces QC-PG-3 48.139 mV per W/mm2 / 44.51 mV CHECKED),
VDD drop + VSS bounce co-located per block, 450-um window edge excluded, F 0.27 W/mm2, + 4.597 mV below-M7 A0 budget.
Pass = <= 35 mV total. All PDNSim solves EXIT 0, PSM OK, pad_fallback 0 (CHECKED as run outputs; no independent NUMBER-CHECK).

## 1. Which basis gates static IR
A0 tiles run in lockstep (one broadcast matvec), so the whole array switches between floor and busy together.
Busy runs are 64-1,583 cycles (53 ns-1.3 us): the 256-cycle gate/up run is 213 ns and the LM head 1.3 us, long against the
package/bump/decap settling (~10-50 ns). The grid therefore reaches the busy-state DC drop inside every run: **the burst
(busy, 1.448 W/mm2) basis is the static-IR gate**; window and token averages are energy/thermal numbers, not IR numbers.

## 2. (a) Per-tile ICG on A0 (incl. the ROM macro clock) -- estimate
Floor breakdown of the NK parent 4_cts (a0_floor_brk.tcl, activity 0, TT, placement RC; brk/clock_levels.txt CHECKED):
parent clock tree 32.43 mW over 21 levels (levels 0-14 = 3.1 mW trunk, 15-20 = 29.3 mW leaf), seq clock-pin 18.95 mW
(1,317 input-face regs 1.68 mW, 13,717 others 17.27 mW), 19 child clock pins at levels 10-13. ICG probes (Liberty, EN 0,
CLK at the root): ICGx1 1.43, x2 1.72, x4 2.19, x8DC 4.68 uW.
Gated idle floor per NK tile (ESTIMATE): leakage (all children + parent, from the QC-PG-3 reports) 0.60 mW + ungated input
faces (tap_q/n_a_q/n_b_q, 1,317 regs: 1.68 seq + 2.57 leaf-tree share at 1.95 uW/sink + 0.5 face trunk) 4.75 + ICGs 0.10 +
enable logic 0.03 + region trunk above the tile root 1.0 (allowance; not in the 0.822 either) = **6.5 mW = 0.012 W/mm2**
(was 435.6 mW = 0.822). Busy unchanged 1.448 W/mm2 (the ICG cannot reduce truly busy power).
Duty with ICG: drain hangover D <= 64 cycles per run (UNCHECKED bound on go -> n_y/t_out latency), 145 runs/token:
token 9.6 % -> 0.151 W/mm2; gate/up window (256+64)/537 = 59.6 % -> 0.868 W/mm2.
(a+) also ICG each romleaf on its own bank ce (2 of 10 banks read per cycle): busy 767.8 -> 656.8 mW = 1.239 W/mm2 (ESTIMATE).

Placement in the local clock form (12.13b/12.16e): ONE ICG (ICGx8DC) at each A0 tile clock root, i.e. the leaf end of the
region tree, below the region node and below every crossing node. The tile root splits into (1) an UNGATED face branch
(input face regs, the go/valid face bits, reset landing, any CA landing buffer and its counters) and (2) the GATED branch
(everything else: parent glue tree, 8 rawleaf, 10 romleaf incl. the ROM macro CLK, node). Output faces t_out_q/n_y_q are
gated (they hold).
Enable (static schedule, no protocol or port change): en = go_face (tap_q[0]) | engine busy | drain counter != 0 |
n_va face (n_a_q[512]) | reset not released. go is registered at the face at edge t; the ICG latch passes it for edge t+1,
which is exactly the first gated capture (the IREG go_q stage) -> **1 cycle of lead, already present; 0 added schedule cycles**.
Timing path face Q -> OR -> ICG.E at the root: ~833 - 250 (face insertion) - 30 (setup) = ~550 ps for <= ~700 um (UNCHECKED).
CA / start-tree impact: **none**. The ICG is below the tile root, so the shared clock up to every crossing node and the
unshared clock per crossing are unchanged; CA counters and landing buffers sit on the ungated branch (must not be gated);
reset release is unchanged (en forced 1 until reset is released). In-tile cost: one ICG delay (~30 ps) between the face and
gated branches, balanced by CTS (related pairs inside the tile, within the in-region 150-ps spread).
Proof needed before adoption: production benches (rawleaf/romleaf/tile) with the ICG model trace_identical + LEC.
Cost per NK tile: 1 ICGx8DC (0.70 um2) + ~35 enable cells (~15 um2), ~0.003 % area; die 768 ICG + ~27k cells (~0.012 mm2);
(a+) +10 ICGs per tile. No routing tracks, no bump change.

## 3. (b) 75-um bump field over the A0 array only -- SOLVED (mixbump.py on the QC-PG-MAP kits)
| field (37.5-um pads in the field, 150/70 elsewhere) | A unit mV per W/mm2 | burst total | note |
|---|---|---|---|
| none (150 everywhere) | 48.14 | 74.68 FAIL | QC-PG-3 reproduced |
| 75 over A0 outlines only (streets keep 150) | 24.62 | 46.47 FAIL | worst at tile edges next to 150-pitch streets |
| 75x150 (2x bumps) over the array incl. streets | 41.69 | 65.19 FAIL | 2x bumps buys only 13 % (near-field drop) |
| **75 over the array incl. streets (outlines +155 um), A0 window** | **16.48** | **28.46 PASS** | = B75 interior |
| same, SU window (array-edge tiles + su_c at 150) | 16.41 | 28.37 PASS | su8 22.35 (F 0.27) unchanged; edge band at flat F 0.5823 33.95 = base |
A naive field edge (outlines +80 um) put a 37.5-um-shifted bump row at the edge: 39.4 mV at flat F 0.5823 in su_c (artefact);
the +155-um field with every 150-um bump >= 75 um from the fine field kept removes it (33.95 = the 150-um base value).
Bumps (ESTIMATE from 43.0 vs 176.6 bumps/mm2, field area by raster of the 768 A0 outlines): A0 array incl. streets +155 um
= 630 of 819.9 mm2 -> ~119k bumps (+84k, 3.4x) vs die-wide 75 ~145k (+110k, 4.1x) vs today ~35k. Outline-only (407 mm2,
~90k) FAILS. So the A0-only field saves ~18 % of the added bumps versus die-wide.
Package/RDL: no package rule deck exists in the repo (BUMP-SURVEY: no plan carries bump pitch/pad/map). Industry practice
allows a mixed-pitch power field on one die when the whole die uses one fine-pitch-capable bump process (Cu pillar on a
fine-line substrate, or an interposer/RDL), with power bumps of the dense field landing on plane via arrays; a 150-um C4
solder field mixed with 75-um bumps on one die is not standard. -> UNCHECKED; package choice is the owner's.

## 4. Table (A0 window unless noted; total = upper + 4.597; PASS <= 35)
| option | floor mV | window mV | burst mV | verdict (burst gates) | cost |
|---|---|---|---|---|---|
| current (no ICG, 150 um) | 44.51 | 59.74 | 74.68 | FAIL | - |
| (a) ICG per tile, 150 um | 12.81 | 46.74 | 74.68 | FAIL (burst, also window) | ~768 ICG + 27k cells, 0 tracks, RTL+LEC proof |
| (a+) ICG + per-bank ROM ICG, 150 um | 12.81 | <= 46.7 | 64.59 | FAIL | +7.7k ICG |
| (b) 75 um over A0 array incl. streets, no ICG | 18.14 | 23.35 | 28.46 | PASS | ~119k bumps (3.4x), fine-pitch package |
| (c) ICG + (b) | 7.29 | 18.90 | 28.46 | PASS (burst same as b) | (a)+(b) |
| (c') ICG + 2x (75x150) field | 10.53 | 40.99 | 65.19 | FAIL | ~2x bumps |
| (d) 75 um die-wide | 18.08 | 23.27 | 28.37 | PASS | ~145k bumps (4.1x) |
Burst needs A unit <= 20.75 mV per W/mm2 at 1.448 W/mm2 (or busy <= 0.62 W/mm2 at 48.14): only a 75-um-class field (or G12
grid, QC-PG-3: 30.0) gets there. ICG closes the floor and token terms (energy, thermal) and is still a design requirement,
but it cannot close the static-IR burst.
