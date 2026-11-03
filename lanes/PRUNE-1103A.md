# PRUNE-1103A — successor of PRUNE-1102B (scratch recovery intel2 / epyc2)

## Start (2026-11-03 03:24 PST)
- Read brief + PRUNE-1102B.md; no queue line 23:41-03:22 names PRUNE (no open ASK/RELEASE). Predecessor left no live jobs (deletions were synchronous).
- df 03:22: intel2 scratch2 191 GB free/95%, epyc2 scratch2 137 GB/84% (root 1.8 TB free), intel1 350 GB.
- Target: intel2 + epyc2 scratch2 >= 300 GB free. Exclusions per brief (PROTECTED-DBS, .keep, refs, tok-/kv-fn-/codex-ds-/vehicle, live, re-sign/stage-resume DBs, idle <24 h).
