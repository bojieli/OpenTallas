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

## 11-18 23:5x PST (fix written, proof kit running)
- Lane clone: intel2 /srv/opentallas-scratch2/claude/fable-fix-qc-main (sparse tools + physical/common_flow), ONE local commit 74cf953c6ef
  (not on main yet): tools/die_plan/pad_chain_site.tcl + gen_phys.pad_chain_site_place (opt-in gen env OT_PAD_CHAIN_SITE = unsited | auto |
  all; unset = kit unchanged) + kit_istations rs_place_all separator-blind keys (su_c x3) + tests (test_pad_chain_site.py 6,
  test_kit_istations.py +1; 78 pass). Push: cd clone && python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main.
  PUSH ONLY AFTER p1 prints "OT_PAD_CHAIN_SITE mode auto chains N of 2393 sited" in 3_3 without a Tcl error.
- Dry read of the hook on the wave kit DB (W/pcs_dry.sh ctl372 3_3_place_gp.odb auto firm): 2,387 of 2,393 chains sited, 530 stale
  plan-sited chains re-sited, worst hop 401 um (x_fw_i; was 651 um to the pin), x_fw_p1_i 114, b_tw_data_i 255, x_st_a_i 17.
- Proof kit p1: W/kit/p1/gen/sle_ctl__cl372cea1c = copy of the wave N4 kit (epyc9 .../s29q103S4Q9N4/items/sle_ctl__cl372cea1c/gen) +
  pad_chain_site.tcl + hook line at the end of face_flops.tcl + "export OT_PAD_CHAIN_SITE = auto" in config.mk (W/kit_p.sh).
  Run: ot-run --hosts localhost --mem 96 --threads 16 --dir $W -- bash $W/run_p.sh p1 route 96 16; log W/logs/kit_p1.otrun.log,
  kit log $K/run_route.log. Started 23:2x. Base to beat (same kit without the hook, live wave job): CTS TT -97.91 / tns -19,117
  (tt_setup_measure.log), 757 negative ends.
- Read after CTS: grep "measure TT" $K/tt_setup_measure.log; census: bash W/pull.sh is not needed (kit is local): copy
  W/k/p1/work -> symlink is NOT allowed by census.sh (docker mount), use: mkdir -p W/k/p1 && ln -s $K W/k/p1/work, then census.sh p1 4_cts.odb placement.
- After a pass at GRT TT (>= -42): (1) ot-push-main, (2) kit_wave_edit --set /dies/qwen_compute/item_env/<item>/OT_PAD_CHAIN_SITE="auto" for the 7
  sle_ctl items (cl372cea1c, cl503337ff, cl67434795, cla4f6f12f, cl503337ff__padE0, cl503337ff__padE4, cl67434795__padW5; the three pad
  items have no item_env entry yet: set the whole object), dry run first, (3) post, (4) follow the wave kits to sign-off and export.
- Posted to QC-PLAN-R3 (23:4x): fw_v2 flt_wo hop 1,247 um (2 stations), st_b_v2 cland_origin -> cland_rstart_tx 1,075 um (2 stations).
- Not owned, facts for the st_b owner: slw_st_b_v1__cle6023ec2 -210.4 = SRAM u_u_r4.u_scale_wait.u_m.g_bank[0].u_m rd_out (clk->q 255 ps)
  + 276 ps wire + 22 logic levels into g_sc[1].u_mul...u_d.u_741 (122 ends); the other st_b types are +2..+44 at CTS.
