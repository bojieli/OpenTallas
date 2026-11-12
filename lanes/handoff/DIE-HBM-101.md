# DIE-HBM-101 lane handoff (HBM die owner, phase 2, ~96 threads). Updated 2026-11-12 07:45 PST.

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
S3A ended NOT SIGNED (posted). S3B bench ended 6/6 PASS, negative control 0/6 (posted).
Core builds (check with: intel2 `grep -a "ot-run: RAN\|SIGNOFF" ~/cores-hbm-1-logs/<log>`):
- vp4_banks_cp vPose3G / vPose3GD: epyc7 .../cores-hbm-1/ot_hgi_dma_back_static_vp4_banks_cp/{vPose3G,vPose3GD}, detail route at 06:10; logs vp4cp_vPose3G(D).otrun.log
- idx_topk D (chan_block + evac): epyc9 .../ot_hbm_idx_topk_link_static/genD/..-D, PAST DPL, CTS at 06:10; topk_D.otrun.log. A2 (CTS) and C2 (GRT) are settings fallbacks: if D signs off, cancel neither, just let them finish.
- fused_lane_c S3C: epyc8 .../hnx_fused_lane_c/flc_S3C, GRT; flc_S3C.otrun.log
- q2n2_vm_core A ENDED NOT SIGNED (setup -280.6, hold -324.37, route render BAD: N-face pile; posted). B still in route (q2n2_B.otrun.log).
- q2n2 FORM C (COORD ruling, parallel to B): kit epyc9 .../ot_hfd_coll_q2n2_vm_core/kitC/ot_hfd_coll_q2n2_vm_core_1dd834f4b149-die-hbm-101-C, GOAL=place, log q2n2_C.otrun.log. Pins pins_q2n2_formC.json from q2n2_repin_hbm101.py, gen script genC.sh (cd wt, git 6d5646ac63). RULES: when place lands, view run/layout_review/place/density.png and post the path to GEOM-VIS-5; after GOOD / ISSUES-ACCEPT resume with `bash ./run_kit_hbm.sh $K finish 48 8` through ot-run (same env as the launch line). If B signs off clean, cancel C (kill only its own ot-run unit). +1 cycle on writer_kq0-7 is DECLARED; the q_hub_ne pins/window update goes into t40w.
- svgr_top A (epyc8 formA) / B (epyc9 formB): GRT; svgr_{A,B}.otrun.log
- rxbm3 SA/SB: epyc7, queued on the load gate; rxbm3_S{A,B}.otrun.log
VISLAYOUT2 (intel2 drivers under /srv/opentallas-scratch2/claude/vislayout2-hbm/kw/<item>/drv.log; the drivers STOP at place, and enqueue is manual after viewing the place density):
- q_su31_g1e + q_su31__physical_v1_g1e: kit_rtl -> place (epyc8 runs_g1e). G1e is the arm that matters.
- q_su31__physical_v1_g1d: comparison only. q_su31_g1d FAILED at prov_views rc 3; it is not relaunched.
- trials 0bed5ae1978b (su30pv1) / 88b8264ee90f (su30): route (intel2 ~/coord/autopilot/jobs/<id>/a1.log), on renders viewed earlier.
- q_su20__physical_v1_su2030: place on intel1.
- q_su11 / q_su00 __physical_v1_s1100: both FAILED preflight (macro path mismatch, see 8; posted). Not retried.
Die-level analysis (epyc8, through ot-run from intel2; logs ~/die-hbm-101-logs/):
- hm_hp1: DONE (exit 0). CSVs in .../hbm101_hm_hp1/out/hm_*.csv sum all layers (the Layer setting is ignored headless); exact-capacity hot bins are posted in the 06:5x RESULT.
- tri_hp2.otrun.log: triage of the hp2 plan -> .../hp1lane/tri_hp2/TRIAGE.log (GRT line = total overflow). Queued.

HBM-CORES-B (agent adf5204cb4034d7c1, LIVE, reports to DIE-HBM-101; its handoff is intel2 ~/coord/lanes/handoff/HBM-CORES-B.md, logs ~/hbm-cores-b-logs/):
- pvm_F2T (F2 + RDREG + TREG) building on epyc9. TREG 243ed13930: all proofs pass. pvm_F2R ended NOT SIGNED (TT -87.42, bp -> TREG).
- RDREG + TREG combined READY: HELD on RDREG equivalence (unproven cells behind the unpaired stack-SRAM rd_out). Blackbox reruns eq_p0d/eq_p1d plus BMC m0 (must PASS) and m2/m3 (must FAIL) are running on epyc2.
- kshare LCREP 1973ee13bd: HELD on LCREP=0 equivalence; the fork a99fe9538ce71ed45 is running eq0f (pairs the renamed shared regs). ksh_abcrl3 / ksh_pfrvl3 are building on epyc8. ksh_pfrvl2 ended NOT SIGNED (TT -4.69, FF hold -199.96, sdc -152.46, DRC 0); the core-owned vs port-start hold split is still open.
- OPSA1 SREG d8c51ee924: READY already posted (by DIE-HBM-100). opsa1_SREG is building on epyc9 (760.32x233.28); on a GRT congestion fail, the outline-growth call is mine (pre-approved; size it from the GRT map).
- b128_canonT / canonU (tie clone) on epyc7. Renders/verdicts due: opsbg_E, q3bc_ISS2EM, dtap_rb, opsa0_B.

WBQ (HBM-WBQ-QUAL-1 reports to me; handoff ~/coord/lanes/handoff/WBQ.md): RULING posted 07:4x. ADOPT the RTL fix (a write-done with 0 matching outstanding writes faults within 2 fifo_clk). kit_g0_cpl ended NOT SIGNED (setup -38.07 on 2 endpoints, hold -85.59 on 1086, DRC 6). Next: WBQ-QUAL makes the RTL change + bench + mutant and posts READY; HBM-CORES-C builds the new g0 kit with --clock-pin-landing on, after classifying the cpl hold/DRC.
HBM-CORES-B update 07:4x: RDREG=0 equivalence PROVEN (7092/7092, 8321/8321, u_stack cut). BMC m0/m2/m3 time out at about 08:50; m1 FAILED as required. If m0 times out: k-induction on the lock-step relation (my choice); stub-fadd BMC is second.

## 4 Watchers (re-arm)
- `bash <scratch>/hbm/w101.sh` (background; exits with one line per new build end, VL2 driver end or trial end; seen file w101.seen). Re-run after each event.
- hp2 triage watcher: loop on epyc8 .../tri_hp2/TRIAGE.log for TRIAGE_DONE|FAIL.

## 5 Results (all below are POSTED by 06:5x; only the hp2 triage is outstanding)
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

## 7 Open asks / READYs I must post
- When HBM-CORES-B sends the RDREG+TREG sha (eq_p0d/p1d 0 unproven + bmc_m0 PASS + m2/m3 FAIL): post ONE combined READY to ROOT-MERGE (branch claude/hbm-cores-b-pvm-treg-1112, proofs/pvm_rdreg_1112 + pvm_treg_1112 RESULTS.txt). If anything is still unproven: no READY.
- When eq0f gives LCREP=0 with 0 unproven: post READY for claude/hbm-cores-b-ksh-lcrep-1112@1973ee13bd.
- No other open asks. The i8w shrink is DECLARED by COORD (05:49), valid only while it is unsigned.

## 8 Gotchas
- `pgrep -f` matches your own ssh shell: kill only exact PIDs from `ps`.
- S00/S11 s1100 run on src_hbm_main_9446d18f5d: preflight macro paths u_fcore.u_core.u_l/u_s are missing in ot_hbm_su_pg_lane_exp_core (plan/src mismatch). They need a src tree matching the plan's macro paths; do not just retry.
- The triage scripts (hbm_triage.sh, triage2.sh) call docker directly; always wrap them in ot-run. Peak RSS of the GRT is ~6 GB.
- hp* plans need fixtaps (q_su20 added_taps names) before the kit; hp2 inherits the fix from hp1_tf.
