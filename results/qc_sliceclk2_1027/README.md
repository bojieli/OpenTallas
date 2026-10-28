# QC-SLICECLK-2 (2026-10-27): balanced per-slice clock: root cause, analytic design, split pricing, cell-estimate fix

Basis: claude/qc-sliceclk-1027@88bc183c7c merged with origin/main abbbffac9b. Data: intel2 /srv/opentallas-scratch2/claude/qc-sliceclk-1027 (QC-SLICECLK-1), /srv/opentallas-scratch2/claude/qc-sliceclk2-1027 (G0C rerun).
Labels: OWN = my run, not independently checked (all numbers here are OWN/UNCHECKED unless marked CHECKED).

## 1. Root cause of the 1,634 ps in-slice spread (OWN, from tree.json + arr_TT.txt)
- The region bisection is equal-length on paper. The `--tree-site-slide` legaliser breaks it.
- The slice centre column (x = slice centre = the c-column boundary, e.g. 17,626 in E0) is blocked by A0 core halos over the c rows.
- `site.slide` moves a node ALONG its parent leg. In a 10.6:1 slice the children split on the same (y) axis, so the slide shortens one child leg and lengthens the other.
- Example in E0: the level-14 node wanted y 19,699 and slid to 14,471 (5.2 mm). Its children then sit 1.9 mm and 8.5 mm away.
- Effect: in-slice tree path 36.1-43.7 mm, with 106 vs 125 stages; the far rows (bf/tf) run +1.6 ns.
- Delay fit over 7,121 taps: 199 ps/mm TT, 198 FF (405-um BUFx24 stages).
- Legal geometry per slice (E0, mirrored): full-height legal columns at x ≈ +681 um right of the c-column boundary (18,307-18,322) and at the slice east edge. Full-width legal rows sit in bands every ~1.3 mm (the inter-core rows of each c partition).

## 2. Design (per slice), predicted analytically BEFORE building
- Slice spine: all y-bisection nodes of the slice tree sit ON the legal full-height column x_s (= the leg axis), so no slide is needed and siblings stay equal.
- After 4 y-levels (strips of 1.64 x 2.47 mm), one equal horizontal leg (x_s -> strip centre, 689 um, the same for every strip) leads into a local x/y bisection to 600-um leaves. Only these local nodes slide, and their imbalance stays bounded inside one strip.
- Root -> leaf path 14.37 mm, insertion 2.87 ns TT per slice.
- Top feed = ONE shared horizontal spine (common point) along the sl band (y ≈ 12.5-13.1 mm), crossing all 12 slices + HUB, driven by a balanced 1-D tree.
  - Every slice crossing (sl_fe <-> sl_fw, y 11.96-12.97 mm) sits <= ~1 mm from this spine, and neighbour slice roots get equal nominal arrival.
  - A balanced top H-tree is rejected: W0|E0 split at the die root, giving ~29 mm unshared, damage 429 ps TT > 416.5.
  - A forwarded chain is rejected: its nominal |d| per hop is ~490 ps > P/2, which 12.11g forbids.
- Shared-model OCV (main clk_aocv.branch_pessimism + APPROVED g021 table; predict.py, predict_out.txt):

| item | unshared | TT setup pess | FF hold pess | note |
|---|---|---|---|---|
| intra-slice worst pair (diverges at slice root), K=1 | 14.37 mm/side | 183 ps (261 if droop not shared) | 157 (214) | hold -> HB4 data hold buffers (allowed) |
| same, K=2 (13.1-mm domains) | 7.80 | 100 (142) | 86 (117) | |
| same, K=3 (8.8-mm domains) | 5.61 | 75 (105) | 64 (86) | |
| slice crossing, K=1 + shared spine | 14.37+14.37 = 5.73 ns TT | damage 235 TT / 194 FF | | margin vs P/2 416.5 after 80 ps nominal target: **+102 TT / +142 FF** |

## 3. Vertical split priced (nativev7 composer, same harness; price/mkreq_v.py + case.sh), OWN, UNCHECKED
| case | crossings | cycles/token | tok/s | delta vs 4,051.0 |
|---|---|---|---|---|
| slice K=3 (QC-SLICECLK-1, CHECKED) | 269 | 298,285 | 4,024.6 | -0.65 % |
| v3 = c-bottom / sl band / c-top per slice, K=3 | 413 | 299,149 | 4,013.0 | -0.94 % |
| v2 = split at y 13,133 (sl centre), K=3 | 569 | 300,769 | 3,991.4 | -1.47 % |

- The split does NOT help the landing crossings under 12.11g (|phase| < P/2, nominal + OCV).
  - Neighbour domains must match their nominal insertion from the last common point. So the unshared clock is the sum of the two insertions below that point, whatever the domain size.
  - Example, v3 with c roots fed 7.9 mm from the spine: either nominal d ≈ 2.1 ns at the c<->sl crossings, or a matched sl detour that brings the unshared clock back to ~5.2-5.7 ns.
  - Only a 2-D grid of common points (= the continuous-mesh path) avoids this.
- The split only lowers the intra-domain pair pessimism (183 -> 100/75 ps), and that is already covered by hold buffers.
- -> Cheapest form that is predicted to close: K=1 slice domains + shared sl-band spine + spine-column slice trees. Price -0.65 % CHECKED.
- Caveat: 5.73 ns unshared exceeds the COORD guidance of ≤~3.4 ns. The predicted margin is +102 ps TT, just above the HEAD-ruling ~100 ps line, so the build must confirm it.

## 4. Cell-estimate fix (tool path shared with LAND-KV-1)
- `tools/die_plan/cells.py` rule 6:
  - A cohort type (`landing_base_type`, set by clock_landing_plan.compose) inherits its base estimate. This also works when the base type left the plan, through its by_type row (the QC case: all instances moved to cohorts).
  - Plus measured landing rings (LAND-KV-1 model 4(W+4)+124+612/64-bit chunk) on every non-type.cells estimate. type.cells is taken as complete.
- 5 tests: `tools/die_plan/test_cells_landing.py`.
- QC slice landed plan G0C: 24 E -> **PASS 0E/142W** with NO side evidence file (= the predecessor's result with cohort_cells.json), OWN.

## 5. Not done in this lane (and why)
- (4) build / (5) GRT incl routed clock / (6) STA are NOT run.
  - The ONE shared M8 clock-row reservation (INFRA-FIRST-QC-R35) is not published yet. No R35 result is on coord/state at 19:31, and its WT exists but has no result.
  - The spine-column slice tree is a builder change: an opt-in in die_trial build_htree (`spine column` for region trees, plus a length-preserving perpendicular slide), plus the top spine.
  - die_sta_related needs a die_clock_mesh proof (tap_arrivals_<C>.json). For crossings, run landed_phase_ocv.py (claude/land-head-2-1027@be648cbdd7) on the die_trial tree.
