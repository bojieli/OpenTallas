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

## Current Codex replacement status (2026-11-16; supersedes LIVE C above)
- All six C forms were rejected on measured structural CTS failures and stopped under coordinator exact-scope authorization; source, logs and DBs retained. Six exact generation+route holds remain in kit_wave: release result:FABLE-FIX-S81-SERDES:serdes-corrected is NOT posted. F2s3 source adoption alone must not restart them.
- Normal source gate pinned978eeface1f21c0ed95a3e0b086347bbd01abd02 GREEN57/57; source carries selector, phase pair, clock-group ownership, RPC8, RCK4 model/proofs and helpers. Current clean follow-on tipad2ec50d51d additionally carries FT endpoint/cohort and BOOT3; merge_ops owns next normal gate, no duplicate component proofs.
- D selector-only t14 actual postCTS WNS-1248.5974ps, ready94 skew1547.20ps: insufficient alone. D intel1 and E epyc7 remain active until coordinator cancellation scope. E halfcycle nominal+116.136215ps versus C-476.132690ps is mechanism-only; ready94 remains independently failed.
- F2 t14 current-source RCK4/RPC8 pilot intel1 unitoth-ubuntu-2190004-1794857619: actual mapped inventory2216relay+4reset+9AM+24RPC PASS; actual GPL image reviewed, hop311.570um, face->stage1 310.343um, pair8.116um, clear macros. Live run_place.log DPL0alignment/overlap/spacing violations; CTS follows successful place. rx_transport owns continuation.
- G t1clb explicitstage0/forwardedclock physical-only FT pilot epyc7 unitoth-ubuntu-184798-1794859029 remains live placement, actual logG_grt.log. Inherited run_route.log is stale C and must not be read as G results. LEC_ASYNC is R-MINIMAL dropped rc0, NOT equivalence. rm_select owns targeted FT output timing.
- H t13 BOOT3+pairedPMA successor awaits actual strip3 coherent bind_report; existing bind progressing, EXTERNAL_G0 FAIL368 broader plan classes owned by strip_refloor, no duplicate bind. reset_form owns current-source GEN/inventory/actualimage before CTS.
- DATA START/reset t1clfe and t15cla3d have concrete nine-stage successor from S81 plan/start_reset, canonical S81-START-RESET-rows.json coord78cd5973: maxhop317.625um, payload0cycles, readerboot+8/writerboot+9, miter3576comparisons/8warmresets PASS+mutant. Plan owner composes next tuple, no physical closure claim.

## PARKED FOR CLAUDE RESET — terminal Codex continuation

All three workers (reset_form including reset_graph, rx_transport, rm_select) are PARKED. No further edits, launches, gates or proof runs. Existing jobs may continue. This section supersedes older LIVE baseline descriptions above.

Source: inherited epyc7 fable-fix-s81-serdes/wt, branch claude/fable-fix-s81-serdes-1116. Last read HEAD 4cbe3ec8a237a5beeeb9c739b6d84c8a9795a7df. Corrected 7809af790dd normal source gate GREEN147/147; failed ad2 gate retained. Later committed steps f7731aa3713 LOCAL_EMPTY8, fbceb790300 clock family, 524f7a9a480 LPL model/minimal proof, 4cbe3ec8a23 native RM placement helper await combined source gate. No component proof repetition needed.

ACTIVE:
- I: intel1 oth-ubuntu-3385755-1794863330 / dpkit-serdes__t14-3385802, lane/I/serdes__t14/gen; CTS posthooks after raw13:16 report. 38 groups (512 payload ingress + ENC, reset29, native8), followers0. Raw upstream ring.dch0.u_dsel.y36 -> binq36 hold -619.56 means ingress-only grouping is insufficient; next owner reset_form must trace whole LOCAL readside through actual clk pins up to forwarded-writer barrier. Raw RM bank0q31 -> bout_coll_o0q31 setup -471.03 still needs clock/data separation; do not claim native placement fixes unchanged q/bout positions. Final4ODB targeted STA not yet run.
- H: ep10 oth-ubuntu-426491-1794862085 / client78058, lane/H/gen_boot3_t13.sh; official e37 GEN on coherent strip3 tuple (BIND0, LATCHECK873/873). KitRTL/topology completed0, no config at last read. After GEN refresh actual current native/locksafe source + BOOT3, check actual inventory, review actual placement. Old bound tuple is NOT BOOT3 adoption evidence.

FINISHED, NEXT PHYSICAL FORMS NOT LAUNCHED:
- J2: epyc7 oth-ubuntu-1132048-1794863478 SYNTH_RC0, REG_FANOUT40991/over640, FACE1034/1034. lane/J2 source profile has RCK/RPC8/LOCAL_EMPTY8/LPL_CHUNK/E and current locksafefile. J earlier lint failure (old locksafefile lacked release_chain even BOOT0) preserved; refresh must always copy current dependency. Collect actual mapped inventory/model reconciliation before place: 2216 relay +4reset +9AM +24RPC +8wrap;89writer/89reader chunks;69 bank registers. Then compose native58FF helper + corrected clock family + AM helper, render/look before CTS.
- G2 FINALIZED_PRELAUNCH: epyc7 lane/G2/serdes__t1__clb45db5be/gen/serdes__t1__clb45db5be. Final legality unit oth-ubuntu-1214135-1794863838 EXIT0; no active G2 job. Refined 3_place.odb installed, original3_place.G_before_refine.odb retained, resume.start=cts. Actual maxhop403.164/0>405, shifted2565/4104FTFF,20536data pins/218977FIRM anchors unchanged. Balanced roots [7,6,5,4,3,2,1,41];114/115 atomic to clk;112/113 pinned original9/24 to stop follower cascade. Commit pending source+review artifacts, then reviewed G2 CTS/GRT (32GB8CPU); check ALL7 FT legs/input/output plus112->113->114->115/consumers. G output mechanism already closes (all outputs TT+380.09/FF+181.31); whole G failed internal clock imbalance.

PENDING SOURCE, DO NOT DROP OR STAGE OTHER WORK:
- rx_transport owns cts_post.tcl, gen_phys.py, test_txl_mid_exports.py, rck_am_cohort.tcl, test_rck_am_cohort.py, and current uarch_model.py follow-on changes. AM helper tests15PASS incl deep-root/gated negatives; actual probe3 moved10clock sinks/21FF, TT -70.136 -> -35.437 (inside -42), RCK+304.790, SYN-20.933. Helper FF still pending;147.824ps normalized opposite-edge skew is INFO under latest academic gate, not a new blocking threshold. No blanket physical PASS.
- rm_select owns schema.py, die_plan.schema.json, face_flops_release.tcl, test_ft_keep_firm.py (4focusedPASS), plus results/geom_review/s81_ft_g2_{typed_row_1116.json,model_review_1116.json,review_1116.png,refine_1116.tcl}. gen_phys companion belongs rx_transport. Commit exact paths together; regenerate schema JSON with source, retaining main pg_pin_rule/copy_depth.
- Native RM helper4cbe supports 50 existingFF or J58 incl8wrap; viewed image/5243RM identity PASS, q/wclk/FIRM untouched. Fixed light roots/all-load tails and actual J DPL/CTS remain to measure. Four TYPE-LOCAL t14 RRL >405 edges explicitly owned by START/reset plan owner, distinct from global PLAN4.

STOPPED/PRESERVED: all six C, selector D, phase-pair E, F2, G, old S81-SERDES-DPL t15 were exact-scope stopped after measured whole-form failures. Logs/placement/CTS DBs retained. No active old t13 or failed F scope. Final F2 RCK TT+302.753/FF+26.674, PMA/valid and SYN mechanisms retained; remaining AM/LPL/ingress/reset/global-empty failures have owned successors. G exact scope184798/container184846 verified absent. No evidence or failed verdict overwritten.

Exact six generation+route holds remain in kit_wave. DO NOT POST result:FABLE-FIX-S81-SERDES:serdes-corrected PASS until required corrected whole-type results exist. F2s3 adoption/source readiness alone cannot release the rejected six. No OWNER question from this lane.

Terminal worker clarifications: J2 detailed mapped inventory is NEXT, not completed. REG40991 versus F2 38130 is +2861, while coarse +2794LPL/+8empty is +2802: reconcile the 59-register difference with existing mapped netlist parser, without another Yosys sweep. Expected chunks include356writeOH+356readOH. J2 physical helpers are NOT yet staged: it still has old F2 94-only clocks/cts_post; after inventory stage current family hooks preserving generated footer, native helper+69-bank groups and pending AM source, then review actual placement. Native actual identity/image proof covers50existingFF; future58 has selector checks only. AM FFhold and changed12RXheader checks remain pending on existing probe3 DB. Four type-local reset overreach anchors intersect SRAM: restoring original anchors is invalid; START/reset owns the corrected physical/transport remedy.

## 13:5x PST 11-16 Fable census of C serdes__t13 at CTS (owner of the -517 / -492 class)
- Method: epyc7 fable-fix-s81-serdes/an/t13C (census2.tcl = the kit tt_setup_repair.tcl preamble + report_checks; run2.sh, read-only kit mount; paths.rpt = 294 failing endpoints below -42 ps, TT, placement RC). DB = C/serdes__t13 4_cts.odb after TT repair (F2s2 plan + bind, TXL hook on).
- The -517 on the retired S81-SERDES-DPL F2sv t13 kit is NOT the form of record: that kit has no OT_TXL_MID hook. Same class, older form.
- ot_s81_kp4_dchn is in NO failing path (0 macro stages in all 294). The G0 73-ps-for-wire warning is not what fails here.
- Classes (worst, count): RXNEG half cycle u_rxf_q[*] (rck fall) -> u_dec.u_face_p_d.q[*] -326.0 x197 (launch clock 2229.5 vs capture 1816.1: 413 ps insertion skew against a 416.5 half cycle; data only 366); reset relays u_rrl_N (clk fall) -> u_rrl_M / collect_rst_rl -375.2 x15 (launch 727.9 vs capture 174.4 = 553 skew, data 208); cland_origin -> reader_start_ft*_i -120.2 x18 (631.5 vs 167.7 = 464 skew); u_dec.u_syn am_ok/ldr -> xs/dz/wc -185.7 x60 (20 stages, 13 buffers, + 168 skew: real logic + placement spread); locksafe lock_sync recovery/setup -361.6 x3 (11 buffers of distance).
- So 230 of 294 endpoints are related-sink clock insertion skew (same clock, sinks on different tap trees / depths), not data distance and not a core interface. Fix path = related sinks in one clock cohort (the I / G2 forms) + RXNEG pair placement (E); u_syn am_ok fanout needs a register copy or pipe (RTL, bench + LEC) if it still misses after the cohorts.
- Open: sta worst_slack reads -492.5 while the worst reported path is -375.2 (117 ps gap, endpoint not in the 294; not explained yet). Find it before trusting a whole-form WNS.
- Nothing launched by Fable after 09:3x; live forms are the Codex-run ones listed above.


## Codex handback — Claude reset, 2026-11-16 (supersedes earlier 13:5x status)

PARK ORDER received from root: no new edits/jobs/probes/gates. Existing H/J3/G3 compute continues. Children reset_form (+reset_graph), rx_transport and rm_select have been told to park. All paths below use L=/srv/opentallas-scratch2/claude/fable-fix-s81-serdes unless fully spelled out.

**Source and gates.** Inherited WT epyc7 L/wt, branch claude/fable-fix-s81-serdes-1116. Clean final source tip 1c8178c9ca2ead6829e8292b1934d8c3ef590c89 is fetchable on canonical mirror. Carries 02cb43f BOOT3 mapped-final alias, 849f487 default-off bounded ingress d0 API, 142e54d public explicit-stage0 complete FT sites, and 1c8178c whole-FF clock ancestry guard. Guard rejects functional ICG bypass/enable tie, INV bypass and clock-pin polarity mutants: 40 focused PASS; FT serializer8 focused PASS. Root says exact8a971a513822786713ca5d61cc8ec69778559cd5 snapshot approved; ONE final1c normal gate is authorized behind critical QC gate, no component/intermediate repeats. No physical adoption implied. Public gen RM mover is explicit OT_SERDES_RM_LOCAL=1 only; RTL LOCAL_EMPTY8/RPC/RCK flags do NOT autoenable it.

**Active jobs (last observed; do not restart).**
- H t13 guarded CTS RUNNING epyc2 unit oth-ubuntu-1837673-1794876958,80GB16threads; inherited L/H kit. DPL0, original lock_sync authority FIRM preserved; actual BOOT hops284.951/338.330um, native294.573um;36 reset cohorts max382.860um/244 original direct-clk FF. New source1c ancestry guard/footer verification and approved HOLD-SDC tuple/checker CLEAN, original golden SDC hash unchanged; mapped source hashes match. H_CTS_review.json + images in H kit. No GPL/SYNTH repeat. Earlier apparent resize-moved authority was a same-prefix TIEHI selector bug; actual FF stayed put. Existing OT_RESET_PAIR_FIXED fixes the genuine DPL release. No new restore-after-resize mechanism is needed.
- J3 T14 PLACE active intel2 L/J3/serdes__t14, session58004, authoritative scope oth-ubuntu-3609837-1794874199, container dpkit-serdes__t14-3610047/PID3611370. Last observed DPL random improvement after reordering; earlier overlaps/spacing0. Full LOCAL_EMPTY8/LPL/RCK/RPC architecture, native physical mover OFF. J4 CTS successor NOT CREATED. Prepared L/rx_transport/J3_geometry scripts combine original-SYNTH→final-DPL→after-assignment clock fingerprints, native570/ingress1874/TX per-bit maps and cone geometry in one read. Resume after reset, no duplicate engine.
- G3 T1clb PLACE active intel2 unit oth-ubuntu-3820978-1794875067, session78197, kit L/G3/serdes__t1__clb45db5be/gen/serdes__t1__clb45db5be. Last observed second GPL progressing; no final3_place yet. Exact SYNTH reused, mapped49543FF inventory PASS (RCK2216/reset4/AM9/RPC24/wrap8/LPL12772 with89+89 chunks,356OH each). Native mover OFF, current face helpers and4104 legal G2 FT per-bit sites including stage0 staged before PLACE. Full macro/halo image LOOKED; no active-kit edits after launch. L/G3/physical_stage/G3_placement_successor.json pins exact files. Final pose probe prepared/owned rm_select, NOT launched before park.

**G3 pending clock/model composition.** Original1_synth SHA4857c94bc9448b30fdc5bbcdc5674d764d732c139e571eb3bb9be6a22c1eae89: required ancestry PASS943 proposed RM/reset/control targets and PASS4104 FT targets, all original clk/INV parity0/BUF_INV_ONLY, no functional ICG;4112 PHY writer FF explicitly excluded/preserved. Evidence L/rm_rpc8/ft0_probe/G3_t1_model/G3_*original*ancestry*.{tsv,log}. Final physical q7→clk41 must still be checked. Same directory T1_reset_rows_candidate.json/.png:44 reviewed bounded reset groups/192RRL/371FF,185 compiled reset-edge max385.722um; final G3 pose applicability pending. Native natural old538FF bbox Manhattan402.084um, but existing root13 includes74 distant TX FF (y859..942), so it is NOT a compact isolated clock feed.
- Concrete new native t48 feed owned clock_reach: proposal G3_t1_model/native_feed_proposal.json, pin[1985.048,228.960], clone current13 parent b30607/lk_ES0MY, +3fF parent load priced TT11.144621/FF8.186148ps plus~1.1um differential wire. Zero data cycles/FF. Existing fixed-group selector matches exactly570 native FF=561u_rm+rt_c/rt_d9; excludes rt_e/rt_s2/reset371/PHY writers. Needs fresh typed plan/interface and actual R3 TT/FF contract; current G3 SDC has only clk..clk_t47. NEVER fabricate t48 in active DB or copy old75ps latency. Actual fresh570 geometry/count assertion still required.
- Native input boundary rs_t[1]/g_mid.rt_mr→rt_c/rt_d must get TT/FF checks alongside rt_c→rpq removal and per-bank reset recovery/removal; do not silently broaden570. Tight reset pilot watchlist:182q→collector182 Q→D361.05ps, ideal half margin52.53, existing75ps window leaves TT−22.47, only19.53ps extra adverse physical skew before−42 gate.151/152 similarly tight. Same cohort is NOT closure. Private q-only pairing fallback preserves state/collector/FIRM anchors and all affected hops≤372um; actual RTL has state(posedge)→q(negedge)→collector/nextstate(posedge), BOTH legs halfcycle. No claim a full-cycle leg absorbs distance; both-leg cell/wire floor was being priced when parked.

**I/I2 failure diagnosis and next owned form.** L/I2/I2_result.json is terminal actual full-form FAIL, with measured successful mechanisms preserved. I2 full readside grouping fixed LOCAL→BIN (TT+153.032/FF+123.922), ready95(+270.611/+461.341), relay62→65(+152.838/+543.994), writer barrier(+131.339/+51.927). Remaining exact failures: BIN→ENC FF−39.858; RM output TT−86.115; rt_c→rpq FF removal−95.056; reader START→LOCAL FF−750.192; origin→reader START−90.480; RRL73→BIN/EQ removal−697.870; d0→backend FF−3.775; backend→p_d FF−45.657. Most serious old post-place RM mover stranded anonymous complex mux gates: RPQ→q TT−1610.145, wire933.62ps+cell645ps; REJECT this physical mover. J2 applied58 helper before repair and has coherent final cone max174.2um, so preserve as unqualified evidence, NOT blanket RTL rejection; no J2 CTS.
- New actual p_d254→TX0 TT−489.895/FF+214.035: PDCLK1421.746 vsTX409.901, data171.816/setup23.234/window116.544 actual pairs max762.318um/234>405; TX0 roots19/20/21 vary, so blanket p_d→21 is wrong. reset_form+rx_transport own exact per-bit adjacent-row/root intervals after final J3 pose; no speculative extra RTL stage. Bounded ingress proposal puts1874 LOCAL/BIN/d0/19readerSTART FF on22; backend stays23, origin/forwarded START/writer clocks stay authoritative. All START/reset/data holds above remain explicitly owned for actual repair+TT recheck. I3/J4 physical form not launched.

**The old t13 −492 vs−375 WNS gap is DIAGNOSED, not unresolved.** Default report omitted a max_delay path: io_pma_lock[0]→u_bound.u_core.g_locksafe.u_hold.lock_sync[0]/RESETN, explicit max_delay833ps, input arrival323.6/internal delay1023.946/data arrival1347.5458, required855.0097, slack−492.5361. Last BUFx12 delay403.441ps; two raw reset loads were spread~1192um. BOOT3 later stages alone cannot fix this input path. H authority/BUF locality is the measured remedy in progress. Force this endpoint or use sta::worst_slack_vertex max at H CTS; do not accept only the old default−375 report. Evidence intel2 L/an/t13_gap/{census_gap.tcl,run.log,all_groups.rpt,census_vertex.tcl,vertex.log,worst_vertex.rpt}; source record results/physical/s81_serdes_t13_pmalock_maxdelay_1116.json carried by8a. No SDC exceptions/relaxations.

**Approved HOLD-SDC runtime tuple for NEW checkpoint successors.** intel2 L/approved_hold_sdc_be1 contains hold_sdc_guard.tcl,hold_sdc_check.py,final_ff_hold.tcl,repair_ff.tcl,pregrt_ff_hold.py,hold_pad_hb4.tcl and source_receipt.json with all hashes. Exact source be1ed4fdf6f170efa34824cc98c0146ce98631fa; runtime origin4b77c1216d09863f44b035c9ed96b2af694c5908. Fresh successor config hashes its actual golden constraint SHA[:16]; regenerate pregrt TCL guard source and run approved checker. Do NOT retrofit active J3/G3. H already staged correctly. Future J4/G4 should reuse completed checkpoints without Yosys/GPL repeats where exact source/interface permits.

**Stops/holds and extra wave failures.** C6/D/E/F2/G/legacy DPL measured failed forms were stopped under exact prior authorization; immutable source/DB/logs remain. G2 exact intel2 scope oth-ubuntu-2717625-1794869136/container2717690 inactive/absent; all FT TT+340.95..431.01/FF+67.57..117.26 successes preserved, whole-form RRL112→113 TT−703.86 FAIL remains. G2 final placement SHA20ccfa93b22fff1417938b39d343ce1108befe9f9de7e8aa47e5160a4c3ef4ce seeded legal G3 FT sites. No stops of successors. Six GEN+route holds remain CLOSED; no serdes-corrected PASS posted. Fleet_flow confirmed release must pin exact corrected per-type source/event/profile/native tuple; existing D2 tree readiness plus one global result must not release old recipes. Unrelated eligible types remain eligible.
- ACKed54f35f7354 t12 geom: actual intel1 PLACEunit3799539 exit0,581MB3_place and two reviewed images; sealed wrapper wrongly copied epyc8→epyc9, geom then failed missing checkpoint on epyc9. Queue REBALANCE was chatter; actual geom exit2. t3 class8e5635694b: actual epyc9 physical_completion/dpkit-serdes__t3-4057998.json rc0 and668669443-byte legal3_place, DPL0violations/LEC0; outer command1 after completion with stale truncated run_place.log. Both images LOOKED. No duplicate PLACE. Canonical posts3849e649/a8e86ba3 and hub tails coord/autopilot/kit_wave/s81_serdes__t12_be46dfc38759d/a3/{place,geom}.log and s81_serdes__t3_ba06d4f117307/a6/{place,place_probe}.log. Fleet_flow received exact evidence; explicit shared wrapper/resume owner confirmation requested before park. Respect epyc9 no-new-bulk/job hold. Neither class is a measured timing FAIL or physical SIGN claim.

RMIN remains DRC0, TT>=−42ps, INTERNAL reg FF>=0,833ps/0–25ps uncertainty; port hold/skew/LEC advisory, known functional error never waived. No new clock/uncertainty relaxation, no new worktree/lane, no duplicate engine. At handback there is still NO whole-form SerDes physical PASS claim.


### Final park corrections (authoritative over preceding model wording)
All three children have confirmed PARKED/HANDOFF DONE; reset_form instructed reset_graph to park. No new job, source edit or probe after the reset order. Existing H/J3/G3 continue. Exact H kit epyc2 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes/H/serdes__t13/gen/serdes__t13; CTS startup preflight/SDC lint0 was last observed. J3 final combined probe and G3_pose_extract.tcl/G3_analyze_pose.py are prepared but NOT RUN; do not auto-launch them until Claude resumes ownership.

**t48 is NOT a finished row/qualified feed.** clock_reach final update: same b30607 feed/+3fF/distinct PG coordinate still need strict bounds and a new clock graph. The earlier TT11.144621/FF8.186148ps fanout calibration figures are NOT qualified3fF measurements. Treat them MODEL/unqualified, not evidence of closure. Actual current13 TT early/late7539.163086/8540.111320ps, FF6681.067383/7610.113273ps; common absolute spread must NOT become independent13-versus48 windows. Primitive INVBUF/SEQ TT/FF libraries are staged in clock_reach W/reach_codex/lib_model; that owner is parked. Parent/root/Claude own successor composition. Current G3 still has only ports through47.

**Latest reset fallback is unreviewed.** rm_select local-only /tmp/reset_q_balanced_fallback.json/.png and generator .py: q151[1320.516,229.5],q152[951.804,229.5],q182[1225.098,229.5], all affected hop max190.134um; move sourceINV_3 with q, preserve state/INV_2/collectors/FIRM. BOTH legs remain halfcycle. Image rendered but NOT LOOKED before reset; JSON REVIEWED label is erroneous and must be treated UNREVIEWED. No launch/legalization. Adjacent-only v1 /tmp/reset_q_pair_fallback.json is weaker (max371.952/fault182337.608). Current44-row clock pilot is still separate and not measured on fresh G3.

J3 pending package exact intel2 L/rx_transport/J3_geometry/{combined.tcl,clock_taps_next.tcl,clock_config_next.mk,clock_ancestry_lib.tcl,native_ancestry.tcl,native_group_re.txt,placement_nodes.tcl,tx0_pairs.tcl,select_cone.tcl,target.tcl}. Source1c body SHA97a25a7b20475ddf0967f705639f4dde6d539ca49b4f720eddbcb5774472d2c2, footer preserved; NONE of these new J3 probes ran. J3 actual mapped hash412d43fe5c98, RM_LOCAL0. I2 additional families in L/I2/I2_stage_addendum.json; canonical worker post cb748369. J2 graph14770nodes/21949edges/max174.2um is geometry evidence only. Existing AM mechanism TT−35.437/FF+573.751/headerFF+201.848 remains useful positive evidence; whole form is pending.


# FABLE-FIX-S81-SERDES restart 2026-11-17 01:2x PST (Fable; family owner of the 11 S81 SerDes types)

L = /srv/opentallas-scratch2/claude/fable-fix-s81-serdes (per host). My logs: intel2 ~/fable-fix-s81-serdes/. My probes: E8 L/probes_fable_1117
(dens.tcl + run_dens.sh TAG KIT ODB BIN; run_cts_worst.sh TAG KIT ODB). Partner lane: S81-SERDES-R2 (Opus) owns H5 + H4 reads.
Gate R-MINIMAL: DRC 0, routed TT >= -42, internal reg FF hold >= 0; port hold advisory.

## Form classes (plan_h2_2249 clock.keepouts_um)
- H class (shore band, keepout y > 681): t13 (pilot), t16, t4, t15__cla2127225, t15__cla3d02796.
- G/J class (lot keepout y > 238.76, 75 % of the partition): t1__clb45db5be (G pilot), t1__clfe1f0815, t2, t14 (J pilot).
- t3 (keepout y > 452), t12 (keepout y > 840): own shapes, not yet piloted.

## Finding 1: encoder clump = density target, not region (measured, H3p 5_1_grt.odb)
385,433 movable cells, 56.8k um2, 1.4 % of free area. GPL: -density 0.5 -pad 0, routability mode dropped by OT_GPL_SPARSE.
585 10-um bins at 0.40-0.65 hold 29.3k um2 (52 % of cell area). 247k anonymous XOR cells in two plates: u_enc x 870-990 y 670-780,
u_dec.u_syn x 1230-1360 y 670-740. M8 shorts (7.7k at iteration 0) = M8-grant track obstructions, a separate normal class.
Fix axis: lower the GPL target / pad cells. H5 = 0.30 (R2, epyc2 unit 121200-1794907016). H6 = H5 + 0.20 + GPL pad 2
(mine, epyc2 unit oth-ubuntu-342711-1794908033, kit L/H6 on intel1+epyc2, log ~/fable-fix-s81-serdes/h6-route.out).
Decision rule: first of H5/H6 with routed DRC 0 / TT >= -42 / FF >= 0 is the H-class form; then the same config lines go into the
other four H-class kits and, as a flow default for sparse kits, into gen_phys (branch + gate + READY).

## Finding 2: G4 keepout
Plan type keepout for the G/J class is the whole logical PHY lot [0,238.76,2735.76,1226.88]; the kit PHY supply region (real no-core-cell
zone, pdn.tcl) is only [240.192,947.16,2500.96,1226.88] for t1. Blanket sources: type clock.keepouts_um, die.io phy_macro rect_um
(die_clock.keepouts), die.pg.domains rect_um (VDDPHY M8/M9 grid + bump rows over the lot; phy_macro_um already holds the PMA body).
schema.tap_clear already avoids placement_boxes (real macros), so scoping = plan delta for S81-DIE-R2 (C4 or next event).
G4 CTS r5 exit 0 (E8); post-CTS census running: E8 unit oth-ubuntu-763446-1794908124 -> probes_fable_1117/G4_cts.

## Next
1. Read H5/H6 GPL density (run_dens.sh on 3_place.odb), CTS TT, GRT TT, DRT. Do not route H4 (density 0.5).
2. G4 census -> if local entries fix the G class, post the scoped-keepout delta (exact rects per lot) to S81-DIE-R2.
3. On the first routed PASS: visual review, export AGIdock + rtx-pro, INDEX rows, then the 4 sibling H-class kits.

## 02:2x PST 11-17
- H5 attempt 1 failed at the post-GPL hook (OT_BOOT_RELEASE tail 550.87 um > 405). R2 patched the kit script (tail pull to 380 um) and relaunched H5
  (epyc2 unit 637956-1794909388). Same patched file copied into running H6 before the hook (backup .H6_before_tailpull); H6 passed the hook
  (four rs_r/rs_t tails 554-559 -> 380 um). H6 GPL: max 10-um bin 0.189, HPWL 9.09e9 (+41 % vs H3p 6.44e9); H5 HPWL 7.37e9 (+14 %).
- Branch claude/fable-fix-s81-serdes-sparse-1117@056ad948eaba6c7828deb01a852eb5999e576370 (epyc7 L/wt): OT_GPL_SPARSE_DENSITY / OT_GPL_SPARSE_PAD
  (face_flops.tcl) + generator tail pull (serdes_boot_release_local.tcl, proc ot_serdes_boot_tail_pull) + tests 23/23 in the clone.
  Gate: INFRA twice on epyc2 slot0 (missing asap7_memory_macros_v2 sources in the gate tree). Posted READY-PENDING-GATE; rerun when the slot is repaired:
  ot-run --mem 48 --threads 16 --hosts epyc2,epyc9 --dir /srv/opentallas-scratch2/claude/mq-gate -- bash /srv/opentallas-scratch2/claude/mq-gate/ot-gate-remote claude/fable-fix-s81-serdes-sparse-1117@<sha> 16
- G4 census: TT -656.66 / 817 endpoints, FF -789.04: local entries do not close the G class. Proposal posted (01:4x): G/J lots (t1 x2, t2, t14) to the
  t13 shore-band form (keepout bottom 681.372, SRAM pair re-placed under it, taps in y 238..681); NEEDS-LANE under S81-DIE-R2.
- Watch: H5/H6 4_cts.odb -> run_cts_worst.sh census (copy probes to epyc2 probes_fable_1117; h_worst.tcl + h_parse.py live in E8 probes_serdes_r_1116),
  then GRT TT (grt_policy.json, never 5_1_grt.json), DRT. Not sure yet which of 0.30 / 0.20 keeps TT; kit config lines for the siblings follow the winner.

# FABLE-FIX-S81-SERDES handoff (new lane of 11-18; owner of the 11 S81 serdes types)

## State 2026-11-18 12:40 PST
Nothing is signed off or exported. The clock form is decided and measured at CTS only.

**Form: matched-leg star trunk on io_pma_rck** (main bd76ec2856c: tools/die_plan/rck_star.py, rck_star.tcl, test_rck_star.py; plan key
clock.pad_clock.pins[].star = {evidence, optional max_sinks 200, max_extent_um 100, hop_um 92, cell}; PRE_CTS, planned on the placed
sinks, so one identical row serves all 11 types; absent key = kit byte-identical). Keep OT_S81_RCK_BALANCE on. No rck_island fence
and no type split for the clock. Row posted to S81-DIE-R3 (12:35) for the delta after D8e; not acknowledged.

**Evidence (serdes__t13, kit flow, placement RC TT):**
- H18 single tree: rck p1..p99 172, spread 405; after STB span 109.5 with 1,012 pads. STOPPED FAIL_POSTCTS (TT -191.7 at GRT).
- H20 = H18 placed db + star (stage resume at CTS): 207 entries, 13 x 92 um legs, 14-station feeder (pad x 332); p1..p99 40 before
  balance (spread 576 from outliers), span 65.2 with 689 pads after. Insertion still 1.65-1.9 ns (feeder; the D8e centre pin removes it).
  CTS FF hold screen -374 / 7,390 ends (H18 5,563): no gain shown there. Census 376k non-tap at CTS.
- H19 (S81-CORES-OPUS, km16, no balance): rck still 1.72-1.77 ns at the two flops I read; no rck span line in its log.
- H18 and H19 worst path is ONE recovery endpoint, g_locksafe.u_boot_release.g_stage[0].rq QN -> g_stage[1].rq RESETN (data about 900 ps
  for 363 um; H19 -134.8 post-CTS, H18 -153.5 / gate -191.7). Not the tap band. Fix directed to S81-CORES-OPUS (10:2x, 12:35), no ack yet.
- WITHDRAWN: my km16/km32 harness numbers (-clk_nets builds only the named net). The E/ harness is valid only for geometry dumps and
  read-only STA; clock forms must be measured in the kit (stage resume at CTS, about 35 min).

**Running:** H20 route, epyc9 unit oth-ubuntu-2947704-1795033956, kit /srv/opentallas-scratch2/claude/fable-fix-s81-serdes3/H20/serdes__t13/gen/serdes__t13,
client intel2 ~/fable-fix-s81-serdes3/H20-route-1118.out. It carries the boot-release endpoint: expect FAIL_POSTCTS near -150 at the GRT
gate unless the star skew gain (H18 launch was 90 ps late) keeps it above the triage. Read OT_POSTCTS_GATE, hold cell count, then routed
pair skew. H20 is evidence only (H18 pin and taps, not the D8e form): never export it.

**Blocked:** D8e has NOT applied. Control bind on a30d6c6f (epyc2, 12:33 S81-GEOM-OPUS) is BIND_RC=1: LF_CS_DEPTH 30, RESET_ANCHOR 10,
LOCAL_RESET_RAW 2 on serdes t15 / t1. The countable kits need: D8e applied, the star row, the boot_release fix in the generator.

**Next, in order:**
1. H20 gate result -> post. If it stops on the boot-release endpoint only, that is the expected stop, not a verdict on the star.
2. Boot-release fix: if S81-CORES-OPUS has not posted a generator change, do it here (serdes_boot_release_local.tcl: stage 0 and 1 as
   one cohort, or RESETN of stage 1 on its own short branch); prove on an H20 copy resumed at placement.
3. After D8e (or its successor) applies with the star row: generate serdes__t13 from the plan, route, r708 sign-off
   (signoff.py run, nomcap recipe as in lanes/handoff/S81-CORES-OPUS.md), AUTO-EXPORT; then the other 10 types in parallel.
4. Open clk-domain item: north taps / u_txl.g_reg (-49.7, 22 ends in H18); H19 carries the north-strip tap move, read its tap lines.

Files: epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes3/{E (harness, sta18, sta19, dump), H20}; lane clone intel2
/srv/opentallas-scratch2/claude/fable-fix-s81-serdes3/wt (cone tools, physical/common_flow, rtl, physical/die_plan/s81).

## State 2026-11-18 12:55 PST
- Boot-release stop root cause (H20 4_cts.odb fan-out walk, epyc9 E/fan/fan.log): stage 0 -> stage 1 is ONE private chain with no fan-out,
  but its inverter _341715_ sat at (1113, 511), 544 um west of both flops: chain about 1.37 mm for 363 um. The fix already existed as an
  opt-in (serdes_boot_release_local.tcl ot_serdes_boot_path_local, OT_SERDES_BOOT_PATH_LOCAL); it was never exported and the H kits carried
  an older copy of the hook. Main dc9b82ef5b5: the generator exports it with OT_SERDES_BOOT_RELEASE_LOCAL. S81-CORES-OPUS task withdrawn.
- H21 RUNNING: epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes3/H21/serdes__t13/gen/serdes__t13 (H20 kit + main hook copy +
  OT_SERDES_BOOT_PATH_LOCAL 1 + star; stage resume at PLACE, goal route), client intel2 ~/fable-fix-s81-serdes3/H21-route-1118.out.
  Read: OT_BOOT_PATH line at global place, OT_RCK_STAR + OT_STB_SPAN at CTS, OT_POSTCTS_GATE, route DRC, sign-off line; then r708 re-sign.
  Evidence only (H18 pin/taps): no export. Expect about 6-7 h.
- H20 (no boot fix) keeps running to its GRT gate as the star-only comparison; a background watch in my session reports it.

## State 2026-11-18 17:55 PST (D8e live since 17:37, event 3fa87b84b18, plan df7446e48ba9; no star row in it)
- H19 (km16, no STB, no boot fix): PASSED the GRT gate TT -108.47 / hold -20.48; pre-GRT hold cells 14,776; GRT census 410.3k; in detail
  route (first pass 88k violations). S81-CORES-OPUS reports its routed result.
- H20 (star, no boot fix): CTS span 65.2; post-CTS TT -147.83 (the one boot endpoint); pre-GRT hold cells 19,280 (H18 16,652, H19 14,776);
  GRT hold +919; GRT census 421.1k. GRT TT repair running, gate verdict pending (may stop near -150 on the boot endpoint).
  The star has NOT reduced hold cells so far; its case rests on routed skew, not shown yet.
- H21 first launch FAILED at global place: the current main hook derives the boot stage sites from the DB and got a 413 um hop (> 405) on
  the H18 floorplan (anchor 1769,1222 north strip). Relaunched 17:45 with OT_BOOT_RELEASE_SITES = the H18 sites; client log
  intel2 ~/fable-fix-s81-serdes3/H21-route-1118-r2.out. WATCH the D8e wave kits for the same "derived hop exceeds 405" error.
- D8e wave: fresh attempts are being generated now (serdes__t12 attempt_7 01:31 UTC has OT_SERDES_BOOT_PATH_LOCAL); older attempt dirs in
  3fa87b84b18 are pre-apply and say nothing. Items: <gen host>/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/3fa87b84b18/items/serdes__t*.
- Next delta rows (S81-DIE-R3): star row on the 11 io_pma_rck pins; die-level rck trunk field (asked 17:55, not designed).

## State 2026-11-18 18:15 PST
- D8e wave serdes FAIL class is NOT the 413 um hop. Every attempt I read (17 on epyc8/epyc10/intel1) stops at global place with
  "OT_BOOT_RELEASE expected3 kept stages, found 0": the bound RTL has ot_pdie_serdes_col #(.BOOT_RELEASE_STAGES(0), ...) (die bind
  elaborates without the type define), which overrides -DOT_S81_SERDES_BOOT_RELEASE3; netlist has only released_n, no g_stage.
  Main 2551bd7f342: gen_phys.serdes_boot_stage_param drops that explicit zero in the kit copy of *_bound.sv. NOT yet seen in a
  generated kit: check the next attempt for "OT_SERDES_BOOT_STAGES ... dropped" at gen and "OT_BOOT_RELEASE placed3" at place.
- Still open on real D8e kits: the derived-site 413 um hop (seen only on H21), and OT_S81_LPL_CHUNK: the 6 kits generated
  00:41-01:31 UTC (just before the 01:37 apply) have NO LPL_CHUNK define. Re-check on a post-apply kit; if absent, tell S81-DIE-R3.
- Source fix for the next delta (S81-DIE-R3): the die bind must elaborate serdes with the type defines (or set the stage count).

## State 2026-11-18 18:25 PST
- Compare pilots at GRT / routed only (COORD, S81-GEOM 01c4b1e891d). My CTS-stage numbers were not from 4_cts_final.rpt: -134.8 / -147.8 are
  OT_TT_SETUP_REPAIR and my own STA on 4_cts.odb (after the hooks), rck spans are the OT_STB lines (after padding) - but all placement RC.
- GRT gate, TT setup_est / hold_est: H18 -191.68 / -5.26 STOP; H19 -108.47 / -20.48 PASS (FF +59.2 / -60.3); H20 -99.98 / -10.92 PASS (FF pending).
  H19 and H20 are within 9 ps: no GRT-level case for the star over k-means roots. Routed pair skew and FF hold decide.
- H19 detail route first pass 88,168 violations. H20 entering route. H21 r2 in placement.

## State 2026-11-18 21:15 PST
- Die trunk key defined: main cf3ac71da15, clock.pad_clock.pins[].die_trunk = {from_xy_um, stations_um, layer, host die|type, evidence,
  optional cell}, type frame, hops <= 405 um, validated by pad_clock.die_trunks + schema. NO reader yet (die clock tool / kit): open work.
  Open design point sent to S81-DIE-R3: repeater sites inside a hard type are not die-owned, so host "die" only works unrepeated
  (stations []) or with sites outside the type; host "type" = kit builds the chain (the star feeder already does this in-kit).
- Routed status: none routed. H19 detail route 88,168 -> 18,478 -> 11,584 violations (3 passes). H20 in detail route, no pass line yet;
  GRT gate TT -99.98 / -10.92, FF +67.06 / -27.35. H21 (star + boot path localisation): OT_BOOT_PATH stage 0->1 1518 -> 362 um,
  1->2 1106 -> 340 um; rck span 86.3 after STB; CTS finished 04:59 UTC, GRT gate pending.

## State 2026-11-18 21:35 PST
- Kit-side die_trunk reader on main e4587ebd3e2 (COORD ruling: host type inside the hard type; rows go into D8g, not D8f):
  pad_clock.port_xy (kit port at from_xy_um for host type), pad_clock.trunk_tcl + pad_clock_trunk.tcl (PRE_CTS, last pad-clock hook;
  stations must be within 6 um of a placement row), pct_report in cts_post.tcl. Run once in OpenROAD on the H18 placed db
  (epyc9 E/pct/t.log): 5 stations built, 26,277 loads moved, report line printed. NOT run in a generated kit.
  NOT done: (1) the M8 layer of the row is validated but not enforced on the trunk nets; (2) other readers of the pin xy_um (sidecar
  pad_clock.json, kit_preflight clock_pin_geometry, face_guard, die port position) still use xy_um: audit before the first D8g kit;
  (3) host die segments: no reader. Stations in the PRX/PTX channel are illegal (row-less): D8g rows need stations on rows (y <= 917 on t13).
- Routed status 05:07 UTC: H19 detail route 88,168 -> 18,478 -> 11,584 -> 310 violations; H20 in detail route (no pass line);
  H21 CTS done, heading to the GRT gate. No routed TT/FF yet. Form choice on routed numbers only.
