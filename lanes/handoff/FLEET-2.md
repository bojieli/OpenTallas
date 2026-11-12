# FLEET-2 lane handoff (updated 2026-11-12 06:5x PST)

## 1 Scope
Fleet disk/queue lane, successor of SPILL-1 and DISK-1111: epyc4 root and kw45 trees, epyc2 scratch2 capacity, intel1 as kit-wave host, hourly load/queue report, guard for spill-copy swaps. Rules: ~/coord LANE-RULES (scratchpad copy: /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/LANE-RULES.md on localhost). Never touch other lanes' builds; no git in /home/ubuntu/OpenTallas; owner aggressive-cleanup rule (keep live/queued refs, signed, protected; export signed first).

## 2 Worktree
epyc7:/srv/opentallas-scratch2/claude/wt/fleet2, branch claude/disk-1111-autoclean-expiry-1112, HEAD bfcca667a9 (pushed to origin; contains guard v2 tools/ot_safe_swap.sh + tools/test_ot_safe_swap.py on top of DISK-1111's cb2a23ef3e). No uncommitted files. Master copies of scripts: localhost scratchpad /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/ (ot_safe_swap.sh, test_ot_safe_swap.py, f2_*.sh).

## 3 Running jobs
- epyc4 restore of 4 kw45 trees from epyc9/epyc8/epyc2 into REAL dir /srv/opentallas-scratch2/claude/kw45-real (nohup ~/fleet2_restore2.sh <tree> <srchost>): src_head_main_m8w1_7b84010b1c (epyc8, log ~/f2_head_main.log), src_kv_main_40e22dd1d2 (epyc9, ~/f2_kv40.log), src_kv_main_2041e424bb (epyc2, ~/f2_kv20.log), src_head_h94_9ddabba952 (epyc9, ~/f2_h94.log). 93 GB of ~182 GB at 06:52. Check: ssh epyc4 'grep -h "LINKED\|MISMATCH\|COPYFAIL\|NOTREAL" ~/f2_*.log; du -sh /srv/opentallas-scratch2/claude/kw45-real; pgrep -af "rsync -aH"'. Each script verifies (rsync -aHn --delete empty) then ln -sfn kw45-real/<tree> -> /srv/opentallas-scratch3/claude/kw45/<tree>. NOTE /srv/opentallas-scratch2/claude/kw45 on epyc4 is a symlink to scratch3/claude/kw45, so both paths resolve to the link location.
- epyc2 autoclean (DISK-1111's, not mine): ot-autoclean-dx pid ~3714793 --aggressive; scratch2 120 -> 213 GB free by 06:45. A dry run of mine in ~/.local/state/ot-autoclean-f2 left a sticky ALERT file there (425 protected hits at recheck); harmless, state dir is separate from -dx.

## 4 Watchers/scripts
None re-armed. REAL_ADMIT watchers on epyc4/intel1 finished clean (1 h, no revert). Scripts: epyc4 ~/fleet2_restore2.sh, intel1 ~/f2_i1pull.sh, epyc2 ~/f2_move.sh and ~/f2_undo.sh (done; do NOT re-run f2_move.sh).

## 5 Results not yet posted
- intel1 pull DONE 06:48 PST: all 125 wave src/bind paths (KV, S81, HEAD, QC; list: scratchpad f2_paths.txt, also epyc9/epyc8/intel1:~/f2_paths.txt) exist as real copies on intel1 (verify-missing=0, log intel1:~/f2_i1pull.log). intel1 scratch2 ~480 GB free. KW-FIX-46 NOT yet told: post RESULT [FLEET-2 -> KW-FIX-46, COORD]. HBM trees not copied. Check the wave src check accepts intel1 (kit_wave src_incomplete) before claiming intel1 is a host.
- epyc2 f2-moved leftovers: /srv/opentallas-scratch3/claude/f2-moved/ss29 and codex-kv-phy-reset-1551 (copies; originals restored in place, only group differs). Delete both after one more rsync -aHn -i compare shows only group diffs, via rm -rf --one-file-system (my own copies). Needs a post of the deleted list.
- Earlier results are already posted (epyc4 loop finding, epyc7 pkill check, intel1/epyc4 REAL_ADMIT clean, guard READY).

## 6 NEXT STEPS
1. Post the intel1 RESULT to KW-FIX-46 (above). Rule: only after wave src check passes for intel1 (run kit_wave src_incomplete as in epyc7 fleet2 worktree tools/autopilot/kit_wave.py with ~/coord/autopilot/kit_wave.json); if a die fails, copy the named missing path from epyc8 the same way (mkdir -p parent; rsync -aH --omit-dir-times epyc8:P parent/).
2. Wait for epyc4 restore; when all 4 show LINKED, post RESULT (list), tell KW-FIX-45/46 that kv/head kw45 trees are real on epyc4. Per COORD ruling do NOT restore qc_s27, hbm p18, hbm_rd1 p18 on epyc4 (re-pull only if a live/queued row must run on epyc4). If a script shows MISMATCH, re-run it (rsync is resumable); never link an unverified tree.
3. epyc4 root is 89% (target <=85%): no safe swap exists now; rely on aggressive autoclean hourly; do not swap trees without guard v2 (ot_safe_swap.sh --apply) and snapshot refusal files.
4. epyc2 scratch2 target >=400 GB: COORD ruled no more deletes by me; check df hourly and report; autoclean-dx continues.
5. Hourly: load vs nproc, waiters (ot-run --status), admit headroom per host; report hosts <70% load with RAM and waiters elsewhere to COORD. LOAD_GATE_FACTOR=1.1 stays on epyc2.
6. Await COORD approval of guard READY bfcca667a9 (supersedes suspended d18d205756); on ruling hand to merge lane. Post a STATE line every 60 min.

## 7 Open READY/ASK
READY [FLEET-2] claude/disk-1111-autoclean-expiry-1112@bfcca667a9: COORD must approve to the merge lane. No ASK open.

## 8 Gotchas
- epyc4 scratch2/claude/kw45 -> scratch3/claude/kw45 symlink made the DISK-1111 swap a self-loop and deleted 7 trees. Always readlink -f + stat dev:inode of trees AND parents before any swap.
- Root-owned files in some epyc2 trees (lecrun/*.aig, __pycache__): rm and chgrp fail; never rm -rf a tree without a deletability proof.
- rsync -R tries to set times on /srv: use mkdir -p + --omit-dir-times.
- Do not move/delete dirs named by autoclean snapshot protected.tsv/queue.json/kitwave.json or the kit-wave keep list (the epyc2 move of die-kv-64-rfc, codex-wave-1105, grt-patch-1 was wrong; undone).
- KV "pruned bind worktree" FAILs at 06:06/06:31 were not caused by my move (first posted before it); cause unconfirmed (suspect wt-reaper idle-2h worktree prune); KV owner DIE-KV-98 to check.
- restage_waiters is autopilot-internal (kit_wave.py); no CLI. ssh form: timeout N ssh -n -o ControlPath=none <host>. No pkill; kill exact PIDs. No sleep in foreground (use Monitor).
