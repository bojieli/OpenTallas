# FAM-S81-COL-R5 handoff (Opus; started 2026-11-21 11:0x PST; successor of FAM-S81-COL-R4)
Scope: col_h9_r1 and col_h9_r2, plus the shared J7 col rows. h9_r0 = FAM-S81-COL-H9R0-R3. h10, FIT selector and hard-core view fix = FAM-S81-COL-H10-R3 (COORD dispatch 11-21). Work dir: /srv/opentallas-scratch2/claude/fam-s81-col-r5 (epyc8/9/10/2). The R4 proof dirs stay at fam-s81-col-r4.
## Done
- SAFETY: on epyc8, src_rb shared 309,141 inodes with the J5 tree kw45/src_s81_pin_3c913dbdfb23_d8j6r1_1117_work. Each one is now a real copy. src_tc links only to src_rb (nlink 2, 0 files above 2). J5: verify --ro OK (files 328061) and links OK. Log: epyc8 fam-s81-col-r5/verify_j5_post.log.
- Strays: all deleted 11-21 via rt/current ot-delete (file mode); posted CLEANUP DONE.
- Ruling 2a (h9_r1 pv047ea3b3): rk/rank.py joins the placed_raw legs to the routed ep_tt.tsv of dear-crayfish (epyc2) kits pv047ea3b3-4010677 and pv4bd36c74-2843429. Only 127 legs in 5 groups fail: xa_4->t4/xai, xb_5->t5/xbi, xb_4->t4/xbi (all RLYBR already), and c5_6->s5/q6 and c7_6->s7/q6 (19 legs each, 410 um). Some fails come from no long leg: s5/s6/s7 q3, e5/6/7/9 xs_q0/xs_q1/cfg_d, bn6/e_r0; these need a path read. COORD: NO new station rows while FIT fits 0 (both h9_r1 kits fit 0/80).
- Fix #4 per-class placed check: table posted to S81-J6-ASSEMBLY-R4 (posts 11-21 ~12:0x). Probe tool: fam-s81-col-r5/probe/probe_cls.py + runprobe.sh + runall.sh (docker, read-only). Flag: h10_r0_p4 xo strip (DRT 31). In J7 v7, 53 h9_r0 types have e3 at y 648. 13 classes have no placed DB.
## Running
- hub chain_e8.sh (R4 name, posts redirect here): rb_e8 (RLYBR rep) and tc_e8 (bank taps), both at geom 11:36 PST. Then place, then route on epyc8. Read t4/xai, t5/xbi, t4/cci and s5/s7 q6 from sign-off ep_tt.tsv. Compare against the ranking above.
## Next
- After the J7 bind (apply 11-22 04:15) and the H10-R3 FIT fix: run one place+GRT private kit (kit_wave.py private-spec) per h9_r1/r2 class (7) and run the probe on each.
- mkresite: after the J7 bind, read the longest bound reset hop on h9_r0_p1/p3/h9_r2. If the captured bound_native_reset bypassed it, write the bound_reset_placement overlay. The 146 residual reset hops (R4 rc/rrl_try.json) are held under the COORD station-row stop until FIT is fixed.
- Carry the H10-R3 FIT and view fix to the h9_r1/r2 siblings once it is proven.
- e3 y 648 flag (53 h9_r0 types) posted to S81-J6-ASSEMBLY-R4 + FAM-S81-COL-H9R0-R3.
## 18:2x PST resume (after the weekly limit; Codex covered 14:23-18:1x)
- Adopted these Codex posts filed under my lane: FIT-poly replay 83/87 fit (14:47); rb/tc CTS TT -36.11/-35.73 (15:18); old D8 pv047ea3b3 xai93 analysis (18:02).
- rb_e8 and tc_e8 are in GRT on the old obs_gcell_cap.tcl, inside the slow OBS planner (one core at 100%; logs last written 13:48 and 14:23 PST). The fix 86cda1125201 is in rt/current. hub chain_e8 waiters are alive.
- Plan: if GRT shows no progress by 22:00 PST, relaunch one arm from 4_cts with the refreshed obs_gcell_cap.tcl, copied and mvd into a new kit dir, on epyc10 or epyc2. E8 is 9999-drained.

## 11-22 07:0x PST update (FAM-S81-COL-R5)
- J8 rows (intel2 + epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-r5/j8/):
  - COL-H9R1-IST-SITES sha fc17a6c28976: removes sites=float on pv1c15776f internal_stations[6] (frame_int_o1). This fixes the J7 kit_rtl "native station sites missing". Proof is in epyc10 j8/chk.
  - COL-RST-RESITE sha a9a12d7e46a2: removes the 138 col types from reset.relay_resite_skip_types. Reset hops over 405 um drop 1075 -> 485, 0 cycles. Residual list: rows_COL-RST-RESITE_J7_residual.json. The 485 hops go to J9 (leaf tap-relay slide), ETA 11-23 10:00 PST.
- GATE: epyc10 j8/ (plan_j8r5.json sha ec692ca478d7, symlinked plan dir, ot_build.log, ob/). Script rst/gate_j8r5.sh, started 06:53 PST; local waiter bnc6kbd7s.
- tc_e8 cancelled 14:08Z: DRT flat at 1430, Lef58EolKeepOut on hard-core pins (H10-R4 owns the pin-access fix). GRT TT classes = H10-R4 class 1 (qbank -> e*.u_w) + class 2 (ROM c*_6 -> s* q6). The lever is COL-E15E-CHAN / COL-H10R2-CTAP.
- Worst-path report on epyc8 grtread/run2.sh tc writes ep2_tc.tsv.to.

## 11-22 10:1x PST update (FAM-S81-COL-R5)
- J8 gate GREEN (epyc10 j8/ob/b_0ce2d64bf6cc): strict bind 0 errors, LATCHECK 873/873, pv1c15776f 28 is_place per o1 station. Handed to S81-J6-ASSEMBLY-R5 (hub ede1742a0c9).
- Solid-view proof kits (COORD 07:xx): intel2 fam-s81-col-r5/wave_tc8s2 and wave_rb8s2 (rt 0890cc9405b7, --ab OT_POROUS_VIEWS = 9 modules without hw/he/payload536, goal route). Work dirs epyc8 fam-s81-col-r5/kits/tc8s2 and rb8s2. run-item pids on intel2: 3668210 (tc, KW_RUNITEM_NO_UNIT=1) and 3650263 (rb). In CTS since 09:00. Auto-geom FAIL (advisory). The src_manifest seal was refused (R4 private trees).
  READOUT: Lef58EolKeepOut count in 5_route_drc.rpt vs tc_e8 at 1430, then GRT TT from the final 5_1_grt.odb.
- Finding: tc_e8 and rb_rest used the porous rewrites of the J8 base LEFs (POROUS-DEFAULT-s81.tsv), so the EOL markers trace to the porous splice. H10-R4's vprobe5 control is that same porous hw LEF.
- J9: 485 residual reset hops, ETA 11-23 10:00 PST.

## 11-22 19:5x PST update (FAM-S81-COL-R5)
- tc8s2 (solid J8 views) FAILED GRT-0116: overflow 2831 vs 1924 porous. The EOL fix belongs in the porous LEFs 9924dfc8290c / 659819b4718b / 0187b355ac71. Asked H10-R4 (hub 6d878c00f3a); no reply yet. When the fix exists: one sealed private col_h9_r1 kit with --goal route, plus a twin with --ab OT_PROBE_THROUGH=1 (rt >= 5fb3e1e7822). rb8s2 was stopped.
- J9 COL-RST-TAPSLIDE: epyc10 fam-s81-col-r5/j9/ (row, plan_j9_tapslide.json be87d01d774c on J8 f65f62779bef). PRE PASS 0 findings; reset hops 485 -> 437.
  - Strict bind: waiter intel2 pid 522540 (fam-s81-col-r5/wait_j8_then_bind.sh, log wait_j8_then_bind.log) launches rst/bind_j9.sh once the assembly lane posts J8 GATE GREEN. Then read j9/ot_build.log and post.
  - Builders: rst/slide_probe.py -> rst/slide_j8.json; rst/mkslide.py.
- Residue of 437 hops: proposal posted (05703bff2bb) to close it by routed recovery measurement. tc_e8 GRT has 0 failing reset endpoints; the worst reset recovery slack is +249 ps.
