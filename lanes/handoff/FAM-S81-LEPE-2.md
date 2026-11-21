# FAM-S81-LEPE-2 handoff (11-21 ~06:15 PST)
Representative dsdv_slice_lepe_mu_LP__t2. Family: lepe_nh_mus_LP t1, lepw_mu_LP t2, lepw_mus_LP t2, lepw_mu_C t1, lepe_mu_C t1.
## Done this lane
- lepe_mu_C t1 split rows (COORD lever 5): lanes/handoff/FAM-S81-LEPE-2-lepeC-split-rows.json (strip/body as FAM-S81-SLICE split B; strip ~232k, body ~265k, 0 cycles; LC-G1 xg macro / W-S band precondition). Posted to S81-J6-ASSEMBLY-R3.
- Env ruling d442c09bb6e: proof7/7b/8 used a hand-written env on the J5 d8e tree (missing OT_CBC_REACH_UM, OT_PLACE_MAX_TRANSITION; config.mk lacks OT_ABC_RECIPE/TARGET, tap window 208 vs 51 etc). Posted. Not comparable; evidence only.
- J5 wave kit LP (epyc9 ot-jobs ...-603778, route, 11-20 kit) = -891 post-CTS: it has NO RIP1 (define absent in that old kit) -> rid at the E face (rd_out->rid 1602 um). Not a J6 result.
- J6 wave kit LP t2: kit_wave s81_..._b872f1c33699a/a2, gen on epyc8 (ot-jobs ...place-outgoing-giraffe-1647699), place goal. Kit copy on epyc10 .../dc92652f0d5/items/dsdv_slice_lepe_mu_LP__t2/attempt_2/gen. It is the comparison baseline.
## proof9 (epyc10 /srv/opentallas-scratch2/claude/fam-lepe/p9)
Form: cp of the J6 wave kit (exact env/args/flow tag) + overlays (prepare9.sh):
 1 lep = J6 lep + ROS hunk (patch_ros.py, j6_lep_ros.sv), `define RIP 3 / ROS 3 prepended.
 2 rx[2] banks moved beside the rx[1]/rx[3] rows (622.08/691.2/760.32 @ y 293.772, 622.08/691.2 @ 259.212) (mv_rx2.py): rd_out->rid/ml_wd/rtq/f_host were all lane-2 banks at x 976-1304.
 3 li0-3 _d/_v D1 relays (plan9.py + apply_krd9.py on the bound module). n_st NOT added (J6 has n_st internal stations).
 4 FIRM sites (sites9.py + p9_body.tcl appended to istations.tcl): ro/t_host chains at j/(ROS+2) source->roq anchor; ri chain at j/(RIP+1) rid anchor->bout; li relays at lnl pin/rx bank midpoint; u_status regions at their ph_r slices; g_wrep replicas at their push groups. Anchors = J6 wave 3_place dump (in/j6_pos.tsv, dumpj6.tcl).
Benches (J6 tree copy p9/btree + main tb RIP<=4/ROS modelling ported): RIP3 CRP2 WREP5 ROS3 pab/ab/hab all PASS, mutants FAIL as expected (runbench.log).
K for rows: ro/t_host/t_kd/mu_c +3 (ROS3), ri +3 (RIP3 vs J6 RIP1: +2), li<N>_d/_v +1.
## Not yet done
- RX registered read is replaced by the bank move (no cycles); if rd_out classes stay < -42, next is the split-register rid/mwd form (rid = ridA|ridB regs at each pair's banks, OR before rd_r[0], 0 cycles).
- g_wrep: replicas sited only; relay not added.
## Old proofs (epyc9, leave to finish): proof8 fam-lepe/p8x (unit oth-ubuntu-1650150-1795255723, GRT), proof7 opus-p7-r2, 7b opus-p8-local/r4 (GRT). Read run_grt.log.
