# VISLAYOUT2-QC lane handoff (refreshed 2026-11-12 06:51 PST)
W = /srv/opentallas-scratch2/claude/vislayout2-qc (same path on intel2 hub, epyc9, epyc2, epyc7, intel1). All forms are private DO_NOT_COUNT. QC owner: DIE-QC-100.

## 1 Scope
QC visual re-layouts of the s25/s27 private forms: coll_n (forms e/f), sle_su_c (HOLD-TAP-SPLIT bins), the sc family (plan_sc_p, 9 types) and the st_a family (plan_vl2_sta_a, 9 types). Each form goes through place, geom, posguard and route to sign-off. Post the results to CLEANSLATE2-QC.tsv and COORD-REVIEW-QUEUE.md.

## 2 Worktree
- Host and path: epyc9:$W/wt_fo, branch claude/vl2qc-fanout-cap-1112.
- HEAD 4f3117a95b, pushed to origin.
- Commits: 0080dc2d5c PLACE-FANOUT, 90b3fc7310 tap_group schema, 4f3117a95b LEAF-AFF-ASYNC.
- Uncommitted: none of mine. The ARCHIVED.json files there are untracked noise; do not add them.
- Private src trees (cp -al, never edit hard-linked files in place):
  - epyc2 $W/suc/src27 and src27c (they live on scratch3).
  - epyc9 suc/src27v is the bind tree.
  - SC src: epyc9 $W/sc/src_sc_lr2. The tools/ dir is also synced to epyc7.
  - STA src: kw45/src_qc_s25_4e2764d237 (read-only).

## 3 Running jobs (intel2 hub orchestrates, kit_wave.py = kw38/rt)
- suc: 3 run-items via suc/go3.sh: sle_su_c (runs/s27b), coll_n e (runs/ce27), coll_n f (runs/cf27). Gen runs on epyc2; place on epyc2/intel1, then posguard and route on epyc2.
  - Logs: suc/spec/{sle_su_c,coll_n}/unit.log and suc/specf/coll_n/unit.log; suc/launch2_*.out.
  - Check: grep KW_STAGE_RC <unit.log> | tail.
- sc: run-items under sc/spec/<item>/unit.log; result.json is in the same dir.
  - sc/geom_route_sc.sh re-runs geom on epyc7 for 6 items (log sc/geom_route.log), then posguard and route.
  - sc/route_5e0.sh routes slw_sc_v1__cl64543eaf__cl5e017c6f on intel1.
  - sc/route_after_place_sc4.sh (pid 3802073) is the original watcher.
- sta: run-items under sta/spec/<item>/unit.log.
  - sta/recover_sta.sh routes sle_st_a_v1__cl67389ecd on epyc7.
  - sta/recover_sta2.sh restores the 3 place-FAIL items from the hub copy to epyc9, then runs geom on epyc9, posguard and route. Log: sta/recover2.log.
  - sta/route_after_place_sta2.sh (pid 3957507) watches the rest.
- Route logs: <lane>/spec/<it>/route.otrun.log, which ends with ROUTE_RC=. Sign-off: <kit>/signoff.log on the route host.
- Still routing on epyc9: stm (sle_stm_v1__clbe630b9c runs/d attempt_2) and hc2 (slw_hc2__cl6bcaba89 runs/e).

## 4 Watchers and scripts (Codex re-arms these)
- sc/route_after_place_sc4.sh
- sta/route_after_place_sta2.sh (RHMAP in sta/run_sta2.sh)
- sc/geom_route_sc.sh
- sta/recover_sta2.sh
- suc/launch2.sh (runs posguard and then route itself)
- $W/posguard.py (epyc9 and epyc2 copies). Fixed 11-12 for u_bound.<inst> core names and for a missing grt_transition.json.

## 5 Results not yet posted
- coll_n f: clk_t2 estimate about 266 ps (reach 295 um). The tap group raises clk from about 287 to about 393 ps.
- Everything else is posted (COORD-REVIEW-QUEUE commit 1bc858f08a9).

## 6 Next steps
1. When suc kit_topology is 0 for all 3, wait for place. On place PASS, launch2 runs posguard and route itself. If kit_topology fails, read the kit_topology log. The asbuilt must be the tree runtime path, and --clock-landing must be the s27 sidecar (27b0eca895ef).
2. Route done means read signoff.log and post a CLEANSLATE2-QC.tsv row (TT/FF WNS, DRC, LEC).
   - coll_n f: check the 4 removal endpoints u_rx.r_rst_n -> u_rxcal.u_rc.c[*]. If they are still negative, post a FINDING on OT_LEAF_AFF_ASYNC.
3. sc geom2: on PASS the script routes. On "AUTO-GEOM FAIL" or "NO VERDICT", read spec/<it>/geom2.log and fix the class, never one item.
4. sta recover2: same rule as step 3.
5. The sc family E sliver (GEOM-VIS-3/4 ISSUES) needs a family re-floor (see FINDING 1bc858f08a9). Do it only if DIE-QC-100 or QC-S28-VISFORM hands it back.
6. Each item that passes place must get a visual render review (GEOM-REVIEW) before you call it good.

## 7 Open READY and ASK
- READY claude/vl2qc-fanout-cap-1112@4f3117a95b. KW-FIX-46 must answer (merge).
- ASK FLEET-2: who removed $W/sta/runs/a/items/*/attempt_1 on epyc9 on 11-12 between 01:32 and 05:40?
- suc-hold and suc-hold-2 (sink bins for 17 density types without bins): DIE-QC-100 must answer.

## 8 Gotchas
- Never rm the epyc2 run dirs after go3.sh has started. Clean first, then launch; the race costs a kit_rtl failure.
- ssh -n with a heredoc gives an empty stdin, so check.json comes out empty.
- Kill processes by PID only. pgrep/pkill -f matches your own ssh shell.
- epyc7 disk is at 95% (408 GB free). epyc2 has a 150 GB floor. Keep builds off epyc8/epyc9 for new place jobs.
- kit_wave.json qwen_compute gen_args point at the s28 sidecar now. The s27 forms must re-point it (the mkspec_*.py do).
- intel2 is the hub only: no heavy jobs, and no git in /home/ubuntu/OpenTallas.
