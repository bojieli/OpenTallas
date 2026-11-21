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
