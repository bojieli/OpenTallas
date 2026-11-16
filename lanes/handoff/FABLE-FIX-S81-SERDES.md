# FABLE-FIX-S81-SERDES handoff (owner of S81 serdes__t1 x2, t13, t14, t15 x2)

Gates: DRC 0, TT setup >= -42 ps, FF non-port hold >= 0, bind + LATCHECK. Lane S81-SERDES-DPL (Opus) follows this lane; it had no live builds at 06:40 PST 11-16.

## Facts (06:40-07:20 PST 11-16)
- Hub log: only serdes__t13 and serdes__t15__cla2127225 fail DPL-0033 (01:23, plan G3b 3fa87b84b18, v1 tree). t1__clb45, t15__cla3d, t16, t12, t2, t3 pass DPL on G3b. t14 and t1__clfe stopped at sdc_lint (B6gE) before place.
- t13 failed DPL log (epyc8 kw43 wave attempt_5, logs kept): 233 movable cells never legalise (repair buffers in u_cland_ft3/4/5_i, u_ft_ft3/4/5_o_0, reader_start flops), 116 off-site, 146 overlaps, 151 edge-spacing. 39,612 ring cells FIRM. Failed DB was cleaned.
- v2 tree kit_preflight refuses the old ring form (ring_ff: ring >= 256 bits without ring_place=ff), so on v2 these kits stop before place until the plan has ring ff.
- F2s family (F2sv, F2s2) serdes blocks vs G3b: only landing bands change: ring_place ff and rect x 17.28..92.88 -> 17.28..56.16 (E side 2792.88 -> 2829.6).

## Builds (epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes, v2 tree src_s81_pin_eb1e73448bd0, v2 bind kw45/s81bind_pin_eb1e73448bd0/out)
- gen.sh / gen2.sh FORM TYPE: wave recipe (die_gen_env + item_env of kit_wave.json 11-16).
- A/ = G3b plan as is, ring_ff preflight line disabled in the private kit (old form, to get the failed DB): serdes__t13, serdes__t15__cla2127225, place running.
- B/ = planB.json + sideB.json = G3b with the 11 serdes type blocks + sidecar collector types of F2sv (ring ff, narrow bands); kit-rtl + prepare-stations on G3b (bind matches), gen phys on planB: all six items, place running.
- Client logs: localhost scratchpad placeA_*.log, placeB_*.log; kit logs <form>/<type>/run_place.out.

## Next
1. Read A t13 3_5_place_dp-failed.odb: where the 233 cells sit (rows/sites, FIRM neighbours, blockages). Name the cause.
2. Read B place: DPL pass or not. If pass: the fix is the F2s ring-ff rows (already in the die plan) and the serdes items go to route on B; if fail: flow fix on branch claude/fable-fix-s81-serdes-1116.
3. Route the passing kits (run_kit.sh route 80 16), sign-off, export to AGIdock /archive/opentallas-signed-1114 + rtx-pro.

## 08:xx-09:xx PST 11-16 update (after COORD re-target + epyc8 disk notice)
- Forms A and B (G3b based) are REMOVED from epyc8 scratch2 (containers stopped by exact name, dirs deleted). Kept: epyc8 /home/ubuntu/ot-scratch/fable-fix-s81-serdes/{planB.json,sideB.json,keep/A_t13_logs}. No new kit on epyc8 scratch2.
- A t13 result (v2 tree, G3b OLD ring form, ring_ff preflight off): DPL PASSED, 0 violations (iteration 0: 8,760 -> 0 at 400). So the 01:23 failure does NOT reproduce on v2 with the same plan. The one difference seen in the logs: the v2 kit has NO OT_TXL_MID step (the failed v1 kit moved 4,820 + 2,484 hop cells after GPL).
- FOUND (flow gap): branch claude/serdes-txpipe-1114 (018cb1c0ac + 40f6ca71cd) was never merged. main and the v2 tree and B6gF2s2/src have the TXPIPE RTL only through the tree overlay and LACK the gen_phys hook (txl_mid_exports defines= / SERDES_PIPE_CHAINS). Every serdes kit generated from v2 / F2s2 has the TXPIPE/RXPIPE/RXNEG defines but no OT_TXL_MID, no POST_GLOBAL_PLACE_TCL: the pipe rows are not placed at the PMA faces (the -455..-719 ps TX distance class of 11-14 comes back).
- Branch: epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes/wt, claude/fable-fix-s81-serdes-1116 @f84ed61a70 = main e671bdd4a2 + the two commits cherry-picked (clean). Pushed. Gate: localhost scratchpad gate1.log (ot-run epyc2/epyc9).
- Form C = real F2s2 plan + bind (epyc10 s81-b3-clk/run/b/B6gF2s2, src = that run src): epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes/C/<type>, six items, gen logs localhost scratchpad genC_*.log. Kits have ring:+ff and bands 38.88 um wide.
- Next: add the hook lines to the never-run C kits (txl_mid.tcl + OT_TXL_MID=1, CHAINS "u_txl u_rxf u_dec.u_face_p_d", FACE=1, POST_GLOBAL_PLACE_TCL) = what the branch generates; copy the kits (31 MB each) to epyc7 scratch2 fable-fix-s81-serdes/C; run_kit.sh <T> route 80 16 via ot-run; read 3_5 DPL, then sign-off; export.

## 09:3x PST 11-16
- Branch claude/fable-fix-s81-serdes-1116 @f84ed61a70: gate GREEN 63/63, r309 approved, MERGED 09:18 as 8b9258eb3ce (mirror main has SERDES_PIPE_CHAINS). It was in the lane mirror all along; COORD push ask answered, no push made.
- LIVE: six F2s2 kits in route on epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes/C/<T>/gen (run_kit.sh <T> route 80 16 via ot-run, started 09:3x; kit log C/<T>/run_route.out; client logs localhost scratchpad routeC_<T>.log). Types: serdes__t13, serdes__t14, serdes__t15__cla2127225, serdes__t15__cla3d02796, serdes__t1__clb45db5be, serdes__t1__clfe1f0815. Kits = real F2s2 plan + bind (generated on epyc10 from s81-b3-clk/run/b/B6gF2s2), plus the 4 hook lines + txl_mid.tcl added post-gen before any run (config.mk.orig kept) = what main now generates.
- epyc7 scratch2 had 96 GB free at launch: watch it; six serdes kits use about 5-10 GB each through route.
- Read order: 3_5_place_dp.log (0 violations expected), OT_TXL_MID lines in 3_3, 4_1_cts TT, 5_1_grt, signoff/signoff.json. Pass = DRC 0, TT setup >= -42, FF non-port hold >= 0 -> AUTO-RESIGN row + export to AGIdock /archive/opentallas-signed-1114 and rtx-pro.
- Not done: no sign-off yet; old-form DPL-0033 cause not isolated to one cell class (did not reproduce on v2; failed DBs were cleaned before I started).
- Open for the wave: KIT-OPS-5 keeps serdes__t* held until TOOLS-CONVERGE rebuilds the S81 tree from main >= 8b9258eb3ce and the die adopts F2s2/F2s3.

## CODEX notes 2026-11-16: prepared reset authority fallback
- Existing six C F2s2 kits remain active in GPL on epyc7, preserved without edits. No signoff yet.
- Older F2sv S81-SERDES-DPL t13 proves ring_ff DPL 0, but CTS lock_sync[0]->[1] -729.08; ODB locations (2575.692,1220.940) to (1658.016,946.890), Manhattan1191.726um. These older proofs lack TXL hook and are not C evidence.
- Prepared default-off placement-only fallback on inherited branch claude/fable-fix-s81-serdes-1116 @607205aa5d8, tools/die_plan/serdes_reset_local.tcl. Group includes authority registers and bounded short fanin/fanout; no RTL/net/stage/clock identity changes. Added cycles0, cells0, model delta0.
- Read-only off/on ODB gate PASS: default-off identical, 34 authority pin/net maps unchanged. 97 cells moved, area16.67952um2; pocket12.96um square near native consumers, existing area43.11306um2, no blockages, conservative combined occupancy35.60%.
- Viewed epyc7 fable-fix-s81-serdes/reset_probe/reset_local.png (source/density TSV + renderer beside it). Macro halos clear and compact region has room; PDN/pins/macro sites unchanged. Review PASS-COND in results/geom_review/s81_serdes_reset_local_1116.json.
- Enable only if C postCTS reproduces same-class locality miss. Candidate recipe: copy fresh C kit after GPL, combine txl_mid + reset_local in post-GPL hook, set OT_SERDES_RESET_LOCAL=1, re-place through CTS/GRT after review. Do not patch active C kits. CTS clock locality remains to measure per original domain; never splice clk/rck clocks.

## CODEX RXNEG correction and phase-aware E (2026-11-16)
- Source @b3e9f4a365d: RXNEG u_rxf_q selector + 545-bit coverage refusal; gate22/22 PASS, including incomplete-valid mutant. Old matcher silently found0/0. Corrected C3_3 finds545/545; 544 data flops already FIRM at PMA (core_out_land), moves1 valid row +786 hop buffers.
- D t14 (buffer-placement baseline) LIVE intel1 unit oth-ubuntu-2329411-1794853045, fable-fix-s81-serdes/D/serdes__t14/gen, logs ../run_route.out and kit/run_route.log; starts place using copied synth/floorplan. Replicas epyc7 + intel1. No active C kit edits.
- FIRST C t14 CTS raw report FAIL: u_rxf_q6 (falling) -> face_p_d6 (rising) -432.82; u_rrl_94 (falling) -> collect_rst_rl_94.ready_o -973.54; native rt_d5 -> u_rm.g_rd5.q57 recovery -358.87. Await reloaded TT-repair/GRT read.
- Source @fe73c2c47bb: optional OT_TXL_MID_RXNEG_PAIR=1, phase-aware face_p_d + scalar face_p_v beside falling RXNEG source. Default off. Gate25/25 PASS; all actual hierarchy + valid width, scalar valid row, on/off geometry. Pure placement, RTL/stages/edges/data nets unchanged, added cycles0/cells0/modeldelta0.
- Viewed actual t14 C3_3 preview reset_probe/rx_pair.png: 544 half-cycle data-pair Manhattan max664.998->8.088um, mean361.2459->8.0647. FIRM PMA rows and macro sites unchanged; adjacent face rows below macro halos. Full-cycle output leg max1321um is still a timing risk, not a closure claim. Review in results/geom_review/s81_serdes_rxneg_pair_1116.json.
- E t14 LIVE epyc7 unit oth-ubuntu-2642341-1794853506 at fable-fix-s81-serdes/E/serdes__t14/gen; ot-run --dir ../ready, source E config sets phase-pair and existing OT_LEAF_AFF_DEPTH=12. Analytic halfcycle budget416.5-64.36cq-16.27setup-60uncertainty-80targetskew-50shortwire=145.87ps reserve; propagated-clock CTS/GRT still required. E replica to intel1 copying at launch.
- Reset-local helper deliberately NOT enabled on D/E: C3_3 has FIRM lock_sync1 boundary authority, so existing helper correctly REFUSED. Focused reset_form worker owns anchor-aware variant + native/relay reset failures in existing S81-SERDES-DPL private dirs; no source edit until integration.
- First actionable next read: C reloaded postCTS, then D/E hook line (all545 RXNEG and scalar valid) + CTS/GRT classes. Root signoff gate remains DRC0, TT>=-42, FFhold>=0, LEC; R-MINIMAL export to both archives after terminal PASS.
