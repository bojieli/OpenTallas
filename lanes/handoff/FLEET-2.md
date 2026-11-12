# FLEET-2 lane handoff (updated 2026-11-12 08:4x PST)

## 1 Scope
Fleet disk/queue lane (successor of SPILL-1 + DISK-1111; COORD gave me DISK-1111's scope incl. the autoclean branch): epyc4 kw45 source trees, epyc2 scratch2, intel1 as kit-wave host, autoclean safety (unknown-row class), hourly load/queue report. Rules: LANE-RULES (localhost scratchpad /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/LANE-RULES.md). Hub is intel2 ~/coord; localhost ~/coord is a STALE clone: post via `ssh intel2` (append to lanes/COORD-REVIEW-QUEUE.md, `bash ~/coord/bin/coord-commit.sh "<msg>" <paths>`; scp a text file to intel2:/tmp/ first). Never git in /home/ubuntu/OpenTallas. Owner aggressive-cleanup rule; export signed first.

## 2 Worktree
epyc7:/srv/opentallas-scratch2/claude/wt/fleet2, branch claude/disk-1111-autoclean-expiry-1112, HEAD ab76fa4734 (pushed; APPROVED by COORD for the merge lane after KW-FIX-46). Clean tree. Commits on origin tip cb2a23ef3e: d18d205756, bfcca667a9 (tools/ot_safe_swap.sh + tools/test_ot_safe_swap.py, 8 tests), edad026ee4 (imports the deployed ot-autoclean.py, md5 5a3b395e), ab76fa4734 (fix: unknown row never deleted; layout_review/geom renders held 24 h; visual_hold.txt support; lane-root .keep; tools/fleet/test_ot_autoclean_unknown.py 6 tests). Test runs: cd tools/fleet && python3 -I test_ot_autoclean_unknown.py (1 min); test_ot_autoclean_auto.py (4.5 min; only test_reduce fails, pre-existing). Run long tests with nohup + Monitor, never foreground (ssh drops at 120 s).

## 3 Running jobs
- Nothing of mine is running now. epyc4 restore finished: kv_main_2041e424bb, kv_main_40e22dd1d2, head_main_m8w1_7b84010b1c, head_h94_9ddabba952, qc_s28_88018018ef are real dirs in epyc4:/srv/opentallas-scratch2/claude/kw45-real, linked from /srv/opentallas-scratch3/claude/kw45/<tree> (both kw45 paths resolve; scratch2/claude/kw45 on epyc4 IS a symlink to scratch3/claude/kw45). qc_s27 and the two hbm p18 trees are intentionally NOT restored (COORD). Partial qc_s27 in kw45-real removed via guarded checks. Check: ssh epyc4 'for t in src_qc_s28_88018018ef src_head_main_m8w1_7b84010b1c; do readlink -f /srv/opentallas-scratch3/claude/kw45/$t; done'. epyc4 sshd resets connections at times: one ssh at a time, retry with backoff.
- localhost archive drives (DISK-1111's, running, progressing, do NOT touch unless hung: check log mtimes): pids 202350/202351/202352 (logs ~/wt-ac2/logs/arch2-epyc{4,7,8}.log) and 467773 (log scratchpad kw46/drive_apply_epyc4_s2.log).
- intel1 pull DONE: 125/125 wave src paths real on intel1 (list ~/f2_paths.txt on epyc8/9/intel1). KW-FIX-46 told.

## 4 Watchers/scripts
None armed. Scripts: epyc4 ~/fleet2_restore2.sh <tree> <srchost> (copy+verify+link), ~/f2_s28.sh, ~/f2_rmpartial.sh; intel1 ~/f2_i1pull.sh; epyc2 ~/f2_move.sh (DO NOT RUN) / ~/f2_undo.sh. ot_safe_swap master copy: worktree tools/ot_safe_swap.sh.

## 5 State of the autoclean timers (important)
All 8 timers (intel1, intel2, epyc2, epyc4, epyc7, epyc8, epyc9 by me ~07:3x; localhost by COORD 07:55) run NON-aggressive, --classes abc: ~/.config/ot-autoclean-auto/env, backups env.bak-fleet2-1112 (localhost: env.bak-coord-1112). Revert = restore the backup. epyc2 aggressive one-off pass (ot-autoclean-dx) killed. The fix is in the branch but NOT deployed (deployed file md5 5a3b395e on all hosts).
Results posted: epyc4 self-loop loss + correction, epyc7 pkill check, run-dir loss cause, vislayout2 gen loss cause, .keep interim (VISLAYOUT2-QC run roots touched on 7 hosts; lanes told), intel1 ALLDONE, READY ab76fa4734.
epyc2 scratch2 ~211 GB free (target 400 not met; COORD: no more deletes by me). Leftover copies: epyc2 /srv/opentallas-scratch3/claude/f2-moved/{ss29,codex-kv-phy-reset-1551} (originals restored; delete after rsync -aHn -i shows only group diffs).

## 6 NEXT STEPS (COORD order 08:4x)
1. Wire visual_hold.txt writer: driver (localhost `ot-autoclean.py drive` snapshot step, tools/fleet/ot-autoclean.py ~line 2400 writes queue.json etc.) must also write <snapshot>/visual_hold.txt from (a) kit_wave state rows with a WAIT-VISUAL stage/status (see ~/coord/autopilot kit_wave state + lanes/VISUAL-QUEUE.tsv; attempts as absolute paths or item names, one per line) and (b) lanes/VISUAL-QUEUE.tsv. Add a test; commit on the branch; post READY sha. Rule: if neither source can be read, write NO file (the tool then uses the 24 h render hold).
2. After the branch merges to main (merge lane): per host back up ~/.local/share/ot-autoclean-auto/ot-autoclean.py (.bak-fleet2-1112), install main's tools/fleet/ot-autoclean.py, run ONE dry pass per host (env args without --apply) and compare with the last real manifest: no unknown row, no held attempt in the delete list. Also the localhost drive's copy (the driver copies the file to hosts).
3. Only then restore --aggressive --classes abcd in the env files (backups exist), post the diff.
4. Hourly: ot-run --status + load/nproc/waiters per host; report hosts <70% load with waiters elsewhere. Post STATE at least every 60 min.
5. Delete epyc2 f2-moved copies (above) when safe; post list.

## 7 Open READY/ASK
READY ab76fa4734 approved (train after KW-FIX-46). No ASK open.

## 8 Gotchas
- Self-loop: epyc4 scratch2/claude/kw45 -> scratch3/claude/kw45; prove readlink -f + stat dev:inode of trees AND parents before any swap; guard v2 does.
- Aggressive mode deleted "unknown/no-state-row" attempts and lane trees (hbm bind trees, vislayout2 gen, d44v items): do not restore aggressive before the fix is deployed and dry-run compared.
- Root-owned files in some trees: rm -rf can partially delete; guard v2 refuses.
- Timestamps: epyc9/epyc4/epyc7/8 logs are UTC, intel/epyc2/localhost PST.
- rsync -R sets times on /srv and fails: use mkdir -p + --omit-dir-times.
- No pkill; kill exact PIDs. No foreground sleep.
