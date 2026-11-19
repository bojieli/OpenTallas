# FABLE-PD-STRUCT 2026-11-18 18:40 PST (1840): QC N4.2 and S81 D8f, read in parallel with their binds

Reviewer: FABLE-PD-STRUCT-1840. Read-only: no job launched, killed or patched. Technical PD only.
Marking: **V** = file opened this round. **R** = reported by the named lane. **I** = inferred from V data. **P** = proposal.

## 0. Headline

1. **QC seam_ps 110 is not safe die-wide (V).** The 91.33 basis is the 10-31 gen55a tree. The current tree needs 147.87.
   Five hc1 types are the receivers of that tail, and sle_hc1 is the type N4.2 relaunches.
2. **S81 D8f moves bn11 / bn12 half an M5 track off grid (V).** 257 of the bank's 258 pins are M5. Snap the two x values before the kits launch.
3. **S81 slice_station START depths differ between reader and writer by -1 to +2 cycles, per type (V).** The bind must show the count-aligned crossings still pass.
4. The other D8f items (h10_r1 site, halos, u_vq) and the QC su_l1 and wep items carry no structural stop.

## A. QC N4.2 (S4Q9N42, bind running on epyc9, V 18:35)

### A1. seam_ps 160 -> 110

Evidence (V, epyc2 `fable-die-qc-r/chain/qc/s4q9m4/reg/sta/die_sta_related.json`, plan 32bba5467a18, 11-17 05:12; this chain is the source of the N4.2 `tap_offset` rows):

| number | value |
|---|---|
| seam kit-contract window needed (FF) | 147.87 ps, PASS at 160 with +12.13 |
| seam pairs | 2,016,452 |
| damage percentiles | p50 0.45, p99 71.14, p99.9 107.11 |
| pairs over 80 ps | 19,256 |
| worst five | sl_E0 / E3 / E4 `hc2 clk` -> `hc1 clk_t13` 147.87 / 147.84 / 147.19; sl_E0 / E3 `hc2 clk` -> `hc1 clk_t41` 146.66 / 146.62 |
| TT seam setup | +550.14 |

History (V, lanes/FABLE-DIE-QC.md section 6 and 7): on the S4q9c routed clock, window 110 gave seam contract hold -59.2 on 2,797 pairs (need 169.2). That is why the window went 110 -> 180, then 160 on s4q9m_r (147.87 + 10).
The 91.33 in the N4.2 note is DIE-QC-56 on gen55a (10-31), a different tree.

Reading:
- At 110 the die seam contract is -37.87 worst. The failing set is a thin tail: under 0.1 % of pairs lie above 107 ps, so at most about 2,000 pairs (I; no run at 110 on this tree).
- The tail has one cause (V, N4.2 plan rows). The `clk` port of sle_hc2 / slw_hc2 sits 78 to 98 ps early: tap_offset TT -92.1 / -93.2 / -97.7, per-port window 160 to 163. Everything else in the listed types is small: stm and fe ports have windows of 22 to 47 ps.
- Receivers of the tail are the hc1 types (sle_hc1 x2, slw_hc1 x3). sle_hc1 relaunches on N4.2 for the wep fix, so it would be built with 85 ps of port pad where its own seam needs about 133 (147.87 + 10 - sender 25) (I).
- For slw_stm_v1/v2 and slw_fe_v1 the 110 window is right: their seams are far inside it. Port hold moves from -135 to -85 in the SDC, the level the signed siblings closed at (R, QC-SLW-STM-1118).

Not measured: the N4 tree itself (the plan note asks for a re-measure on the N4 clock chain); hold on real views (0 pairs measured, all declared-budget).

### A2. su_l1 flt_su_c_i uniform 5

V, `plan_n42_b.json` sle_su_l1__cl5ea486db rows 36 to 39: all four chains have 5 regs. Manhattan hops, pad to core pin: lane4 about 52 um, lane5 about 87 um, lane6 max 267.8 um, lane7 max 287.5 um. No hop over 304. The lane table already carried 5 (R, bind 1921/1921). No risk found.
Side note (V, `respace_n42.json`): the x_su_c_i and x_su_c_p1_i rows came down from 422.6 / 481.9 um to 350.3 / 333.5 um, still the longest hops in the type.

### A3. sle_hc1 wep pin (1a2846af93)

RTL pin only; nothing to check in the plan. Its routed TT was -59.5 (R). The risk is A1: the relaunch picks up the 110 SDC.

### A4. Ranked fixes

| # | fix | owner |
|---|---|---|
| 1 | Let the N4.2 bind and apply finish (0 of 213 kit identities change). Hold only the hc1 relaunches (5 types) until fix 2 or 3 lands. | QC-PLAN-R3, QC-TYPES-R3 |
| 2 | Structural: retime the hc2 `clk` root tap (78 to 98 ps early) in the die clock rows so the hc2 -> hc1 seam falls under 100. Then 110 is true for every seam. | QC-PLAN-R3 with the QC clock rows lane |
| 3 | If 2 costs a clock chain: add a receiver-type override `clock.seam_hold.per_type_ps` to `gen_phys.seam_hold` and give the 5 hc1 types 160. About 20 lines plus a test. | WAVE-FLOW-R2 (tool), QC-PLAN-R3 (rows) |
| 4 | Run `die_sta_related` on the N4.2 plan with the s4q9m4 proof: it names every pair above 100 at window 110. | QC-PLAN-R3 |

Will fail if nothing is done: the die seam contract at sl_E0 / E3 / E4 hc2 -> hc1, about -38 ps, once hc1 is signed at 110.

### A5. Stop list

- Do not quote 91.33 as the measured need of the current tree.
- Do not relaunch sle_hc1 / slw_hc1 on the 110 SDC.
- Do not raise the die-wide value back to 160 for the tail: that returns stm / fe to -135.
- Do not wait for the GEOM tap-cluster rule (QC-SLW-STM-1118 item): it is withdrawn with the split-tap class.

## B. S81 D8f (plan 1c6addc1008b, bind r1 running on epyc8, V 18:35)

Diff D8e df7446e48ba9 -> D8f (V, my own deep diff): 467 leaf changes. They are the five items below plus 2 serdes reset rows; nothing else moved.

### B1. col_h9_r2: bank move and 45 ps late capture (60 types)

- V: `u_r2.u_bn11` x 1140.48 -> 1046.088, `u_r2.u_bn12` x 155.52 -> 201.528, the same in all 60 types.
- **V: both new x values are off the plan grid.** 71 of the other 73 cores sit on 4.32 um multiples; these two are 0.648 and 1.512 um off, which is 0.024 um (half a pitch) off the 0.048 um M5 grid. `dsfd_qbank_N.json` has 257 M5 pins and 1 M4. M5 is vertical, so an x shift of half a pitch puts every pin between two tracks.
- I: each pin then needs an off-track access via and blocks two tracks. Expect pin-access DRC or a long detailed route on 60 types. The bind does not check this (GEOM and R3 binds are green with it).
- Fix (P): snap bn11 to 1045.44 or 1049.76 and bn12 to 198.72 or 203.04. The move is under 2.8 um, so the 151 to 160 um ROM hop does not change.
- Late capture: `core_pin_lead_ps` gets lead -45 on `ck[0]` of `u_bn1[12]` (V; the regex matches bn11 and bn12 only). Budget (R, 1530 lever 4): routed family -38 to -59; +13 move +45 capture gives -1 to +20 routed. Kits now at GRT -87 to -109 land at about -29 to -51 at GRT, so the worst kits stay marginal.
- Not measured, by anyone: hold on the other bn11 / bn12 inputs, and setup on paths launched from bn11 / bn12, which lose 45 ps. Read both on the first kit at GRT (`OT_PREGRT_FF_HOLD` class line, ends at `u_bn1[12]` pins).

### B2. col_h10_r1: d1 flop at 0.41 (12 types)

- V: site (809.6, 446.64). Nearest cores are ROM `u_c7_2` at 11.20 um and `u_c7_5` at 11.24 um, so it is mid-channel and legal.
- I, from the pad bit (1228, 301) and station (207, 665) (R): leg 1 is 564 um, leg 2 is 821 um. At 0.28 ps / um (1530, V) leg 2 is about 230 ps of wire. No risk.
- The -138.57 path is real: the post-hook repair line reads -145.99 on the same end (V, 1530).
- The 32 ps "adverse skew" that argued for 0.40 over the midpoint was a pre-pad number (t12 437 / t19 436 after the hook, R). The site is fine either way; do not re-site.

### B3. col_h9_r0_p3..p6: 5 um halo on cfg7_seq (42 types)

- V: 5 halo cores per type in p3 / p4 / p5 (4 `ot_s81_cfg7_seq`, 1 `_bfp`; each 17.28 x 51.84 um), 7 in p6. Facing gaps from a halo core: 3 at 10 to 20 um (p6: 4, plus 1 at 5 to 10 um). No overlap, no gap under 5.
- Risk is low. The one 5 to 10 um channel in p6 becomes cell-free.
- The halo does not buffer anything. The p3 `u_y_cc` -> `u_s0.lc` -440 (867 ps of unbuffered wire, R) needs a buffer or relay site on its way; that row is not in D8f.
- The -330 to -339 "after repair" on 15 kits has no named end now: `ret_o0` and the cf rs relay were both hold paths from the pre-hook report. Owed read at GRT.

### B4. slice_station START reach chains (8 types)

V, per type (reader depth / writer depth; max hop between consecutive stages, Manhattan):

| type | reader | writer | max hop um |
|---|---|---|---|
| t22 | 9 | 7 | 335.8 |
| t25 | 8 | 9 | 324.7 |
| t27 | 7 | 6 | 327.1 |
| t31 | 7 | 6 | 353.7 |
| t36 | 8 | 9 | 351.3 |
| t43 | 7 | 5 | 327.2 |
| t44 | 7 | 6 | 353.7 |
| t52 | 7 | 5 | 322.3 |

- Hops are 322 to 354 um, not "336 or less"; four types are above 336. All are under 380, so reach is fine.
- **Structural question (I): reader minus writer START depth is -1 to +2 cycles and differs by type.** Every S81 crossing is count-aligned, so a START that reaches the reader and the writer on different cycles shifts the pointer distance. LATCHECK 873 / 873 covers lane latency; I found no line that says the count-align start skew was re-checked with these depths.
- Fix (P): read the count-align line of bind r1 for the 8 types. If the bind does not price START depth, pad the shorter chain so both ends of a crossing get the same depth (flops only, boot cycles, free under the 64-clock reset hold).
- Stages use raw resets from several taps (rst_n_t44 / t38 / t29 / t23, V). Same check: one release order per chain.

### B5. u_vq relay re-site (leaf t24 / t8)

R: last hop 90.7 / 95.0 um, reach 155 um allowed, no legal site within 50 um. V: the diff shows the two re-sites plus 19 other leaf relay paths on t40. No timing number exists for the last hop. Accept; read reset recovery at `u_vq/rst_n` on the first t24 kit. The vq move (+4.32 / +8.64 um) stays optional.

### B6. Ranked fixes

| # | fix | owner |
|---|---|---|
| 1 | Snap bn11 / bn12 x to the 4.32 um grid before the D8f kits launch (2 values x 60 types; a row delta on the running bind, or D8f r2). | S81-GEOM-OPUS (rows), S81-DIE-R3 (compose) |
| 2 | Count-align start skew for the 8 slice_station types on bind r1; equalise depths if unpriced. | S81-DIE-R3 |
| 3 | First col_h9_r2 kit at GRT: hold ends on bn11 / bn12 inputs, setup from bn11 / bn12 outputs. Sign-off needs both. | S81-COL-FLOW-1118 |
| 4 | p3..p6: name the post-hook worst setup end, then one relay site for `u_y_cc` -> `u_s0.lc`. | S81-GEOM-OPUS |
| 5 | Copy CTS-POST-RPT-1 (01c4b1e891d) into the D8f tools. It is report only and D8f does not have it. | S81-DIE-R3 |

Will fail if nothing is done: col_h9_r2 detailed route or pin access on 60 types (B1, I, likely). Possibly the boot of crossings in 8 slice_station types (B4, unproven either way).

### B7. Stop list

- No ret_o0 SDC change, no cf rs relay row, no clock rule for the lpl chunk strobe: all three are pre-hook artifacts.
- No re-site of the h10_r1 flop.
- No mass launch of col_h9_r2 on D8f before the bn11 / bn12 snap or one kit through detailed route.
- No second crr stage for u_vq.

## C. Verdicts that rest on pre-hook CTS numbers

Rule (V, main `tools/die_plan/cts_post_report.tcl`): `4_cts_final.rpt` and the `cts__timing__*` metrics are pre-padding on every tap-balanced kit. Lines printed by steps that run on `4_cts.odb` after the hook stand: `OT_TT_SETUP_REPAIR`, `OT_PREGRT_FF_HOLD`, the hold guards, and every GRT or routed number.
Wire-dominated setup ends survive (h10_r1: -138.57 pre-hook, -145.99 post-hook). Hold classes and cross-tap skew do not.
`tools/closure_loop/stuckscan.py` line 284 still reads `4_cts_final.rpt` (V); point it at `4_cts_post_hook.rpt`.

| where | verdict or lever | status |
|---|---|---|
| 1530 lever 1 item 2 | p3..p6 "flow-frame worst" cf rs relay -283.8 and ret_o0 -336.6; "write the relay row" | WITHDRAW (ret_o0 is +34.39 on the balanced DB, R). Re-read p3..p6 at GRT. |
| 1530 lever 5, second class | lpl chunk `rq -> wr -> r` -207.6 / -225.1; "one wr copy per chunk" | WITHDRAW. |
| 1530 lever 5, site at 0.40 | leg asymmetry from 32 ps adverse skew | Skew term void; the site stands on distance. |
| 1530 headline 1 | 146 S81 kits bucketed by "post-CTS or GRT TT" | Counts stand only where the number is a repair or GRT line. Re-bucket at GRT; the slice_station -352 to -1,039 magnitudes are unconfirmed (the 2,496 um hop is real). |
| 1530 lever 6 (KV) | k4 post-CTS -138.19 against k3 +0.43; `u_srl_152` -> `u_srl_153` -114.8 "flow-frame worst" | The wns is a repair line and stands. The named path is from the pre-hook report: confirm at GRT before the relay site. |
| 1530 lever 8, 1320 (QC) | st_a k5 +10.78 / k6 -133.7; "24 of 36 QC kits at 0 or better post-CTS"; candidates at CTS wns 0.00 / -5.29 / -33.43 | Re-read at GRT; the candidates may be worse or better. |
| 1530 lever 7 and older (HEAD) | hd_mesh mesh_w1 cross-tap 10,190 ends at -185.30 with "five taps short of 450" (clk_t45 322 ...); FABLE-PD-HEAD-2045 hd_mesh cross-tap 12,346 ends ws -112, taps 426..462; hd_lep0N p2 -379.62 | The "taps short of target" picture is the pre-pad signature. Re-read at GRT before any tap-window lever. |
| 0220 strip leaf lever 1 | t50 -684.45 from `4_cts_final.rpt` | Stands: 684 ps of data path, far above any pad. |
| QC-SLW-STM-1118 | GEOM tap-cluster rule to feed tap window rows | WITHDRAW. |
| FABLE-PD-QCHOLD-1915, FABLE-TYPES-QC-EAST | cross-tap hold class sizes (7 to 30 k ends) | Stand if taken from `pregrt_ff_hold_open.tsv` (post-hook); I did not re-open them. |

## D. Not checked

- Bind results: both binds were still running at 18:35.
- QC seam damage on the N4 clock tree; the exact pair list at window 110.
- Whether detailed route fails on off-track bn11 / bn12 pins (no kit exists on D8f).
- Whether the S81 bind prices START depth in its count-align check.
- Whether KV kits run tap_balance (the table marks KV rows on that assumption).
- The older FABLE-PD files with one or two CTS mentions (FABLE-FLOW-1750 / 1555, FABLE-PD-QC-1240 / 0750) were listed, not re-read.
