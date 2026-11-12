# DIE-HBM-101 lane handoff (HBM die owner, phase 2, ~96 threads). Updated 2026-11-12 07:55 PST.

## 1 Scope
Single HBM owner for phase 2. Succeeds DIE-HBM-100, HBM-HANDPLAN-1, DIE-LAYOUT-HBM, VISLAYOUT2-HBM, CORES-HBM-1, HBM-CORES-B and the hub/root/stale lanes. HBM is at 1/81 types and 89/119 cores signed off.
Priorities: (1) watch the running builds, NO new arms; (2) hand floorplan v2 (after panel, clock spine off the y 8570 seam, b000 at ~620 um vs the L1241 4-beat) plus triage until overflow is ~0; (3) t40w event: fold in the winning forms, the NW ft-band fix, the declared i8w_front shrink (valid only while it is unsigned) and DIE-LAYOUT-HBM's regrow deltas, then post READY.
Visual gate: every new form stops at place until a GOOD or ISSUES-ACCEPT verdict exists.

## 2 Worktree
No git worktree and no branch yet; nothing has been committed. Work files:
- epyc8 .../hp1lane/plans/hp3/die_plan.json sha 5d65d8af452b (ANALYSIS, DO_NOT_COUNT); hbm101/b10x_mk.py now re-beats from word_bits; hbm101/run_tri_hp3.sh
- epyc8 /srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane/hbm101/ (b10x_mk.py copy, fp_*.json, run_tri_hp2.sh, hp1_nemirror_analysis.json, v2_analysis.json)
- epyc8 .../hp1lane/plans/hp2/die_plan.json, sha256 0d8f8c3fec86 (ANALYSIS plan, DO_NOT_COUNT)
- epyc8 .../hp1lane/{facepanel_hbm101.py, guidemap_hbm101.py, guidemap_lane_hbm101.py, congsum_hbm101.py}
- epyc8 .../hp1lane/hbm101_hm_hp1/ (GRT heatmap dump run: run.sh, out/combo.tcl)
- localhost scratch /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/hbm/ (w101.sh, v2/draw_v2.py, v2/hbm_hand_floorplan_v2.png/.svg, post101_*.md)
Draft-1 inputs: epyc7 /srv/opentallas-scratch2/claude/hbm-handplan-1/ (v1 drawing + decision table); plans s4q, hp1, s4q_tf, hp1_tf are in epyc8 .../hp1lane/plans/. The B10X-1 beat tool is epyc7 /srv/opentallas-scratch2/claude/hbm-layout-b10x-1/mk.py (half(D, lanes, nb)).

## 3 Running jobs
Core builds (check with: intel2 `grep -a "ot-run: RAN\|SIGNOFF" ~/cores-hbm-1-logs/<log>`):
- vp4_banks_cp: vPose3GD ENDED NOT SIGNED (TT -55.18 / 87 ep: reset recovery rst_g1 16-level BUFx2 + reg2reg a_mv->p_hpart -33; posted). vPose3G still in route (epyc7, vp4cp_vPose3G.otrun.log).
  FORM vPose3R (COORD order, parallel to G; cancel R if G signs off clean): builder VP4-RST-1 (my subagent a451df755f3d2c1c8). Kit epyc7 .../ot_hgi_dma_back_static_vp4_banks_cp/vPose3R: -DOT_DMA_RSTG2 (CONTROL split per family, kept rst_g1 copies, 0 release cycles) + -DOT_DMA_AROWS_Q (rows term registered from z_mv). EQ bench pos RT7/RT80 PASS; place build queued on epyc7, log vp4cp_vPose3R.otrun.log. At place: view + REVIEW-REQUEST to GEOM-VIS-6. Builder also checks in the netlist that each reset copy has D = reset_meta.
- idx_topk D (chan_block + evac): epyc9 genD, topk_D.otrun.log; A2/C2 settings fallbacks.
- fused_lane_c S3C: epyc8 flc_S3C, flc_S3C.otrun.log.
- q2n2_vm_core: A and B ENDED NOT SIGNED (B: TT -266.89 kq3 -> __nl, hold -326.79, slew 643; posted). C reached place (epyc9 kitC/..-die-hbm-101-C): GEOM-VIS-6 07:41 ISSUES (N bank collapsed into a 10-um band at 0.91), and COORD ruled: no route for C.
  FORM C2: builder Q2N2-C2-1 (my subagent a4ef59c02a414ba7e): C + 60-um-deep N bank region + writer_kq stage flops boxed outside the top 20 um (E/W stages within ~50 um of their pins) + u_vmasm SL[*].u.sp select copies per 128-um segment (EQ-proven; also the B slew fix; fold into B's successor). Kit kitC2/, log q2n2_C2.otrun.log, GOAL=place -> GEOM-VIS-6.
- svgr_top A (epyc8) / B (epyc9): svgr_{A,B}.otrun.log. rxbm3 SA/SB epyc7.
VISLAYOUT2 (intel2 /srv/opentallas-scratch2/claude/vislayout2-hbm/kw/<item>/drv.log; drivers STOP at place, enqueue is manual):
- q_su31_g1e + q_su31__physical_v1_g1e: G1e is the arm that matters. g1d comparison only (q_su31_g1d FAILED prov_views rc 3).
- trials 0bed5ae1978b (su30pv1) / 88b8264ee90f (su30): route.
- q_su20__physical_v1_su2030: run-item rc=1 = INFRA (place ran on intel1 exit 0, copy-back to epyc8 failed: clean_hub deleted the gen dir at 02:07). Posted to KW-FIX-46; relaunch after their fix/restage. Also macro col 0 E channel 4.32 < 10.8 um for the visual check.
- q_su11 / q_su00 s1100: FAILED preflight (macro path mismatch, see 8). Not retried.
Die-level (epyc8 via ot-run; logs intel2 ~/die-hbm-101-logs/):
- tri_hp2 DONE: total 172,838 (-53% vs hp1_tf), M9 145,329 (-55%), still 84% of total; L75xx/L700x hub-crossing family leads (posted).
- tri_hp3 RUNNING/queued: plan epyc8 .../hp1lane/plans/hp3/die_plan.json sha 5d65d8af452b, out .../tri_hp3/TRIAGE.log, log tri_hp3.otrun.log. hp3 = hp1_tf + 8-beat L7500; 4-beat L5028/L8001/L5042/L5051/L7002/L7503/L7502/L7501/L7504; 2-beat L5076/L5039/L7001/L5064 (L7000 already 2-beat). +16 cycles over hp2 declared (upper bound +37 over hp1_tf).

HBM-CORES-B (agent adf5204cb4034d7c1, reports to me; handoff ~/coord/lanes/handoff/HBM-CORES-B.md): turn ended, waiting on BMC m0/m2/m3 (time out ~08:50 PST). RDREG=0 equivalence PROVEN (0 unproven). If m0 PASS + m2/m3 FAIL -> it commits on the TREG branch and sends the sha. If m0 times out -> k-induction with internal-state lock-step goals (my choice). Resume it with SendMessage if it stays silent after 09:00. kshare LCREP held on eq0f; ksh_abcrl3/pfrvl3 building epyc8; opsa1_SREG building epyc9.
WBQ: RULING posted (ADOPT the RTL fix). HBM-WBQ-QUAL-1 does RTL + bench + mutant; HBM-CORES-C builds the new g0 kit with --clock-pin-landing on.

## 4 Watchers (re-arm)
- `bash <scratch>/hbm/w101.sh` (background; one line per new build end / VL2 driver end / trial end; seen file w101.seen; includes vp4cp_vPose3R). Re-run after each event. q2n2_C2 is watched by its builder.
- hp3 triage watcher: loop on epyc8 .../tri_hp3/TRIAGE.log for TRIAGE_DONE|FAIL (+ ot-run end line).

## 5 Results posted today (queue lines DIE-HBM-101)
- hp1_tf M9 = ft lanes: L7500 31%, L7002 21%, L7503 17%, L7502 10%, L7001 4%; clock ~2% (spine move is not the lever).
- b000 at 620 um REJECTED (b111|hub 12.5/um or b001|b113 8.86/um); L1241 4-beat instead.
- hp2: worst face 6.02 pins/um; overflow above.
- vp4cp GD, q2n2 B, su20pv1 infra, NO-ROW-SOURCE fix (exp_x view items dropped from hbm only_items, coord 7a7b6489eff), WBQ ruling.

## 6 Next steps
1. tri_hp3 done -> RESULT. If M9 ~0: 10.8-um/50-it final check. If L75xx at row y 10368 um (bins x 24 mm, y 10-11 mm) persists: spread/re-layer the q_hub_ne ft windows on that row (structure, not more beats).
2. Redraw v2 with the s4q/hp1/hp2/hp3 numbers (`python3 v2/draw_v2.py`, needs fp_*.json), copy to epyc7 /srv/opentallas-scratch2/claude/hbm-handplan-1/hbm_hand_floorplan_v2.png, REVIEW-REQUEST to GEOM-VIS-6.
3. vPose3R / q2n2 C2 at place: view the render, REVIEW-REQUEST to GEOM-VIS-6; route only on GOOD / ISSUES-ACCEPT (resume `bash ./run_kit_hbm.sh $K finish 48 8` via ot-run, same env). Cancel R if vPose3G signs off clean.
4. G0 on the final hp plan (B10X-1 g0.sh on epyc7), rebase onto t40w + pR3x/pR4, fold in winners (q2n2 pins + q_hub_ne window, G1e if GOOD) -> t40w READY.
5. G1e at place: view density at (1760,1150); GOOD -> enqueue route; BAD -> WAIT-FORM.
6. topk D on sign-off: post CLASS (chan_block + evac; tkm A same class) and propose the next tkm form.
7. STATE post every 60 min (next due ~08:55).

## 7 Open asks / READYs I must post
- When HBM-CORES-B sends the RDREG+TREG sha (eq_p0d/p1d 0 unproven + bmc_m0 PASS + m2/m3 FAIL): post ONE combined READY to ROOT-MERGE (branch claude/hbm-cores-b-pvm-treg-1112, proofs/pvm_rdreg_1112 + pvm_treg_1112 RESULTS.txt). If anything is still unproven: no READY.
- When eq0f gives LCREP=0 with 0 unproven: post READY for claude/hbm-cores-b-ksh-lcrep-1112@1973ee13bd.
- No other open asks. The i8w shrink is DECLARED by COORD (05:49), valid only while it is unsigned.

## 8 Gotchas
- `pgrep -f` matches your own ssh shell: kill only exact PIDs from `ps`.
- S00/S11 s1100 run on src_hbm_main_9446d18f5d: preflight macro paths u_fcore.u_core.u_l/u_s are missing in ot_hbm_su_pg_lane_exp_core (plan/src mismatch). They need a src tree matching the plan's macro paths; do not just retry.
- On intel2 under nohup use ~/.local/bin/ot-run (full path; nohup does not see the login PATH).
- coord-commit can lose an append in a concurrent merge: always check origin with `git show origin/coord/state:lanes/COORD-REVIEW-QUEUE.md | grep -c <text>`.
- The triage scripts (hbm_triage.sh, triage2.sh) call docker directly; always wrap them in ot-run. Peak RSS of the GRT is ~6 GB.
- hp* plans need fixtaps (q_su20 added_taps names) before the kit; hp2 inherits the fix from hp1_tf.
