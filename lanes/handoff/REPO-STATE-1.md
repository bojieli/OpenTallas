# REPO-STATE-1 handoff (successor, 2026-11-14 19:3x PST)

Owner order 11-14: ITEM 3 slim repo (measure, stop growth, fast clones), ITEM 4 per-lane posts. History rewrite = owner decision only (propose, never do).

Work dir: intel2 /srv/opentallas-scratch2/claude/repo-state-1 (full/ = full clone, partial/ = blob:none clone, measure.json, cands.json, proof/ = shadow proof, pc-*/wt-tools = clone-fast timing trees; all deletable when this lane closes).

## ITEM 4 (live since 18:54)
- bin/post.sh, tools/queue_view.py (+tests), bin/coord-commit.sh own-files replay; queue-view.timer (2 min, intel2 user systemd).
- Shadow proof: proof/ 62 min from 18:55 -> proof/shadow_result.json (lost/extra must be 0).

## ITEM 3
- Measured (fresh clone intel2 19:05): full clone 18:29 wall, 10.7 GiB pack, 16,342 refs; partial blob:none 1:29.
- clone-fast.sh timings: --from worktree 8.1 s; partial preset tools 78 s / 741 MB; preset lane (see RESULT).
- Next: guard branch (tools/repo_size_guard.py + test + allowlist + CI step), clone-fast.sh branch, METHODOLOGY section, RESULT + owner-decision numbers.
