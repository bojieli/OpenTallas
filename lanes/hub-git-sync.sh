#!/bin/bash
# hub-git-sync.sh -- INFRA2 2026-10-24: ExecStartPre/Post of the hub timers (die-ci-commit, die-ci-nightly,
# release-task-watch) on the ot-run hub (epyc1).  The live coordination dir is rtx-pro ~/coord (branch coord/state);
# epyc1 ~/coord is only a READ MIRROR of origin coord/state.
#   hub-git-sync.sh coord   (1) harvest the DIE-CI lines that die_ci_cron.sh wrote into the mirror's HANDOFF.md
#                               ("DIE-CI LATEST:" replaced in place, "DIE-CI: verdict" appended) and push them to
#                               coord/state (never main); (2) fast-forward the mirror to origin coord/state.
#                               Any other local edit in the mirror -> exit 1 (fail closed, nothing discarded).
#   hub-git-sync.sh repo    fast-forward ~/OpenTallas main to origin/main (clean tree only; never pushes).
set -uo pipefail
C=${HUB_SYNC_COORD:-$HOME/coord}; R=$HOME/OpenTallas; URL=git@github.com:bojieli/OpenTallas.git   # HUB_SYNC_COORD: tests only
say() { echo "hub-git-sync $1: $2"; }
if [ "${1:-}" = repo ]; then
  [ "$(git -C "$R" rev-parse --abbrev-ref HEAD)" = main ] || { say repo "$R not on main"; exit 1; }
  [ -z "$(git -C "$R" status --porcelain --untracked-files=no)" ] || { say repo "$R has local edits; not updated"; exit 1; }
  git -C "$R" fetch -q origin main && git -C "$R" merge -q --ff-only origin/main || { say repo "fetch/ff failed"; exit 1; }
  say repo "main at $(git -C "$R" rev-parse --short=10 HEAD)"; exit 0
fi
cd "$C" || exit 1
exec 9>"$C/.coord.lock"; flock -w 300 9 || { say coord "lock busy"; exit 1; }
git remote get-url origin >/dev/null 2>&1 || git remote add origin "$URL"
OTHER=$(git status --porcelain --untracked-files=no | grep -v ' HANDOFF.md$' || true)
[ -z "$OTHER" ] || { say coord "unexpected local edits in the mirror: $OTHER"; exit 1; }
LINES=$(git diff -U0 -- HANDOFF.md | sed -n 's/^+\([^+].*DIE-CI.*\)$/\1/p')
NOTDIE=$(git diff -U0 -- HANDOFF.md | grep -E '^\+[^+]' | grep -v 'DIE-CI' || true)
[ -z "$NOTDIE" ] || { say coord "non-DIE-CI HANDOFF edits in the mirror; not touched: $NOTDIE"; exit 1; }
git checkout -q -- HANDOFF.md
for i in 1 2 3 4; do
  git fetch -q origin coord/state || { sleep 5; continue; }
  git merge -q --ff-only FETCH_HEAD || { say coord "mirror not fast-forward to origin coord/state"; exit 1; }
  [ -n "$LINES" ] || { say coord "mirror at $(git rev-parse --short HEAD)"; exit 0; }
  python3 - HANDOFF.md "$LINES" <<'EOF'
import sys
p, new = sys.argv[1], sys.argv[2].splitlines()
txt = open(p).read().splitlines()
if any("DIE-CI LATEST:" in l for l in new):
    txt = [l for l in txt if "DIE-CI LATEST:" not in l]
txt += [l for l in new if l not in txt]
open(p, "w").write("\n".join(txt) + "\n")
EOF
  git commit -q -m "DIE-CI (hub $(hostname)): HANDOFF line

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- HANDOFF.md
  if git push -q origin HEAD:coord/state; then say coord "pushed DIE-CI HANDOFF line(s): $(git rev-parse --short HEAD)"; exit 0; fi
  git reset -q --keep HEAD~1; sleep 3
done
say coord "push failed; DIE-CI lines not delivered: $LINES"; exit 1
