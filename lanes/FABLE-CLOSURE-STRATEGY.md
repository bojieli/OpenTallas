# FABLE-CLOSURE-STRATEGY 2026-11-17 17:20 PST (1720): delta on 15:20

Reviewer: FABLE-CLOSURE-STRATEGY-1720 (Fable). Read-only, no jobs launched, nothing killed. Technical PD only. HBM parked.
Blocking gates: DRC 0, routed TT setup >= -42 ps, internal reg-to-reg FF hold >= 0 (port hold advisory), die bind + LATCHECK.

Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal, not measured.

## 0. Headline

1. **There is routed data on QC, and it shows one dominant class: internal FF hold after route (V).** Not on N1B (0 of 43 N1B rows are past placement), but 12 kits of the same QC families on the previous event (L2) finished route and sign-off STA today. All 12: DRC 0, GRT overflow 0, NOT SIGNED. All 12 fail reg-to-reg FF hold by -10 to -41 ps on 42 to 456 ends. 3 of 12 also fail TT setup (-62, -72, -165). The same hold class is on the 5 routed S81 svc cores (-5 to -11 ps) and on HEAD. Cause is the recipe: GRT hold repair stops at margin 0.
2. **KV PC / PV kits are at -871 to -1,360 ps TT after CTS and cannot close by route (V).** The worst paths have 0 to 2 gates: a pad-chain or boundary register drives a hard-core pin over 1.7 to 2.1 ns of buffered wire. The pad chain is there (37 stages on the worst PV bit) but placement stacks it and `OT_RELAY_MID` handles 0 groups. The same class at smaller size is what fails QC setup. This is a generator siting fix, not relay rows.
3. **HEAD hd_lep0N has an unaddressed structural path (V).** Post-CTS TT -3,897 ps (-2,872 after repair) on a fault flag that crosses the type unpipelined; 76,299 hold cells (17 % of instances); GRT has run for about 29 h. This kit cannot decide the 367 unassigned nets.
4. **Oversized taps: measured, and tap sink count is not the cause (V).** 45 kits with a CTS tap table: taps of 1,650 to 14,081 sinks land within 50 ps of target in 43 of them. Two kits are hurt: S81 serdes t13 (clk_t42, 554 ps) and QC coll_core (four taps at 536 to 782 ps, spread 552, TT -700). In both the tap's sinks are spread over a large area.
5. **No kit has an `OT_TAP_INSERTION` line.** No die tree carries r622 yet, and failure_breakdown at 17:10 prints none. I used the `OT_TAP_BALANCE` tables, which hold the same per-tap numbers.
6. **Not finished at 17:20:** H17 route-only rerun (iteration 1, 32,530 violations at 80 %), merge_x (GRT), sd9g3 (GRT done, in route).

## 1. Evidence I opened

Job dirs are `<host>:/srv/opentallas-scratch2/claude/ot-jobs/<item>-route-*/work` unless a path is given. `W` = that work dir.

| item | file | result |
|---|---|---|
| QC routed kits, event L2 (12) | `W/signoff.log`, `W/signoff/signoff.json` on intel1, epyc7, epyc8 | all DRC 0, antenna 0, NOT SIGNED. Internal FF hold (`std_min_start.nonport_wns` / reg-start ends): slw_fe_v2__cle312294d -40.6 / 324; slw_hc2 -33.6 / 456; sle_hc2 -32.2 / 208; slw_stm_v1 -28.3 / 212; slw_fe_v1 -26.2 / 104; sle_su_l1 -20.9 / 106; sle_st_b_v2 (2) -18.6 / 194 and -10.3 / 120; slw_sc_v2 -14.1 / 82; slw_fw_v1 -11.4 / 56; slw_sc_v1 -10.2 / 42. TT setup: +20.6, +3.7, -1.2, -6.1, -9.3, -14.1, -24.5, -25.5, then slw_sc_v1 -62.1, sle_su_l1 -72.3, slw_fw_v1 -165.0 |
| QC kit hold recipe | `W/config.mk`; `5_1_grt.log` of slw_fw_v2__cl8537f156 | `OT_HOLD_FF_MARGIN = 0`, `HOLD_SLACK_MARGIN = 5`; GRT hold repair ends at `hold ws 0.06 ... margin 0` |
| QC post-route ECO | `W/eco_*/i1/{variant.env,run_prd.log}` (slw_hc2, sle_su_l1) | every one of the 12 has an ECO dir. slw_hc2: 684 HB4 at 650 capture pins for 456 ends, then ECO route, running about 2 h. sle_su_l1: ECO route at 20,679 violations at 80 % after 1 h 12 min |
| QC worst setup paths | `run/reports/.../6_finish.rpt` | slw_fw_v1: `u_pd3_rd_wi_32.q` -> `u_bout_x_st_a_o/q[30]`, 35 buffers, 0 gates, 938 ps data. sle_su_l1: `u_lpad_flt_su_c_i.q[0]` -> `u_ist_flt_su_c_i__u_lane7_3_0/q`, 33 buffers, 0 gates, 862 ps. slw_sc_v1: `u_cland_collect_rst_n_t13/ready_o` -> port `cland_up_ready[0]`, 22 buffers, 715 ps |
| QC GRT (9 kits with a policy file) | `W/grt_policy.json` | `failed: setup_tt`, TT -68.6 to -136.4 before the route-stage repair; overflow 0 / 0 / 0 on all but cbf_q00 (4 / 2 / 4,864) and slw_su_l1__cla2a78701 (4 / 2 / 46) |
| QC N1B wave rows | intel2 `autopilot/kit_wave_state.json` 17:08; epyc8 / epyc9 item and ot-jobs dirs | 33 rows: 30 running, all at or before `3_5_place_dp`; 3 FAIL at place (2 x MPL-0034 st_a, fixed only in N2B; 1 kit self-containment). No CTS log exists for the event |
| QC N1B pilot cbn_q01__clab6e67f2 | epyc9 `/srv/opentallas-scratch2/claude/qc-types-r3-lane/n1b_cbn_q01/run_route.log` | **dead at 16:15 in `3_4_place_resized`**: `OT_XSTN_STRETCH stretched b_d paths 1 > 0 (heads 1 of 2832 paths)`; before it `OT_XSTN_KEEP u_bound.u_u_fab_u_x_1_2 face W external_nets 1000000 > 20 boundary_reg_um 866 (... plan event needed)`. No lane has posted it |
| QC coll_core (L2) | epyc8 `W` logs `4_1_cts.log`, `tt_setup_measure.log`, `pregrt_ff_hold.log` | taps: clk 20,911 sinks 677 ps (651-766); clk_t6 1,955 at 782 (627-943); clk_t8 6,200 at 615; clk_t7 6,311 at 536; clk_t3 3,461 at 439; clk_t4 3,579 at 257; clk_t5 3,471 at 238. Spread 552 for a 250 target. TT setup -699.7, tns -1.12 M. Hold before repair: cross-tap 4,186 ends at -453.8; 18,477 hold cells; 52 ends left at -17.2 |
| KV HG5 kits after CTS | epyc10 `W/tt_setup_measure.log`, `tt_setup_repair.log`, `pregrt_ff_hold.log`, `run/reports/.../4_cts_final.rpt` | TT setup after repair, placement RC: kv3_pc_v1__cl23f6a148 -1,360.2 (tns -468 k); kv3_pv_v1 -1,019.7 (tns -1.83 M); kv3_pv_v12 -871.1 (tns -2.89 M); kv3_hub_Eo -624.8 (tns -15 k); kv3_io_cor +156.2. Hold cells added before GRT: pv_v1 54,334 of 680,992; hub_Eo 46,152; pc_v1 16,570. pv_v12 before repair: 23,772 ends, cross-tap 7,892 at -217.6 |
| KV worst paths | same `4_cts_final.rpt` | pc_v1: `u_bin_i_idpc_Q_N_y/q[5]` -> core `u_kvpc1`, 44 buffers + NAND2 + NOR2, arrival 2,342 against launch 267. pv_v12: `u_pd37_i_vport_W_N_vo_d2_110.q` -> core `u_pvg3_p2` (kv3_pv_pair), 13 buffers, arrival 1,984 against launch 300 |
| KV pad chain | pv_v12 `W/1_synth_odb.v`; `3_*.log` | `u_pd37_i_vport_W_N_vo_d2_110` has stage flops `r[0]`..`r[35]` + `q` (37 stages). Place log: `OT_RELAY_MID placed 0 relay flops of 0 stations (0 relay groups)`. Wave geom on the same rows: relay_collapse 109 (pc_v1), 133 (pv_v12); r2r 1,649 um / 16,249 pairs and 2,376 um / 8,030 pairs |
| KV kv3_io_cor | epyc10 `5_1_grt.log`, `5_2_route.tmp.log` | GRT overflow 7 / 11 / 501 (M3 313), TT +74.1, hold +2.7; route 47,968 -> 9,480 -> 7,351 -> 943 -> 702, iteration 5 running |
| Tap tables | `OT_TAP_BALANCE` last iteration in `4_1_cts.log`, 45 kits, 6 hosts | see lever 4 |
| HEAD hd_lep0N (NF15d2r1 kit) | epyc10 `W` reports `4_cts_final.rpt` (11-16 10:56 PST), `tt_setup_repair.log`, `pregrt_ff_hold.log`, `5_1_grt.tmp.log` | clk max -3,897.06, tns -2.70 M, period_min 4,730; after TT repair -2,872.08, tns -2.28 M. Worst: `u_cland_coll_i0/u_fault_port/q` -> `u_cland_up_coll_o1/fault_o`, 53 buffers + OR3 + OA21, arrival 4,732. Hold before repair: -451.8 at `u_core.u.g_pp[2].u_pair` (lep_pair pin) and -389.8 on `coll_o1[398]`. After: 76,299 hold cells of 459,525 instances. Reset recovery -105.2 (`g_reset_balanced.u_rstr.root_r` -> `group_r`). GRT started 11-16 12:11 PST, still in its third set of extra iterations (12 of 30) at 17:12 |
| HEAD hd_serdes sd9g3 | epyc9 `/srv/opentallas-scratch2/claude/head-types-r4/sd9g3/gen/hd_serdes/run/logs/.../{4_1_cts,5_1_grt}.log` | `OT_PHY_REGION_ROWS ... 3047 overlapping rows replaced by 0 pieces`; `OT_PG_RAIL_CHECK rows 2624 bad 0 PASS`; taps 400-461 ps (spread 61, target 450); GRT hold -20.2 / 14 ends -> +0.09 with 63 buffers; 263,337 non-tap cells |
| HEAD others | epyc10 / epyc9 | hd_spn_end: DRC 0, TT +25.6, internal hold -5.7 on 1 end, ECO running. hd_mesh at CTS: 83 taps, largest 2,216, all 429-491 for a 450 target |
| S81 svc cores `_mm2` | epyc2 / epyc8 `/srv/opentallas-scratch3/claude/s81-svc-split/build/<core>_mm2/{STATUS,corner_sta.json,work/orfs/config.mk}` | hslice, sml, smr, smc, smd: `done flow=0 sta=0`, DRC 0, GRT overflow 0. TT setup +115.9 / +128.1 / +89.6 (hslice / sml / smr). FF reg-to-reg hold -9.5 (629 pins), -7.0 (240), -6.5 (148), -10.6 (smc), -5.2 (smd). `HOLD_SLACK_MARGIN = 0`. SS setup -199 to -254 (information only). merge_x with pin_regs: no setup violation at CTS, GRT overflow 0, in GRT repair at 17:22 |
| S81 serdes H17 r2 | epyc9 H17 kit `5_2_route.tmp.log` | iteration 0 ended at 88,333; iteration 1 at 32,530 (80 %) at 17:12. No routed TT yet |
| S81 D6z G0 | epyc8 `/srv/opentallas-scratch2/claude/s81-die-r3-e8/d6z/r2/g0/g0_report.json` | 30 errors = 25 `ft_channel_tracks` on 20 types (worst leaf__t22 3,427 bit sites in a 34.56-um channel = 2.17 against 0.7; t2 2.09; t9 1.50) + 5 `cuts`: s_4N_L1 3,750 bits on 4,064 tracks = 0.92 against 0.6; s_0S_L0 0.67; s_0S_L1 0.66 and 0.61; s_6S_L0 0.63 |
| S81 D7z kits | intel2 `~/s81-die-r/build_d7z_i1.log`; intel1 `.../s81-die-r3-i1/d7z/r1/kits/slice_station__t51/gen.log` | bind, LATCHECK 873 / 873, PRE pass. **slice_station__t51 GEN_RC=1 (17:17)**: `macros have LEF but no timing liberty: s81p_slice_station__t51_ot_s81_station_t51_native_w` |
| failure_breakdown | intel2, 17:10 | technical rows. S81: macro placement 2 (kv_leaf t1, t3), congestion 1 (phy__t1), place error 1, hold after CTS 1, route held 14, c1x_C t7 / t9 GRTM edge_outline. QC: macro placement 2. KV: CLAND ring band 1 (hroot), route error 1 (io_cor_v1), SPLIT-NEEDED hub_Wo 528,113 cells. HEAD: none |

Not opened: the N2B tree, rs8b gate result, lep_pair signed DB, kv3_sys_c rebuild, D21b gate, the serdes generator port, phy__t1, any die GRT / die STA run.

## 2. Levers, ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | all | reg-to-reg hold margin at GRT instead of a post-route ECO on every kit | every routed kit: 12 of 12 QC, 5 of 5 svc cores, HEAD | WAVE-FLOW-R2, QC-TYPES-R3, S81-SVC-SPLIT |
| 2 | KV, QC, HEAD | site pad / relay chain stages along their source-sink line | KV PC + PV families, QC fw / su / st_b / sc | WAVE-FLOW-R2 (generator), FABLE-FIX-KV-HG, FABLE-FIX-QC-N |
| 3 | HEAD | hd_lep0N fault-flag path and hard-core hold before NF15f releases it | hd_lep0N, then hd_mesh | HEAD-PLAN-R4, HEAD-TYPES-R4 |
| 4 | QC, S81 | split taps by sink extent, not count: coll_core, serdes clk_t42 | coll family, 11 serdes | FABLE-FIX-QC-N, S81-DIE-R3 |
| 5 | S81 | D6z col release; D7z t51 view; the 5 baseline cut errors | 78 col now, 20 ft-channel types | S81-DIE-R3 |
| 6 | QC | cb family: cbn_q01 N1B pilot dead at placement | cb types (count not read) | FABLE-FIX-QC-N, QC-TYPES-R3 |
| 7 | S81 | svc shell with (a)-(d); cores are closed | svc family | FABLE-FIX-S81-SVC2 |
| 8 | S81, HEAD, KV | PHY types: H form port, sd9g3, kv3_sys_c | 11 serdes, hd_serdes, kv3_sys_c | S81-SERDES-GEN, HEAD-TYPES-R4, KV-R3 |

### Lever 1. Internal hold after route (all dies)

Evidence (V): section 1 rows 1-3, svc row, HEAD rows. 18 of 18 routed kits read today end with reg-to-reg FF hold between -3 and -41 ps. HEAD lep_pair needed three ECO rounds for 7 ends (R).
Root cause. The kit repairs hold at GRT to margin 0 (`OT_HOLD_FF_MARGIN = 0`; svc `HOLD_SLACK_MARGIN = 0`) on GRT parasitics. Detailed-route RC then moves the zero-logic station and relay pairs by tens of ps. The worst pairs are station chains on two taps (`u_ft_x_fw_fe_o_1/q[80]` -> `_2/q[80]`, hold pair skew 109 to 343 ps). Each kit then takes a post-route pass of HB4 insertion plus ECO route (2 h and more; sle_su_l1 re-opened 20,679 route violations).
Fix.
1. WAVE-FLOW-R2: reg-to-reg FF hold margin at GRT repair = 40 ps for QC, KV and HEAD type kits (covers the measured worst -40.6), in the die `item_env`; ports unchanged. S81 col already runs 10 (R): compare with its first routed number and raise if it lands negative.
2. S81-SVC-SPLIT: 15 ps on the core recipe, then rerun route on the five cores from their GRT DB (worst measured -10.6).
3. QC-TYPES-R3: the 43 N1B rows are still in placement. Put the margin in before they reach GRT (new `config.mk` by copy and rename, never an in-place edit of a running stage).
4. Check on the first kit with the margin: HB4 count, TT setup on the padded ends (they have no logic, so setup room is large), routed internal hold >= 0 without an ECO.
The post-route ECO stays as the fallback for a few ends; it should not be the normal path.

### Lever 2. Collapsed pad and relay chains (KV, QC, HEAD)

Evidence (V): section 1 KV rows and QC setup rows. Routed QC setup fails are all one path shape: register -> 22 to 35 buffers -> register or port, no logic.
Root cause. The count-aligned pad chains (`u_pd*`, `u_lpad_*`, `u_bin_*`) are in the netlist but are not handed to the relay siting step: `OT_RELAY_MID` reports 0 groups. Global placement stacks the stages (relay_collapse 109 to 517) and leaves one hop of 1.2 to 2.4 mm. The cb kits already do the right thing for one chain class: `OT_NK_CHAIN ... max_hop_um before p50 435 p90 889 max 963 after p50 114 p90 126 max 127` (V, cbn_q01 pilot log).
Fix.
1. WAVE-FLOW-R2: in the generator, register every pad chain whose source and sink are more than one hop apart as a relay group; stage i of N is placed at i / N on the source-sink line, held through placement. No RTL change, no latency change. Read after it: max hop per chain in the place log, TT setup after CTS.
2. FABLE-FIX-KV-HG: where a chain has fewer stages than the distance needs (bin register direct to core, as on pc_v1 `u_bin_i_idpc_Q_N_y` -> `u_kvpc1`), that bus needs stages in the plan (D22 row, latency row). Count these buses first; do not add relay rows where a 37-stage chain already exists.
3. KV PC / PV kits now in GRT are measurement only (overflow map, hold-cell count). No sign-off can come from them and none should be relaunched unchanged.
4. FABLE-FIX-QC-N: same step on QC fw, su, st_b; sc needs the `ready_o` port path (output delay 166.6 ps leaves 416 ps for a 715 ps wire): move the collect flop to the port face or add a face register.
5. The hold-cell load follows from the same thing (pv_v1 54 k cells, 8 %): cross-tap pairs between stacked stages. Re-read `hold_cells` after the siting fix before touching taps.

### Lever 3. HEAD hd_lep0N

Is a die-level structural risk unaddressed? **Yes, this one (V); I could not confirm whether rs8b / NF15f changes it.**
Evidence: section 1 hd_lep0N row. The -3,897 ps path is a fault sideband from the `coll_i0` landing to the `up_coll_o1` landing with two gates and 4.63 ns of wire. tns -2.28 M after repair says it is not one path. 17 % of instances are hold cells, with the worst pre-repair hold at the `lep_pair` hard-core pin (-452) and at `coll_o1` output registers (-390).
Fix.
1. HEAD-PLAN-R4: before the NF15f apply releases hd_lep0N, read `4_cts_final.rpt` of the dry-gen or first kit for (i) the `u_fault_port` -> `fault_o` group, (ii) hold at `g_pp[*].u_pair`, (iii) tns. If (i) is still there, the fault flags get relay registers along the landing path (about 6 stages for 4.6 ns; status signal, no lane latency), as a plan row.
2. HEAD-TYPES-R4: the kit must bind the signed KCRED 28 lep_pair view with its measured clock insertion, so the pair pins sit in their own tap group at that insertion (same rule as S81 svc (b)). -452 ps at a hard-core pin is an insertion mismatch, not a data problem.
3. The running NF15d2r1 GRT (29 h) is not a verdict on the 367 unassigned nets in x 880-1160 and 1230-1472: its netlist carries 76 k hold cells and unrepaired -2.9 ns paths that load the same windows. Decide the 367 on the NF15f kit.
4. hd_mesh (NF15d2r1 kit) at CTS looks sound (taps 429-491). hd_serdes sd9g3: 3,047 rows removed with 0 pieces put back; placement and GRT went through, so read routed TT and the DRC count when it ends, and compare cell density with sd9f.

### Lever 4. Tap size (answer to "do oversized taps hurt")

Evidence (V), 45 kits with a tap table (QC 33, KV 12 incl. hubs, HEAD 5 separately at target 450):
- Taps over 1,650 sinks in 30 kits. Mean insertion of those taps: 234 to 278 ps for a 250 target. Examples: sle_hc2 `clk` 13,638 sinks at 181 (167-263); kv3_hub_Eo `clk_t49` 14,081 at 262 (248-289); kv3_pc `clk_t4` 9,086-11,598 at 267-294; slw_su_l1 `clk_t8` 7,031 at 235.
- Taps more than 50 ps over target: 1 large tap in 2 kits (kv3_pc, max 381) against 3 to 24 small taps in 20 kits. The worst single insertions are on small taps (kv3_pv_v12 505, cbn_q11 497, kv3_pc_v1 474).
- Hurt: coll_core (above) and serdes t13 `clk_t42` 6,502 at 554 (R, 15:09). In coll_core `clk_t6` with 1,955 sinks is the worst tap (782), while `clk_t4` with 3,579 lands at 257.
Root cause. Insertion follows the area the tap's sinks cover (coll_core fill 0.066; serdes `u_enc` group pinned to one tap), not the sink count.
Fix.
1. S81-DIE-R3: keep TAP-GROUP-CAP-1 for serdes (u_enc group dropped, cap 1,700) (R). Do not extend the 1,700 cap to other families.
2. FABLE-FIX-QC-N: coll_core tap split by extent: `clk`, `clk_t6`, `clk_t7`, `clk_t8`, `clk_t3` each cut so that no tap's sink box is larger than the box of `clk_t4` / `clk_t5` (plan row for N2B or the next event). coll_core's route is not worth reading before that.
3. KV: 47 of 52 taps over 1,650 sinks needs no re-floor; the 10 KV kits with large taps balance at CTS. KV's clock problem is cross-tap hold between stacked chain stages (lever 2).
4. Per-tap criterion for plan owners (P): split a tap when its `OT_TAP_BALANCE` mean is more than 100 ps over target after the last iteration.

### Lever 5. S81 die

1. D6z (R: bind, LATCHECK, PRE pass; apply about 18:15): the 25 `ft_channel_tracks` errors are 20 types at 0.73 to 2.17 of a 0.7 limit, covered by the D7 hold (V). Releasing 78 col types on it is sound. Add lever 1's margin check to the first routed col kit.
2. **Unaddressed: the 5 `cuts` errors sit in the accepted baseline (V).** s_4N_L1 carries 3,750 bits on 4,064 tracks (0.92). That is a die-level routing statement, and neither D6z nor D7z changes it. S81-DIE-R3: run the die GRT prototype on the s_4N_L1 and s_0S_L0 / L1 segments (or show the track count excludes layers that are in fact free) before the event after D7z. A 0.92 cut found at die GRT costs a floorplan event.
3. D7z: slice_station__t51 kit generation fails on a missing liberty for the `native_w` core view (V, 17:17). The repoint covered `native_e` only. The view needs its lib (same r1116 archive export) before D7z's kit stage can pass; t22 and t34 are not affected by this error.
4. Still without a fix on any event: c1x_C t7 / t9 `GRTM edge_outline`; kv_leaf t1 / t3 MPL-0041 until D6z applies.

### Lever 6. QC cb family

cbn_q01__clab6e67f2 on N1B stopped at placement on its own siting check (V): one b_d buffer tree longer than 3 times its direct distance, next to an xstn (`u_x_1_2`, face W) whose output leaves across the tile (866 um to the boundary register). The L2 variant `cbn_q01__cld9ff4c40` passed this stage and is in GRT, so compare the two kits' xstn sites before calling it an N1B effect. FABLE-FIX-QC-N: read the stretched head (the log names 1 of 2,832), then either re-site that xstn at its face in the plan or register the crossing output. The tap[0] pad acceptance (TT >= +60, hold >= +50 at four pins) has no data until this kit places.
N2B: st_a MPL-0034 (2 types) unchanged since 15:20.

### Lever 7. S81 svc

Cores are done as a design question (V): 5 routed, DRC 0, TT +90 to +128, overflow 0; merge_x with pin registers has no setup violation at CTS. Open on cores: hold -5 to -11 (lever 1) and merge_x route. No outline or pipeline change is supported by these numbers. All remaining risk is the shell: out_w keep, hcore tap group at 329-376 ps, per-region reset stages, ring macros (R, in the form; none built). First shell CTS must show: load-stage flops per tile 256 x 4 (not 0 / 0 / 0 / 1024), hcore pair skew, recovery, ring max_delay.

### Lever 8. PHY types

- H17 route-only: not finished. Its trajectory matches the E1 proof (97,585 -> 18,313 at iteration 1) (V / R).
- S81-SERDES-GEN has not posted since 15:20 (V); the 11 serdes types have no generated form until it does.
- kv3_sys_c: rebuild on r620 pending (R).

## 3. Stop list (changes; the 15:20 list otherwise stands)

1. Treating the post-route hold ECO as the normal path: 18 of 18 kits need it today.
2. KV: relaunching PC / PV kits unchanged; relay rows in D22 for buses that already have a pad chain; tap splits on the 47-of-52 count.
3. QC: routing coll_core before its taps are split; reading "no N1B data" as "no QC data"; a second cbn pilot before the xstn stretch is read.
4. HEAD: reading the 29-h hd_lep0N GRT as the verdict on the 367 nets; releasing hd_lep0N on NF15f without the CTS read in lever 3.
5. S81: counting the 5 baseline `cuts` errors as harmless; outline or pipeline changes on svc cores; waiting for H17 before the generator port.
6. All: a tap gate or cap from sink count; a family-wide GRT derate (unchanged).

## 4. Corrections to the 15:20 report

1. **"QC and KV have no measured failure class because nothing has routed" was wrong for QC and incomplete for KV.** 12 QC kits finished route today on L2 and KV kits had post-CTS TT numbers from 14:35 on. The 15:20 review read the wave state and not the job directories.
2. **15:20 lever 6 proposed splitting taps at about 1,650 sinks wherever they pair with other taps.** The data do not support a count: 43 of 45 kits balance taps up to 14 k sinks. Extent is the variable.
3. **15:20 lever 3 item 1 said the 16 k KV pairs would need relay rows in the plan.** The pad stages exist on the worst PV bus; the first fix is siting.
4. 15:20 headline 1 (svc cores dead at CTS) is superseded: the recipe fix worked, 5 cores routed.

## 5. Not checked

- Whether the NF15f / rs8b hd_lep0N netlist still has the fault-flag path and the lep_pair hold.
- How many KV buses have a pad chain and how many go bin register direct to core (lever 2 item 2 depends on it). I counted one PV bus and one PC bus.
- That a 40 ps GRT hold margin closes routed hold without an ECO; it is sized from the measured worst case, not tried.
- Whether the QC L2 routed numbers carry over to N1B kits unchanged (N1B adds lockup rows and one slot move; same families).
- Buffer counts in section 1 are from report lines (clock buffers excluded by halving the launch / capture lines); they are within a few cells.
- Internal versus port split of hold on hd_spn_end beyond the one reg end; sd9g3 routed result; H17 routed TT; merge_x routed STA.
- The `cuts` check's track model (which layers it counts).
