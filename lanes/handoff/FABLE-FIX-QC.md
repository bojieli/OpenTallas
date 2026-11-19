# FABLE-FIX-QC handoff (QC closure, hardest families; started 11-18 23:0x PST)

## 11-18 23:5x PST
- Work dir: intel2 (hub) W=/srv/opentallas-scratch2/claude/fable-fix-qc. Scripts: pull.sh HOST TYPE TAG ODB [SDC] (copies a live kit work dir +
  one stage DB to W/k/TAG), census.sh TAG ODB placement|grt (TT census in the kit's own tt_setup_repair.tcl frame, classes + worst paths ->
  W/k/TAG/out/census_<ODB>.log), loc.sh TAG ODB NAME (placement query, patterns in W/k/TAG/loc_NAME.env). Run with
  ot-run --hosts localhost --mem 80 --threads 8 --dir $W -- bash $W/census.sh ... (env does not cross ot-run: pass files).
- Fleet census scripts (run on intel2: bash /tmp/ffq_all.sh /tmp/ffq_c3.sh): per live QC route job, CTS TT (tt_setup_measure.log, post
  tap balance, placement RC) and GRT TT (tt_setup_measure_grt.log). 4_cts_post_hook.rpt / 5_global_route.tt.rpt exist only in kits
  generated after 01c4b1e891d (su_l1, su_l0, coll_ft so far).
- Family ranking (measured, TT): see lanes/posts/FABLE-FIX-QC.md first post.
- TAKEN family 1 = sle_ctl x7. Cause (kit sle_ctl__cl372cea1c N4, 4_cts.odb, census W/k/ctl372/out):
  (a) plan partition_types[sle_ctl*].relay_sites is ONE table shared by all 7 types, keyed by pad depth (u_pd11_x_fw_i, u_pd12_x_st_a_i,
      u_pd4_b_tw_data_i, u_pd5_x_fw_p1_i). The bound types have other depths (cl372cea1c: 11 / 14 / 7 / 6; padE0: 10 / 25 / 8 / 5 +
      u_pd2_x_su_l1_i): OT_RELAY_SITES "plan keys unmatched 10100 of 21808" (padE0 13316). Those chains are left to GPL.
  (b) the matched chain is aimed wrong: u_pd11_x_fw_i_236.q sited (750,145); its consumer pin u_u_ctl/chd_q[236] is on the TOP edge of the
      core at (550,596) = 651 um, 695 ps data against a core clock with 0 insertion (launch tap 238 ps): -97.9, 102 ends.
      type_relay_sites.py point(): a macro consumer counts at its rectangle point nearest the chain, not at the pin.
  (c) second class 652 ends to -66: same tail flops -> u_u_rp repair mux -> u_ist_x_su_c_p{1,2}_o_0 station (820.8,337), 520 ps of wire.
- Same class elsewhere: slw_su_c x2 relay_sites 1034 of 1034 unmatched; cb* 276-294 of 11k; st_a 16 of 196.
- Not taken (reported to owners): fw_v2 -146 = 1 end u_bin_x_sc_i/q[0] -> u_bout_flt_wo (800 ps wire); st_b_v2 pvcd986c42 -106 = 1 end
  u_cland_origin/s2 -> u_cland_rstart_tx (QC-PLAN-R3 group B); slw_st_b_v1__cle6023ec2 -210 = 122 ends u_u_r#.g_sc.u_mul; glue -130 =
  u_sys_face.u_ot_pr_core (648 ends).
- NEXT: per-type relay_sites for the 7 sle_ctl types (type_relay_sites.py with macro PIN capture points), rows to QC-PLAN-R3 for N4.3/N4.4,
  private kit on one type to GRT TT.
