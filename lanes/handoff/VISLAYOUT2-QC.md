# VISLAYOUT2-QC lane handoff (refreshed 2026-11-12 08:10 PST)
W = /srv/opentallas-scratch2/claude/vislayout2-qc (same path on the intel2 hub, epyc9, epyc2, epyc7 and intel1). All forms are private DO_NOT_COUNT. QC owner: DIE-QC-100. Hub scripts run on intel2.

## 1 Scope
QC visual re-layouts:
- coll_n forms e/f and sle_su_c (bins), the "suc" set on the s27 private trees.
- The sc family, plan_sc_p, 9 types. COORD rates it WAIT-FORM (E sliver), so its routes are DO_NOT_COUNT probes until the s28 SC re-floor.
- The st_a family, plan_vl2_sta_a, 9 types.
- VISUAL GATE (COORD 11-12): a route counts only after GEOM-VIS records GOOD or ISSUES-ACCEPT for that place attempt in ~/coord/lanes/GEOM-REVIEW.md. Launch no route without a verdict.

## 2 Worktree
- Host and path: epyc9:$W/wt_fo, branch claude/vl2qc-fanout-cap-1112.
- HEAD 7fa736b945, pushed to origin. Commits: 0080dc2d5c PLACE-FANOUT, 90b3fc7310 tap_group schema, 4f3117a95b LEAF-AFF-ASYNC, 7fa736b945 CLAND-PUTS-QUOTE + fanout log-line fix.
- Uncommitted: none of mine. The ARCHIVED.json files there are untracked noise; do not add them.
- Private trees (cp -al; never edit hard-linked files in place, use .new + mv):
  - epyc2 $W/suc/src27 and src27c. Both carry the patched landing_place.py; src27c also carries the gen_phys/gp_noconverge_gate/schema/leaf_affinity patches.
  - SC src: epyc9 $W/sc/src_sc_lr2 (tools/ also synced to epyc7 + planq25).
  - STA src: kw45/src_qc_s25_4e2764d237 (read-only).

## 3 Running jobs
- **suc** (relaunched 2026-11-12 08:10 PST) through suc/go4.sh -> suc/launch3.sh, one per form:
  - sle_su_c: runs/s27b, log suc/launch.log, unit.log in spec/sle_su_c.
  - coll_n e: runs/ce27, launch_ce.log, spec/coll_n.
  - coll_n f: runs/cf27, launch_cf.log, specf/coll_n (f has OT_LEAF_AFF_ASYNC=1).
  - Flow: kit_wave run-item, then posguard, then "WAIT-VISUAL" (polls vis_verdict.py every 5 min), then route on epyc2.
  - Check: grep KW_STAGE_RC <unit.log> | tail, and tail the tag log.
- **Pre-gate routes (11), DO NOT cancel unless BAD:**
  - $W/route_pc.sh (log $W/route_pc.log): sc sle_sc_v2, cl63e5a7a2, cl4590432d (epyc2); sc cl7479a5ec (intel1); sta clb036e152, clf4365a62 (epyc2); sta cl9f076a5c (intel1).
  - $W/route_v3.sh: sle_sc_v3 and slw_sc_v3 (epyc7).
  - sc/route_5e0.sh: slw_sc_v1 cl5e017c6f (intel1).
  - sta/recover_sta.sh: sle_st_a_v1 cl67389ecd (epyc7).
  - Route log: <lane>/spec/<it>/route.otrun.log, which ends with ROUTE_RC=. Sign-off: <kit>/signoff.log on the route host.
- **Still in kit_wave:** sc slw_sc_v2 and sle_sc_v1__cl115da35f (sc/spec/<it>/unit.log). No watcher routes them any more.
- **Older:** stm (sle_stm_v1__clbe630b9c runs/d attempt_2) and hc2 (slw_hc2__cl6bcaba89 runs/e) on epyc9.

## 4 Watchers and scripts (Codex re-arms these)
- $W/vis_cancel.sh (log $W/vis_cancel.log): polls the 11 pre-gate routes. On a BAD verdict it kills that item's ot-run client by PID.
- $W/vis_verdict.py GR ITEM TAG...: prints GOOD|ISSUES-ACCEPT|ISSUES|BAD|NONE.
- suc/launch3.sh: the gated launcher.
- $W/posguard.py: epyc9, epyc2 and epyc7 copies.
- KILLED (they routed without a verdict): sc/route_after_place_sc4.sh and sta/route_after_place_sta2.sh. Do not re-arm them.

## 5 Results not yet posted
- None. Last posts are in COORD-REVIEW-QUEUE.md: GEOM REQ to GEOM-VIS-6, the FLEET-2 deletion class, and the suc RESULT.

## 6 Next steps
1. suc forms:
   - kit_topology must be 0. If sle_su_c fails at kit_rtl, rerun it: an old kit-rtl overlapped about 1 min at 08:2x and was killed.
   - After posguard PASS, the tag log shows WAIT-VISUAL with the kit/geom paths. Post a GEOM REQ to GEOM-VIS-6 with those paths and the tag suc/runs/<r>. The script routes on GOOD/ISSUES-ACCEPT and stops on BAD.
2. When each route finishes, read signoff.log and post a CLEANSLATE2-QC.tsv row (mark SC rows DO_NOT_COUNT probe).
   - coll_n f: check the 4 removal endpoints u_rx.r_rst_n -> u_rxcal.u_rc.c[*].
3. For slw_sc_v2, sle_sc_v1 cl115da35f, sta cl18eece69 and sle_st_a_v2: wait for kit_wave geom, get a GEOM-VIS verdict, and route only on GOOD/ISSUES-ACCEPT.
   - Their epyc9 gen dirs were autocleaned; use the place-host copy as in route_v3.sh.
   - sle_st_a_v2 push_gen failed: restore it from the intel2 hub copy as recover_sta2.sh does.
4. Judge geom with kit_wave.geom_gate (PASS-COND counts), never the raw "AUTO-GEOM PASS" text.
5. The SC E-sliver family re-floor belongs to DIE-QC-100/QC-S28-VISFORM (FINDING 1bc858f08a9). Do it only if handed back.

## 7 Open READY and ASK
- READY claude/vl2qc-fanout-cap-1112@7fa736b945 (5 commits). KW-FIX-46 must answer. CLAND-PUTS-QUOTE also matters for main.
- FLEET-2: the autoclean deletion class (13 live private attempt dirs, epyc9 05:37 PST). The fix is keep roots for private AP_DIR runs.
- DIE-QC-100: suc-hold / suc-hold-2 (sink bins for 17 types).
- GEOM-VIS-6: 11 + 2 verdicts.

## 8 Gotchas
- Never rm the run dirs after a launcher has started. Killing a kit_wave run-item leaves ot-run clients and remote jobs: kill those by PID too before you clean.
- ssh -n with a heredoc gives an empty stdin.
- Kill processes by PID only.
- epyc7 disk is at 95%. epyc2 has a 150 GB floor. Keep new jobs off epyc8/epyc9.
- kit_wave.json qwen_compute gen_args point at the s28 sidecar. The s27 forms re-point it to the s27 sidecar (mkspec_*.py on intel2 suc/).
- kit_rtl.asbuilt must be the tree runtime path, not por15c.
- ot-autoclean on epyc9 can delete private live runs: keep kits on the place host too.
