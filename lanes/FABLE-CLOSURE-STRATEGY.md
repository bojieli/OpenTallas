# FABLE-CLOSURE-STRATEGY 2026-11-21 21:45 PST (lane FABLE-CLOSURE-STRATEGY-2115): the 13 "GRT-0273" kits are one-hotspot kits, 49 to 94 % of their overflow sits in gcells with under 10 tracks; KV pv bind 12 died on the per-consumer vo legs; S81 kv_leaf t5 band is full at 0.97

Supersedes the 20:30 round (`git log -2 -- lanes/FABLE-CLOSURE-STRATEGY.md`). Its levers and stop list stand unless a line below changes them. FABLE-PD-QC-2045 corrected the 20:30 lever 4 (st_a / glue stop on `SETUP_TRIAGE`, not on the tap bound); that correction is adopted here.

Reviewer: FABLE-CLOSURE-STRATEGY-2115 (Fable). Read-only: nothing launched, cancelled, patched or deleted; no ot-run job. One helper script was written to `/tmp/fcs_cong.py` on epyc2, epyc8, epyc9, epyc10, intel1, intel2 (a 30-line report reader; safe to delete).
Scope: S81, HEAD, QC, KV physical design. Gate: DRC 0, TT setup >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. No die or outline growth. Nothing below is a new gate.
Marking: **V** = read or computed by me this round from the named file. **R** = reported by the named lane or review. **I** = my inference. **P** = proposal.

## 0. Measurements this round (V)

### 0.1 The GRT-0273 kits (NOPROG-TABLE 21:00)

Read on each live kit: `run/logs/asap7/*/base/5_1_grt.tmp.log` and the newest `run/reports/asap7/*/base/congestion-N.rpt` (capped at 20,000 gcells per report, so sums of 20,000-gcell rows are lower bounds). Bins are 100 um, named by their lower-left corner.

| Kit (host) | Die um | Components | NDR drops (taps) | Report | Listed overflow | In gcells under 10 tracks | Top bins (x, y): overflow | Top named net family |
|---|---|---|---|---|---|---|---|---|
| sle_ctl cl67434795 padW5 (epyc10) | 1227 x 1339 | 548,972 | 8 (3) | it 25 | 50,457, capped | 77 % | (400,300) 16.8k, (400,400) 12.7k, (600,300) 10.1k | `u_ist_b_hw_hc*_o` 84k mentions, `u_ist_b_tw_data_st_a_o` 44k |
| slw_su_c cl19bb38ef (epyc10) | 1227 x 1400 | 574,227 | 7 (4) | it 30 | 1,525 | 75 % | (500,400) 824, (500,500) 420 | `u_ist_x_su_l*_p*_o` |
| slw_su_c cl92142dac (epyc10) | 1227 x 1400 | 515,792 | 3 (3) | it 30 | 171 | 42 % | (500,400) 76 | `u_ist_x_su_l*_p*_o` |
| sle_su_c 156998 (epyc9) | 1227 x 1400 | 557,394 | 9 (6) | it 15 | 11,846 | 70 % | (900,200) 4.1k, (500,400) 1.6k | `u_ist_x_su_l*_p*_o`, `x_su_l*_i_b` |
| sle_su_c 3965819 (epyc9) | 1227 x 1400 | 555,726 | 23 (6) | it 20 | 23,105 | 65 % | (900,200) 6.4k, (600,300) 3.4k | same |
| leaf t28 (epyc9) | 1590 x 1279 | 540,617 | 25 (8) | it 15 | 8,164 | 65 % | **(400,400) 5,301** | `u_ft_ft*_o` chains, `vni_gd_s` source flops |
| leaf t44 clf6cf8492 (epyc10) | 1443 x 1279 | 343,767 | 55 (13) | it 10 | 60,390, capped | 66 % | (300,400) 20.1k, (300,300) 8.7k, (300,500) 8.3k | `vp_g_hig_*_u_cst_gd_s` 54k, `u_ft_ft*_o` 28k |
| leaf t35 (epyc8) | 1443 x 1227 | 258,240 | 29 (4) | it 20 | 10,187 | 49 % | (200,500) 2.9k, (300,500) 2.8k | `vp_g_hig_*_u_cst_gd_s` |
| kv3_hgi_v4 (epyc2) | 1279 x 1521 | 313,784 | 25 (18) | it 20 | 37,819, capped | 85 % | **(100,600) 16.4k** | `u_hst*_t*.u_reg.ti_b` 55k, `cland_ft*_i` 12.7k |
| kv3_hgi_v1 cl42bc8b12 (intel1) | 1279 x 1521 | 243,755 | 4 (1) | it 20 | 11,039 | 94 % | (0,1200) 3.1k, (600,300) 1.7k | `u_bin_i_ectl_Q_N_tN` |
| kv3_hgi_v1 cl141fc26e (intel2) | 1279 x 1521 | 242,138 | 4 (2) | it 30 | 14,987 | 82 % | (100,1200) 5.4k, (200,1200) 3.2k | `u_bin_i_ectl_Q_N_tN` |
| kv3_hg_v1p6 2680076 (intel2) | 1279 x 1521 | 529,606 | 76 (41) | it 5 | 55,974, capped | 61 % | (500,600) 11.1k, (600,700) 7.6k | `u_ist_o_ectl_Q_N_tN` 28k, `u_ist_o_astk_Q` 10.5k |

leaf t25 (intel1) and the second sle_ctl / hg_v1p6 kits were not read (same types as rows above).

Reading:
- **GRT-0273 is a label, not a cause.** It fires on 1 to 41 taps per kit (3 to 76 lines), and clock nets are under 2 % of the named sources in the overflow gcells (t35: `clknet` 1,020 of about 90k mentions).
- **Each kit has one hotspot.** One or two 100-um bins hold 30 to 65 % of the listed overflow on 9 of 12 kits. It is not a die-wide density or utilisation problem.
- **The hotspot gcells have little capacity.** 49 to 94 % of the overflow is in gcells with under 10 tracks in total (a free gcell has about 30). That is routing over a macro, in a macro slit, or under the PG track obstructions (`OT_PG_TRACK_TRUTH` adds 2,561 to 3,430 obstructions per kit). Same finding as HEAD hd_lep0N (64 %, FABLE-PD-HEAD-2000). Which of the three it is per kit was not separated (section 4).
- **What crosses the hotspot is a named station or ring bus**, plus resizer buffer nets (`netN`) of the same paths: internal-station chains (`u_ist_*`) on sle_ctl, su_c and hg_v1p6; feed-through chains (`u_ft_ft*_o`) and the `gd_s` source registers on leaf; the head-station `ti_b` buses on hgi_v4; the `i_ectl_Q_N_tN` landing bin on hgi_v1.
- Six of the kits have 516k to 574k components (this count includes tap and filler cells; the non-tap count was not read). On HEAD the same ratio was 492k components = 396k non-tap, so these six are at or over the 400k cap (I).
- su_c cl92142dac reached overflow 171 and is UNSIGNABLE on setup (-504 ps, NOPROG-TABLE): for that type the remaining stop is timing, not routing.

### 0.2 KV pv split, bind 12 (V: epyc8 `opus-fix-kv-pv-r4/split28/bindgate_12/gate.out`, intel2 `~/tmp/okpvr7/chain_r7a.log`)

- `RC_BIND 1 ValueError: native stations pv_N_7e.o_vport_E_N_vo_d1_p_2: expected one outgoing lane`. Elab passed (74 modules). No bind report was written, so no latency read exists for the 15-type split e997b2f7ad71.
- `o_vport_E_N_vo_d1_p_2` is one of the per-consumer legs `_p_2 .. _p_6`: one landed vo bus leaves the piece as five output buses, one per consumer station in the other half. The native station model wants one outgoing lane per station.
- R (OPUS-FIX-KV-PV-R7 20:24): the same legs are why kv3_pv_v1n does not fit its cut: 30 legs x 270 pins = 8,100 of 16,191 cut pins against a budget of 13,001.

### 0.3 S81 kv_leaf t5 landing band (V: intel2 `.../private/FAM-S81-MISC-R4/ot_s81sl_kv_leaf__t5_1121195713/gen/ot_s81sl_kv_leaf__t5/run_place.log`)

- `OT_CLAND BAND FAIL u_cland_ft0_i` and `ft1_i`: 7,191 cells each, reserve need 2,392.0 um2 against band area 2,465.2 um2, ratio 0.97. `u_cland_monitor_0`: 326 cells, 113.8 of 242.6 um2, ratio **0.47, and it also fails**.
- Same log: `strip density ring:ft0_i 2.59 flops/um2 at rows 1, target 1 -> rows 3 (band fits 3, 50 columns, 1661 flops)`.
- Reading: ft0_i / ft1_i are an area misfit (no legal non-overlapping site at 0.97). monitor_0 at 0.47 is not area; its band is short of legal rows or sites for another reason (I: rows taken by the neighbouring strip or a blocked row; not read).
- The A/B in flight sets `OT_CLAND_STRIP_DENS=2`. That changes the strip row count, not the band area, so it cannot move the 0.97 (I).

### 0.4 s81_head_cl canary (V: `lanes/posts/FLOW-CANARY-R2.md`, main `git log 7b6af7dd04..3b2f4d0447`)

- 19:30 run at 7b6af7dd04: no regression. 20:15 at 3b2f4d0447 and 21:00 at cd2cd11c4e: TT setup 127.20 -> 109.93 (-17.27 ps), tap insertion 448.77 -> 441.03, GRT DRV 0 -> 14.
- 17 commits are in that window. Two touch the build of an existing kit: `8a2a7b31a97` (relay / station / landing / reset-sync registers kept from `opt_merge` by default) and `3c2f3758f4c` (tap splitter, opt-in). The first is the likely cause (I): more kept registers, more clock sinks, a different tree.
- The canary type hd_turn_a still has +109.93 ps. This is not a closure stop. It matters for types that sit within 20 ps of the gate.

### 0.5 Carried from the lanes since 20:30 (R)

- QC coll_core: FABLE-FIX-QC-COLL-R2 21:03 re-solved the seats with a legal map: 0 seats in a core box, 0 in a slit (was 97 and 599), at most 2 per point (was 254); the two 5.4 um slits are opened to 35.6 um by moving four ring SRAMs 30.24 um. 351 connections remain over 405 um (max 448, four at 558). Package v2 (28 rows) is in strict bind. No kit has run with the seats.
- QC V3p6n ships without the coll delta, without the 66 station hops over 405 um (19 types), and with cb row A on one type. QC-PLAN-R13 recorded all three as the V4 carry list. FAM-QC-CB-R4 delivered row A for 17 cb types from one LIB read (bind running).
- KV hg / hgi: R6c strict bind is green, but `lockup_regions` did not take effect inside bind on hgi_v2 (one rest copy with 40 loads; 18 regions only in a post-bind replay). Debug bind running.
- S81 leaf: plan b cleared 37 tap errors and two cut errors, then segment `s_2S_L0` on t22 reads 0.60 at cut 10750. Plan c adds the t32 nudge (lanes by (0, -17.28)) on t22.
- S81 col_h10_r1 rep: post-CTS TT -1.98 before repair; the CTS TT repair made it -21.04 and the regressed DB was kept (flow bug, fixed on main 650916ebb262 for newly generated kits).
- S81 leaf t39: 2,578 FF hold ends at -89.3, all input port to register; slack follows capture latency (r = -0.988), needed data delay 49 to 90 ps per port (TAP-GRID-R5).
- HEAD hd_lep0N: type_split cuts it at x 820.8 into two pieces; cut-form LEC running.

## 1. Levers, ranked by types and dies unblocked

### Lever 1. S81 col: decide the J8 entry from the three running proofs (216 types; unchanged rank)
- Evidence (R): lever-1 kit col_h10_r0_p4 pvcc166a6d and proof A are in place / geom on epyc7; rep col_h10_r1 cld01bb4ae is past CTS with ROM-pin ends at +13.67 and a pval output path as WNS (ROM clk->pval 611.6 ps + about 316 ps wire, capture tap about 424 ps late).
- Root cause: ROM output delay of 612 ps leaves about 220 ps for wire and capture, so the pval stage only closes with the capture register at the ROM pin.
- Fix (P): as the 20:30 lever 1. Add: judge the rep on `5_1_grt.odb`, and relaunch it from CTS on a kit generated at or after 650916ebb262 if it ends under the gate, because its present DB carries the regressed TT repair.
- Owner: FAM-S81-COL-H10-R4, FABLE-FIX-S81-COLROM-R5, FAM-S81-COL-R6, S81-J6-ASSEMBLY-R5.

### Lever 2. S81 START and reset reach rows as J8 GEN steps (writer 104 types, reader 38, raw reset 73; unchanged)
- Evidence (R, FABLE-PD-S81-2000 section 2): J7eL6 has rows for slice_station only. Serdes 7 ops to 3,328 um, svc 16 types to 4,087 um, leaf 50 types on the falling-edge `fstart_k <- rst_rl_*` relay.
- New (R): the svc J8 plan failed strict bind at `reset_tree` on two stale die relay rows; `relay_r9.sh` re-plans them (+31 boot cycles, longest hop 290 um). The same re-plan must run on the J8 plan after every family's rows are in, not per family.
- Owner: each S81 family lane; S81-J6-ASSEMBLY-R5 (order: all rows, then one die relay re-plan, then bind).

### Lever 3. One-hotspot GRT class: move the named bus or the macro, per type (S81 leaf t25 / t28 / t35 / t44, QC sle_ctl + su_c 3 types, KV hg_v1p6 + hgi_v1 + hgi_v4; 3 dies, about 30 types with their variants) NEW
- Evidence: section 0.1.
- Root cause: a station or feed-through bus is sited so that its hops cross gcells that a macro, a slit or the PG tracks have already emptied. The router has no capacity there in any iteration, so the overflow goes flat (sle_ctl 43k -> 50k, t44 62k -> 50k, hgi_v4 34k -> 38k) and the clock NDR is dropped as a side effect.
- Fix (P), one plan row per type, in the daily event:
  1. Overlay the top two bins of the table on the type's macro map (the kit `auto_geom.png` already draws both). If the bin is over a macro: re-site the stations of the named bus to the nearest channel. If it is a slit or macro corner: move the macro (cores move, no re-shape) to open the channel to the bus width at 30 tracks per 0.57 um gcell.
  2. Named first moves: sle_ctl `b_hw_hc*_o` and `b_tw_data_st_a_o` internal stations away from x 400..700, y 300..500; leaf `u_ft_ft*_o` chains and the `gd_s` source registers at x 200..500, y 300..600 (t44, t35, t28 share the region, so one leaf rule); hgi_v4 `u_hst*_t*.u_reg.ti_b` at x 0..300, y 500..700; hgi_v1 the `i_ectl_Q_N_tN` landing bin at x 0..300, y 1000..1300; hg_v1p6 `o_ectl_Q_N_tN` stations at x 500..700, y 600..800.
  3. For the six kits over about 500k components, the cap split comes first (lever 6); the hotspot row goes on the piece that keeps the bus.
- Flow (P, NEW): add "overflow share in gcells under 10 tracks" and the top two bins with their top net family to the GRT-flat verdict line. It is 30 lines of python on a report the kit already writes, and it turns "GRT-0273" into a located row.
- Owner: FABLE-FIX-S81-LEAF-R9 (leaf), FAM-QC-SLWSLE-R1 (sle_ctl, su_c), OPUS-FIX-KV-HGI-R6 (hg, hgi); verdict line NEW (FLOW-OPS / NOPROG owner).

### Lever 4. KV: one shared vo crossing per bus on every pv piece; lockup_regions inside bind; stable blocks (pv 16 + hg / hgi 19 of 50 unsigned)
- Evidence: section 0.2 (V); section 0.5 hgi (R); FABLE-PD-KV-2000 (0 sign-offs in 22 events, 52 of 56 blocks re-keyed per event).
- Root cause (pv): the vo landing fans out to five consumers before the cut, so one input becomes five output buses. That breaks the one-lane station model at bind and costs 6,480 cut pins on v1n.
- Fix (P): apply the row R7 wrote for v1n to all 16 pv types: ring -> one 270-bit station -> one cut crossing -> a fan-out station in the consumer half, from which the five consumer rows start (+1 cycle pre-approved if a hop needs it). 30 legs become 6. This is one structural row that removes the bind error and the v1n cut misfit together, so v1n no longer needs to stay unsplit. Do not teach bind to accept several outgoing lanes instead.
- Fix (hg / hgi): the in-bind `lockup_regions` defect is the gate for all 19 types; the hgi_v2 cle0015330 kit is meaningless until the bound text shows the 18 regions.
- Stands: no die-wide re-key in D28; pc x6 and io_cor x2 sign first.
- Owner: OPUS-FIX-KV-PV-R7, KV-PLAN-R6, OPUS-FIX-KV-HGI-R6, TAP-GRID-R5 (per-half tap rows after the fan-out row, since it moves sinks).

### Lever 5. QC V4 as one package: station rows, cb row A family-wide, coll v2 (cb 17, hops 19 types, coll 3, SETUP_TRIAGE 18 types)
- Evidence (R, FABLE-PD-QC-2045 and section 0.5): 66 hops over 405 um in 19 types unchanged since V2; lockup latch bit `n_b[372]` fails on three cb types; `SETUP_TRIAGE` (setup estimate under -150 ps) stopped 18 types since 11-19; FAM-QC-HCST-R3 classified its stops (btab re-site, R8S seat, `u_cland_origin -> rstart_tx` station, split).
- Fix (P): V4 carries, keyed by type on V3p6n: (a) +1 station with sites on cb `bc_i00` / `bc_i10` / `bc_i30`, `nb_i12`, `y_o00`, slw_hc3 `cw_n3` (515 bits), slw_fe_v2 `arv_ei` / `arm_ei`, sle_ctl's three groups, slw_stm `flt_o`; (b) cb row A rev4 on 17 types; (c) coll v2 with the legal seats and new `sink_bins/coll_core.json` from the seats; (d) HCST setup-triage rows. For sle_ctl and su_c, cut the station rows together with lever 3, since the same `u_ist_*` buses are the GRT hotspot.
- Owner: QC-PLAN-R13 (V4), FAM-QC-CB-R4, FABLE-FIX-QC-COLL-R2, FAM-QC-HCST-R3, FAM-QC-FEFW-R3, FAM-QC-SLWSLE-R1, TAP-GRID-R5.

### Lever 6. Cell cap by split (S81 c1x_C 9 + svc hi4 + leaf t28; QC 21 + su_c / sle_ctl; KV hub 5 + hg_v1p6; HEAD hd_lep0N)
- Evidence: section 0.1 component counts (V); S81-2000 section 3, QC split table, KV hub census, HEAD lep0N (R). HEAD lep0N now splits end to end at x 820.8 (R).
- Fix: FLOW-STRIPBODY-R2's bind path stays the common dependency. Add the six types of section 0.1 to the split census after reading their non-tap counts from the kit `4_cts.odb`. A split piece must carry the wall or hotspot row with it (HEAD-2000 section 2.2; lever 3 here), or the piece inherits the flat GRT.
- Owner: FLOW-STRIPBODY-R2, FAM-S81-SLICE-R5, OPUS-FIX-S81-SVC-R9, FAM-QC-HCST-R3, FABLE-FIX-KV-HUB-R5, FABLE-FIX-HEAD-LEP0N-R7.

### Lever 7. Landing bands sized in the plan at 0.70 fill or less (S81 kv_leaf t1 to t5; same class as HEAD hd_ctl strip and KV pv CLAND band x5)
- Evidence: section 0.3 (V); HEAD hd_ctl south strip 0.945 at rows 1 against 0.878 at rows 3 (R); 5 KV pv CLAND band stops on D26 (R).
- Root cause: the ring needs 2,392 um2 and the plan band is 2,465 um2. A 277-bit ring with 1,661 flops and 7,191 cells cannot be legalised at 0.97.
- Fix (P): a J8 plan row that deepens the ft0_i / ft1_i bands of kv_leaf t1 to t5 to at least 2,392 / 0.70 = 3,420 um2 (+39 %, three strip rows as the log already asks), taken from the type interior; move the nearest macro if the depth is not free. Read why monitor_0 fails at 0.47 before the row is cut, since area alone does not explain it. Stop the `OT_CLAND_STRIP_DENS` A/B after its one result.
- Owner: FAM-S81-MISC-R4 (rows), S81-J6-ASSEMBLY-R5 (J8).

### Lever 8. Clock taps: split and balance before pads; watch the no-merge default (S81 42 types measured, QC 9 partial types, KV 12 partial pieces)
- Evidence: TAP-INSERTION advisory (R): S81 insertion max 838 ps against p50 461, skew max 328 ps, 102 taps over 1,650 sinks; QC max 696 ps. t39 input-port hold tracks capture latency one to one (R). KV pv pieces: 12 PARTIAL, 2 BLOCKED, worst 5,825 sinks on a 1,000 tap (R). Canary: section 0.4 (V).
- Root cause: over-loaded taps have late capture clocks; every forwarded or port-launched path into them loses hold by the same amount. Padding 49 to 90 ps per port on t39 is the bounded case; an 838 ps tap is not paddable.
- Fix (P): tap split rows first on the taps over 1,650 sinks (S81 102, QC 58), with `tap_balance_to: slowest`; port padding only for the residue after the split. For sinks banked beside macros (QC 9 types, KV v5 / v6), assign taps by bank. For the canary: bisect `8a2a7b31a97` against `3c2f3758f4c` on hd_turn_a once, and re-baseline only if the kept registers are the cause.
- Owner: TAP-GRID-R5, FABLE-FIX-S81-LEAF-R9 (t39, plan c), FLOW-CANARY-R2 (bisect).

### Smaller items
- S81 leaf plan c: cut 10750 has now hit t32 and then t22, one gate round each. Before gate c, list every lane segment under 1.0 at cuts 10750 and 20000 over all 68 types in one G0 pass and nudge them together (P). Owner FABLE-FIX-S81-LEAF-R9.
- slw_fe_v2 cle312294d: 8 FF hold ends at -3.78 ps on a routed DRC-0 DB; one local ECO (20:30 lever 8, still open). Owner FAM-QC-FEFW-R3.

## 2. Stop list (new or changed; earlier lists stand)

| # | Dead end | Why |
|---|---|---|
| 1 | Treating GRT-0273 as a clock or NDR problem, or changing NDR / clock layer settings for it | 1 to 41 taps per kit; overflow is 49 to 94 % in gcells under 10 tracks, in one bin (V) |
| 2 | More GRT iterations, relaunches or utilisation changes on sle_ctl, leaf t44, hgi_v4, hg_v1p6 as built | Overflow flat or rising between rounds; capacity is missing at the hotspot (V) |
| 3 | Waiting on slw_su_c cl92142dac for routing | Overflow 171 but setup -504 ps (R) |
| 4 | Splitting an over-cap type without its wall or hotspot row | The piece keeps the same low-capacity crossing (V here, R HEAD) |
| 5 | Making bind accept several outgoing lanes on `vo` stations, or keeping v1n unsplit as the answer | One shared crossing fixes bind and the cut budget together (V, R) |
| 6 | Another pv bind on e997b2f7ad71 unchanged | Dies at `expected one outgoing lane` (V) |
| 7 | hgi_v2 or any hg / hgi kit before `lockup_regions` shows in the bound text | Rows had no effect in bind (R) |
| 8 | `OT_CLAND_STRIP_DENS` or other strip settings for kv_leaf t5 | Band is 0.97 full; rows do not add area (V) |
| 9 | Port padding as the first fix for input hold on taps over the sink cap | Hold follows capture latency; 838 ps taps (R) |
| 10 | Reading the canary -17 ps as a closure regression, or re-baselining before the bisect | +109.93 ps left; two candidate commits (V) |
| 11 | Judging a kit generated before 650916ebb262 on its post-TT-repair DB without checking `RESTORE` | Regressed DB was kept (R) |
| 12 | One leaf gate round per cut collision | Same cut line, second type in two rounds (R) |
| 13 | From 20:45: `insertion_ps` raises to release st_a / glue; routing coll_core without legal seats; cb row A cut per type; slw_hc3 rebuilds without a `cw_n3` row | FABLE-PD-QC-2045 |

## 3. Status of the items named in the brief

| Item | Finding |
|---|---|
| S81 MISC t5 band | Confirmed (V): 0.97 on ft0_i / ft1_i; monitor_0 fails at 0.47 for an unread reason. Lever 7 |
| QC coll_core slit seats | Fixed in the model (R): 0 in slits, 0 in core boxes; bind running, no kit yet. Lever 5 |
| KV pv split bind | Confirmed (V): `expected one outgoing lane` on a per-consumer vo leg. Lever 4 |
| S81 leaf plan-c t22 cut | R only: 0.60 at cut 10750, nudge as t32. Smaller items |
| s81_head_cl -17 ps | Confirmed (V); window of 17 commits, two candidates; not a gate failure. Lever 8 |
| QC 66 hops over 405 um | Unchanged in V3p6n, on the V4 carry list (R). Lever 5 |

## 4. Not checked

- Whether each hotspot of section 0.1 is over a macro, in a slit or under PG obstructions: the bins were not overlaid on the macro maps, and no render was viewed this round.
- Non-tap cell counts of the six large kits; leaf t25 and the second sle_ctl and hg_v1p6 kits.
- True total overflow where the report is capped at 20,000 gcells.
- Why `u_cland_monitor_0` fails at 0.47; the result of the `OT_CLAND_STRIP_DENS=2` A/B.
- Which consumer rows of the 15 pv pieces carry the vo legs (only the first bind error was read); the fan-out row was not priced for latency.
- The canary cause: no bisect was run; the commit attribution is inference.
- S81 col, START reach, HEAD and KV hub numbers were not re-measured; they are the lanes' and the 18:57 reviews' numbers.
- failure_breakdown at 21:10 gives row states only (S81 types 45 of 394, HEAD 25 of 26, QC 55 of 127, KV 6 of 56), no technical class, so the classes above come from kit logs.
