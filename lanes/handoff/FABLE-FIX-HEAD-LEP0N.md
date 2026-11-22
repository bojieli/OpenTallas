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

## LIVE 11-22 09:4x PST (read first)
- PAIR VIEW SIGNED 09:14 (rst_n on the S face), views built, tree r18j gated, E + W kits launched 09:44. Details: rows file section 7.
  Tree epyc9 L/trees/s81_head_r18j_pairs, plan 762441fd7f142bf6 (r18h + pair view vE28s + rekeyed reset rows). Gates PASS (L/bind_r18j2).
- E kit: unit fable-lep0n-e1 on intel2 (pid 1145048), spec ~/coord/autopilot/private_specs/FABLE-FIX-HEAD-LEP0N/s81_head_hd_lep0N_1122094359/spec.json,
  log ~/fable-fix-head-lep0n-1122/runitem_e1.log. First E build with: status relays to agg_1 (LEP-FACESTAT-1), new pair view.
  Known E risks at place (r18e census): u_bout_o_h2r1_p -229.6 x186 (hub stamp logic + 590 ps wire to the W cut face), lepk_i0 band top 501.13 <
  pin top 510.98 (44 bits fall to the band bottom), coll_i3 band y 854-941 vs pins y 645-759, g_rxh.u_ctl -191. Read 3_detailed_place.rpt first.
- W kit: unit fable-lep0n-w9 (pid 1151380), spec .../s81_head_hd_lep0N_w_1122094408/spec.json, log runitem_w9.log. Rows RINGFF-1/2 + RSTART-1/2 + pair view.
  W build A (r18g) died FAIL_POSTCTS GRT-0116 in the tap pre-pass (688 overflow after 30 its); expect w9 to need a congestion row:
  probe (8 its) = W channel top of the ring bands (x 0-60, y 300-350 and 850-900, vertical) + TX SRAM mid band x 210-660 y 600-700.
  30-iteration probe: intel2 L/grt_probe30/cong.rpt (summarise with ~/fable-fix-head-lep0n-1122/cong.py-style regex on "bbox = (x, y)").
- w8 (r18h) stopped before place admission (superseded by w9). A, w4, w7 dead. Nothing else of mine is running except e1, w9, probe30.
- ot-run --direct is allowed ONLY for the pair sign-off/views (NEAR-CLOSE.tsv row 218, done). Kits use the normal queue.
- Durable waiters: ot-wait --durable <pid> --cmdline run-item for 1145048 and 1151380 (re-run the same command to re-attach).
- NEXT: read E/W place (3_detailed_place.rpt), CTS post-hook, pre-GRT; fix rows by measurement; sign-off + EQUIVALENT routed LEC -> PROVENANCE
  -> AUTO-EXPORT; post every 2 h; flow follow-ups: guard for +ff y-column bands not covering their pin column; landing_reader_start origin on relay pieces.

## NEW TASK 07:1x (COORD ruling, mine): E reset blocker, option (b) = pair rst_n pin to the S face, re-sign the pair view, E kit --goal route
Problem (R8 hub 3316ceac): hd_lep0N E PLACE-SETUP-STOP -441: gated reset tap u_rrl_380 (535.7,1343.5) -> u_rg0.u_pair rst_n, M5 pin at the pair
centre (388.824,246.24) under full M4/M5 OBS; rg3 mirror (u_rrl_234). Plan + ETA posted 07:15 (view ~10:30, E kit ~11:15).
Facts: - pair = ot_s81hd_lep_pair 777.6x492.48, 1.10 M cells, ONE module for rg0/rg3 (E) and rg1/rg2 (W): new view changes W too.
 - signed view results/head_lep_pair_views_vE28_1118 (README, splice.json, clock_contract.json, source_signoff.json). Signed routed DB:
   epyc9 /srv/opentallas-scratch2/claude/fable-fix-head-lep0n/ve28_hold2/so_run/results/asap7/hbc_ot_s81hd_lep_pair/base/6_final.odb; sign-off session
   .../ve28_hold2/so_out/{tt,ff}/(cmd.sh, session.tcl, libraries.json); view inputs .../fable-fix-head-lep0n/ve28_views/(run_views.sh, res/, views/).
 - DELETED 11-21: kit epyc9 /srv/opentallas-scratch2/claude/head-lep0n-opus/lep_ve28/kit/ot_s81hd_lep_pair_kit (only kit/_inputs left) and
   head-plan-r4/ve28_detail (M6/M7 detail splice). Regenerate the kit (gen only): python3 -I head-lep0n-opus/lep_ve28/lep_pair_kit_ve28.py TREE
   SRC_PLAN OUT_PLAN_DIR KITROOT (plan_lep_pair_kitview.json in lep_ve28/plan).
 - core_pins/lep_pair_pins_777r.json (rst_n S face x 397.464) COLLIDES with the signed clk entry (397.464,0.24 M5): use a new file
   lep_pair_pins_777s.json with rst_n at (399.384, 0.042) M5; only rst_n differs from 777.
 - ECO recipe to copy: rt tools/die_plan/hold_eco_internal_run.py (steps 3-5: docker drv.tcl -> post_route_drv/hold_eco_internal_route.tcl with
   selected nets -> signoff.py run minimal profile); 11-18 run took 35 min.
 - Open check: bind picks the core reset gate tap nearest the core CENTRE (bind.py ~4700 CORE_SPLIT reset_gate); make it follow the pin or add a tap row.
Steps: a) kit regen + read net rst_n on the DB; b) pin-move ECO + incremental route of rst_n; c) signoff; d) views (LEF, ETM tt/ff, detail splice,
clock_contract, signed_view_sha); e) tree r18j = r18h + 4 pair rows (pins_file, lef, lib) + gates; f) E kit --goal route; relaunch W on r18j; tell R8 the sha.

### E reset task progress 08:0x (all on epyc9, P=L/pair, scripts L/tmp/pair_*.sh / pair_eco.tcl; hub logs intel2 ~/fable-fix-head-lep0n-1122/pair_*.otrun.log)
- DONE a) kit regenerated (gen only): P/kit/ot_s81hd_lep_pair_kit (constraint.sdc identical to the signed golden.sdc; made from tree r18f + lep_ve28 plan).
- DONE probe: net rst_n = 1 port + 1 load (input8829 BUFx2 at (389.0,245.97)); clk BPin M5 (397.44..397.488, 0..0.48).
- DONE b) ECO: P/eco/in/6_final.odb (copy of signed DB) -> P/eco/out/pe_routed.odb: rst_n BPin M5 (399.372,0)-(399.396,0.192), only net rst_n
  re-routed (GRT 257 um), DRC 0 (pe_drc.rpt empty), insts 1,101,619 unchanged, obstructions 0.
- RUNNING c) sign-off: ot-run pid 1409281 on intel2 (pair_so.otrun.log), script pair_so.sh -> P/so_run, P/so_out/signoff.json, P/so.log; pass =
  "VERDICT_RC 0". Queued on the epyc9 load cap at 08:02.
- NEXT d) bash L/tmp/pair_views.sh via ot-run (--mem 96): P/views/views (blanket LEF + tt/ff ETM), P/views/detail/detail_b1.lef, splice ->
  P/views/view/ot_s81hd_lep_pair.{lef,_tt.lib,_ff.lib} + splice.json; then clock_contract.json (tools/die_plan/core_clock_contract.py; needs
  PYTHONPATH with physical/die_plan `cores` module: run from a tree, see the old results/head_lep_pair_views_vE28_1118/clock_contract.json form),
  README + source_signoff.json copy -> new tree dir results/head_lep_pair_views_vE28s_1122.
- NEXT e) tree r18j = fork of r18h + new view dir + core_pins/lep_pair_pins_777s.json (= 777 with rst_n {M5, x 399.384, y 0.042}) + the 4 pair
  hard_cores rows of hd_lep0N (rg0, rg3) and hd_lep0N_w (rg1, rg2): pins_file, lef, lib -> republish both wrappers (reset tap of the pair
  follows the pin: today tap 204 u_rrl_380 (535.7,1343.5) = pin x, N of rg0) -> bind/cohort/LATCHECK + plan_gate_pre (chain script name must
  start with chain* for ot-run --priority plan).
- NEXT f) E kit: private-spec s81_head hd_lep0N --tree r18j --goal route --src-manifest seal --rt c9b8d5f226ca (or newer), run-item --goal route;
  relaunch W on r18j; post the view sha256 to R8 + COORD.
- W build B relaunched 07:44 as unit fable-lep0n-w8 (pid 826765, spec s81_head_hd_lep0N_w_1122074440, plan 163383b979fca607): attempt w7 died at
  place "OT_CLAND no mapped cells found under u_cland_origin" (landing_reader_start.origin_rect_um pins u_cland_origin, absent on a relay
  piece) -> key dropped (L/tmp/rstart3_fix.py). st.sh now reports w8.

## LIVE 11-22 06:0x PST (read this first; older sections below are history)
- FLOW: private-spec/run-item --goal finish DIES at the place->cts hand-over (run_kit.sh stage resume accepts floorplan|place|cts|grt|route only).
  Use run-item --goal route (wave chain: route + sign-off + routed LEC). Use kit_wave.py + --rt of rt c9b8d5f226ca or newer (seal mode, face-status gen).
- W attempt 4 (r18f) ENDED by that flow bug (result stage cts FAIL / FAIL_PREFLOOR); it had coll_i1 ctl_w -> rv -708.55 at place. Dead, nothing to cancel.
- BUILD A = W attempt 6: tree r18g (epyc9 L/trees/s81_head_r18g_ringff2, plan 0c7056cd38b8b1f6 = r18f + LEP-RINGFF-2 coll_i1 rect
  [17.28,629.64,30.24,864.0]); spec ~/coord/autopilot/private_specs/FABLE-FIX-HEAD-LEP0N/s81_head_hd_lep0N_w_1122050625/spec.json; unit
  fable-lep0n-w6 on intel2 (pid 2920517, run-item --goal route), log ~/fable-fix-head-lep0n-1122/runitem_w6.log.
  Kit epyc9 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r17b/private/FABLE-FIX-HEAD-LEP0N/hd_lep0N_w_1122050624/gen/hd_lep0N_w
  PLACED 05:45 (on intel2): tns -484.07 (r18e -62198, r18f -3938), wns -211.84, OT_PLACE_WIRE_RATIO 0; whole piece has 2 violating clk ends +
  path-delay -18.65. Chain (goal route) started 06:00 on epyc9, container dpkit-hd_lep0N_w-880189; CTS wait armed by run-item.
  The 2 ends = u_cland_rstart_rx/q (W face y 1154.5) + copy _otdup1 (y 453.6), reset by cland_reset_coll_i0 from (814,1085): -144 / -145.6.
- BUILD A CTS post-hook 06:24 (on intel2, chain spilled there; kit path same as epyc9): setup_ws -347.30 tns -16424.8, all ring groups met;
  failing cluster = START relay only (rst -> rstart_rx -347/-322; rstart_rx -> reader_start_coll_i0_0 -183 x33). hold_ws -270 (pre hold repair,
  u_bin_coll_i2 -> u_rg2.u_pair). Now in pre-GRT (OT_TAP_GRT_PRE). Keep running (GRT/channel probe; cancel only on the measured rule).
- BUILD B = W attempt 7: tree r18h (epyc9 L/trees/s81_head_r18h_rstart, plan 301a0f1635d65898 = r18g + LEP-RSTART-1 (rstart_rx on local reset k3)
  + LEP-RSTART-2 (landing_reader_start depth 2)); gates PASS (L/bind_r18h2, chain_r18h2.otrun.log). Spec
  ~/coord/autopilot/private_specs/FABLE-FIX-HEAD-LEP0N/s81_head_hd_lep0N_w_1122063509/spec.json (goal route, seal, rt c9b8d5f226ca), unit
  fable-lep0n-w7 on intel2 (pid 2519647), log ~/fable-fix-head-lep0n-1122/runitem_w7.log. Launched 06:35.
  CHECK at place: 3_detailed_place.rpt wns/tns (A: -211.84 / -484.07) and that rstart_rx / reader_start ends are met; then CTS post-hook.
  When B's CTS post-hook is clean and A is still failing the START cluster after GRT repair, cancel A (exact units only).
- Rows file lanes/handoff/FABLE-FIX-HEAD-LEP0N-rows.md (sections 1-6).
- STA recipe: ot-run --hosts epyc9 --dir L --stage KIT -- bash L/tmp/sta_kit.sh KIT dp_hd_lep0N_w OUTDIR L/tmp/sta_w.tcl (edit the tcl).
- Poll with short (<170 s) ssh loops; background waiters do not outlive the turn reliably.

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
