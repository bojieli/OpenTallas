# DIE-HBM-101 lane handoff (HBM die owner, phase 2, ~96 threads). Updated 2026-11-12 06:45 PST.

## 1 Scope
Single HBM owner for phase 2. Succeeds DIE-HBM-100, HBM-HANDPLAN-1, DIE-LAYOUT-HBM, VISLAYOUT2-HBM, CORES-HBM-1, HBM-CORES-B and the hub/root/stale lanes. HBM is at 1/81 types and 89/119 cores signed off.
Priorities: (1) watch the running builds, NO new arms; (2) hand floorplan v2 (after panel, clock spine off the y 8570 seam, b000 at ~620 um vs the L1241 4-beat) plus triage until overflow is ~0; (3) t40w event: fold in the winning forms, the NW ft-band fix, the declared i8w_front shrink (valid only while it is unsigned) and DIE-LAYOUT-HBM's regrow deltas, then post READY.
Visual gate: every new form stops at place until a GOOD or ISSUES-ACCEPT verdict exists.

## 2 Worktree
No git worktree and no branch yet; nothing has been committed. Work files:
- epyc8 /srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane/hbm101/ (b10x_mk.py copy, fp_*.json, run_tri_hp2.sh, hp1_nemirror_analysis.json, v2_analysis.json)
- epyc8 .../hp1lane/plans/hp2/die_plan.json, sha256 0d8f8c3fec86 (ANALYSIS plan, DO_NOT_COUNT)
- epyc8 .../hp1lane/{facepanel_hbm101.py, guidemap_hbm101.py, guidemap_lane_hbm101.py, congsum_hbm101.py}
- epyc8 .../hp1lane/hbm101_hm_hp1/ (GRT heatmap dump run: run.sh, out/combo.tcl)
- localhost scratch /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/hbm/ (w101.sh, v2/draw_v2.py, v2/hbm_hand_floorplan_v2.png/.svg, post101_*.md)
Draft-1 inputs: epyc7 /srv/opentallas-scratch2/claude/hbm-handplan-1/ (v1 drawing + decision table); plans s4q, hp1, s4q_tf, hp1_tf are in epyc8 .../hp1lane/plans/. The B10X-1 beat tool is epyc7 /srv/opentallas-scratch2/claude/hbm-layout-b10x-1/mk.py (half(D, lanes, nb)).

## 3 Running jobs
Core builds (check with: intel2 `grep -a "ot-run: RAN\|SIGNOFF" ~/cores-hbm-1-logs/<log>`):
- vp4_banks_cp vPose3G / vPose3GD: epyc7 .../cores-hbm-1/ot_hgi_dma_back_static_vp4_banks_cp/{vPose3G,vPose3GD}, detail route at 06:10; logs vp4cp_vPose3G(D).otrun.log
- idx_topk D (chan_block + evac): epyc9 .../ot_hbm_idx_topk_link_static/genD/..-D, PAST DPL, CTS at 06:10; topk_D.otrun.log. A2 (CTS) and C2 (GRT) are settings fallbacks: if D signs off, cancel neither, just let them finish.
- fused_lane_c S3C: epyc8 .../hnx_fused_lane_c/flc_S3C, GRT; flc_S3C.otrun.log. The S3B bench is queued: flc_bench_s3b.otrun.log
- q2n2_vm_core A/B: epyc9 .../ot_hfd_coll_q2n2_vm_core/kit{A,B}/..., route; q2n2_{A,B}.otrun.log
- svgr_top A (epyc8 formA) / B (epyc9 formB): GRT; svgr_{A,B}.otrun.log
- rxbm3 SA/SB: epyc7, queued on the load gate; rxbm3_S{A,B}.otrun.log
VISLAYOUT2 (intel2 drivers under /srv/opentallas-scratch2/claude/vislayout2-hbm/kw/<item>/drv.log; the drivers STOP at place, and enqueue is manual after viewing the place density):
- q_su31_g1e + q_su31__physical_v1_g1e: kit_rtl -> place (epyc8 runs_g1e). G1e is the arm that matters.
- q_su31__physical_v1_g1d: comparison only. q_su31_g1d FAILED at prov_views rc 3; it is not relaunched.
- trials 0bed5ae1978b (su30pv1) / 88b8264ee90f (su30): route (intel2 ~/coord/autopilot/jobs/<id>/a1.log), on renders viewed earlier.
- q_su20__physical_v1_su2030: place on intel1.
- q_su11__physical_v1_s1100: preflight. q_su00__physical_v1_s1100 FAILED at preflight (see 8).
Die-level analysis (epyc8, through ot-run from intel2; logs ~/die-hbm-101-logs/):
- hm_hp1.otrun.log: GRT rerun on the hp1_tf kit that dumps the gui::dump_heatmap Routing M9/M8/M7/M6 CSVs into .../hbm101_hm_hp1/out/hm_*.csv. Queued on load. If OT_HM_ERROR appears in out/hm.log, heatmap dumping is not available headless; drop this run (the lane ranking in 5 is already enough).
- tri_hp2.otrun.log: triage of the hp2 plan -> .../hp1lane/tri_hp2/TRIAGE.log (GRT line = total overflow). Queued.

## 4 Watchers (re-arm)
- `bash <scratch>/hbm/w101.sh` (background; exits with one line per new build end, VL2 driver end or trial end; seen file w101.seen). Re-run after each event.
- bench watcher: loop on intel2 ~/cores-hbm-1-logs/flc_bench_s3b.otrun.log for "RAN on".
- hp2 triage watcher: loop on epyc8 .../tri_hp2/TRIAGE.log for TRIAGE_DONE|FAIL.

## 5 Results not yet posted
- Floorplan finding (not yet posted in full): M9 overflow in hp1_tf (M9 324,628) is ft lanes. By lane, using a mean-capacity model on route_TT.guide: NE:L7500 42.9k (31%), NW:L7002 28.7k (21%), NE:L7503 23.6k (17%), NE:L7502 14.4k (10%), NW:L7001 5.4k (4%), together 83%. Clock ck_* is ~2% of M9 gcell spans, so moving the spine is NOT the lever. L7001/L7002/L7502/L7503 run su31 <-> b113 straight N-S through the hub (332-596 b). L7500 is NE_hub -> su21 at 1554 b over 6 hops (the LADDER re-route).
- hp1 left the NE mirrors out. NE_b113|NE_hub stayed at 9.74 pins/um, NE_b100|hub at 7.04, NE_b000|b111 at 6.46, NE_b000|b113 at 6.43.
- hp2 = hp1_tf + 4-beat L5028/L8001/L7500/L5042/L5051 + 2-beat L5076/L5039/L7002/L7503/L7502/L7001: worst face 6.02 (NE_b000|b001; NW_b000|b001 6.00, from L14). Upper-bound cycle cost: +3 x5 +1 x6 = +21 cycles on those lanes; TOK-VERIFY-1 prices it.
- b000 at 620 um REJECTED with numbers. Widening into the hub cuts b111|hub to 106 um (12.5/um) and b113|hub to 598 um (7.45/um). Widening west raises b001|b113 to 8.86/um (shared 478 um). L1241 4-beat (+3 cycles) is the cheaper form.
- S00 preflight fail and tkm A/B results: tkm was posted in the 06:13 STATE; S00 is not yet posted.

## 6 Next steps
1. When tri_hp2 is done: post RESULT (overflow by layer vs hp1_tf 366,443 / M9 324,628). If M9 falls >50%, the lever is confirmed: build hp3 by beat-forming the next lanes from the guidemap_lane ranking (rerun guidemap_lane_hbm101.py on tri_hp2/grt_TT/route_TT.guide), then triage again. Stop when total overflow is ~0, then do the 10.8-um/50-iteration final check. If M9 falls <20%: the hub ft windows are the cause; spread the L700x/L750x hub ft_slots windows, or move them onto M8.
2. Redraw v2 with the triage numbers: `python3 draw_v2.py <dir> '{"s4q":..,"hp1":..,"hp2":..}'` (needs fp_*.json), copy it to epyc7 /srv/opentallas-scratch2/claude/hbm-handplan-1/hbm_hand_floorplan_v2.png, and post REVIEW-REQUEST to GEOM-VIS-5.
3. Clock spine: in v2 the W/E arms stop at the hub edges and the outer x 2.9/25.5 mm branches stop at the band edges. Needs die-clock tool support (a spine keepout); REACH-FIX owns the taps. Low value (clock is ~2% of M9).
4. G0 on the final hp plan (B10X-1 g0.sh on epyc7), rebase onto t40w + pR3x/pR4 (DIE-LAYOUT-HBM deltas, epyc7 hbm-cut-1111/deltas), and fold in G1e if it is GOOD -> t40w READY.
5. G1e at place: view the place density at (1760,1150) east strip; if it is GOOD, enqueue the route (trial); if BAD, do WAIT-FORM.
6. topk D: on sign-off, post CLASS (chan_block + evac for HBM cores with emptied SRAM channels; tkm A's PSM-0069 is the same class) and propose the next tkm form = D's chan_block.

## 7 Open asks
None open yet. The i8w shrink is DECLARED by COORD (05:49), valid only while it is unsigned.

## 8 Gotchas
- `pgrep -f` matches your own ssh shell: kill only exact PIDs from `ps`.
- S00/S11 s1100 run on src_hbm_main_9446d18f5d: preflight macro paths u_fcore.u_core.u_l/u_s are missing in ot_hbm_su_pg_lane_exp_core (plan/src mismatch). They need a src tree matching the plan's macro paths; do not just retry.
- The triage scripts (hbm_triage.sh, triage2.sh) call docker directly; always wrap them in ot-run. Peak RSS of the GRT is ~6 GB.
- hp* plans need fixtaps (q_su20 added_taps names) before the kit; hp2 inherits the fix from hp1_tf.
