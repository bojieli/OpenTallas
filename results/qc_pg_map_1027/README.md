# QC-PG-MAP (2026-10-27): QC upper-deck per-core load map (R35 plan), re-solve, total vs 35 mV, priced fixes

Sub-lane under DIE-QC (COORD 21:13 ruling on PG-ACTIVITY-5). Deck = the QC .672 canonical deck of the 30.403 number
(M8 0.48@8.64 / M9 0.672@8.64, offset 4.32, 150-um bumps, 70-um pads, VDD drop + VSS bounce co-located per load block,
canonical interior >= 450 um from the open window edges, 2972.16-um window, 43.07-um load blocks), generator
bump-survey bs_psm.py / infra_pg.window_kit, image openroad/orfs sha 16470cea (= asap7lock). Plan = R35 slice plan
(results/qc_sliceclk_1027/plan/die_plan_sliceclk.json.gz @ claude/qc-sliceclk-1027 88bc183c7c). R35 cuts no PG stripe,
so the new kits carry NO R28 clock holes (the 30.403 deck had them: +1.06 mV, see 1.3).

## 1. Method (CHECKED where marked)
- Core census from the plan (`cores.py`): 377 partitions, 974 hard cores with an outline; die 819.9 mm2.
  A0 (qfd_tile_nk/nl_a0c) = 768 cores, 407.2 mm2 (50 % of the die); signed QC cores = vmr/crh/crh_rp1/prog/su8 (84 cores, 5.67 mm2,
  0.7 %); the rest (~407 mm2) = flattened partition logic + su_lane_w + btab + stations, with no signed view.
- Load classes (`loads.py`), PDNSim is linear, so one solve per class at unit density; then exact superposition per node
  (`combine.py`, `su_total.py`): S = signed cores at OWN vectorless W (OpenSTA report_power, 6_final + spef) spread over the plan
  outline: vmr 0.0119, crh_rp1 0.0098, s8x_crh 0.00947 (this lane, qc/closed), prog 0.0169, su8 0.0337 W (1.505 W/mm2);
  A = A0 cores at 1 W/mm2; F = every other partition area at 1 W/mm2 (channels 0).
- Collector check: combine.py on the original 30.403 deck returns 30.403 (u_b25_47) -- CHECKED reproduction.
- Linearity check: HC window F-unit solve x 0.5823 = 29.339 (same window, no R28 holes); 30.403 - 29.339 = 1.06 mV = R28 holes.
- Windows: SU = x 26352-29324, y 9504-12476 (sl_E4 su_c strip: 3 vmr, 2 crh, prog, btab, su8, 12 su_lane_w; 5 A0 at the
  south edge), A0 = same x, y 3456-6428 (cb array, A0 + cb stations), HC = the old 30.403 window (sl_E4 hc/ctl/st; no hard core).
  All 12 slices are translations (2471.04 pitch), so SU is representative of every su_c strip.

## 2. Results, M9 .672 deck, 150-um bumps (all solves EXIT 0, PG_CHECK OK; CHECKED as solves)
No own-power view exists for A0 or the flattened partition logic (99.3 % of the die area), so the map is
"own vectorless where signed, background d W/mm2 elsewhere". Background shown at 0.5823 (flat cap kept), 0.3, 0.
| window / location | upper bg 0.5823 | upper bg 0.3 | upper bg 0 | below-M7 (PG-ACT-5) | TOTAL bg 0.5823 | verdict |
|---|---|---|---|---|---|---|
| SU: su8 (u_b39_32/33) | 43.824 | 37.434 | 32.040 | 6.602 | **50.43** (44.04 / 38.64) | FAIL at every background |
| SU: crh | 21.925 | 15.727 | 9.141 | 4.282 | 26.21 | PASS |
| SU: vmr | 21.476 | 12.495 | 6.806 | 4.390 | 25.87 | PASS |
| SU: prog | 16.503 | 10.896 | 7.300 | 5.989 | 22.49 | PASS |
| SU: worst non-signed block (u_b36_33, flattened logic 9 um W of su8) | 34.566 | 24.712 | - | 4.597 budget (no view) | 39.16 | FAIL (su8 spill) |
| A0 window (cb array), A+F at bg | 29.303 | - | - | 4.597 budget (no A0 view) | 33.90 | PASS iff A0 <= ~0.60 W/mm2 |
| HC window (old 30.403 site), F at bg | 29.339 (30.403 with R28 holes) | - | - | 4.597 budget | 33.94 (35.00) | PASS / marginal |
Unit responses (mV per W/mm2): HC 50.38; A0 window A-only 48.14, F-only 42.70; SU background-only at su8 ~20.2.
su8 ALONE (only the 12 su8 loaded, 0.0337 W each): 31.799 mV at its own block (VDD 16.09 + VSS 15.71) = 99 % of the S-class 32.04.
=> The su8 hot spot is self-inflicted: 34 mW in a 173 x 129-um core = one 150-um bump cell at 1.5 W/mm2 on an 11 %-metal
upper grid. A VDD bump already sits inside su8 (1631,1379 local) and a VSS bump 27 um east -- bump placement cannot help.
The per-core map makes QC WORSE than PG-ACT-5's 37.0 (which put the flat 0.5823 upper under a 1.5 W/mm2 core).
Below-M7-only fixes cannot close su8: even at 0 background, 32.04 + any below > 28.4 needs below < -3.6.

## 3. In-core fixes for prog / su8 (PRICED, NOT BUILT; ESTIMATES unless CHECKED)
Static PDNSim IR is DC: decap does not reduce it (dynamic only); the levers are local metal and current spreading.
| fix | prog below-M7 | su8 below-M7 | cost |
|---|---|---|---|
| (a) clock-tap hotspot: re-place / split the worst clkbuf onto M5xM6 strap crossings (plan-computed per-tap sizing, 12.8 allowed) + 2 local M6 0.288 straps over the tap cluster | 5.99 -> ~3.7-4.0 (worst cell isolated: p99.9 3.65) ESTIMATE, gain ~2.0 | 6.60 -> ~5.7 (broad: p99.9 5.68, p99 5.15) ESTIMATE, gain ~0.9 | core ECO + re-sign (place/CTS/route); local M6 +2 tracks over ~20-40 um, ~0 % die tracks |
| (b) 2x-width M6/M7 partition straps (0.576) | 5.69 CHECKED (PG-ACT-5) | 5.50 CHECKED | M6/M7 PG 13 -> 27 % tracks in the core |
| (a)+(b) | ~3.5 ESTIMATE | ~4.6 (p99.9 of w2 run 4.60) ESTIMATE | both |
| (c) su8 at half density (outline 2x, util 17.9 -> 9 %) | - | ~4.5 ESTIMATE (below ~ density) | +0.022 mm2 per slice; su_c has room? (not checked) |
prog passes already on the map (22.5). su8 total with (a)+(b) = 43.8 + 4.6 = 48.4 at bg 0.5823 -> still FAIL: su8 is an
UPPER-deck problem.

## 4. Smallest grid / bump change that passes (SU window, worst = su8; DO NOT ADOPT -- report only)
| change (all other deck items identical) | M8 / M9 PG tracks | su8 total bg 0.5823 | bg 0.3 | bg 0 | status |
|---|---|---|---|---|---|
| current .672 (M8 .48@8.64, M9 .672@8.64) | 14.6 / 40.1 % | 50.43 | 44.04 | 38.64 | FAIL |
| M8 2x density (M8 .48@4.32) | 29.4 / 40.1 % | 39.54 | 34.16 | 29.16 | FAIL at cap, PASS bg <= ~0.33 |
| M9 6.48@34.56 only (C3 M9, M8 unchanged) | 14.6 / 48.3 % | 38.64 | 33.56 | 29.30 | FAIL at cap, PASS bg <= ~0.4 |
| C3 (M8 .48@4.32, M9 6.48@34.56) | 29.4 / 48.3 % | **33.11** | 28.48 | 23.77 | PASS (1.9 mV margin) |
| G12 (M8 .48@4.32, M9 12.96@34.56, HEAD standard) | 29.4 / 85.7 % | 21.81 | 19.52 | 17.57 | PASS (13 mV margin) |
| 75-um bumps, 37.5 pad, grid unchanged | 14.6 / 40.1 % | **23.97** | 23.35 | 22.69 | PASS (11 mV margin) |
C3/M8-2x interplay with the R35 clock reservation (OWN reading of results/qc_infra_r35/README.md): R35 puts 16w clock tracks
at VSS +-1.16 inside each 8.64 M8 pair-row with VDD at +-4.32; M8 at 4.32 pitch puts a 0.48 stripe every 2.16 um and
removes those tracks -> any M8-2x option (M8x2, C3, G12) forces a new R35 reservation. M9 34.56-pitch options change the
M9 spine pair-col phase. 75-um bumps touch no metal class.
SMALLEST PASSING CHANGE (report only, not adopted): 75-um bumps (pad 37.5) with the grid unchanged: su8 23.97 mV at
background 0.5823 (CHECKED solves), 0 track cost, 4x bump count -- or, ESTIMATE, a 75-um field only over the su_c strips.
Grid-only pass needs C3 (M8 +14.8, M9 +8.2 track points, R35 re-reservation): 33.11 mV.
75-um bumps everywhere = 4x bump count (380 -> 1560 per 8.83 mm2 window). OWNER rule: 75 um only if 150 still fails --
it does (su8). A smaller variant (ESTIMATE, not solved): 75-um field only over the 12 su_c partitions (1.64 mm2 each,
~+220 bumps per slice, ~2.6k die-wide) -- su8 is a one-bump-cell hot spot, so the local field should behave like B75 (~24 mV).

## 5. What is still missing
- A0 and flattened partition logic own power (99.3 % of the area). Placed-only A0 proxy (rawleaf a0k 3_place, placement
  parasitics, no CTS) = 0.0767 W / 0.0162 mm2 = 4.73 W/mm2 vectorless -> die-wide this would be ~1.9 kW >> 474 W cooling cap:
  vectorless default activity is not physical for A0; measured RTL toggle (KV method) is required before any A0 number.
- su8 measured activity: su8 passes on 150 um only if its power factor f <= ~0.60 (bg 0.5823) / ~0.75 (bg 0.3) of
  vectorless (31.8 f + 6.6 f + bg <= 35; linear, ESTIMATE). Clock is 18.7 % of su8 vectorless power.

## 6. Render (viewed)
`su_window_upper.png` / `su_window_upper_zoom.png` (render.py): SU window upper map (S own + bg 0.5823), core outlines, bumps.
Viewed: the hot spot sits on the su8 outline (cyan) between its in-core VDD bump (1631,1379) and the VSS bump 27 um east;
prog/vmr/crh areas are darker than the background (own power 0.13-0.18 W/mm2 < 0.5823).

Run data: intel2:/srv/opentallas-scratch2/claude/qc-pg-map-1027/{kits/<class>/<grid>_SU|A0|HC, comb, tot, pwr}.
