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
