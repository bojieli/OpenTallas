# FABLE-FIX-HEAD-LEP0N (Fable, restarted 11-22 03:3x PST by COORD; pairing OPUS-FIX-HEAD-LEP0N-R8)

The 11-21 07:50 stand-down text of the first lane of this name is in git history of this file (and in -R2..-R7, OPUS -R8 handoffs).
Goal: hd_lep0N (+_w) signed off = HEAD complete. I diagnose + write the structural fix + build ONE sealed private kit. R8 keeps its builds.
Post with: POST_NO_RESOLVE=1 bash ~/coord/bin/post.sh FABLE-FIX-HEAD-LEP0N "..." (without it the post is redirected to R8).

## Dirs
- epyc9 lane dir L=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-1122 (tmp/ringff_fix.py, trees/, plan/). Hub logs intel2 ~/fable-fix-head-lep0n-1122/.
- Base tree (Codex seal, epyc9 only): /srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r18e_split_s0 (b4f489665c04, plan sha256 e84371ca5dcf).
- My fork: L/trees/s81_head_r18f_ringff (ot-tree-fork of r18e, started 03:5x; log ~/fable-fix-head-lep0n-1122/fork_r18f.log).

## DIAGNOSIS (measured)
Failure history by form: uncut 2x2 (r11b/r16 wave) and shelf: GRT overflow flat + 98.9 % of the 400k cap -> type split W|E (R4-R7).
Split kits E7/W7 (F tree): CTS post-hook setup -1007 / -1465 on the unrelayed landing fault path (u_cland_*_i/u_fault_port -> u_cland_up_*_o/fault_o);
r18 added the status relays. r18b/c/d died in kit_rtl on tools (v1 stage groups, missing common_flow). r18e = first complete tree.
1. SETTINGS (W only, E is exact wave env): kit_wave.json item_env has no hd_lep0N_w row, so W builds with die_gen_env only:
   OT_PG_PIN_CHECK=1 (hd_lep0N: warn), no OT_PG_CELL_KEEPOUT=0, no OT_PG_TRACK_TRUTH_WIDE_SPACING=1, no OT_IO_HOLD=sender_min /
   OT_GEN_M8_GRANT=1 rows. Also plan clock.tap_window.per_port_ps / tap_offset.per_port_ps and die.layer_budget.type_m8_grant.type_guides
   name hd_lep0N only (old uncut tap names; advisory, die clock retargets the pieces).
2. STRUCTURAL (W): R7 tmp/recompose_merge.py ran CLP.compose(band_reserve='padded', band_ring='all', ring_ff_min_bits=0). Bands coll_i1 /
   coll_i2 of hd_lep0N_w lost ring_place=ff + spread (r16/r17b: ring:coll_i2@2.0666+ff, rect 45.36 x 206 on the pins). r18e tags are
   ring:coll_i1 / ring:coll_i2 = whole ring FIRM in netlist order (FABLE-FIX-S81-RINGS class; kit_preflight ring_ff only judges die s81),
   and coll_i2 is a 12.96 x 531.36 sliver [17.28,17.28,30.24,548.64] (pair 2 at x 34.56 leaves a 17-um W channel).
   r18e W placed DB (epyc9 .../opus-fix-head-lep0n-r8/r18e/hd_lep0N_w_dry, 3_place.odb f59f132d39c1): TT setup -495.73 (ctl_lap -> lap_ok,
   max_delay 416.5), -204.08 (g_oh -> ghi0 half cycle), -135.10 (tc -> wen), tns -62198, all in u_cland_coll_i2; OT_PLACE_WIRE_RATIO
   ghi1 -> ghi2 direct 1.9 um built 654.6 um; 40,751 FIRM cells. coll_i0 (ring ff) +392, coll_i1 +231.
   main _storage_band at ring_ff: coll_i1 legal [17.28,634.78,62.64,840.78] @2.0666; coll_i2 FAIL "required depth 23.76 um" (channel 12.96).
3. E piece: bands all ring ff; r18e E place still running at 03:5x (dpkit-hd_lep0N-734152 epyc9). E7 CTS: fault path -1007 (relayed in r18),
   coll_i3 fs_q -> wen -216 (fclk), lap_ok -155: re-read on the r18e E placed DB.

## E finding (r18e E placed, 3_detailed_place.rpt): TT -800.56 u_cland_face_fault_i_coll_i0_p -> u_cland_agg_1 (cut-leg status child is
sidecar mask.intra_inputs; head_sideband_street_rows only relays mask.inputs). R8 found it too and pushed the generator support to main
c293b03e90 (03:49, in rt b9cca3992f80). coll_i3 lap_ok -191.73 at place (pre-repair). E build is R8's.

## LIVE KIT (supersedes the spec/unit/pid named in STATE below) 11-22 04:2x PST
- Attempts 1-3 died before place on tooling: (1) kit_wave.py of rt 6d2e = verify not seal (SRC_MANIFEST DRIFT); (3) rt 6d2e tools replace the
  tree tools in the launch view, so GEN failed on the E face rows. Attempt 4 = rt c9b8d5f226ca (has c293b03e90 face-status generator and
  my b589d27539 preflight): spec ~/coord/autopilot/private_specs/FABLE-FIX-HEAD-LEP0N/s81_head_hd_lep0N_w_1122041412/spec.json, src_manifest seal,
  run-item = systemd --user unit fable-lep0n-w4 on intel2 (pid 1483054), log ~/fable-fix-head-lep0n-1122/runitem_w4.log.
  Kit epyc9 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r17b/private/FABLE-FIX-HEAD-LEP0N/hd_lep0N_w_1122041410/gen/hd_lep0N_w
  kit_rtl PASS, gen_lint PASS; tags ring:coll_i1@1.8697+ff, ring:coll_i2+ff (verified). Waiter: ot-wait --durable 1483054 --cmdline run-item.
- COORD 04:1x asked about stage wdq_bank3 4.0 x 169.4 (E): measured NOT a problem (STA on r18e E placed DB, epyc9 L/sta_e: u_land.wdq worst +310.2,
  0 violating). E census: 443 violating ends, ws -707: agg_1 status (fixed), NEW u_bout_o_h2r1_p/q 186 ends worst -229.6 (hub stamp logic + 590 ps
  wire to the W cut face), g_rxh.u_ctl -191, lepk reader_start -> dsel -191, rg3 txi v_o -155. Posted 04:1x. E is R8's build.
- STA recipe (read-only, any kit): L/tmp/sta_e.sh + sta_e.tcl (docker ORFS `make ... RUN_SCRIPT=/out/x.tcl run`, kit mounted ro).

## STATE 11-22 04:0x PST
- Tree r18f = fork of r18e + LEP-RINGFF-1 (W bands) + LEP-FACESTAT-1 (E: 4 status relays agg.i_coll_i0_p + local resets f0..f3 + my own
  equivalent generator patch in the TREE tools, tmp/patch_cl.py). Plan sha256 f23abfbd22780d25. Gates PASS (chain_r18f.otrun.log, unit
  oth-ubuntu-2529493-1795347713): plan_gate_pre 0 findings, bind PASS, cohort 27/27, LATCHECK 334/334, W wrapper unchanged. bind out epyc9 L/bind_r18f.
  DO NOT edit the tree any more: the W kit seals it at gen.
- Rows file: lanes/handoff/FABLE-FIX-HEAD-LEP0N-rows.md (posted to R8 + COORD 03:5x).
- kit_wave.json item_env.hd_lep0N_w added (coord 424a945b2b91) = hd_lep0N row.
- MY ONE KIT: hd_lep0N_w from r18f, goal finish, sealed. Spec ~/coord/autopilot/private_specs/FABLE-FIX-HEAD-LEP0N/s81_head_hd_lep0N_w_1122035312/spec.json.
  run-item = systemd --user unit fable-lep0n-w1 on intel2 (pid 339647), log intel2 ~/fable-fix-head-lep0n-1122/runitem_w1.log.
  Work dir epyc9 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r17b/private/FABLE-FIX-HEAD-LEP0N/hd_lep0N_w_1122035310
  Waiter: ot-wait --durable 339647 --cmdline run-item --timeout 3000 (on intel2; re-run the same command on exit 75).
  CHECK FIRST at place: landing_placement.tcl tags ring:coll_i1@1.8697+ff and ring:coll_i2+ff; OT_CLAND pinslot lines; then
  3_detailed_place.rpt wns (r18e: -495.73). Cancel only if setup < -300 after CTS/GRT repair, flat repair, or functional bug.
- Lane clone epyc7 /srv/opentallas-scratch2/claude/fable-fix-head-lep0n-1122/clone: commit b589d27539 kit_preflight ring_ff judges die s81_head
  (ot-push-main started 04:1x, log epyc7 .../tmp/push1.log).

## NEXT
1. W kit: read each stage from the final DBs; sign-off + EQUIVALENT routed LEC -> PROVENANCE.json -> AUTO-EXPORT; report COORD.
2. Post progress every 2 h. If W fails in the 13-um channel (density / GRT), next lever: band rect incl. the face strip x 4.32-17.28
   (ff_rect_um), or pair 2 MX -> swap so coll_i2 pins face the mid band.
3. E is R8's build (from r18f or its own tree with the same rows).
