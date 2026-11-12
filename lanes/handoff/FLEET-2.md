# FLEET-2 lane handoff (updated 2026-11-12 10:0x PST)

## 1 Scope
Fleet disk/queue lane (successor of SPILL-1 + DISK-1111; COORD gave me DISK-1111's scope incl. the autoclean branch): epyc4 kw45 source trees, epyc2 scratch2, intel1 as kit-wave host, autoclean safety (unknown-row class), hourly load/queue report. Rules: LANE-RULES (localhost scratchpad /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/LANE-RULES.md). Hub is intel2 ~/coord; localhost ~/coord is a STALE clone: post via `ssh intel2` (append to lanes/COORD-REVIEW-QUEUE.md, `bash ~/coord/bin/coord-commit.sh "<msg>" <paths>`; scp a text file to intel2:/tmp/ first). Never git in /home/ubuntu/OpenTallas. Owner aggressive-cleanup rule; export signed first.

## 2 Worktree
epyc7:/srv/opentallas-scratch2/claude/wt/fleet2, branch claude/fleet2-autoclean-unknown-1112, HEAD 066f52a037 (pushed to origin; 3 commits on main 26c9ae03a493; READY posted to ROOT-MERGE-60; COORD APPROVED and sent it to merge). Clean tree. It replaces the old branch claude/disk-1111-autoclean-expiry-1112 (ab76fa4734 / 85f0fd26f5; DROPPED, its import of the deployed file was stale; do not use). Content: unknown kit-wave row never deleted in any mode; layout_review/geom renders + <snapshot>/visual_hold.txt attempts held; lane-root .keep; driver writes visual_hold.txt from lanes/VISUAL-QUEUE.tsv + kit_wave_state WAIT-VISUAL rows read fresh (<15 min) from origin/coord/state or the hub intel2, else no file (24 h render hold). Keeps main's class-d running-process guard, da4defde85, delete journal. Tests: cd tools/fleet && python3 -I test_ot_autoclean{,_auto,_dx,_stub,_unknown}.py = 40/58/6/17/11 OK (auto takes 7 min: nohup + Monitor). tools/ot_safe_swap.sh + test already on main.

## 3 Running jobs
- Nothing of mine is running now. epyc4 restore finished: kv_main_2041e424bb, kv_main_40e22dd1d2, head_main_m8w1_7b84010b1c, head_h94_9ddabba952, qc_s28_88018018ef are real dirs in epyc4:/srv/opentallas-scratch2/claude/kw45-real, linked from /srv/opentallas-scratch3/claude/kw45/<tree> (both kw45 paths resolve; scratch2/claude/kw45 on epyc4 IS a symlink to scratch3/claude/kw45). qc_s27 and the two hbm p18 trees are intentionally NOT restored (COORD). Partial qc_s27 in kw45-real removed via guarded checks. Check: ssh epyc4 'for t in src_qc_s28_88018018ef src_head_main_m8w1_7b84010b1c; do readlink -f /srv/opentallas-scratch3/claude/kw45/$t; done'. epyc4 sshd resets connections at times: one ssh at a time, retry with backoff.
- localhost archive drives (DISK-1111's, running, progressing, do NOT touch unless hung: check log mtimes): pids 202350/202351/202352 (logs ~/wt-ac2/logs/arch2-epyc{4,7,8}.log) and 467773 (log scratchpad kw46/drive_apply_epyc4_s2.log).
- intel1 pull DONE: 125/125 wave src paths real on intel1 (list ~/f2_paths.txt on epyc8/9/intel1). KW-FIX-46 told.

## 4 Watchers/scripts
None armed. Scripts: epyc4 ~/fleet2_restore2.sh <tree> <srchost> (copy+verify+link), ~/f2_s28.sh, ~/f2_rmpartial.sh; intel1 ~/f2_i1pull.sh; epyc2 ~/f2_move.sh (DO NOT RUN) / ~/f2_undo.sh. ot_safe_swap master copy: worktree tools/ot_safe_swap.sh.

## 5 State of the autoclean timers (important)
All 8 timers (intel1, intel2, epyc2, epyc4, epyc7, epyc8, epyc9 by me; localhost by COORD) run NON-aggressive, --classes abc, in ~/.config/ot-autoclean-auto/env (backups env.bak-fleet2-1112; localhost env.bak-coord-1112). Live file on all 8: ~/.local/share/ot-autoclean-auto/ot-autoclean.py md5 96d3ada9 (has the class-d guard + journal, NOT my fix). The fix is merged only after ROOT-MERGE-60 lands 066f52a037.
Results already posted: epyc4 self-loop loss + correction, epyc7 pkill check, run-dir loss cause, vislayout2 gen loss cause, .keep interim, intel1 ALLDONE, READY 066f52a037. epyc2 scratch2 ~211 GB free (400 target not met; COORD: no more deletes by me). Leftover copies on epyc2: /srv/opentallas-scratch3/claude/f2-moved/{ss29,codex-kv-phy-reset-1551} (originals restored; delete after rsync -aHn -i shows only group diffs; post list).

## 6 NEXT STEPS (COORD woke-me-after-merge plan)
1. Check merge: ssh intel2 'cd ~/coord; grep MERGED lanes/COORD-REVIEW-QUEUE.md | grep 066f52a037' and `git -C <worktree> fetch origin main; git branch -r --contains 066f52a037`. Do nothing until merged (rule: deploy only after merge).
2. Deploy to all 8 hosts (intel1 intel2 epyc2 epyc4 epyc7 epyc8 epyc9 + localhost): per host `cp -p ~/.local/share/ot-autoclean-auto/ot-autoclean.py ~/.local/share/ot-autoclean-auto/ot-autoclean.py.bak-fleet2-1112b`, then install main's tools/fleet/ot-autoclean.py (also wt-reaper.py if main changed it; the localhost drive copies tools to hosts itself, so install localhost first). Verify md5 equal on all 8 and `python3 -I ot-autoclean.py run --help | grep -c visual` not needed; run the 5 suites on main first.
3. One DRY pass per host with the env args WITHOUT --apply (python3 -I ot-autoclean.py run --host <h> <args minus --apply> --state ~/.local/state/ot-autoclean-f2 --snapshot ~/.local/state/ot-autoclean-auto/snapshot). Compare its manifest with the last real one (~/.local/state/ot-autoclean-auto/manifests/*): NO row whose verdict is WOULD/DELETE may be a "kit-wave unknown" attempt, a layout_review/geom/gen of a held attempt, an attempt in visual_hold.txt, or under a .keep. Any hit: stop, do not restore aggressive, post it.
4. Only if clean: in each env file replace "--classes abc" by "--classes abcd" and add " --aggressive" (backups exist); post the exact diff per host; watch the next :30 run's deleted.log for vislayout2-qc, d44v, kv items.
5. Hourly: ot-run --status + load/nproc per host; report hosts <70% load with waiters elsewhere to COORD; STATE post at least every 60 min.
6. Follow-ups: epyc2 f2-moved copy cleanup; epyc4 root 89% (target 85%), epyc2 scratch2 (target 400 GB) via the (then safe) aggressive autoclean only.

## 7 Open READY/ASK
READY 066f52a037 (ROOT-MERGE-60): approved by COORD, in merge. No ASK open.

## 8 Gotchas
- Self-loop: epyc4 scratch2/claude/kw45 -> scratch3/claude/kw45; prove readlink -f + stat dev:inode of trees AND parents before any swap; guard v2 does.
- Aggressive mode deleted "unknown/no-state-row" attempts and lane trees (hbm bind trees, vislayout2 gen, d44v items): do not restore aggressive before the fix is deployed and dry-run compared.
- Root-owned files in some trees: rm -rf can partially delete; guard v2 refuses.
- Timestamps: epyc9/epyc4/epyc7/8 logs are UTC, intel/epyc2/localhost PST.
- rsync -R sets times on /srv and fails: use mkdir -p + --omit-dir-times.
- No pkill; kill exact PIDs. No foreground sleep.
