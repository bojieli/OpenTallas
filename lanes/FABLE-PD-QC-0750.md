# FABLE-PD-QC 0750: QC N3 type failures, root causes from kit reports

2026-11-18 07:50 PST, FABLE-PD-QC, read-only. Event s29q103S4Q9N3. Sources: autopilot/kit_wave_stages.tsv (91 types with an N3 row), run_route.log / hold_gate.log / tt_setup_measure.log / 5_1_grt.log of the kits on epyc9, epyc8, epyc2, intel1, live containers (docker ps + the /work mount of each), COORD-REVIEW-QUEUE 06:00-07:36. **V** = read in a log or file this round, **E** = estimate.

## Verdict

No N3 type has failed for a design or plan reason yet. Every N3 kit that reached the end of global route (12 of 12) stopped on the same flow error, and 21 more live kits carry the same old file and will stop the same way. Global route congestion is 0 on all 12. Until the old file is replaced in the live work dirs, QC N3 produces no routed result at all.

## 1. Root causes, ranked

### R1 (blocks every route): kits generated before 05:53 still carry the old vclk_measured_hold.tcl. Owner QC-TYPES-R3

- Error (V, 12 kits): `Error: global_route.tcl, 195 OT_VCLK_MEASURED_HOLD: pin-register mean unavailable (samples N missing 0 clocks 2|3|4)`, then `make: do-5_1_grt Error 1`. The wave reported the first ones as "route FAIL FLOW ... OT_LAYOUT_RENDER local_density" (the render line is only the last log line; it is not the cause).
- The fix e1ce3e0b234 (05:49) is right and proven on HEAD: hd_spn_eshim_tx prints `OT_VCLK_MEASURED_CLOCK clk samples 581 mean 385.790` and binds (V). But a kit runs the copy made at gen time, inside its ot-jobs work dir. Failures after the fix landed: sle_sc_v1__cl115da35f 06:19, slw_st_b_v2__pvc2ec5bfb 07:09, slw_sc_v1__cl64543eaf__cl4590432d 07:10, slw_st_b_v1__cl6357f1cc__pv6ace3e48 07:41 (V).
- Failed so far (12, V): sle_sc_v1 x2, sle_sc_v2, sle_sc_v3, slw_sc_v1 x3, slw_sc_v3, slw_hc0__cl1bc59e1c, coll_ftc, slw_st_b_v2__pvc2ec5bfb, slw_st_b_v1__cl6357f1cc__pv6ace3e48.
- Live containers with the old file (21, V, 07:46): epyc9 sle_hc0__cl929603c0 x2, slw_st_a_v1__clfc5867a6__pvdf8e5ca4 x2, slw_st_a_v2__clf4365a62; epyc8 sle_sc_v1__cl115da35f, slw_fw_v1__clf51c11d8__clc7ddab13, slw_st_a_v1__..pvdf8e5ca4; epyc2 sle_st_b_v1__pv0e7b1dcc (+ 2 cbn_q11 containers up since 11-16, see R5); intel1 sle_sc_v1__cl7479a5ec, sle_st_b_v2__clfde1249e, sle_stm_v3, slw_fe_v1__cl95cd1d0c x2, slw_fw_v1__..cl592e3d37, slw_sc_v1 x3, slw_sc_v2, slw_st_a_v1__..pvf82a6c28. All are in 4_1_cts or 5_1_grt.
- The job re-runs 5_1_grt in the same work dir after the error (slw_sc_v1__cl64543eaf__cl4590432d: error 07:10, new flow.sh 5_1_grt 07:21, V), so each one burns another ~1.6 h and ~24 GB to hit the same line.
- Fix: in each live work dir replace vclk_measured_hold.tcl with the rt/current file by copy to a temp name + mv (never sed -i). The diff is self-contained: per-clock sums, and the stop condition drops `ncl != 1` (V, diff of kit copy vs rt/current/tools/die_plan). The file is sourced once at the end of GRT, so a swap before that point takes effect in the running stage. Cost of not doing it: a full relaunch is ~5.4 h per type (gen 01:44 -> GRT end 07:10, V) against ~1.6 h for the GRT re-run already in flight.
- For the dead ones: re-run route in the existing kit (4_cts.odb is there) with the new file, instead of a new attempt from kit_rtl.

### R2 (the two "cause unknown" types): cell gate at enqueue, not a build failure. Owner QC-TYPES-R3, closed

- sle_hc0__cl05696ed1 a3 and slw_st_b_v1__cle6023ec2 a5: placed clean, geom GRT `0 / 0 / 0` total congestion, usage 10.07 % and 8.40 % (V, geom/grt.log). The FAIL was "AUTO-GEOM PASS but enqueue failed rc 1: SPLIT-NEEDED" (rule C density 0.79 and 0.46 cells/um2). Waived by r696 and made advisory by stops_off; both relaunched 06:20 as a4 / a6 and are in 3_3 global place with the fixed vclk file (V).
- The earlier a3/a4 of slw_st_b_v1 had no log beyond gen lint: launch churn, no design signal.

### R3 (structural, 21 types): child hard cores with no signed view and no build row. Owner QC-PLAN-R3 (names the builder), NEEDS-LANE if none

- 21 N3 types sit at prelint LINT-ADVISORY "planned hard core without a signed view" (V): st_a 10, sle_ctl 7, su_c 3, plus sle_su_c. 16 child names (qfd_dv_s8_station_tail1_h15/16/17_*, sta_cland_w1081/1574/259/515_*, sle_cland_w120/w2104, qfd_dv_s5_ctl_repair4_leaf, qfd_dv_s8_tap_bounded, qfd_dv_s8x_btab, qfd_dv_s8x_prog) have 0 rows in the stage table (V), while the counter says QC cores 70/70. These types launch on PROVISIONAL views, so none of them can count until the children are signed. Not checked: whether they are built outside the wave.

### R4 (after R1, measured risk): pre-GRT hold repair spends the setup margin on the sc family. Owner QC-TYPES-R3

- pregrt_ff_hold adds 4,151-12,605 hold cells per type and moves TT setup (placement RC): sle_sc_v1__cl115da35f +19.2 -> -27.6, sle_sc_v2 +44.9 -> -10.1, slw_sc_v1__cl5e017c6f +6.1 -> -17.4, slw_sc_v1__cl63e5a7a2 +1.7 -> -6.1 (V). All still inside -42, before route RC.
- The cells go to the port_in class (517-2,712 endpoints, ws -42 to -153), which R-MINIMAL does not gate; same_tap and cross_tap classes are 0 (V). The 40 ps family margin (r641) is what drives it.
- GRT hold repair adds 0 cells on all 12 while its own number stays negative (-8 to -45 against the 40 ps margin; slw_sc_v1__cl5e017c6f -45.3, slw_hc0__cl1bc59e1c -40.6) (V). If that number is slack minus margin, those two end at about -5 and -1 ps internal hold (E). First routed kit decides.
- coll_ftc: TT setup -46.5 at CTS, tns -758 (V): the only type outside -42 before route.

### R5 (small, flow)

- cbf_q01_s2: gen refuses `FT bit sites rx_flit_serdes_rx,4,258 and tx_up_serdes_up,2,0 snap to one site [8.64, 1296.0]` (V); relaunched 07:06 unchanged, will repeat. Plan row, QC-PLAN-R3.
- cbn_q11__cl5cc92dfe: FAIL PLAN "GRTM mode edge_outline" at place (V); relaunched.
- Duplicate live runs of one type: slw_st_a_v1__..pvdf8e5ca4 x3 (epyc9 x2, epyc8), slw_fe_v1__cl95cd1d0c x2, sle_hc0__cl929603c0 pair is two types. Two cbn_q11 containers on epyc2 run since 11-16 on an old event.
- kit_rtl reset receipts: repaired 07:2x (17 of 130 -> 0); the a2 rows failed at 07:18 before the repair was read, one more relaunch needed.

## 2. Fix order

| # | fix | evidence | owner |
|---|---|---|---|
| 1 | Swap the vclk file in the 21 live work dirs (cp + mv); re-run route in the 12 dead kits | 12 of 12 GRT ends fail on it; 4 after the fix landed | QC-TYPES-R3 |
| 2 | N4 gen must copy tools from rt/current at launch; confirm one N4 kit prints OT_VCLK_MEASURED_CLOCK | kit copy is the file that runs | QC-PLAN-R3 |
| 3 | Name a builder for the 16 child cores | 21 types provisional only | QC-PLAN-R3 |
| 4 | On the first routed sc kit read internal FF hold and TT setup; if setup < -42, set hold_ff_margin_ps per type for sc | setup loss 8-47 ps from port_in padding | QC-TYPES-R3 |
| 5 | cbf_q01_s2 FT site collision row | gen error text | QC-PLAN-R3 |
| 6 | N4.1 stays private until kit k2 is routed and measured | n41d bind 0 errors, LATCHECK 1921/1921; kit not measured | QC-N-OPUS |
| 7 | Kill the duplicate and the 11-16 containers via ot-run cancel | list in R5 | QC-TYPES-R3 |

## 3. Stop list

- Do not relaunch a type from kit_rtl for the vclk error; patch the work dir or re-run route in place.
- Do not read "route FAIL FLOW ... local_density" as a density failure; open run_route.log for the Error line.
- Do not split sle_hc0__cl05696ed1 or slw_st_b_v1__cle6023ec2: geom GRT is 0 overflow at 10 % and 8 % usage.
- Do not start congestion or re-floor work on sc / st_b / hc: 12 of 12 GRT 0 overflow, usage 8-17 %.
- Do not add hold cells for port_in ends beyond the present pass; they are outside R-MINIMAL and cost setup.
- Do not apply N4.1 on top of N4 before one st_a kit is routed.
- Do not count any of the 21 provisional types.

## Not checked

- No N3 kit has a routed (post-DRT) result, so DRC, routed TT and routed hold are unmeasured for the whole event.
- The meaning of the OT_HOLD_BUDGET hold_ws number (slack or slack minus margin) was not read in the Tcl.
- Whether the 16 child cores are built outside the wave; whether the wave already queued new attempts for the 12 dead kits (sle_sc_v2 and sle_sc_v3 were relaunched from scratch at 06:31).
- epyc8 and epyc2 item dirs hold no run_route.log; their state is from the live containers only.
