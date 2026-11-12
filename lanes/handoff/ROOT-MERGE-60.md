# ROOT-MERGE-60 handoff (2026-11-12 ~14:50 UTC epyc8 clock)

## 1 Scope
Merge lane, successor to ROOT-MERGE-59. Land COORD-APPROVED branches on main via trains. Rules: ~/coord/lanes (LANE-RULES). No force-push, no -X, never run git in /home/ubuntu/OpenTallas. Commit trailer: Co-Authored-By line from the session. Poll lanes/COORD-REVIEW-QUEUE.md (intel2) every ~30 min for APPROVED lines to ROOT-MERGE (59/60).
PD (plan-package-abs 954d9b966565 + die-proto-3 f76c3411bc) is ALREADY on main d767dc851b70 (checked, nothing to redo).

## 2 Worktrees (all on epyc8, /srv/opentallas-scratch2/claude/wt/)
- rm60  = train 60 tip, detached, HEAD 3d65e863df9025ae319370b3f8eeb2c3eb0ae8f3 = d767dc851b70 + merge 52a724781a52 (kv-vn-event, 9fd0c97cb8) + merge 2132a3e0d660 (qc-verify-gaps, base aac9d8eba287, 3d65e863df). Merges are committed, no conflicts. Untracked: tools/die_plan/vclk_measured_band.json (test artifact, ignore).
- rm60-main = main d767dc851b70 (comparison baseline).
- venv60/ = venv (system-site-packages + pytest-xdist). Use venv60/bin/python -m pytest. System python has no xdist.
- Bare repo for fetches: origin = hub:OpenTallas (fetch branches with git fetch origin claude/<name>).

## 3 Running jobs (epyc8)
- runwide60.sh (pids 1189131, 2179672 + pytest children) = wide-list pair, tip and main. Logs: wt/rm60.wide.raw, wt/rm60-main.wide.raw; done markers wt/rm60.wide.done, wt/rm60-main.wide.done; failure lists wt/*.wide.fails. Check: ls wt/*.wide.done; tail wt/rm60.wide.raw. Files: 1021 (tip) / 1020 (main), list in wt/wide.list.
- Never exceed 2 suites at once (SPILL-1), -n 16.

## 4 Watchers / scripts
- Claude Monitor bblgneqhw (persistent): prints 59-style diff and wide diff. Codex must re-arm: until both wt/rm60.wide.done and wt/rm60-main.wide.done exist; then diff wt/rm60-main.wide.fails wt/rm60.wide.fails.
- wt/run60.sh = 59-style runner (git ls-files tools/die_plan/test_*.py tools/autopilot/test_*.py, pytest -q -n 16 --tb=short -rfE --continue-on-collection-errors -p no:cacheprovider -W ignore, junit wt/<v>.xml, fails wt/<v>.fails). Copy of ROOT-MERGE-59 runner /srv/opentallas-scratch3/claude/rm59/e2pj.sh on epyc2.
- wt/runwide60.sh = wide runner. List built by: git diff --name-only <main>..<tip> | xargs -n1 dirname | sort -u -> test_*.py/*_test.py in those dirs + grep -rlE "bind_verify|import bind|from .*bind import|die_plan.bind" in tools physical test_*.py; exclude tools/hier_contract/test_pair_check.py (sys.exit at import). Saved wt/wide.dirs, wt/wide.list. REUSE for next train.

## 5 Results not yet posted
59-style (epyc8, full checkout, -n 16): main d767dc851b70 1145 files, 9494 tests, 41 failed + 2 errors, 37 skipped, 692 s. Tip 3d65e863df 1146 files, 9509 tests, 41 failed + 2 errors, 37 skipped, 648 s. Failure sets IDENTICAL (43 each). Not directly comparable with 59's 58+50 (sparse tree).
Wide list: pending (see 3).

## 6 NEXT STEPS
1. When both wide.done exist: diff wide.fails. Rule: tip failures equal or subset of main's (load flakes OK e.g. test_watchdog CPU sample). If so:
   cd wt/rm60; git fetch origin main; confirm origin/main still d767dc851b70 (if moved, merge new main into tip, rerun affected tests, or re-do train on new main);
   git push origin 3d65e863df:refs/heads/main (no force). Tag flow-20261112-<xx>-<die> if the previous train tags (see 59 MERGED lines: pairs lz-head,na-qc,lu-kv,nz-s81,ow-hbm; pick next unused two-letter prefixes). Post MERGED line to COORD-REVIEW-QUEUE.md via coord-commit.sh with sha, both counts, command.
2. HOTFIX train (COORD approved): claude/kv99-taps-path-1112@ae71bf887a8f (taps.py import Path + test_taps_sink_bins_path.py). Merge on new main; run tools/die_plan/test_taps_sink_bins_path.py test_density_taps.py test_plan_package.py on new main vs tip; push; MERGED.
3. TRAIN after hotfix (full): cef99b3203 (land-override-stale, GEN-CLASS-1) + bfcca667a9 (disk-1111-autoclean-expiry, FLEET-2 guard v2; replaces d18d205756 which is suspended; gate tools/test_ot_safe_swap.py 8 cases) + 3d254c4a7973 (die-s81-87-ready12 package) + 33e70e1695 (cland-slew-1112b; tests tools/die_plan/test_cland_slew_reach.py + landing tests; IGNORE 3375e6375c) + a07f957bc5 (street-fixedface-1112, sits on street-rule 3cca0a68ed so carries both; test tools/die_plan/test_street_rule.py). Hand-resolve additive conflicts; non-trivial conflict -> ASK COORD. Gate: 59-style + wide list (same runner) tip vs main, subset rule; plus the named tests.
4. Then poll queue every ~30 min for new APPROVED lines, land in trains. Post STATE at least every 60 min.

## 7 Open READY/ASK
None posted by me. COORD answers merge approvals; nothing pending from COORD except new APPROVED lines.

## 8 Gotchas
- Plain `pytest .` crashes collection (tools/hier_contract/test_pair_check.py sys.exit at import); use the file lists.
- No foreground sleep; use Monitor or background waits. SSH: timeout N ssh -n -o ControlPath=none <host>.
- Worktree creation on epyc8 full checkout is slow (~10+ min); reuse rm60/rm60-main (git checkout --detach <sha>) instead of making new ones.
- Kill only exact pids. Hub intel2 ~/coord changes only via coord-commit.sh.
