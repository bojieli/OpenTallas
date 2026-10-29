# DIE-QC-38 (2026-10-29 16:01-17:05 PDT) - QC-001 stage-2 classes, leaf drivers, VMR, A0

QC die FROZEN, fix-only. Base: DIE-QC-37 R7 (intel2 die-qc37/bb2/R7, 20,751 top-access conflicts, census 535 short / 89 spacing).
Run data: intel2:/srv/opentallas-scratch2/claude/die-qc38/ (diag_R7, prov_R7A..D, leaf_apply).

## 1. QC-001 root cause (diag_R7, reproduces R7 exactly: 20,751 top, census 535/89) - CHECKED
| class | count |
|---|---|
| provider FF CLK M1 endpoints on HORIZONTAL trunk branches (8,896 branches) vs shields 8,213 / PG 7,930 / tree 2,519 | 18,662 (90%) |
| native M7 port M9 jogs vs M9 PG / shields | 2,005 |
| clock-cell vias | 144 |
| census rows involving provider escapes (provider escape column == re-sited clock-cell stack column; provider access was planned on the pre-resite clock_seed) | 564 / 624 |
| census rows, other (native/other drops vs stacks) | 60 |

5,802 / 22,365 provider pins sit inside an M8 PG strap +- (0.32+0.04) band.

## 2. Fix variants (scripts/fixed_tree_prov.py monkeypatches C128._fixed_wires_stack; estimate = scripts/est.py)
| var | rule | top conflicts | census short/spacing | track stage |
|---|---|---|---|---|
| R7 | baseline | 20,751 | 535 / 89 | PASS |
| A | provider port near trunk (<=2.5 um) -> VIA78 riser branch on trunk; far -> M9 drop to nearest PG-clear M8 row | 3,290 | 542 / 89 | PASS |
| B | near <= STACK_RISER_MAX; far -> router M8 jog + M9 drop | - | - | FAIL 7 no_clock_track (ck_rn*_2 M8 11016.675) |
| C | A + native vertical-trunk drop on landing row | 3,290 | 542 / 89 | PASS |
| D | C with near <= 8.64 um (6,035 near / 2,861 far) | **2,903** | 542 / 88 | PASS |
All CHECKED (prebuild.json + classify.json in runs/). Best = D, -86% top conflicts; prebuild still FAIL (pin-access shorts).

Residual in D (runs/prov_R7D/classify.json): native/other M9 at port x vs M9 PG 1,803 (+ shields 174); provider M1 vs shields/tree 774;
clock-cell vias 144; census 542 short (296 provider M7 vs re-sited cell stacks, 156 clock-cell via vs provider M7) / 88 spacing.
Measured cause of the M9 class: 1,678 / 7,889 native M7 ports have pin x inside an M9 PG strap + spacing band, so ANY M9 jog at pin x
conflicts; when the drop row is moved off the landing row (router, 1,002 of 1,396 in C/D) the adapter draws that M9 jog.
Fix for successor: for these 1,678 ports reserve the M8 landing row from trunk column to pin x BEFORE tree tracks (no M9 at pin x),
and plan provider access against the R7 re-sited stacks (not clock_seed) -> clears the 564 provider census rows.

## 3. Leaf drivers (ot_clk leaf-drivers, main tools/clk/leaf_drivers.py, no fork)
GEOM-64 PASS-COND + GEOM-65 PASS (lanes/GEOM-REVIEW.md 16:07 REQ, render leaf_review.png).
Applied on reachfix source_bound.odb (sha 978a3f01, preflight READY_FOR_REVIEW 0 issues) with Codex apply_cells.py:
54,791 cells (22,365 flops + 32,426 comb), 6,532 new CKINVDC cells, native cells/connections/routes preserved (sha unchanged) - CHECKED.
Post-apply checks (leaf_apply/): 0 off-row, 0 off-site, 0 overlap of the 6,532 new cells vs all placed cells; readback ACTUAL_REACH_PASS,
32,514 registered arcs, max 403.698 um (<=405), 0 undriven - CHECKED. Applied ODB: intel2 die-qc38/leaf_apply/provider/provider.odb (sha 27ffec18).
readback_complete_leaf.py = Codex readback_complete.py with only the hard-coded cell/term counts updated (48,259/185,698 -> 54,791/198,762).
Open: fixed-tree endpoints must become the 3,266 trunk-side CKINVDCx5p33 A pins (FF CLKs now on leaf nets); tools/clk/provider_clock_loads.py
accepts DFF/SDFF masters only -> shared tool change (ROOT-MERGE). Expected: provider top class scales 22,365 -> 3,266 endpoints.

## 4. VMR MIF1 (epyc2 die-qc-37-vmr/kit_mif1)
Unit oth-ubuntu-2071164: GRT hold pass 1 FAIL (-61.12 -> -16.05, 7 int). Pass 2 (unit oth-ubuntu-2180717, f4i_chain_h2.sh): GRT hold +7.70/0,
clock fingerprint unchanged, clock-first DRC 0, signal DRT DRC 0, LAYER_SEP PASS, LEC EQUIVALENT 5959/5959.
Sign-off first stopped on a tool-bundle gap (snapshot main_sofix lacked physical/common_flow/clock_family.tcl; added from main, signoff.py == main 0047bca58).
Rerun (unit oth-ubuntu-2377699): NOT SIGNED OFF - TT setup +204.21, FF hold -5.27 ps / 29 ep (sdc -11.77), TT slew 3 pins 332.7/320 ps
(_12945_/A, _14774_/A, _14788_/A), DRC 0, pair skew 36.9/35.6 - CHECKED (signoff_main/signoff.json).
Next: post-route hold repair on measured routed arrivals + 10 ps and resize the 3 slew drivers, ECO route, re-sign.

## 5. A0 (branch claude/die-qc-38-a0-1029@a44efbbe510)
No build. V2 per-stage measured 33-47 ps real vs 27.55 planned (~14 TritonCTS); NL -281.18 / NK -289.88 CHECKED.
Next generator: standard stages (fanout 2, legs 40-60 um, ~24+-3 ps/stage). core_infra opt-in stays OFF.
