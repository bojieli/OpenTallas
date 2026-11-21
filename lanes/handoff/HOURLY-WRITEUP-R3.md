# HOURLY-WRITEUP-R3 handoff (successor of R2; R2 left no handoff file, its state is in HANDOFF.md 15xx-22xx lines)
Started 2026-11-21 01:05 PST. Each hour: ssh intel2 `cd ~/coord; python3 -I tools/count_hourly.py --force` (auto rows come at :05), `python3 -I tools/failure_breakdown.py --write-release-tree`, two GEOM renders (scp auto_geom.png from the GEOM REQ rows to scratchpad, view, append GEOM VERDICT), then append SIGN-RATE row, replace RELEASE_TREE.md line 3, append HANDOFF.md line, `bin/coord-commit.sh`.
Waiter: background sleep loop about every 60 min. Stand down before 330k tokens: add row to lanes/LANE-STATUS.tsv.
## State 01:40
count 492 any / 407 current, flat since 23:05. No new sign-offs. R2's open items (stage funnel, count explanation): count explained above (474/409 at 22:15 -> 492/407 at 23:05, defer 6 -> 19, retired 59 -> 66, i.e. re-classification on QC/head plan change, not new sign-offs).
DRT scan script: scratchpad drt3.sh (find 5_2_route*.log mtime<180 min under claude/ot-jobs, kit-wave, kw43*, kw45, read head -1 of reports/.../4_cts_post_hook.rpt). Result 01:35: none with TT>=-42 and hold>=0; hosts use UTC clocks in find output.
Scratch watch: intel1 scratch2 free 193 -> 165 GB; cause S81 svc_hi_dsdv_svc_* place jobs (~21 GB each) plus 143 kit-wave attempt dirs; recheck df each hour. epyc7 host key changed (185.189.44.212), ssh refused.
