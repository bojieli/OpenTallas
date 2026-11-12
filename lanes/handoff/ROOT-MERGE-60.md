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

## UPDATE 06:58 PST
- LANDED hotfix ae71bf887a8f as main (ff, MERGED posted, tags flow-20261112-{ma-head,nb-qc,lv-kv,oa-s81,ox-hbm}). origin/main = ae71bf887a8f.
- LANDING PROCEDURE (main is checked out on hub, direct push is rejected): copy of /srv/opentallas-scratch3/claude/rm55/land2.sh at intel2 /srv/opentallas-scratch2/claude/rm60-land2.sh. Usage on intel2: bash rm60-land2.sh <new-tip> <old-main-sha> <shas-to-verify...>. It flocks ~/coord/merge.lock, needs tip objects in the hub repo (git push the tip to hub as a branch first, e.g. from epyc8 wt: git push origin <tip>:refs/heads/claude/rm60-train-<x>), ff-only merges, pushes to GitHub origin. Tag push from epyc8 worktree: git push origin <tags>.
- Train 60 tip 3d65e863df is based on d767dc851b70; must be re-merged onto ae71bf887a8f (no taps.py conflict expected): in rm60 (after wide2 rerun done) git merge --no-ff ae71bf887a8f into a fresh detached HEAD at ae71bf887a8f then merge 52a724781a52 and 2132a3e0d660 again; rerun touched tests (kv/qc bind tests) and land.
- Wide first run: 6 extra FAILED in test_partition_ft_reserve.py on tip (die_sta pollution, passes alone both); rerun of tip wide list: wt/rm60.wide2.{raw,fails,done}; monitor bxqj7qvr2. Rule: if wide2 has no partition_ft_reserve failures, treat as flake.
- Added to the post-hotfix train by COORD: vl2qc-fanout-cap-1112@4f3117a95b (2 commits beyond main: 90b3fc7310 tap_group schema, 4f3117a95b leaf_aff async; tests test_place_fanout_cap.py test_schema_tap_group.py test_leaf_aff_async.py). The HEAD-94 gp_noconverge get_full_name fix (8e14620b54) is ALREADY on main (checked gate tcl), no extra branch needed.

## UPDATE (supersedes earlier sections where they differ) -- after train 2 landed
STATE: origin/main = hub ~/OpenTallas = adf10c2724821c7a0b9527c723eac1d0edc1f8d4. Landed so far by me: hotfix ae71bf887a8f; qc-verify-gaps (main 8eeefa4716dd); train 2 (7 branches, adf10c27248). All MERGED lines posted. Tags used: ...-ma-head,nb-qc,lv-kv,oa-s81,ox-hbm / mb,nc,lw,ob,oy / mc-head,nd-qc,lx-kv,oc-s81,oz-hbm. Next tags: md-head,ne-qc,ly-kv,od-s81,pa-hbm (check ls-remote first).
RUNNING NOW (epyc8): reach-fix train. Tip da838bbe830 = adf10c27248 + merge dadcdf9535 (REACH-FIX-2; 7 files, no deletions, no big blobs) in wt/rm60 (detached). Main baseline in wt/rm60-main at adf10c27248. Runner wt/run60c.sh (59-style list + wt/t3.list 15 test files referencing reach_fix/dieclock_arrivals/schema), outputs wt/t3-tip.{raw,fails,done,xml}, wt/t3-main.*. Monitor bjzt9i3rj (Codex re-arm: until both wt/t3-*.done exist; diff wt/t3-main.fails wt/t3-tip.fails). Rule: tip failures equal or subset of main (flakes: lone differing tests that pass alone on both trees: re-run them alone, background + monitor, host is loaded).
NEXT STEPS:
 1. On gate pass: push tip to a NEW hub branch name (never force, never reset hub): from wt/rm60 git push origin da838bbe830:refs/heads/claude/rm60-train3 ; then on intel2: bash /srv/opentallas-scratch2/claude/rm60-land3.sh <tip-full-sha> adf10c2724821 dadcdf9535 . (copy at epyc8 wt/rm60-scripts/land3.sh, committed 06fab2e). land3.sh = flock ~/coord/merge.lock, checks hub HEAD==old main==origin/main and clean tree, rejects any blob >95 MB, pushes tip to GitHub main FIRST, ff-merges hub checkout only after success. PUSHFAIL leaves hub untouched. Tags: from wt/rm60 git tag flow-20261112-<xx>-<die> <tip>; git push origin <5 tags>. Post MERGED via ~/coord coord-commit.sh (append to lanes/COORD-REVIEW-QUEUE.md using date +"%Y-%m-%d %H:%M" PST).
 2. KW-FIX-46 train (APPROVED): claude/kw-fix-46-live-kitwave-1112@f1cef955221 (= 3ed2a56b106 + 5ec17be7781 LAUNCH label + 573887bd79f host_share + f1cef955221 item-source probe, each with tests) + claude/kw-fix-46-read-at-commit-1112@f4224a7f4900. Tests are listed in KW-FIX-46's READY of 07:34 in the queue (grep 'KW-FIX-46' near 07:34). Build on new main, same gates (59-style + wide: regenerate wide list as in handoff section 4, plus named tests), big-blob check.
 3. KV vN: kv-vn-event-1112@52a724781a52 BLOCKED (commit 760ab6343e adds 262 MB bind9_asbuilt.json; GitHub rejects). ASK posted to COORD/DIE-KV-98; owner is now DIE-KV-99 (re-issues). Land as its own train when re-issued; run bind tests; land3.sh will refuse >95 MB.
 4. Keep polling queue ~30 min; STATE line each 60 min.
GOTCHAS ADDED: main is checked out on hub, direct push rejected, only land3.sh path. No reset/force anywhere (COORD 11-12). Known flakes under xdist: test_partition_ft_reserve (die_sta module name collision tools/s81 vs tools/die_plan), test_xdie::test_ft_budget, test_ot_macro_track_snap::LaunchGate (root path), test_w17_runtime_integration::test_exact, watchdog CPU sample. Wide list fails ~310 on both sides, 59-style 41+2. 59-style: 1146 files.

## FINAL UPDATE (supersedes all earlier STATE/NEXT sections) -- main 26c9ae03a493
origin/main = hub ~/OpenTallas = 26c9ae03a493517832014183eaffeb7f01a1e505. All my trains are MERGED and posted; each has 5 tags on origin (read back).
Landed by me (in order): hotfix ae71bf887a8f (taps Path); qc-verify-gaps -> 8eeefa4716dd; train 2 (7 br) -> adf10c27248; train 3 reach-fix 7ed95e4f02 -> 89adc6c30b98; train 4a vl2qc 7fa736b945 + twf 0e5ce1603c -> b42b54f8c791; train 6 asbtrace 1c787f2e005e + pvm-treg 02b406d779 -> 1bd40a2be037; train 7 KW-FIX-46 edf6623be211 -> 9c8ff818ef19; train 8 ft-hop-m2 689f54a2fb + tcl-puts-quote 475f0c5d0e -> 26c9ae03a493. Last tags: flow-20261112-{mh-head,ni-qc,mc-kv,oh-s81,pe-hbm}; next free: mi-head,nj-qc,md-kv,oi-s81,pf-hbm (check ls-remote first).
NO jobs running. Worktrees on epyc8 /srv/opentallas-scratch2/claude/wt/: rm60c (tip checkout, train 8 tip 26c9ae03a493 detached), rm60-main (baseline), rm60 (old), venv60 (pytest+xdist). Runner pattern: wt/run60f.sh/run60i.sh (sed copy changing list name t5->tN; list file wt/tN.list = changed tests + tests in touched dirs; 59-style list always included; both runs -n 16, outputs wt/tN-{tip,main}.{raw,fails,done}; diff the .fails). Set rm60-main to the old main sha and rm60c to the new tip before running. Scratch hub branches I created: claude/rm60-train2..8, rm60-train3, rm60-train4a, rm60-train6 (leave them; never force/reset).
LANDING: bash /srv/opentallas-scratch2/claude/rm60-land3.sh <tip-full-sha> <old-main> <branch-shas...> on intel2 (copy: wt/rm60-scripts/land3.sh). Push tip first to a NEW hub branch name from rm60c: git push origin <tip>:refs/heads/claude/rm60-trainN. Tags from rm60c, push, read back with git ls-remote --tags origin. Post MERGED via ~/coord/bin/coord-commit.sh.
STANDING WAITS (nothing to do until posted):
 1. FLEET-2: claude/fleet2-autoclean-unknown-1112 (f8147ba806 + 4a2da75de0, rebuilt on main b42b54f8c791, old-rule test updated). Wait for FLEET-2's READY with the final sha after its 5 suites. Then: build on current main, gate = tools/fleet/test_ot_autoclean{,_dx,_stub,_auto,_unknown}.py + tools/test_ot_safe_swap.py + 59-style, tip vs main. My earlier ASK (85f0fd26f5 dropped main class-d running-process guard) is the reason; check the new tip keeps 20bca54b21/da4defde85/6b8a55ca6b logic: test_class_d_skips_lane_with_running_process must pass.
 2. WBQ: replacement H13 READY (claude/hbm-cores-c-wbqsw-h13-1112, H13 + DCHK 1) from DIE-HBM-101 after its proofs; 746fe8f88aa9 and e1f778f65d are DROPPED. Gate: 59-style list + HBM recipe tests (test_rf1_build_1103::test_rf1_clock_regions must also fail on main).
 3. KV vN: DIE-KV-99 re-issue of kv-vn-event-1112 (52a724781a52 is blocked by 262 MB physical/die_plan/qwen_kvsys/plan_of_record/inputs/bind9_asbuilt.json; land3.sh refuses blobs over 95 MB). Own train, run bind tests.
 Poll lanes/COORD-REVIEW-QUEUE.md every ~30 min for new APPROVED lines to ROOT-MERGE (59/60); STATE every 60 min.
KNOWN FLAKES (tip-only or main-only singles that pass alone on both trees): test_partition_ft_reserve (die_sta name clash tools/s81 vs tools/die_plan under xdist), test_xdie::test_ft_budget, test_ot_macro_track_snap::LaunchGate, test_w17_runtime_integration::test_exact, test_kit_wave_otherfail own_cap_sigkill_247 (shared). Baseline failure counts: 59-style 41F+2E, 1146-1165 files.
