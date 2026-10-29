# DIE-S81-4 (2026-10-27/28): S81 die GRT collect, main link_htree rebuild, die STA (x1.00 + 12.15 spice), HCPL kit on main

All numbers UNCHECKED (own scripts, no NUMBER-CHECK) unless marked CHECKED (= log/file read, mtime after run start).
Scratch: intel2:/srv/opentallas-scratch2/claude/die-s81-4 (kit, clk, out_TT/FF, proof, proof_spice, sta_*, lpo, ca_s*, hcpl).
Inputs (unchanged from DIE-S81-3): plan die-s81-3/die_plan_r98.json (sha 06301f33d226), map98.json, feed_spinespt_335.json.

## 1. DIE-S81-3 GRT collect (region_tree=htree option kit, CHECKED logs)
TT+FF EXIT 0, 50 congestion it (no -critical_nets_percentage 0 flag -> superseded by 2.), overflow 0 on M1-M9;
usage M4 3.04 / M5 4.38 / M6 4.91 / M7 8.58 / M8 0.86 / M9 1.00 %. 3 slew violators 1.5-3.4 ns (legs over the lk_EN2
SerDes macro and the s_5N_x06 feed leg). Route guides deleted (superseded).

## 2. Rebuild with main link_htree + balance_legalize (810b714798)
Kit: --tree-form link_htree --leaf-um 200 --rep-um 250 --tree-site-slide (KV H200B recipe): 30,230 nodes, 8,164 reps,
38,394 cells, 6.17 m clock wire, 47 levels, 0 illegal; balance_legalize 512 unbalanced nodes (446 > 50 um, 90 > 500 um,
worst 9,319 um in SerDes region std_b7_0_1; 721 um in macro slices std_b5_7_0 / std_b6_4_0 ...).
Die GRT incl clock (go_grt.sh: 50 it, -critical_nets_percentage 0, signal M4-M7, clock M8-M9), TT+FF EXIT 0 (CHECKED):
**overflow 0 on every layer**; usage M4 3.04 / M5 4.38 / M6 4.91 / M7 8.58 / M8 0.87 / M9 1.00 %; 38,395 clock nets.
Slew FAIL (CHECKED): ck_r18589_4 3.32 ns, ck_r228_4 1.75 ns, ck_r18583_4 1.03 ns (same legs: over lk_EN2, s_5N_x06),
3 more 333-361 ps.
Measured nominal in-region tap spread (GRT-RC, x1.0485): 85 non-SerDes regions p50 134 / p90 333 / max 416 ps TT
(FF 112/288/362); 13 SerDes regions (lk_* taps inside the macros) 0.68-3.11 ns. hard_phy_hbm: taps 6334-6539 ps
(205 nominal; phy tap 6429, partners within -95/+110).
## hard_phy_hbm estimate (s81_inregion.py, OCV+droop, spice): htree spread max 161.7 @335 ps/mm, 151.4 @305, 145.7 @290;
DME 156.2 @335. Structural floor: phy_hbm = ONE clock tap at the region centre paired with 8 partitions over 11.5 mm
(both directions, 1120-1368 bits each) -> any zero-skew tree has unshared ~R = 7.25 mm; a region split is not possible
(X->phy crossings would need a landing ring inside the PHY macro). <=150 needs clock wire <= ~300 ps/mm in that region.

## 3. Die STA (main die_sta_related, --cppr-lca, clk_aocv table, shared droop, class data droop, core lat 250/202.5)
| clock | intra TT setup / FF hold | intra skew TT | seam TT setup / FF hold | seam skew TT |
|---|---|---|---|---|
| x1.00 | -2649.4 / -2787.7 | 3117 | -2469.5 / -2635.2 | 2906 |
| spice 12.15 (gate) | -2804.9 / -2942.0 | 3268 | -2616.4 / -2781.2 | 3047 |
Worst pairs = SerDes regions (lk_ES0 <-> s_7S_x10, 3.05 ns damage). FAIL. Gate failure is the region-tree balance, not GRT.
CA re-price (landed_phase_ocv main -> MESO-RECONCILE-2 count_align_plan 32e8cbb164, 2306 crossings, 398 plan regions):
x1.00 0 FAIL, D4 1887 / D8 419, lo 106.6 hi 121.8, lat vs old -788, MC 500 0 viol; x1.0485 10 FAIL; x1.0552 11 FAIL
(D4 1922 / D8 373, lat -821).

## 4. HCPL kit on main 810b714798 (CHECKED)
gen_core_kit_legacy --module ot_dsrom_su_hcpost_lane_pr --master-slice slices --trial: r28ce (plain), r28cs (+ shift clock
2144). Both carry lec_hints.json and main lec.py (sha d1762260...). KIT_PREFLIGHT PASS 0 issues (both).
