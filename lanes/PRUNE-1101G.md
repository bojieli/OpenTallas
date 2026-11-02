# PRUNE-1101G localhost root (md0p1) prune

- 2026-11-01 19:47 PST MANIFEST (before delete): df / = 89% used, 405G free. 38 paths, 179.0 GB. Patches/untracked lists: /home/ubuntu/coord-scratch/prune-1101G/.
- Checks per path: no file modified <12 h (find -mmin -720), no process cwd/fd/argv inside (/proc scan + ps), not in PROTECTED-DBS.txt, no non-tracked .keep (the tracked results/rtl/dsrom_recovery_20261004/levers/.keep in every checkout is a repo file, not a protection marker), no refs in origin HEAD (git grep), lanes/*.md, or 707k *.f/*.mk/PROVENANCE.json/recipe json/tcl/sh under /srv/opentallas-scratch/claude, ~/artifacts, ~/wt, live wt-codex-*. Registered worktrees removed with git worktree remove --force; no branch deleted.
- signoffwave1030 note: INFRA-DISK-3 (10-31 07:24) called ~/signoffwave1030 live; head_recipe has no file newer than 10-30 09:45, branch pushed -> removed. Its small sibling dirs (~100 MB) kept.
- KEPT: all other 110 worktrees (files <12 h), wt-claude-closure-daemon-1010 (code of running closure-loop.service), codex-token-1101 / codex-signoff-1101 (lane refs), codex-hbm-tailmax-balanced-1101 (07:59 files + lane ref), ~/.claude/jobs worktrees, ~/artifacts, ot-scratch/qwen-recovery-jobs/scratch-qwen-tp8-die/exactness-fixtures (repo refs), hgi_ds_subset (model weights), *preserve*/*retire*/*retention* dirs, /tmp/dh53host.

```
path	MB	mtime	class	reason
/home/ubuntu/signoffwave1030/head_recipe	45788	2026-10-30 07:25	wt	registered worktree codex/head-wave-stage-1030 (pushed), idle since 10-30 09:45, 2 untracked saved
/srv/opentallas-scratch/claude/wt/codex-kv-macro	525	2026-11-01 06:15	wt	registered worktree codex/kv-macro-1101 (pushed), 14 untracked saved, idle since 06:28
/srv/opentallas-scratch/claude/wt/codex-s81-pg-parts-1101	507	2026-11-01 06:33	wt	registered worktree codex/s81-pg-parts-1101 (pushed), untracked tmp/ list saved
/srv/opentallas-scratch/claude/wt/codex-s81-multiroot-1101	357	2026-11-01 06:04	wt	registered worktree codex/s81-sta-canary-1101 (local branch kept; only a merge commit unpushed), clean
/home/ubuntu/wt-clkplan	10	2026-10-27 19:17	wt	registered worktree claude/oss-clkplan-1027 (pushed), idle since 10-27, diff+untracked saved
/srv/opentallas-scratch/claude/wt/codex-head-1101	35698	2026-11-01 05:50	orphan	unregistered partial checkout (no .git), idle since 11-01 05:50
/srv/opentallas-scratch/claude/wt/codex-kv-macro-interrupted	42609	2026-11-01 05:56	orphan	unregistered interrupted checkout (no .git), idle since 11-01 05:56
/home/ubuntu/scratch-el1013-smh-r11	5410	2026-10-13 03:44	run	superseded 10-13 el1013 run scratch, unreferenced
/home/ubuntu/s81-fe-fault-native-1014	5388	2026-10-14 04:28	run	superseded 10-14 S81 fe fault run, unreferenced
/home/ubuntu/s81-fe-fault-local-native-2e054e8e9	2156	2026-10-14 05:30	run	superseded 10-14 S81 fe fault run, unreferenced
/home/ubuntu/tput-scratch	5218	2026-10-11 03:02	run	superseded 10-11 tput scratch, unreferenced
/home/ubuntu/ds-hbm-import-base-20261003	3460	2026-10-03 05:28	run	superseded 10-03 repo snapshot, unreferenced
/home/ubuntu/nhbvp	3401	2026-10-03 04:47	run	superseded 10-03 build runs, unreferenced
/home/ubuntu/scratch-fill-s2	2939	2026-10-15 13:27	run	superseded 10-15 fill gate runs, unreferenced
/home/ubuntu/lvscratch	1931	2026-10-03 00:40	run	superseded 10-03 scratch, unreferenced
/home/ubuntu/b2vm_scratch	1783	2026-10-12 14:54	run	superseded 10-12 scratch, unreferenced
/tmp/release-tree-plan.06jxebm9	1518	2026-10-31 01:07	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.0tf39zsk	1085	2026-10-30 06:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.aco05x22	1486	2026-11-01 06:49	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.bunxzrqh	921	2026-10-29 16:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.dp8db5h7	702	2026-10-29 02:25	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.fl9i07kt	1557	2026-10-31 19:49	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.h3nc26xz	1085	2026-10-30 10:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.i7tyoa37	922	2026-10-29 22:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.jzfeds8_	1441	2026-10-31 18:49	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.k3x37ak8	1085	2026-10-30 07:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.lp_o7js4	702	2026-10-29 06:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.ns5tld54	1560	2026-11-01 00:49	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.oz_airvz	1560	2026-11-01 01:49	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.tau8nxwl	1531	2026-10-31 05:45	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.tn06423r	701	2026-10-29 01:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.uflw76u3	922	2026-10-29 21:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.ukdew081	702	2026-10-29 07:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.wgie7y1w	1551	2026-10-31 14:49	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.wwy6h0dv	1085	2026-10-30 11:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.ywdtqeh_	1074	2026-10-30 05:40	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.z_cw5kx_	1396	2026-10-31 03:26	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
/tmp/release-tree-plan.znwn1kew	1560	2026-10-31 22:49	tmp	leaked release_tree_plan.py temp dir, idle >12h, no open files
```
- 2026-11-01 19:48 PST RESULT [CHECKED df]: deleted 38/38 manifest paths, 179.0 GB (6 registered worktrees via git worktree remove --force, 2 orphan checkouts, 9 superseded 10-03..10-15 run scratch dirs, 21 leaked /tmp/release-tree-plan.* dirs). df / 89% 405 GB free -> 84% used, 584G free. (Brief start 90%/383 GB; codex-hardchildren-1101 24.5 GB was removed by another actor before my delete, not by this lane.) Nothing killed, no branch deleted. Follow-up for owner/COORD: release_tree_plan.py leaks ~1-1.6 GB mkdtemp dirs per run in /tmp (7 recent ones kept); main .git has 40 GB loose objects (1.0M, 31k prune-packable) -- a scheduled git gc in a quiet window would recover tens of GB.
