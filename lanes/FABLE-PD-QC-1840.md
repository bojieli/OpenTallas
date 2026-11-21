# FABLE-PD-QC-1840: QC V1 structural review, in parallel with its bind (2026-11-20 19:25 PST)

Read-only. No job launched, cancelled or signalled. V = verified by me today on the named file, R = reported by another lane.
V1 = epyc9 `/srv/opentallas-scratch2/claude/qc-plan-r6/v1/p_h.json` (plan sha aeae20148627, base ph8). Bind `b_n4` on rt/current with
`r8_v1a.json`: strict errors 0, LANE_ASBUILT 1921/1921 PASS (V, `b_n4.log`, `b_n4.rc` = 0). The q3 errors (TYPE_SPLIT, head-pad PARAM, EMIT tile_id) are not on this base.
A4 evidence = intel2 `autopilot/kit_wave_state.json` 18:39 + each kit's `run/logs/.../3_*.json`, `run/reports/.../3_resizer.rpt`, `3_detailed_place.rpt`, `4_cts_final.rpt`, `geom/placed_scan.json`.
My outputs: epyc9 `/srv/opentallas-scratch2/claude/fable-pd-qc-1840/knee300.tsv` (knee replay of V1 at 300 um).

## 0. Headline

1. V1 binds clean and fixes the three kit stops it was written for (st_a packed bank, su_c / sle_ctl knee, su_l core contract, hc param split). 15 + 3 + 1 FAIL rows can relaunch.
2. V1 is still a 405 um plan. `budgets.ft_station_max_um` 405, `reset.hop_um` 405. Over 300 um in V1 (V): 523 of 921 per-bit chains, 89 of 188 routed station rows (27 over 405), 212 of 267 ft slots (0 over 405).
3. V1 does not fix the class that dooms the cb family. 11 of the 13 held cb rows have detailed-place WNS -1.3 to -8.6 ns on one class that V1 leaves unchanged.
4. Of the running rows, one is measured unable to sign (N46C cbn_q00__cldbcda913, CTS -1107 ps). No A4 row in the route queue is below -300 ps at place.

## 1. The V1 rows

| row | what I checked (V) | result |
|---|---|---|
| st_a two-stage (11 types) | rs_s0 / rs_s1: 2 stages x 515 sites each. Same-site 0, footprint overlap 0, against relay_sites 0, inside a hard core or halo 0, outside the outline 0. Stage-to-stage leg max 287.3 / 300.0 um. | PASS. Open (R, R6 handoff): 4 control bits per type fan out 506 to 524 um; rs_s1 25 to 61 bits at 300.2 um. Same types still have x_fe_o 375.8 um (2 stations) and x_ctl_o [388, 140] um. |
| cross-row overlap | above, all exact rows of each type on one map | 0 on 11 types |
| b_hw_hc2_o at 6 | knee replay: 268.47 um | PASS. Other sle_ctl__cla4f6f12f chains (V): x_su_l1_i 397.08 (1 station), x_su_l0_i 391.07, x_hc3_i 384.72, x_hc2_i 383.47, b_hw_hc3_o 337.0. x_su_l1_i is 6 um under the 403 kit stop. |
| su_c x_sc_o | 3 stations on 3 types, 269.8 um | PASS. 8 to 12 other chains per su_c type at 311 to 365 um. |
| su_l parent_budget | 12 taps on 3 types changed `budget_owner` SIGNED -> parent_budget (early tap 143 to 176 ps TT), nothing else in the type | Form change only. Four sibling types still carry SIGNED `budget_owner` on 4 taps each (slw_su_l0__cl76fb247e, slw_su_l0__cl1e5219ea, sle_su_l0__cl086d85ba, sle_su_l1__clc6d66f5b). They have no live wave row; a regen would stop at the same `core_clock_contract` line. |
| sle_hc0 split (6 bases, 12 clones) | each base has 0 partitions left; clones hold 2+2, 1+1, 3+1, 1+1, 5+1, 1+5 partitions; clone pairs differ in module, note, param_set (N_PAD 1 / 2) and clock only | PASS. slw_hc3__cld86a7ad4 clones have identical clock blocks, the other five pairs do not: confirm that is intended. |
| cb* reset_leg | 6 of 17 cb types have `reset.inst_taps` (4 rows each, legs 744 to 1523 um -> 77 to 133 um). cbn_q11__cl5cc92dfe keeps one leg of 378.8 um (u_ist_bc_o33_1, needs a local tap). | 11 cb types have no row: cbf_q00 x2, cbf_q00_s2, cbf_q01, cbf_q01_s2, cbf_q11, cbn_q00__cld7bf7197, cbn_q01 x3, cbx_q10__cl94a12200_h. Their A4 kits show the same leg at 1228 to 1845 um. Rows are tap indices of the A4 tree (R6 note); the V1 kit must confirm them. |
| coll_ftc pin registers | no row in V1 (R6: land-ring hold_mux captures, check counts a cone over 6 cells). A4 a5: pin_unreg 21, pin_reg_max 497 um, place WNS -171 ps on fclk_in_tl_st_wi_i -> cland ring. | Agree with no bus-splitting register. Stays open as a checker-class item, not a V1 blocker. |
| q3 remnants | b_n4 strict 0 | gone |

### Hops over 300 um left in V1, by family (V)

- cb, routed rows: bc_i00 / bc_i10 / bc_i30 have ONE station on 1,225 to 1,271 um: legs [634, 637], [614, 611], [634, 628] (cbf_q00 x2, cbf_q00_s2, cbn_q00 x3, cbx_q10 x3). nb_i12 legs [418, 415, 415, 411] (cbf_q01, cbf_q01_s2, cbn_q01 x3). 27 routed rows are over 405 um, all cb or slw_stm flt_o (544 / 536 / 548, 2 stations).
- Slice per-bit chains: fw arl / art 393.0 (2 stations, needs 4); fw_v1 x_st_b_o 393.1; su_l0 x_su_c_p1_o 383.5, x_sc_o 383.5; su_l1 x_su_c_p1_i 377.0; st_a x_fe_o 375.8; st_b x_fe_o 334.8.
- The knee tool reports 6 chains over 403 (sle_fe_v1 arv_wi 584.9 / arm_wi 506.5, slw_fe_v2 arv_ei 559.3 / arm_ei 530.0). These are 1-bit rows with a bin at 1/3 and a station at 2/3 (3 legs of about 275 um); the A4 kits of these types placed. Tool and kit disagree on this row form; not a V1 stop.

### Rows most likely to fail at place or CTS on V1

1. All cb types (17). Section 2 class A. V1 changes only reset taps on 6 of them.
2. sle_ctl__cla4f6f12f. Section 2 classes C and D. The hc2 fix does not touch its worst paths.
3. st_a (11). First build of the two-stage bank; the 506 to 524 um control fan-out is one hop.
4. coll_core. Unregistered memory read, -1054 ps at place, unchanged.

## 2. The held rows (19 ROUTE-HELD on A4; reason on every row is WAIT-VISUAL, not timing)

Place WNS below is resizer / detailed place, ps. CTS has not run on any of them.

| row | resizer | detailed | worst class | V1 |
|---|---|---|---|---|
| cbf_q00__cl1b5a6458 | -517 | -3267 | A, B | no change |
| cbf_q00_s2 | -683 | -3272 | A, B | no change |
| cbf_q01 | -296 | -418 | B (L) | no change |
| cbf_q01_s2 | -296 | -1523 | A | no change |
| cbn_q00__cl622f65d2 | -296 | -3213 | A | B fixed, A open |
| cbn_q00__cld7bf7197 | -300 | -3272 | A | no change |
| cbn_q00__cldbcda913 | -298 | -3228 | A | B fixed, A open |
| cbn_q01__cld9ff4c40 | -296 | -8639 | A | no change |
| cbn_q11__cl49ae4555 | -296 | -2004 | A | B fixed, A open |
| cbn_q11__cl5cc92dfe | -364 | -2002 | A, B | B fixed but 1 leg 378.8, A open |
| cbx_q10__cl89936551 | -296 | -1268 | A | B fixed, A open |
| cbx_q10__cl89936551_h | -851 | -1496 | B | B fixed |
| cbx_q10__cl94a12200 | -296 | -1266 | A | type not in V1 |
| coll_core | -1054 | -1171 | E | no change |
| sle_ctl__cla4f6f12f | -262 | -363 | C, D | hc2 knee only; C, D open |
| sle_ctl__cl372cea1c, cl503337ff__padE0, __padE4, cl67434795__padW5 | -288 to -395 | -428 to -528 | C, D | types merged away in V1 |

Classes (V):

- **A. Tile link, last station to pin capture, across the tile macro.** `u_d<N>_u_t_x_y_{n_y_sg1,t_out}.q -> u_pc_nk_u_t_x'_y'_{n_a,n_b}.q`. cbn_q00__cl622f65d2: FF QN 116.5 fF, INVx1 116.0 fF, slew 2861 / 3831 ps, slack -3213. The same class after CTS repair on the N46C kit of cbn_q00__cldbcda913: BUFx12f into 122.4 fF, 1078 ps of wire, slack -1107, 83 violating endpoints, GRT repair starts at -925. The tile macro is 457.9 x 1157.8 um and takes no buffer. These chains and the pc_nk registers have no site in `relay_sites` (the cb types site only u_d#_u_fab_*_a_d, u_st.b_d / tap_d / cap and u_bin_bc_i). auto_geom on the 13 cb rows: relay_collapse 67 to 1159, channel_v 1.85 to 3.56 x capacity, r2r 1206 to 1845 um.
- **B. Reset leg, form R.** `u_rrl_* -> u_u_fab_u_x_*.u_st.g_seg cnt / run`, 1206 to 1845 um, 15 to 22 buffers. This is what RESET-RELAY-GEN rows fix. On N46C cbf_q11 the class is -579 at place and the kit is +66 after CTS, so B alone does not doom a row.
- **L. Lockup latch into an early-tap core pin**, `u_lk_nk_*_n_b DLATCH_N -> u_tXY/n_b`, exactly -295.8 on 9 rows. Ideal-clock artefact: N46C cbf_q11 and cbn_q01__cld9ff4c40 show it at place and are +66 / +45 after CTS. Do not count -296 as a place failure on cb rows.
- **C. ft landing far from its pin.** `cws2_i[388] -> u_cland_cws2_i/d`: input delay 245, five buffers 250 ps, fall-edge capture required 237. Zero wire would still be -8. cl_cws1_i sits 153 um below the N-face entry. N46C sle_ctl__cl67434795__padW5 after CTS: -231.
- **D. Reset into a hard core.** `u_rrl_234 -> u_u_tap/rst_n` (qfd_dv_s8_tap_bounded): 447 um, 13 buffers, -232 to -395. `reset_leg_plan.py` skips macros, so no row can appear.
- **E. Unregistered memory read.** coll_core `u_coll.g_sring[4].u_m -> out_data[495]`, -1054. Same form at -201 on slw_st_b_v1__cle6023ec2 (`u_scale_wait.u_m.g_bank[0].u_m -> g_sc[0].u_mul`).

Count: V1 fully fixes 1 of 19 (cbx_q10__cl89936551_h, if the tap rows hold). 5 rows retire with their type. 13 stay open: 11 on A, coll_core on E, sle_ctl__cla4f6f12f on C and D. cbf_q01 has only B and L and should be released to CTS as it is.

## 3. The running rows

Live QC rows at 18:39: 49 A4 + 29 N46C + 1 N46R3 in the route queue (most still waiting for admission; only 6 have a CTS result), and 9 A4 in the wave.

- **A4 route queue (49):** none below -300 at place. Worst resizer WNS: slw_st_b_v1__cle6023ec2 -201 (E), sle_sc_v1__cl115da35f -188, tt_ctlm -173, coll_ftc -171, slw_sc_v2 -134, slw_hc1__cl68f9248e__cle683a076 -131. 32 of 49 are at -45 or better. No knee stop. None is doomed. Nine are on types whose V1 row differs from A4 in ft_slots or clock only (sle_sc_v1__cl7479a5ec, sle_sc_v2, sle_sc_v3, slw_fe_v1 x3, slw_fe_v2 x2, slw_fw_v1__clf51c11d8__cl592e3d37) and four are on types absent from V1 (slw_fw_v1__cl51d45468, slw_fw_v1__clf51c11d8__clc7ddab13, slw_stm_v1__cl05fc43f7__cl2086fa2c, __cl389df4e9); any-plan sign-off still counts, keep them.
- **N46C / R3 queue (30):**
  - cbn_q00__cldbcda913 a1 (intel1, 24 h): CTS -1107 on class A, GRT repair -925, last log write 7.2 h before my read. Measured unable to sign.
  - cbx_q10__cl94a12200_h a4 (epyc9): place -836 / -2052, class B, no CTS yet. Not proven; B recovered at CTS on cbf_q11.
  - sle_ctl x5 (cl372cea1c, cl503337ff__padE0 / E4, cl67434795, __padW5): place -366 to -470 on C and D; the one with CTS is -231. Cannot reach -42, but above the -300 cancel line. Four of the five types do not exist in V1.
  - cbf_q11 a2 (+66 CTS, hold -71) and cbn_q01__cld9ff4c40 a1 (+45, hold -74) are the best cb rows on the die. Keep.
- **A4 wave (9):** cbf_q00__cl870de686 -377, cbf_q11 a3 -377 / -690, cbn_q01 x2 -296 (L), cbx_q10__cl94a12200 a9 -296 / -1266, native59 -44; three have no place log yet. cbx_q10__cl94a12200 has two live attempts on the same event (a9 RUNNING, a10 ROUTE-HELD).

## 4. Root causes

1. cb types have plan sites for the fabric and the face banks but none for the tile-link station chains and pin-capture registers, and their face rows are sized for 405 to 637 um legs. Placement collapses the chains; the last hop crosses a 458 um macro with no buffer site.
2. The reset-leg tool covers soft instances only. Hard-core reset pins (sle_ctl u_u_tap) and 11 of 17 cb types have no row.
3. Two ft landing cores in sle_ctl sit 150 to 200 um off the face with a half-cycle capture and a 245 ps input delay.
4. Memory reads feed logic directly in coll_core and st_b u_r6.
5. V1 scope was the kit stops. The 300 um pass (1600 fix 6) is not in it.

## 5. Fix list, ranked

| # | owner | fix | evidence | check |
|---|---|---|---|---|
| 1 | QC-PLAN-R6 | cb family: site the tile-link chains and u_pc_nk registers (`relay_sites` or station rows) in the channel beside the destination pin, last hop under 300 um and not across a tile; raise bc_i00 / bc_i10 / bc_i30 from 1 to 4 stations and nb_i12 from 3 to 5. +cycles are pre-approved. | sec 2 A; sec 1 hops | one private cbn_q00 kit to CTS: class A endpoints 0, relay_collapse 0 |
| 2 | RESET-RELAY-GEN-R2 | Rows for the 11 cb types without `inst_taps`; a local tap for cbn_q11__cl5cc92dfe u_ist_bc_o33_1; extend form R to hard-core reset pins (sle_ctl u_u_tap). | sec 1, sec 2 B, D | `reset_leg_plan.py` legs over 300 = 0 on 17 cb types + sle_ctl |
| 3 | QC-PLAN-R6 | sle_ctl__cla4f6f12f: cl_cws1_i / cl_cws2_i at the N face (`cland_face_home_types`), and re-derive the 245 ps input delay against the fall-edge capture. | sec 2 C | place slack on fclk_in_cws2_i >= 0 with zero-wire margin > 0 |
| 4 | QC-PLAN-R6 | Registered reads: coll_core g_sring -> out_data; st_b u_r6 scale_wait bank -> multiplier. | sec 2 E | resizer WNS on those endpoints >= -42 |
| 5 | QC-PLAN-R6 | st_a: last-stage copies for the 4 control bits (506 to 524 um); one v1 + one v2 proof kit to place before volume. | sec 1 | worst leg <= 300; place passes the packed-bank line |
| 6 | ADOPT-CENSUS-1800 | Event census rows: per-type count of station rows / chains over 300 and over 405, cb types without tile-link sites, cb types without `inst_taps`, SIGNED `budget_owner` taps. Reconcile `istation_knee.py` with the kit on the bin + 1 station row form. | sec 1 | census on V1 reproduces 523 / 89 / 27 / 11 / 16 taps |
| 7 | QC-PLAN-R6 | Next event: per-bit chains 300 to 403 (fw arl / art 2 -> 4, su_l, su_c, st_a x_fe_o 2 -> 3, sle_ctl x_su_l1_i 1 -> 2 first: it is 6 um under the kit stop). | knee300.tsv | knee tool at 300 |

Rows 1 to 5 fit V1 only if they bind before the 09:30 cut; otherwise V1 ships as it is (it unblocks 19 FAIL rows) and rows 1 to 4 lead the next event.

## 6. Stop list

- Do not release the 11 class-A cb rows to route on A4 inputs after their visual verdict: cbf_q00__cl1b5a6458, cbf_q00_s2, cbf_q01_s2, cbn_q00 x3, cbn_q01__cld9ff4c40, cbn_q11 x2, cbx_q10__cl89936551, cbx_q10__cl94a12200.
- Do not relaunch those cb types on V1 for volume before fix 1; one proof kit only.
- Cancel candidate under the owner rule (>3 h, measured, setup < -300), for the wave owner, exact unit only: N46C cbn_q00__cldbcda913 a1 on intel1. I cancelled nothing.
- Drop one of the two live cbx_q10__cl94a12200 attempts (a9 / a10); the type is not in V1.
- Do not cancel on -296 alone (class L), on class B alone, or on detailed-place WNS alone outside class A.
- Do not cancel any of the 49 A4 route-queue rows, cbf_q11 a2 or cbn_q01__cld9ff4c40 a1.
- Do not add a pin register on the 20 coll_ftc ring bits.
- No die, outline or core-shape change is needed for any row here.

Left behind by this review: `~/.fable_col_1840.py.tmp` and `/tmp/in_<host>.tsv` (under 10 kB each) on epyc2, epyc7, epyc8, epyc9, epyc10, intel1.
