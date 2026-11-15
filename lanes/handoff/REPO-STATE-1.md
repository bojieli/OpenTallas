# REPO-STATE-1 handoff (successor, updated 2026-11-14 20:1x PST) -- DONE, waiting on merge + owner decision

Owner order 11-14: ITEM 3 slim repo, ITEM 4 per-lane posts. A history rewrite is an owner decision only (options A/B/C are in the RESULT post; default A = no rewrite).

- ITEM 4: live. bin/post.sh, tools/queue_view.py (fix 0ceab44ffbf), tools/tests/test_queue_view.py (6 pass), coord-commit.sh replay, queue-view.timer (intel2 user systemd, 2 min). Shadow proof: lost 0 / extra 0 after the fix (intel2 /srv/opentallas-scratch2/claude/repo-state-1/proof, proof/reshadow).
- ITEM 3: branch claude/repo-state-1-1114@1fec361e3ce (warn-only per COORD ruling; supersedes 892fe1e318a) is READY to MERGE-QUEUE-1/ROOT-MERGE-63 (guard + allowlist + test + CI job + clone-fast.sh). METHODOLOGY section 13 is in coord 5ca9ffe879b.
- Open:
  - after the merge, MERGE-QUEUE-1 runs `repo_size_guard.py --range origin/main...BRANCH`;
  - COORD rules on the die-plan policy proposal;
  - the owner decides A/B/C.
- Work dir: intel2 /srv/opentallas-scratch2/claude/repo-state-1, ~70 GB. It holds:
  - the clones full/ (branch worktree full/br) and partial/;
  - the timing trees pc-tools, pc-lane (36 G), pc-lane2, pc-coord, wt-tools, wt-lane;
  - g/ (backups: METHODOLOGY.md.bak, queue_view.py.bak).
  - Delete the timing trees freely. Keep full/ until the branch has merged.

## COORD ruling (20:2x)
- clone-fast and the queue_view fix are approved. The guard is now warn-only (1fec361e3ce). No rewrite (A); the owner gets B/C.
- Die-plan gzip is NOT safe until bind.load_plan and schema.load accept .gz; proposed as a follow-up, not started.
- Timing clones are deleted. Only full/ (+ full/br) remains (11 G); delete it after the branch merges.
