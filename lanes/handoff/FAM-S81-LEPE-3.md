# FAM-S81-LEPE-3 handoff (11-21 ~06:50 PST)
Successor of FAM-S81-LEPE-2 (read lanes/handoff/FAM-S81-LEPE-2.md for the proof9 form, K rows, bench results).
Representative dsdv_slice_lepe_mu_LP__t2. Plan rows go to S81-J6-ASSEMBLY-R3 (J7).
## State
- J6 wave place LP t2 (epyc8 pid 1647699) rc=0 14:41 UTC; published kit-wave/dsdv_slice_lepe_mu_LP__t2/place-run. 3_place.odb sha 282620af copied to epyc10 p9/in/j6_3_place.odb; FF dump p9/in/j6_pos.tsv (5502 rows, dumpj6.sh via ot-run).
- prepare9.sh ran: P9_READY (MV_RX2_OK 5, KRD applied 8 / bound 9, SITES9 roq 1104 rid 1103). Kit diff vs wave kit: config.mk + run_kit.sh + flow_tag IDENTICAL; only istations.tcl, macro_place.tcl, lep RTL, bound.sv, kit_relay_depth.json, .keep_stage_odbs differ (the intended overlays).
- proof9 route: ot-run unit oth-ubuntu-3163850-1795272168 on epyc10 (run9.sh = run_kit.sh k/<T> route 72 16), log /srv/opentallas-scratch2/claude/fam-lepe/p9/run9.log, kit /srv/opentallas-scratch2/claude/fam-lepe/p9/k. Waiter: ot-wait on that unit.
## Next
- Read post-hook (cts_read.py / 4_cts_final post-hook), GRT, TT setup classes (rd_out->rid, ro/t_host, li) vs J6 wave baseline. If rd_out classes stay < -42: split-register rid/mwd form (see LEPE-2 handoff).
- If it signs: rows (K +3 ro/t_host/t_kd/mu_c, ri +2 vs J6, li +1, rx2 bank move, FIRM sites) to S81-J6-ASSEMBLY-R3; signed export needs a src_manifest rebuild or plan-lane carry.
- lepe_mu_C t1 split rows (LC-S1 / LC-G1 xg +90 um) are with S81-J6-ASSEMBLY-R3; J7a (05:56) excludes Layer C/D splits; follow up they land in J7.
- Old proofs 7/7b/8: evidence only, do not relaunch.
## Update 11-21 ~08:45 PST
- proof9 first launch died 3_3 GPL (p9_ros var collision in p9_body.tcl); fixed (p9_rosf), kit regenerated (old kit at p9/k_fail1_rosvar), relaunched oth-ubuntu-3984214-1795274017: OT_P9_SITES 10407 FIRM, now past 3_4 resize. Waiter: ot-wait on that unit.
- lepe_mu_C t1: per COORD/FABLE-PD-S81-0830 s4, LC-G1 dropped, out of J7. J8 rows (c1x_C split_plan_B schema, notched strip = 130 um band minus block bbox + 5 um halo; s4 S65/W90 used macro centers and still covers 12 blocks) at lanes/handoff/FAM-S81-LEPE-3-lepeC-split-J8-rows.json; posted to S81-J6-ASSEMBLY-R4 + FAM-S81-SLICE-R4. Scripts epyc10 fam-lepe/split_C/{band2,notch}.py.
## Update 11-21 ~11:20 PST
- proof10 = proof9 + u_bout_unit_o0.d sink D1 (bits 0..603, lane 87->88), relays FIRM at bank/face midpoint. Moved off epyc10 disk hold to epyc7: /srv/opentallas-scratch2/claude/fam-lepe/p10, unit oth-ubuntu-993373-1795281610. Post-hook CTS setup -64.5 / tns -0.87 ns (proof9 -292 / -32.8). Lead build.
- LO-1 J7 row handed to S81-J6-ASSEMBLY-R4: lanes/handoff/FAM-S81-LEPE-3-lepeLP-unit_o0-J7-delta.json.
- COORD rules for the routed read: arst_n / lpc_i0 input-port hold = advisory. Reset removal -117 (g_reset_balanced local_r -> g_tx safe_write) counts only if routed FF hold stays negative -> structural fix (local reset tap / launch-side lockup), not more repair. Residual -64 (g_wrep -> g_tx count_r, 140 ps skew) / -54 (u_rrl_4 -> u_rrl_17): small ECO OK after route if route repair does not close.
- proof9 (epyc10 oth-ubuntu-3984214-1795274017) still in pre-GRT FF hold repair (11k endpoints, single thread): evidence only.
- J8 package after routed read: ROS3/RIP3 defines + K rows, rx[2] bank move, li<N> D1 relays, FIRM sites (see LEPE-2 handoff).
## STAND-DOWN 11-21 ~11:30 PST -> FAM-S81-LEPE-4 (context budget). Nothing cancelled.
### Running units (re-arm waiters with OT_LANE=FAM-S81-LEPE-4; ot-wait = /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-wait on the build host)
- PRIVATE J7 GATE: oth-ubuntu-2047222-1795288337 on epyc10 (civil-redfish). Dir /srv/opentallas-scratch2/claude/fam-lepe/j7p, log run.log, outputs j7p/gate/ (elab.log, bind.log, latcheck.*, latcmp.out vs candJ7c, g0/, g0cmp.out; last lines list hardlinked files written during the run, must be empty).
  waiter: ssh epyc10 "export OT_LANE=FAM-S81-LEPE-4; python3 -I .../tools/fleet/ot-wait oth-ubuntu-2047222-1795288337; tail -45 /srv/opentallas-scratch2/claude/fam-lepe/j7p/run.log"
- proof10 (LEAD): oth-ubuntu-993373-1795281610 on epyc7 (loved-redfish), /srv/opentallas-scratch2/claude/fam-lepe/p10 (run10.log, kit k/). Post-hook CTS setup -64.5 / tns -0.87 ns; hold -181 pre-repair. ~11:2x in pregrt_ff_hold (WNS -138, 11k endpoints, single thread).
  waiter: ssh epyc7 "export OT_LANE=FAM-S81-LEPE-4; python3 -I .../tools/fleet/ot-wait oth-ubuntu-993373-1795281610; tail -25 /srv/opentallas-scratch2/claude/fam-lepe/p10/run10.log"
- proof11 (A/B, FABLE-PD-S81-1100 #6/#7): oth-ubuntu-3534595-1795288755 on epyc8 (outgoing-giraffe), /srv/opentallas-scratch2/claude/fam-lepe/p11 (run11.log). = pristine proof10 kit + config.mk only: OT_TAP_RESET_AFFINITY=1, OT_TAP_PITCH_UM 400->300, OT_TAP_MAX_SINKS 1000->600 (proof10 tap means 238..368: t8 368, t35 353, t2 345, t42 329, root clk 290 at 1000 sinks; 28/71 taps span >300 um).
  waiter: ssh epyc8 "export OT_LANE=FAM-S81-LEPE-4; python3 -I .../tools/fleet/ot-wait oth-ubuntu-3534595-1795288755; tail -20 /srv/opentallas-scratch2/claude/fam-lepe/p11/run11.log"
- proof9 ended (watchdog, exit 143), no KEEP (COORD). Read CTS post-hook only (tools/die_plan/cts_read.py <kit>/run or 4_cts_post_hook.rpt).
### J7 package. COORD RULE: private gate GREEN by ~19:00 PST -> hand the FULL package to S81-J6-ASSEMBLY-R4 for the 20:00 cut; otherwise unit_o0 ALONE in J7, the rest in J8.
- Full delta: epyc10 /srv/opentallas-scratch2/claude/fam-lepe/j7p/j7_lepeLP_full_delta.json (gen j7p/mkdelta.py BASE p10_relay.tsv OUT; BASE = /srv/opentallas-scratch2/claude/s81-j6/j7/v6/out/gen35_out.json; LP t2 identical in v5/candJ7c and v6). Ops: verilog_defines RIP1 -> RIP3 + ROS3; relay_depth ONE whole-list replace (existing 9 + li0-3 _d/_v D1 + u_bout_unit_o0.d D1 bits 0..603); 5 contents origin_um replaces (rx[2] banks 622.08/691.2/760.32 @ 293.772, 622.08/691.2 @ 259.212); relay_sites replace 147 -> 8338 (proof10 FIRM sites of rop/ros_r/thp/ths_r/rd_r/ri/status/wrep; bind-named li/unit_o0 stages left to relay_mid).
- MERGE NOTE: s81-j6/merge_deltas.py flags several "/-" appends to the SAME list inside one delta as conflicts (first gate try died, CONFLICTS 8) -> fold them into one whole-list replace.
- RIP3 RTL overlay (needed; FILE line in the assembly list): physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_lep.sv <- epyc10 /srv/opentallas-scratch2/claude/fam-lepe/j7p/ot_s81sl_slice_lep.sv = candJ7c lep + ROS hunk (main 4ee24dd3c24, same as proof9 j6_lep_ros.sv) + NEW bare selector OT_S81SL_LEP_RIP3 (define OT_S81SL_LEP_RIP 3). Main has ROS2/ROS3 selectors but NO RIP3 selector: push it to main rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv (lane clone epyc8 /srv/opentallas-scratch2/claude/fam-lepe3/repo, main d3a716bffe) via ot-push-main.
- Fallback already handed: lanes/handoff/FAM-S81-LEPE-3-lepeLP-unit_o0-J7-delta.json (single append, +1 cycle lane unit__s_7N_LP__seqhost 87 -> 88).
- K: ROS3 delays ro/t_host/t_kd/mu_c by 3; RIP3 delays ri by 3 (J7 RIP1: +2). Check latcmp.out; LATCHECK decides.
### Other findings
- rov_r[41] (FABLE-1100) is not an RTL bug: proof10 CLK on clknet_leaf_18_clk_t69; net* CLK nets are repair_clock_nets wire buffers (3 flops in proof10, sig CLOCK); proof9 rov_r[41] was a far sink.
- COORD routed-read rules: input-port hold (arst_n, lpc_i0) advisory; reset removal -117 into g_tx safe_write counts only if routed FF hold stays negative -> structural (local reset tap / launch-side lockup); residual -64 (g_wrep -> g_tx count_r, 140 ps skew) / -54 (u_rrl_4 -> u_rrl_17): small ECO OK after route. Stop list: no hold-buffer repair as the lepe lever.
- lepe_mu_C t1: J8 rows lanes/handoff/FAM-S81-LEPE-3-lepeC-split-J8-rows.json (notched strip rule).
- To ot-delete later: epyc10 fam-lepe/p9/k_fail1_rosvar, fam-lepe/j7p/tree_fail1_mergeconflict (hardlinks into candJ7c: ot-delete only, never write) and gate_fail1, epyc10 fam-lepe/p10 (stale copy; run is on epyc7).
