# HOURLY-WRITEUP-R5 handoff (successor of R4, R4 left none; chain R3 file has older method)
Method each hour (~:15 PST): ssh intel2, cd ~/coord; run `python3 -I tools/count_hourly.py --force` then `python3 -I tools/failure_breakdown.py --write-release-tree` in background via nohup sh -c (redirect stdin/stdout to /dev/null or ssh hangs; check /tmp/wr5_done2). If count_hourly says "another run holds the lock", rerun later. Confirm lanes/SIGN-RATE.tsv row. Two GEOM renders: find auto_geom.png on intel1 (find /srv/opentallas-scratch*/claude -name auto_geom.png -mmin -1500), scp to scratchpad, Read, append verdict to ~/coord/GEOM-REVIEW.md (it is at coord root, not lanes/). Update line 3 of RELEASE_TREE.md (replace prefix up to "Blockers:"), append HANDOFF.md line, then bin/coord-commit.sh. Hosts epyc4/epyc7 have changed host keys; epyc10 has no matplotlib.
## State 23:15 PST 11-21
530 any / 434 current (was 528/432 at 22:05). S81 46/394, HEAD 25/26, QC 57/127, KV 6/56, HBM 4/84. Deferred 21, retired 75.
## State 00:15 PST 11-22
544 any / 437 current (was 530/434 at 23:05). QC 60/127, S81 46/394, HEAD 25/26, KV 6/56, HBM 4/84. Deferred 21, retired 86. LECGATE-R2 un-revokes in the row: the 6 committed (COORD said 10 of 24; check git log --grep un-revoke next hour). GEOM renders: used KV hub die_plan pngs from fable-fix-head-lep0n-r5 clone (find on epyc10 timed out, no fresh auto_geom.png on intel1/epyc9). Always run nohup jobs with </dev/null.
## State 01:25 PST 11-22
548 any / 438 current (was 544/437 at 00:05). QC 61/127, S81 46/394, HEAD 25/26, KV 6/56, HBM 4/84. Deferred 22, retired 88. LECGATE: 6 un-revoked, 18 revoked. Waiter: scratchpad wait.sh as run_in_background, then ssh nohup count job with </dev/null.
## State 02:30 PST 11-22
548 any / 438 current, flat vs 01:15. RESUMED 02:18 after limit (no jobs of mine live). GEOM source this hour: flow-canary runs/*/gen/*/run/layout_review/place/layout.png (fresh, found with find -mmin -240 on intel2). LECGATE: 6 un-revoked, no new commits.
## State 03:20 PST 11-22
549 any / 439 current (+1/+1 vs 02:18). QC 62/127, S81 46/394, HEAD 25/26, KV 6/56, HBM 4/84. Deferred 21, retired 89. Private kits: no renders yet for col_h9_r0 or hub_Ei (ls private dirs on intel2 found no png); use FAM-S81-* private dirs under kw43-wave-1109n/.../a9ed808a98d/private. Round fired 03:05 (COORD asked 03:1x).
## State 03:30 PST 11-22
549 any / 439 current flat vs 03:05 (round fired 03:15 because wait.sh targets the next :15 more than 5 min away; COORD wants ~04:15, so next waiter armed for 04:15). GEOM: canary place renders only (private kits have none yet).
## State 04:30 PST 11-22
549 any / 439 current FLAT since 02:32 sign-off. Wave 2/2/0; disk all above floors. Owner ruling 04:14: no-growth rule withdrawn. GEOM: found private kit renders under epyc9 .../a9ed808a98d/private/<LANE>/<kit>/geom/auto_geom.png (use ls -dt then find). Next round 05:15 (wait2.sh with hard-coded time; edit 04:15 -> 05:15).
## State 05:25 PST 11-22
550 any / 440 current (+1/+1 vs 04:15, KV kv3_io_cor). wave stalled 04:24-05:01 fixed. Round fired 05:05 on COORD request; waiter bs82axith (05:15) stopped; next waiter armed for 06:15 (wait2.sh edited).
## State 06:35 PST 11-22
558 any / 447 current (+8/+7 vs 05:05): S81 cores 68 (+6), QC types 63 (+1). Waiter pattern: wait2.sh with hard-coded HH:15; count job started inside the same bg command that waits (output file only fills at the end). Next round 07:15 (edit wait2.sh).
## State 07:25 PST 11-22
558 any / 447 current FLAT vs 06:15. Round run at 07:05 on COORD request, waiter bl0kmb4dd stopped, next waiter for 08:15.
## State 08:35 PST 11-22
562 any / 452 current (+4/+5 vs 07:05): S81 cores 72, QC types 64. J7 wave items live under kit-wave/s81/18a2688b741/items/*/geom/auto_geom.png (intel2). Next round 09:15 (waiter armed). After commit, verify HANDOFF line exists (a 07:05 commit once reported NOTHING-COMMITTED).
## State 09:25 PST 11-22
563 any / 453 current (+1/+1 vs 08:15, QC slw_st_b_v1__cle6023ec2). Wave 93 S81 launches, 9 BIND-GEN-TOOLSKEW fails fixed. Next round 10:15 (waiter armed).
## State 10:25 PST 11-22
565 any / 453 current (any +2, current flat vs 09:06). QC slw_sc_v2 signed 09:59 counted as superseded. Next round 11:15 (waiter armed).
## State 17:35 PST 11-22 (RESUMED after weekly limit)
574 any / 459 current (+9/+6 vs 10:05). Missed 11:15-17:15 rounds; auto SIGN-RATE rows exist at 11:15/12:15/13:15/14:14. Next round 18:15 (wait2.sh edited to 18:15).
