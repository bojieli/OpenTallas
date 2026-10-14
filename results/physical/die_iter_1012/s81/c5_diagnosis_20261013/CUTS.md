# S81 die c5 (v13): cut check, Qwen method (2026-10-13)

Bits crossing a cut line against the routing tracks GRT had on that line, for the c5 die run (GRT overflow 1,053,305, TT WNS -2,596.5 ps) and for c3 (v11) on the same lines. Script `tools/s81/c5diag_cut_dump.py` (container) + `tools/s81/c5diag_cuts.py` (host); cut lines in `cuts_def.json`; every number below is in `cuts.json`. Overflow by region and net family is the sibling's `CONGESTION.md`; timing is not covered here.

## Verdict

1. **No die-level cut is infeasible.** Of the 68 lines through the spine W column, the SU and hub faces, the SU/HC channel at full width, the E-column corridor, the hub seams, the field edges and the full-die bisections, 67 are at 0.00..0.46 of GRT's supply and one is at 0.577 (H_wspine_ch_y13325, row 4 below); the worst position of the full-width SU/HC channel sweep is 0.443 (y 18,182).
2. **c5 fails on four local structures, three of them pin placement, all four reproducible as a ratio > 0.60 on a short cut:**

| # | structure | cut | demand b | supply tracks | ratio | c3 | share of c5 overflow (CONGESTION.md) |
|---|---|---|---|---|---|---|---|
| 1 | wq_d station column W of sp_hc_s (230 um) | y 18,864, x 16,995..17,225 | 13,462 | 8,905 | **1.512** (59 of 83 positions > 0.60, 23 > 1) | 0.875 (4 of 29 > 0.60) | strip 270,214 = 25.7 % (c3 46,891) |
| 1b | same, east 512 um of the channel | y 18,979, x 16,800..17,312 | 15,366 | 18,278 | **0.841** (21 of 100 > 0.60) | 1.049 at its own position (22 > 0.60) | same strip |
| 2 | ctrl_SW / svc_SW seam, lateral | x 7,613, y 1,200..1,700 | 10,116 | 5,718 | **1.769** (19 of 31 > 1) | 1.769 | 107,352 = 10.2 % (c3 107,399) |
| 3 | field xa / xb relay north face under a bf tile | relay face 17.256 um, M9 only over the tile | 283 / 266 | 183 | **1.54 / 1.45** (estimate, see b) | same masters | field 651,846 = 61.9 % (c3 651,844) |
| 4 | spine W column at the SU / hub seam | y 13,286, x 13,277..13,781 | 10,271 | 15,074 | **0.681** (1 of 105 > 0.60; 0.577 on the 694 um line) | 0.256..0.326 | about 1,150 M6-M9 in its 480 um window |

3. **v13 against v11:** the SU / hub move raised the spine W column (0.18..0.33 -> 0.58..0.68) and tripled the wq_d path (32 relay stations on two passes where c3 has 7 on one); the strip overflow went 46,891 -> 270,214, which is the whole c5 - c3 increase. The field and the SW seam are identical in c3.

## Accounting

- **Supply** = GRT's own free capacity per gcell edge, read back from `ckpt_grt.odb`: `cap - (stored usage - guide tracks)`, layers of the crossing direction only (vertical line: M4, M6, M8; horizontal line: M5, M7, M9; M3 excluded). It contains the run's layer adjustment (30 % on M4/M5, 14.6 % on M6-M9) and the macro OBS. The routed database has **no PG shapes** (no SPECIALNETS in the DEF): the 14.6 % adjustment is the only PG allowance on M6-M9, clock nets are routed as signals and so sit in "used". Free supply in open area: 140 / 128 / 102 tracks per 9.6 um gcell on M4-5 / M6-7 / M8-9 = 38.5 tracks/um per direction. 19 masters carry OBS M4-M7 (bf, pq_root, sp_su, sp_vm, ...): over them only M8 / M9 remain.
- **Checks against grt.log:** guide tracks per layer M4 37,181,103 (log 37,181,104), M6 30,797,518 (= log), M8 21,121,053 (= log), M5 / M7 / M9 within 0.01 %; reconstructed overflow M6 526,533 (= log), M8 457,718 (= log), M7 32,960 (log 33,139), M9 35,374 (log 35,841); M6-M9 total 1,052,585 against 1,053,231. GRT stores usage as uint8 (wraps at 256); the reduction is recovered modulo 256.
- **Demand** = nets of the placed netlist with terminals on both sides of the line; "captive" = terminal extent along the line inside the segment. All 370,512 abstract pins are DIRECTION INOUT, so source and destination cannot be told from the database: bus ends are named, not directed.
- **Column "ratio M4-M7"** = the same demand without M8/M9 (contract: M8/M9 are die power / global). Flags use the full GRT supply.

## a) Cuts (c5), selection; all 85 in cuts.json

| cut | line | span um | demand bits (captive) | used by guides | supply M4-M9 (M4-M7) | ratio | used/supply | ratio M4-M7 | worst 480 um | worst ~200 um | flag | c3 same line |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V_wfield_edge | x=13,276.8 | 3,300..22,560 | 26,345 (26,332) | 26,492 | 579,165 (374,349) | 0.045 | 0.046 | 0.070 | 0.28 | 0.40 | ok | 0.045 |
| V_wfield_tier_ch | x=13,276.8 | 6,399..7,026 | 1,172 (976) | 1,710 | 24,457 (17,725) | 0.048 | 0.070 | 0.066 | 0.06 | 0.14 | ok | 0.048 |
| V_wfield_vch2 | x=12,163.2 | 3,300..22,560 | 26,754 (26,749) | 26,816 | 707,109 (502,293) | 0.038 | 0.038 | 0.053 | 0.23 | 0.43 | ok | 0.039 |
| V_su_w_face | x=13,766.4 | 3,370..13,392 | 636 (0) | 6,618 | 386,650 (280,060) | 0.002 | 0.017 | 0.002 | 0.04 | 0.06 | ok | 0.020 |
| V_su_e_face | x=15,686.4 | 3,370..13,392 | 96 (94) | 98 | 386,650 (280,060) | 0.000 | 0.000 | 0.000 | 0.01 | 0.01 | ok | 0.052 |
| V_hub_w_face | x=13,929.6 | 13,414..21,701 | 6,903 (6,901) | 6,914 | 318,775 (230,647) | 0.022 | 0.022 | 0.030 | 0.12 | 0.20 | ok | 0.008 |
| V_hub_e_face | x=15,686.4 | 13,414..21,701 | 40,714 (40,713) | 44,803 | 316,947 (228,819) | 0.128 | 0.141 | 0.178 | 0.64 | 1.38 | PINCH>1 | 0.076 |
| V_vm_e_face | x=15,686.4 | 13,414..16,144 | 14,788 (14,529) | 16,605 | 103,735 (74,665) | 0.143 | 0.160 | 0.198 | 0.64 | 1.38 | PINCH>1 | 0.153 |
| V_coll_e_face | x=15,686.4 | 18,678..21,399 | 13,944 (13,815) | 14,071 | 105,451 (76,381) | 0.132 | 0.133 | 0.183 | 0.56 | 0.68 | pinch>0.60 | 0.010 |
| V_vch_mid_lo | x=16,492.8 | 3,370..13,392 | 3,621 (3,468) | 3,840 | 386,650 (280,060) | 0.009 | 0.010 | 0.013 | 0.15 | 0.22 | ok | 0.056 |
| V_vch_mid_hi | x=16,492.8 | 13,392..22,434 | 37,452 (37,089) | 39,583 | 344,496 (248,412) | 0.109 | 0.115 | 0.151 | 0.42 | 0.65 | pinch>0.60 | 0.041 |
| V_hot_strip_peak | x=17,001.6 | 15,360..24,000 | 9,684 (9,683) | 81,723 | 323,413 (231,511) | 0.030 | 0.253 | 0.042 | 0.12 | 0.26 | ok | 0.013 |
| V_hcs_w_face | x=17,299.2 | 14,083..22,434 | 11,560 (11,558) | 28,914 | 322,239 (233,397) | 0.036 | 0.090 | 0.050 | 0.53 | 0.72 | pinch>0.60 | 0.035 |
| V_hcs_w_face_pins | x=17,299.2 | 17,950..18,570 | 10,251 (10,251) | 15,223 | 24,389 (17,657) | 0.420 | 0.624 | 0.581 | 0.53 | 0.72 | pinch>0.60 | 0.000 |
| V_hct_w_face | x=17,299.2 | 3,681..12,571 | 2 (0) | 0 | 342,990 (248,436) | 0.000 | 0.000 | 0.000 | 0.00 | 0.00 | ok | 0.032 |
| V_corr_w_mouth | x=17,308.8 | 12,571..14,083 | 9,782 (9,782) | 9,784 | 58,219 (42,103) | 0.168 | 0.168 | 0.232 | 0.24 | 0.30 | ok | 0.000 |
| V_corr_mid | x=18,220.8 | 12,571..14,083 | 8,362 (8,362) | 8,364 | 57,639 (41,523) | 0.145 | 0.145 | 0.201 | 0.23 | 0.28 | ok | 0.000 |
| V_corr_e_mouth | x=19,132.8 | 12,571..14,083 | 9,045 (8,189) | 9,241 | 58,352 (42,236) | 0.155 | 0.158 | 0.214 | 0.23 | 0.36 | ok | 0.000 |
| V_efield_edge | x=19,564.8 | 3,300..22,560 | 12,052 (12,050) | 12,054 | 400,945 (196,129) | 0.030 | 0.030 | 0.061 | 0.27 | 0.44 | ok | 0.030 |
| V_sw_x7560 | x=7,564.8 | 0..3,300 | 10,072 (10,072) | 10,814 | 59,015 (23,928) | 0.171 | 0.183 | 0.421 | 1.91 | 4.51 | PINCH>1 | 0.171 |
| H_wspine_ch_y9000 | y=9,004.8 | 13,277..13,781 | 4,506 (4,334) | 4,458 | 19,342 (13,936) | 0.233 | 0.230 | 0.323 | 0.24 | 0.50 | ok | 0.233 |
| H_wspine_ch_y13000 | y=12,998.4 | 13,277..13,781 | 8,876 (8,498) | 9,065 | 19,342 (13,936) | 0.459 | 0.469 | 0.637 | 0.48 | 0.72 | pinch>0.60 | 0.192 |
| H_wspine_ch_y13325 | y=13,324.8 | 13,249..13,943 | 10,656 (10,240) | 10,808 | 18,476 (11,030) | 0.577 | 0.585 | 0.966 | 0.72 | 0.81 | WATCH | 0.323 |
| H_wspine_ch_y15000 | y=14,995.2 | 13,249..13,943 | 9,185 (9,069) | 9,092 | 26,720 (19,274) | 0.344 | 0.340 | 0.477 | 0.49 | 0.70 | pinch>0.60 | 0.258 |
| H_wspine_ch_y16560 | y=16,560.0 | 13,249..13,943 | 8,427 (8,011) | 8,582 | 23,032 (15,586) | 0.366 | 0.373 | 0.541 | 0.45 | 0.58 | ok | 0.062 |
| H_vch_y9000 | y=9,004.8 | 15,671..17,312 | 1,132 (1,132) | 1,134 | 63,272 (45,728) | 0.018 | 0.018 | 0.025 | 0.03 | 0.07 | ok | 0.043 |
| H_vch_y15500 | y=15,504.0 | 15,671..17,312 | 19,671 (19,671) | 19,864 | 63,367 (45,823) | 0.310 | 0.313 | 0.429 | 0.44 | 0.70 | pinch>0.60 | 0.408 |
| H_vch_y17200 | y=17,203.2 | 15,671..17,312 | 15,978 (15,974) | 17,071 | 62,023 (44,479) | 0.258 | 0.275 | 0.359 | 0.35 | 0.65 | pinch>0.60 | 0.067 |
| H_vch_y18600 | y=18,604.8 | 15,671..17,312 | 24,349 (24,194) | 23,948 | 62,844 (45,300) | 0.387 | 0.381 | 0.538 | 0.92 | 1.70 | PINCH>1 | 0.034 |
| H_vch_y20000 | y=19,996.8 | 15,671..17,312 | 22,857 (19,812) | 23,301 | 63,273 (45,729) | 0.361 | 0.368 | 0.500 | 0.64 | 1.44 | PINCH>1 | 0.033 |
| H_strip_y17200 | y=17,203.2 | 16,800..17,312 | 5,390 (5,390) | 6,237 | 18,432 (12,924) | 0.292 | 0.338 | 0.417 | 0.32 | 0.65 | pinch>0.60 | 0.052 |
| H_strip_y18600 | y=18,604.8 | 16,800..17,312 | 16,390 (16,390) | 15,884 | 19,353 (13,845) | 0.847 | 0.821 | 1.184 | 0.92 | 1.70 | OVER | 0.000 |
| H_strip_y20000 | y=19,996.8 | 16,800..17,312 | 11,328 (11,268) | 12,122 | 19,716 (14,208) | 0.575 | 0.615 | 0.797 | 0.62 | 1.44 | WATCH | 0.000 |
| H_strip_y21500 | y=21,504.0 | 16,800..17,312 | 8,611 (8,326) | 8,614 | 19,712 (14,204) | 0.437 | 0.437 | 0.606 | 0.46 | 1.04 | PINCH>1 | 0.000 |
| H_strip_y23000 | y=23,001.6 | 16,800..17,312 | 8,288 (8,196) | 8,373 | 19,982 (14,474) | 0.415 | 0.419 | 0.573 | 0.45 | 1.04 | PINCH>1 | 0.005 |
| H_stncol_y17000 | y=17,001.6 | 16,995..17,225 | 4,181 (4,181) | 4,045 | 9,250 (6,700) | 0.452 | 0.437 | 0.624 | 0.45 | 0.54 | ok | 0.111 |
| H_stncol_y19300 | y=19,296.0 | 16,995..17,225 | 12,292 (12,292) | 7,497 | 8,635 (6,085) | 1.424 | 0.868 | 2.020 | 1.42 | 1.70 | INFEASIBLE | 0.000 |
| H_stncol_y21000 | y=21,004.8 | 16,995..17,225 | 9,220 (9,220) | 6,178 | 9,250 (6,700) | 0.997 | 0.668 | 1.376 | 1.00 | 1.17 | OVER | 0.000 |
| H_stncol_y22600 | y=22,598.4 | 16,995..17,225 | 8,196 (8,196) | 5,975 | 9,250 (6,700) | 0.886 | 0.646 | 1.223 | 0.89 | 1.04 | OVER | 0.000 |
| H_hct_n_face | y=12,585.6 | 17,312..19,129 | 7,975 (7,062) | 7,899 | 70,300 (50,920) | 0.113 | 0.112 | 0.157 | 0.19 | 0.22 | ok | 0.000 |
| H_hcs_s_face | y=14,073.6 | 17,312..19,129 | 7,062 (7,062) | 7,063 | 70,300 (50,920) | 0.100 | 0.100 | 0.139 | 0.13 | 0.21 | ok | 0.000 |
| H_seam_su_vm | y=13,401.6 | 13,943..15,671 | 17,137 (17,137) | 17,138 | 66,970 (48,508) | 0.256 | 0.256 | 0.353 | 0.54 | 0.54 | ok | 0.000 |
| H_seam_vm_capture | y=16,156.8 | 13,943..15,671 | 13,832 (13,376) | 14,517 | 63,195 (44,733) | 0.219 | 0.230 | 0.309 | 0.64 | 0.64 | pinch>0.60 | 0.000 |
| H_seam_capture_gather | y=16,310.4 | 13,943..15,671 | 7,175 (6,959) | 7,290 | 64,970 (46,508) | 0.110 | 0.112 | 0.154 | 0.42 | 0.64 | pinch>0.60 | 0.000 |
| H_seam_gather_pq | y=17,203.2 | 13,943..15,671 | 990 (858) | 1,009 | 66,212 (47,750) | 0.015 | 0.015 | 0.021 | 0.06 | 0.11 | ok | 0.000 |
| H_seam_sseq_coll | y=18,595.2 | 13,943..15,671 | 1,887 (1,675) | 1,780 | 66,970 (48,508) | 0.028 | 0.027 | 0.039 | 0.09 | 0.22 | ok | 0.000 |
| H_su_mid | y=8,400.0 | 13,781..15,671 | 0 (0) | 0 | 20,361 (165) | 0.000 | 0.000 | 0.003 | 0.00 | 0.00 | ok | 0.000 |
| H_sw_phy_ctrl | y=1,200.0 | 2,885..11,385 | 22,238 (22,238) | 31,048 | 364,259 (273,887) | 0.061 | 0.085 | 0.081 | 0.09 | 0.10 | ok | 0.061 |
| H_sw_hot | y=1,459.2 | 6,650..8,110 | 19,872 (19,872) | 20,512 | 51,000 (35,394) | 0.390 | 0.402 | 0.561 | 0.51 | 0.66 | pinch>0.60 | 0.390 |
| H_fld_rly_gap | y=7,603.2 | 11,400..11,545 | 566 (566) | 838 | 5,803 (4,171) | 0.098 | 0.144 | 0.136 | 0.10 | 0.10 | ok | 0.098 |
| H_fld_rly_over_tile | y=7,699.2 | 11,400..11,545 | 564 (564) | 567 | 1,632 (0) | 0.346 | 0.347 | 564.411 | 0.35 | 0.35 | ok | 0.346 |
| H_die_south | y=3,302.4 | 0..33,000 | 2,060 (2,060) | 2,070 | 1,271,664 (921,040) | 0.002 | 0.002 | 0.002 | 0.05 | 0.12 | ok | 0.002 |
| H_die_mid | y=13,324.8 | 0..33,000 | 37,312 (37,312) | 37,334 | 1,130,680 (780,056) | 0.033 | 0.033 | 0.048 | 0.72 | 0.81 | pinch>0.60 | 0.030 |
| H_die_north | y=22,560.0 | 0..33,000 | 9,324 (9,324) | 9,324 | 1,271,662 (921,038) | 0.007 | 0.007 | 0.010 | 0.44 | 1.04 | PINCH>1 | 0.002 |
| V_die_spine_w | x=13,526.4 | 0..26,000 | 14,929 (14,929) | 24,307 | 1,001,715 (725,466) | 0.015 | 0.024 | 0.021 | 0.15 | 0.36 | ok | 0.014 |
| V_die_vch | x=16,492.8 | 0..26,000 | 42,717 (42,717) | 45,069 | 964,124 (687,875) | 0.044 | 0.047 | 0.062 | 0.42 | 0.65 | pinch>0.60 | 0.039 |

Sweeps (a cut segment moved along the channel every 96 um / 48 um):

| sweep | span um | positions | > 0.55 | > 0.60 | > 1 | worst at | demand | supply | used | ratio | c3 worst (same sweep) | c3 worst (c3 position) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S_wspine_su | 13,277..13,781 | 105 | 1 | 1 | 0 | y=13,286.4 | 10,271 | 15,074 | 10,625 | 0.681 | 0.280 at 9,830.4 | 0.256 at 6,758.4 (0 > 0.60) |
| S_wspine_hub | 13,249..13,943 | 87 | 0 | 0 | 0 | y=13,392.0 | 9,514 | 20,431 | 9,514 | 0.466 | 0.314 at 13,392.0 | 0.326 at 13,372.8 (0 > 0.60) |
| S_vch | 15,671..17,312 | 211 | 0 | 0 | 0 | y=18,182.4 | 27,141 | 61,295 | 25,156 | 0.443 | 0.494 at 16,070.4 | - |
| S_vch_strip | 16,800..17,312 | 100 | 23 | 21 | 0 | y=18,979.2 | 15,366 | 18,278 | 14,645 | 0.841 | 1.035 at 14,659.2 | 1.049 at 14,640.0 (22 > 0.60) |
| S_vch_stncol | 16,995..17,225 | 83 | 59 | 59 | 23 | y=18,864.0 | 13,462 | 8,905 | 7,865 | 1.512 | 0.568 at 15,888.0 | 0.875 at 14,102.4 (4 > 0.60) |
| S_corridor_ew | 12,571..14,083 | 19 | 0 | 0 | 0 | x=17,692.8 | 9,782 | 57,665 | 9,783 | 0.170 | 0.000 at 17,308.8 | - |
| S_corridor_ns | 17,312..19,129 | 32 | 0 | 0 | 0 | y=14,025.6 | 9,590 | 69,474 | 9,594 | 0.138 | 0.000 at 12,585.6 | - |
| S_hub_e_face | 13,414..21,701 | 17 | 0 | 0 | 0 | x=15,974.4 | 49,046 | 317,826 | 49,069 | 0.154 | 0.076 at 15,686.4 | - |
| S_su_w_approach | 3,370..13,392 | 11 | 0 | 0 | 0 | x=13,276.8 | 15,396 | 304,970 | 15,476 | 0.050 | 0.050 at 13,276.8 | - |
| S_sw_seam_lat | 1,200..1,700 | 31 | 23 | 23 | 19 | x=7,612.8 | 10,116 | 5,718 | 6,417 | 1.769 | 1.769 at 7,612.8 | - |

16 hottest 480 um windows (M6-M9; 13 of them are the strip, 3 the SW seam; the field is 128 frames of 4,284..5,773 each, CONGESTION.md):

| hot window (480 um) x | y | overflow M6-M9 | by layer |
|---|---|---|---|
| 7,200..7,680 | 1,440..1,920 | 48,489 | M6 5,837 M7 17,765 M8 5,254 M9 19,633 |
| 16,800..17,280 | 18,720..19,200 | 43,611 | M6 24,545 M8 19,066 |
| 16,800..17,280 | 18,240..18,720 | 41,780 | M6 21,189 M8 20,591 |
| 7,200..7,680 | 960..1,440 | 35,413 | M6 1,344 M7 15,038 M8 3,899 M9 15,132 |
| 16,800..17,280 | 19,200..19,680 | 28,911 | M6 17,116 M8 11,795 |
| 16,800..17,280 | 19,680..20,160 | 24,063 | M6 14,315 M8 9,748 |
| 16,800..17,280 | 23,520..24,000 | 17,948 | M6 11,486 M7 98 M8 6,308 M9 56 |
| 16,800..17,280 | 20,160..20,640 | 16,988 | M6 10,029 M8 6,959 |
| 16,800..17,280 | 20,640..21,120 | 13,923 | M6 8,744 M8 5,179 |
| 16,800..17,280 | 22,080..22,560 | 13,161 | M6 7,338 M8 5,823 |
| 6,720..7,200 | 1,440..1,920 | 13,139 | M6 3,232 M7 52 M8 9,399 M9 456 |
| 16,800..17,280 | 17,760..18,240 | 12,599 | M6 5,881 M8 6,718 |
| 16,800..17,280 | 21,120..21,600 | 11,545 | M6 6,307 M8 5,238 |
| 16,800..17,280 | 22,560..23,040 | 11,242 | M6 6,563 M8 4,679 |
| 16,800..17,280 | 21,600..22,080 | 10,789 | M6 6,345 M8 4,444 |
| 16,800..17,280 | 23,040..23,520 | 10,355 | M6 6,497 M8 3,858 |


## b) Infeasible by construction against locally pinched

Infeasible by construction (ratio > 1 on the cut that the placement forces): rows 1, 2, 3 of the verdict table. Over the limit but below 1: rows 1b, 4. Everything else is fine on aggregate; the local pinches are wide buses pinned at **20.8 pins/um = every M4/M5 track (0.048 um)**, against 38.5 tracks/um of all three layers of one direction and 14.6 tracks/um of the pin layer itself:

| face | bus | bits | face span um | pins/um | tracks/um on the exit | pins / tracks | measured worst ~200 um window |
|---|---|---|---|---|---|---|---|
| sp_hc_s W, y 17,962.6..18,355.7 | y_d (hb_collective_t_hc_y), 8 slices of 49.1 um | 8,192 | 393.1 | 20.8 | 38.5 | 0.54 | 0.72 demand, 0.74 used |
| sp_hc_s W, y 18,357.8..18,554.4 | wq_d (hb_hc_s_wq_d_vm) | 4,096 | 196.6 | 20.8 | 38.5 | 0.54 | same window |
| hstnv_4096 station N / S face | wq_d, one pass | 4,096 | 196.6 | 20.8 | 38.5 | 0.54 | 0.452 (y 17,000) |
| the same 230 um column, two passes + 4 y_d slices | wq_d x 2 + y_d | 12,292 | 230 | 53.4 | 37.5 | 1.42 | 1.70 |
| sp_vm E, y 15,456..15,860 | collective_vm 2,100 + wq_d 4,096 + vm_pq 2,162 | 8,358 | 404 | 20.7 | 31.4 | 0.66 | 1.38 (two consecutive wq_d segments straddle the line) |
| sp_vm / sp_capture seam (22 um) | hb_capture_vm | 13,376 | 642 | 20.8 | 32.7 | 0.64 | 0.64 |
| svc_SW S / ctrl_SW N | rq 10,912, r_data 8,192, r_tag 544 | 19,648 | 1,439 | 13.7..20.8 | 35.4 | 0.39..0.59 | 0.66; and 488..491 um lateral offset between the two faces |
| rly_283_SN / rly_266_SN N face | xa / xb | 283 / 266 | 17.256 | 16.4 / 15.4 | 10.6 (M9 over the bf tile), 38.5 in the 17 um gap | 1.54 / 1.45 | lateral fan-out used 551 of 747 tracks in the gap (0.74) for 47 b that need to cross |

The xa / xb bundle is 0.346 over the bf tile once it is as wide as its destination (564 b on 1,632 M9 tracks over 145 um): the relay face, not the tile crossing, is the pinch.

## c) Over-limit cuts: buses and structural remedy (arithmetic on the measured cuts, not re-routed)

**1. Station column / strip W of sp_hc_s.** Buses: wq_d 4,096 b, 32 relay stations g0..g31 at x 17,004..17,211: north from the face (y 18,483) to y 23,630, then back south to y 15,779, then 8 stations west at y 15,174 to sp_vm; it crosses every line y 18,600..23,600 twice (8,192 b). y_d 8 x 1,024 b leaves the face in 8 slots of 49.1 um and runs N-S in the same strip to its collective lane (up to y 21,237). Remedy: (A) wq_d pins on the 2,061 um of the sp_hc_s W face that face sp_vm (y 14,083..16,144), at 394 um or more (10.4 pins/um or less): 0 N-S bits and a straight 1,745 um run to the sp_vm E face in place of the 32 + 8 station path; that face segment goes 1,305 -> 5,401 b on 79,920 tracks = 0.068. (B) y_d slice k leaves at the y of collective lane k (pitch 336.96 um from y 18,678): 1,024 b per 337 um = 3.0 pins/um; the segment facing sp_collective goes 2 -> 8,194 b on 105,450 = 0.078. Result (what-if in cuts.json): station column 1.424 / 0.997 / 0.886 -> 0.000; strip y 18,600 0.847 -> 0.053, y 20,000 0.575 -> 0.003; full channel y 18,600 0.387 -> 0.110. Removing only the north overshoot (one southward pass, as c3) is not enough: c3 has that and is at 0.875 in the column and 1.049 in the strip, because of y_d.
   sp_vm E face (same buses, arrival side): the 404 um y 15,456..15,860 carry 8,358 pins at 20.7 /um on 31.4 tracks/um = 0.66; spread over 808 um (two-track pitch; the face is 2,730 um) -> 0.33.

**2. ctrl_SW / svc_SW seam.** Buses n_rq_SW 10,912, n_rd_SW_r_data 8,192, n_rd_SW_r_tag 544, r_beat 128, rv / rk / wd 32 each, svc_SW <-> ctrl_SW, 19,872 b across an 8 um seam inside x 6,650..8,110; the ctrl pins sit 488..491 um west of the svc pins they connect to, so 10,116 b must move sideways where M4-M7 are blocked by both blocks: 1.769. Remedy: ctrl_SW pin x = svc_SW pin x. Lateral demand 10,116 -> under 50 b (what-if 0.000). The seam crossing itself stays 19,872 b on 51,000 tracks = 0.390 (worst 200 um 0.66); pins at two-track pitch over 2,920 um bring the window to 0.33. Identical in c3: not a v13 effect.

**3. Field xa / xb relays (1,280 + 1,280 instances).** 283 / 266 b from a 17.256 um face must cross 199 um of bf tile on M9 alone. Remedy: relay N face of at least 283 / (0.55 x 10.625) = 48.4 um (xb 45.5 um), i.e. 2.8 x the present width; at the destination's own pin span (about 67 um each, 4.2 pins/um) the ratio is 0.40 and no lateral fan-out is left. Not changed by v13.

**4. Spine W column at the SU / hub seam (y 13,190..13,392).** Buses (N-S station chains): aSW 1,026, xWup 981, rW0..rW3 3,010, xWdn 566, qSW 514, KW0..3 t / r 512 each; M5 is 61 % blocked there (8,838 of 14,600) by the stations themselves. Remedy, either: widen the column over that neck from 504 to 624 um (10,271 / 0.55 = 18,675 tracks at the measured 29.9 tracks/um), or take xWup + aSW (2,007 b) through the SU/HC channel instead (8,264 / 15,074 = 0.548; that channel is at 0.02..0.16 south of y 14,083).

## d) c5 (v13) against c3 (v11)

c3 has the same files; total M6-M9 overflow 830,012 against 1,052,585. Same structure at its own position in each run (ratio, worst ~200 um window in brackets):

| structure (c3 position = c5 position - 3,952.8 um N) | c5 ratio (worst ~200 um) | c3 ratio (worst ~200 um) |
|---|---|---|
| H_wspine_ch_y13000 | 0.459 (0.72) | 0.207 (0.49) |
| H_wspine_ch_y15000 | 0.344 (0.70) | 0.215 (0.40) |
| H_wspine_ch_y16560 | 0.366 (0.58) | 0.153 (0.41) |
| H_wspine_ch_y17200 | 0.264 (0.52) | 0.262 (0.41) |
| H_vch_y13403 | 0.109 (0.22) | 0.101 (0.23) |
| H_vch_y15500 | 0.310 (0.70) | 0.303 (0.78) |
| H_vch_y16560 | 0.290 (0.64) | 0.285 (0.55) |
| H_vch_y17200 | 0.258 (0.65) | 0.257 (0.68) |
| H_vch_y18600 | 0.387 (1.70) | 0.456 (2.72) |
| H_vch_y20000 | 0.361 (1.44) | 0.517 (2.05) |
| H_strip_y16560 | 0.346 (0.64) | 0.339 (0.55) |
| H_strip_y17200 | 0.292 (0.65) | 0.273 (0.54) |
| H_strip_y18600 | 0.847 (1.70) | 1.055 (2.72) |
| H_strip_y20000 | 0.575 (1.44) | 0.782 (2.05) |
| H_seam_su_vm | 0.256 (0.54) | 0.300 (0.82) |
| H_seam_vm_capture | 0.219 (0.64) | 0.201 (0.54) |
| H_seam_capture_gather | 0.110 (0.64) | 0.107 (0.64) |
| H_seam_gather_pq | 0.015 (0.11) | 0.000 (0.00) |
| H_seam_sseq_coll | 0.028 (0.22) | 0.024 (0.21) |
| V_hcs_w_face | 0.036 (0.72) | 0.026 (0.14) |
| V_hub_e_face | 0.128 (1.38) | 0.137 (0.89) |
| V_hub_w_face | 0.022 (0.20) | 0.022 (0.19) |
| V_vch_mid_hi | 0.109 (0.65) | 0.063 (0.63) |
| H_wspine_ch_y13325 | 0.577 (0.81) | 0.182 (0.40) |

Raised by v13: spine W column (H_wspine_ch_y13000 / 13325 / 15000 / 16560: 0.15..0.22 -> 0.34..0.58), sp_hc_s W face window (0.14 -> 0.72), hub E face window (0.89 -> 1.38), station column (0.875 -> 1.512), strip overflow (46,891 -> 270,214). Lowered: full-channel and strip share ratios at the collective (0.46..1.05 -> 0.36..0.85) and the SU / VM seam (0.300 -> 0.256). The E-column corridor exists only in v13: 9,782 b E-W on 57,665 tracks = 0.170 (M4-M7 only 0.232), 9,590 b N-S = 0.138; the earlier geometric figure was 0.282 / 0.289 for 20,076 / 20,588 b.

## Not determined / not verified

- Why the generator gives wq_d 32 stations with a north overshoot (path pick, stage count or a latency requirement): not determined.
- Supply contains no PG shapes and no clock reservation; with M8/M9 withheld the strip is 1.18, the spine W neck 0.97, the SW seam crossing 0.56 (column "ratio M4-M7").
- "share" spreads a net uniformly over its terminal extent; for the c3 strip it differs from captive (1.055 share, 0.424 captive), so the c3 strip number is an estimate.
- The q-element -> qbank buses (n_x?_.._eb, 151,698 overflow in CONGESTION.md) were not cut-checked. Remedies are arithmetic on the measured cuts; none was re-routed. Wide / NDR nets count as one track.
