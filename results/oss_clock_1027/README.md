# OSS-CLOCK (2026-10-27 19:52-21:xx PDT): open clock tools, CLKPLAN + METAL + MSCTS in one lane

Branch claude/oss-clock-1027, from claude/oss-clkplan-1027@a3881ae9c (OSS-CLKPLAN-1). OSS-METAL-1 and OSS-MSCTS-1 had no
pushed branch. Run data: intel1:/srv/opentallas-scratch2/claude/oss-clock-1027 (run.sh = the docker commands).
Labels: OWN = my run, not independently checked. Nothing here is a gate number; these are tool results.

## 1. CLKPLAN: region mode (METHODOLOGY 12.13) on the shared schema
- Schema `opentools.plan/1` (opentools/common) gains `feeds[]`: the region clock feed graph. Each feed has `src` (root or a
  region), `dst`, `len_um`, `kind` (forward or spine) and `tap` (root or leaf). It also gains `regions[].clock`, and the
  output sections `region_clock_plan`, `metal_alloc` and `mscts`. The README maps the locality.py feed forms onto it:
  locality 'fwd' = `tap: leaf`, 'top' = `src: root`. There is one schema and no second copy.
- `python3 -m clkplan.run PLAN --mode region` predicts root arrivals and local insertion. For every crossing it gives the
  common point, the unshared clock, nominal d, and the derated margin (AOCV + droop, same functions as die mode).
- Parity: these are tests, and they reproduce the results of two independent earlier tools.
  - It matches main tools/die_plan/clk_aocv.branch_pessimism to 1e-9.
  - It reproduces claude/qc-sliceclk2-1027@d2a6b2d12b predict_out.txt: slice<->slice damage 235 TT / 194 FF, and K=3
    forwarded 133 / 109.
- On the toy plan, a neighbour-forwarded 3-mm hop FAILS on nominal d alone (|d| ≈ 641 ps TT). This is the same reason
  QC-SLICECLK-2 rejected the forwarded chain.

## 2. METAL: top-metal track allocator (opentools/metal)
- `alloc.allocate` places each clock wire at a legal across-run position. The rules:
  - It sits in a PG gap, with NDR width/space.
  - Shields are none, drawn, or pg_flank (pg_flank = one wire per gap).
  - It may enter only its own row's pin window. Every other wire must stay outside all windows.
- `phase_scan` gives the off-window slots per row period as a function of the row phase relative to the PG grid.
- QC R34 case, using the 209 M8 rows of claude/qc-infra-r34-1027@3752a99e90 d18_r2_plan_errors_blockers.json:
  - Every one of the 209 rows reproduces as a structural conflict (OWN). An off-window 16w wire has no legal position
    within 8.64 um of its ideal track, even with nothing else placed, and the blocker is a pin window.
  - The pin rows sit 0.13 / -0.41 um from a PG stripe, which gives 0 off-window slots.
- Plan-level fix, found by phase_scan (OWN, UNCHECKED against real pin access): place the slot rows (or the PG) so each
  row centre falls 1.16-3.16 um from a stripe, i.e. near a gap centre. This frees 1 off-window 16w slot per 8.64 um.
  - The R34 example row (own in + out trunks + one escape) fits only with BOTH changes: the phase shift AND a
    flow-oriented repeater (R34 option B).
  - The phase shift alone, or option B alone, still conflicts.
  - This is input for INFRA-FIRST-QC-R35 (row allotment). It is not a rule.

## 3. MSCTS region mode (opentools/mscts)
- Builder: bottom-up zero-skew merging along buffered L paths.
  - Objectives: `late_split` (listed crossing pairs merge first) or `nearest`.
  - Stage model: a node's cell sees both first segments, and a segment's input slew is charged to the next cell.
  - The model is fitted to OpenSTA (asap7 INVBUF RVT NLDM, TT 0.7 V/25 C, FF 0.77 V/0 C) with
    `python3 -m mscts.calib`: max residual 3.9 TT / 3.4 FF ps.
  - The fit is stored as data in mscts/data/asap7_bufx24_sta_fit.json. Without it, a 2-strip tree showed 23 ps of
    real skew: the default model's short-segment error.
- The emitters write the SAME buffers and RC ladders (4.45 ohm/um, 0.11 fF/um, 45-um pi) as:
  - a transistor-level ngspice deck (ot-ngspice:r3, BSIM-CMG, extracted BUFx24);
  - Verilog + SPEF for OpenSTA (openroad/orfs:asap7lock).
  `mscts.run compare` reports model vs STA vs ngspice per sink.
- QC slice region: E0 geometry from QC-SLICECLK-2, 2.471 x 26.266 mm, 16 strips, 192 taps.
  - The crossings are SYNTHETIC: the 60 strip-boundary neighbour pairs.
  - Placement legality is NOT applied in this version (streets, A0 halos, metal allocation).

| tree (fitted model) | buffers | wire mm | model ins TT | OpenSTA ins TT | STA skew TT / FF | max unshared on listed pairs TT (model) |
|---|---|---|---|---|---|---|
| full slice, late_split | 554 | 176.3 | 3060 | 3088-3103 | 15.0 / 12.8 | 45 ps (worst margin 409.6) |
| full slice, nearest | 555 | 173.6 | 3052 | 3080-3091 | 11.5 / - | 896 ps (357.7) |

- ngspice vs STA, 2-strip region (24 taps, 60 BUFx24, 17.1 mm wire), late_split, OWN:
  - Spice skew is 3.5 ps TT and 3.8 FF. STA skew is 1.9 and 4.1.
  - STA - spice per sink is -28.9 ± 0.8 TT and -25.2 ± 0.15 FF. That is a uniform 4.4 / 4.7 % early STA.
  - The crossing-pair nominal d is the same in both tools (0.00 ps difference).
  - The fitted model is 7 % below spice (model - spice -47 TT, -38 FF). Files: qcs_small_compare_{TT,FF}.json.
- ngspice vs STA, quarter slice (4 strips, 48 taps, about 124 BUFx24, 37 mm wire), OWN:

| tree | spice ins TT | spice skew TT / FF | STA skew TT / FF | STA - spice TT (mean, spread) | FF | model - spice TT |
|---|---|---|---|---|---|---|
| late_split | 1024.8-1034.6 | 9.9 / 11.5 | 6.1 / 6.8 | -45.6 (4.7) = -4.4 % | -42.6 (5.1) = -5.0 % | -69.8 |
| nearest | 1015.2-1018.8 | 3.6 / - | 2.2 / - | -45.8 (1.4) = -4.5 % | - | -68.0 |

  Files: qcq_*_compare_*.json.
- What this shows:
  - STA and transistor-level spice agree on the relative arrivals to within 1.4-5.1 ps per sink, with a uniform
    -4.4..-5.0 % absolute offset (STA earlier).
  - The planner model is 6-7 % optimistic in absolute insertion. It is fitted to STA, so that offset comes on top.
- Caveat: on this regular grid the listed crossing pairs are mirror-symmetric, so their nominal d is 0.00 in both tools
  and that comparison carries no information. The per-sink spread above is the real STA-vs-spice check.
- Late split cuts the model's unshared clock on the listed pairs from 896 to 45 ps TT at the same insertion. Its cost is a
  little more skew (spice 9.9 vs 3.6 ps on the quarter slice).

## Not done / next
- The full-slice ngspice runs (qcs_ls TT/FF, qcs_nn TT; 554 extracted BUFx24 cells) were still running on intel1 at
  20:35, at about 0.01-0.04 ns of sim time per minute, so expect them to take hours.
  - Collect: rsync arr_<C>.dat + sta_arr_<C>.txt into the local build dir, then
    `python3 -m mscts.run compare DIR --corner C`.
  - Containers are named ossclk_<dir>_<C>.
- Placement legality on the allocated tracks, i.e. the mscts <- metal hand-off.
- Neighbour-forwarded region clocks inside mscts. The predictor already covers them.
- A real QC slice traffic list (from locality.py) in place of the synthetic pairs.
