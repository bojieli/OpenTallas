#!/bin/bash
# safe_add_to_main.sh MSGFILE PATH... : publish exactly the given files (taken from the current worktree) onto the
# CURRENT origin/main without a checkout, refusing anything else.
#
# Why (S-VM incident 2026-10-16 01:30): a plumbing commit built from an index whose base was not the commit used as
# parent (sparse worktree index / origin/main moved by another agent's fetch between read-tree and commit-tree)
# silently reverted other streams' files (447607a6f, 274236276; repaired a0e9430ad).  Guards here:
#   1. the parent P is resolved ONCE (after a fetch) and the temp index is read from that same P;
#   2. git runs on the bare git dir with sparse checkout / sparse index disabled (full tree, no skip-worktree);
#   3. before pushing, `git diff --name-only P C` must equal exactly the requested path list (else abort);
#   4. plain push (fast-forward only): if main moved meanwhile the push is refused and the script retries from 1.
set -euo pipefail
MSG=$1; shift
[ $# -ge 1 ] || { echo "usage: $0 MSGFILE PATH..."; exit 2; }
GD=$(git rev-parse --git-common-dir)
G=(git --git-dir="$GD" -c core.sparseCheckout=false -c index.sparse=false)
want=$(printf '%s\n' "$@" | sort -u)
for attempt in 1 2 3; do
  "${G[@]}" fetch -q origin main
  P=$("${G[@]}" rev-parse refs/remotes/origin/main)
  IDX=$(mktemp); rm -f "$IDX"
  GIT_INDEX_FILE=$IDX "${G[@]}" read-tree "$P"
  for f in "$@"; do
    b=$("${G[@]}" hash-object -w -- "$f")
    GIT_INDEX_FILE=$IDX "${G[@]}" update-index --add --cacheinfo 100644,"$b","$f"
  done
  T=$(GIT_INDEX_FILE=$IDX "${G[@]}" write-tree); rm -f "$IDX"
  C=$("${G[@]}" commit-tree "$T" -p "$P" -F "$MSG")
  got=$("${G[@]}" diff --name-only "$P" "$C" | sort -u)
  # unchanged files (already identical on main) are allowed to drop out of the diff, nothing else may appear
  extra=$(comm -13 <(echo "$want") <(echo "$got"))
  if [ -n "$extra" ]; then echo "ABORT: commit would also change: $extra"; exit 1; fi
  if [ -z "$got" ]; then echo "nothing to publish (all identical on main $P)"; exit 0; fi
  if "${G[@]}" push origin "$C:refs/heads/main"; then echo "PUBLISHED $C on $P: $got"; exit 0; fi
  echo "main moved; retry $attempt"
done
exit 1
