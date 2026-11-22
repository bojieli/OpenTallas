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
