# CLEAN-2 lane handoff (updated 2026-11-12 17:5x PST)

## 1 Scope
Fleet disk cleanup rules (COORD task 11-12): why ot-autoclean frees ~0 GB; fix on branch; DRY-RUN every host; RESULT to COORD; STOP for approval before any real delete/deploy. After approval: export signed first, deploy per host as a new inode, verify freed GB.

## 2 Worktree / branch
localhost:/home/ubuntu/wt/clean2 (sparse clone, tools/fleet only), branch claude/clean-2-1112 off origin/main 12994e9e69, HEAD f5c127da65 pushed. NOT merged, NOT deployed.
Change: ot-autoclean `--live-refs-only` (host flag) + hub reduce_live() (additive kitwave.json fields live_attempts/live_keep/live_keep_why) + snapshot protected_stale.txt + wt-reaper `--tracked-ok`; `--wt-reaper-state`, `--wt-reaper-args=` for dry runs. Tests: test_ot_autoclean_live.py 21 OK; existing suites OK (auto 58, unknown 11, dx 6, stub 17, ot_autoclean 40, wt_reaper, wt_reaper_generic 4).

## 3 Running jobs (dry only, nothing deletes)
Every host (intel2 intel1 epyc2 epyc4 epyc7 epyc8 epyc9 localhost): ~/.local/share/ot-autoclean-clean2/in/clean2_dry.sh (dry B: env args minus --apply + --aggressive --live-refs-only, no wt-reaper, state ~/.local/state/ot-autoclean-clean2/aggr, log dryB.log) then clean2_dryA.sh (dry A: env args minus --apply + --live-refs-only, wt-reaper dry --no-rescue with its own state dir; log ~/.local/state/ot-autoclean-clean2/dryA.log). Both end with DONE. Snapshot = copy of the host's deployed snapshot + kitwave.json from the new reducer (run read-only on intel2 17:32) + protected_stale.txt (1755 paths).
Deployed timers untouched (md5 96d3ada9, env non-aggressive --classes abc).

## 4 NEXT
1. When DONE everywhere: per host GB WOULD by class + 5 sample paths per class (manifests in ~/.local/state/ot-autoclean-clean2/manifests and .../aggr/manifests; wt-reaper last-run in .../wt-reaper/last-run.tsv) -> RESULT to COORD via intel2 coord-commit.sh.
2. WAIT for COORD approval. Then: READY branch for merge; after merge: archive signed (drive --apply archive step) first; deploy tools per host as new inode (cp to tmp + mv); add --live-refs-only to env; verify freed GB with df before/after.

## 5 Gotchas
- argparse: pass --wt-reaper-args=--no-rescue (with =).
- the drive's push copies tools with cp onto the existing file (same inode): deploy must be via the drive's script = merged main.
- localhost ~/coord is a stale clone; hub is intel2.
