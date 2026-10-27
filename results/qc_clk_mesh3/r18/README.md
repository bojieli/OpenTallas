# INFRA-FIRST-QC-R18: QC d43b clock, model vs RCX, hold root cause, related-pair die STA

Lane INFRA-FIRST-QC-R18 (2026-10-27). Base: claude/qc-mesh-r17-1027@75c9eca9a6. Inputs: the R17 package,
read-only (epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r17/pkg). Runs: epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r18/{an,run}.
Driver: `pipe18.sh NAME [solve args]`. It runs 14 MC solves, then collect / pairs / sta-export (plain and core views RP1+VMR),
then hb4, then die_sta_related.

Labels: CHECKED means recomputed independently (arithmetic from the JSON terms, or an exact reproduction). UNCHECKED means a single tool output.

## Tool changes
- `clock_routed.py` STA_TCL
  - Cells are `ckt_*`, not `ckm_*`. The script now writes N (Y pin) and A (A pin) arrivals for every ckt cell.
  - Real tap loads are taken from an optional /out/tap_loads.tcl. Tap ports get an output delay.
  - Leaves without ckm_n4: the col_tap cells (place.json plan_kind).
- `clock_routed.py` RCX width guard
  - `rules_width_check`: the second M8/M9 width entry of the RCX rules must equal the NDR width. Otherwise write_route raises an error.
  - Override: `--rcx-width-mismatch-ok`. The result is recorded in rcx_basis.json.
- `qc_clk_mesh3.py solve --top-edge-corr`
  - Opt-in. A per-top-edge RCX fold {d,k}: the nominal equals RCX exactly, and sigma and gradient scale by k.
  - The default is unchanged.
- `die_sta_related.py`: an additive `kit_contract_hold_ocv` report. It compares the kit window W against nominal damage plus clock OCV (pair_unc), and gives a per-pair residual. INFO only; the gate is unchanged.
- Tests: test_clock_routed_r18.py (new). 64 tests pass across the clock_routed / qc_clk_mesh3 / die_clock_mesh / die_sta_related suites.

## Numbers
| # | item | value | label |
|---|---|---|---|
| 1 | R17 build oth-ubuntu-1796220-1793090377 | still in DRC at 02:26 PDT. 3378/20857 boxes at ~02:20, ETA ~05:15. Partial: 88 Min-Step @ M8 (5 nm jogs at trunk-end/pin-stair x) | UNCHECKED |
| 2 | model path root -> col_tap A, TT (excluding the 319.5 trunk) | 6034.65 (6021.8-6083.7). R17's 6341-6403 includes the trunk; RCX does not | UNCHECKED |
| 3 | RCX path, R17 rules (0.16 um widths), TT | 2978.8 (2956.7-3003.7). C 0.087 fF/um vs model 0.502 | UNCHECKED |
| 4 | ROOT CAUSE of the gap | R17 RCX rules held 0.04/0.16 um widths, but the clock NDR is 0.64 um. OpenRCX applies the last width entry to wider wires, so C was under-extracted. R matched (~0.53 ohm/um) | UNCHECKED |
| 5 | RCX path, 0.64 um rules, TT / FF | 3635.6 (3598.0-3675.2) / 2895.8; RCX/model 0.60. The width bug is worth +657 ps TT | UNCHECKED |
| 6 | remaining ~40% model/RCX gap | environment. The model assumes full M7/M9 planes (upper bound); the clock-only RCX has empty M7 (lower bound). The per-edge RCX/model ratio is 0.57-0.77 | UNCHECKED |
| 7 | tap load: real (5.6-70 fF, med 12.5) vs ideal 3 fF | changes col_tap Y by <= ~15 ps. The probe does NOT materially under-load | UNCHECKED |
| 8 | fold | top_edge_corr_rcx64.json. Model = RCX at every col_tap (0 ps by construction) | UNCHECKED |
| 9 | base reproduction of R17 | FF zero-logic hold -115.32, TT setup +540.10, 997 pairs, kit hold +29.36, HB4 2,658,507 / 0.2714 mm2 | CHECKED (exact) |
| 10 | -115.32 decomposition | clkq_min 51.02 - lib hold 24.77 - unc_hold 25.0 - pair OCV 111.91 - nominal damage 4.66. Pair OCV = AOCV random 19.84 + distance 1.14 + mesh MC var 90.93 (worst pair sl_E0_hc0 -> c_E0_tn_00) | CHECKED (arithmetic) |
| 11 | CPPR placement | mesh node "m", range 0 (signed mesh, no credit). Per §12 | CHECKED (code + JSON) |
| 12 | MC worst die skew 328.8 TT / 283.3 FF | real for the model, but dominated by the GRADIENT term. grad=0: 87.6 / 105.3; tree-only: 87.5 / 105.3; tree sigma 0: 305.6 / 246.4. It is a die-wide max-min, not a related-pair quantity | UNCHECKED |
| 13 | pair mesh-MC var (what hold sees), FF median/max | base 20.0/90.9; tree0 4.2/50.0; grad0 19.1/59.0; tree-only 19.0/59.5. Per-stage TREE random dominates the median. Tree and gradient both feed the max | UNCHECKED |
| 14 | worst FF zero-logic hold by variant | base -115.32; tree0 -68.35; grad0 -80.46; tree-only -81.02; f64 -85.17; f64+tree0 -59.68 | UNCHECKED |
| 15 | f64 = RCX-fed die STA (plain), TT setup / FF hold | +565.40 (0 neg) / -85.17 (997 neg, all zero-logic seam). Recompute: 51.02-24.77-25-11.04-75.4 | UNCHECKED |
| 16 | f64 nominal related skew / die tap skew | 27.16 TT / 22.46 FF; die 65.73 / 52.39 (base 25.64 / 24.36). The tree was balanced on model edge delays, which RCX does not preserve | UNCHECKED |
| 17 | f64 insertion TT / MC worst | 4149-4398 / 234.3 TT, 198.3 FF | UNCHECKED |
| 18 | kit-contract hold (W 40, nominal), f64 plain / core views | +17.54 PASS / -1.89 FAIL. 1 pair: sl_W2_su_c -> sl_W2_su_l1, damage 41.89 | UNCHECKED |
| 19 | kit-contract + clock OCV (new INFO), f64 plain / cv | -46.65 (313 neg) / -46.65 (368 neg); p50 36.2, p99 72.9 | UNCHECKED |
| 20 | HB4 over-count | 291 ports sat on default 116.6 ps: the R17 fragment had 724 seam pairs and missed port-connected pairs. Union fragment (773 pairs) gives base 2,601,153 / 0.2656 mm2 and f64 2,442,198 / 0.2493 | UNCHECKED |
| 21 | HB4 residual only (beyond the kit window W, with OCV, cv) | base 1,429,192 / 0.1459 mm2; f64 1,295,752 / 0.1323 mm2 (277 pairs) | UNCHECKED |
| 22 | HB4 floor with ideal leaf shorting (mesh MC -> 0), f64 | 1,619,493 / 0.1653 mm2 at sender guarantee 12.5; 1,277,200 (1/bit) at G >= 30 | UNCHECKED |
| 23 | droop | 0 differential. One continuous mesh / PDN region (SHARED, owner) | UNCHECKED |
| 24 | coverage | 997 seam ordered pairs (773 unordered union). Intra-partition/landed: none in this gate (declared-budget, no QC kit pairs) | UNCHECKED |

## Root cause of the -115.32 ps hold
- The zero-logic budget before clock OCV is only 1.25 ps (51.02 - 24.77 - 25). Every zero-logic seam bit therefore fails on the AOCV floor alone (~20 ps).
- The dominant term is the mesh MC variation between taps fed from DIFFERENT columns 1.2-2 mm apart. The fine mesh does not average over mm, so these pairs see ~75 uncommon top-tree stages of per-stage random variation.
- CPPR is placed correctly (signed mesh, range 0). It is not the cause.
- The zero-logic slack also does not credit the kit window W = 40 that tile hold is signed off against (if the QC kits are signed off at W 40: UNCHECKED). The gate HB4 should be sized against is therefore the kit window plus OCV (#19/#21), not the -115/-85 zero-logic number.
- Possible double count, ASK COORD: the MC gradient (0.21 %/mm) and the AOCV distance term (0.21 %/mm x bbox) both model spatial variation. Likewise, MC tree sigma and AOCV random (k=3) both model random variation. No change made.

## Structural fix (proposal)
1. Re-balance the top tree on the RCX-calibrated stage table, i.e. size with the fold rather than only report it. This removes the +41 ps nominal related skew that RCX introduced (#16) and the 1 cv FAIL (#18).
2. Short the column taps with a spine / mid-level mesh (drop --no-spine), so that pairs 1-2 mm apart share a common shorted level. The mesh-MC term then falls toward the floor (#22).
   - Blocker: `solve` without --no-spine fails on d43b with "point (2177.28, 1339.2) not on a strap". This is a tool fix and is the next lane.
3. Size HB4 for the residual only, after 1 and 2: f64 residual 1.30 M cells / 0.132 mm2 today (#21), against R17's 2.66 M / 0.271. No trims, useful skew or clock ECO were used, so lanes/CLOCK-RESIDUAL.md has no entry.
