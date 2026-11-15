#!/bin/bash
# usage: post.sh LANE "TAG [LANE -> TO; cc ...] text" [more files to commit ...]     (REPO-STATE-1 11-14)
# Appends one post to lanes/posts/<LANE>.md (the lane's own file; no other lane writes it) and commits it with
# coord-commit.sh, which also appends it to the lanes/COORD-REVIEW-QUEUE.md view (tools/queue_view.py) in the same commit.
# The text gets a "- YYYY-MM-DD HH:MM PST " prefix unless it already starts with "- 20". Multi-line text: continuation
# lines are indented two spaces. Extra args are other files of this lane (handoff, lane log) to commit together.
# The old path (append to lanes/COORD-REVIEW-QUEUE.md + coord-commit.sh) still works; the view dedups.
set -e
C=${COORD_DIR:-/home/ubuntu/coord}
lane="$1"; text="$2"; shift 2 || { echo "usage: post.sh LANE TEXT [files]" >&2; exit 2; }
[[ "$lane" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "bad lane name: $lane" >&2; exit 2; }
[ -n "$text" ] || { echo "empty post" >&2; exit 2; }
mkdir -p "$C/lanes/posts"
f="lanes/posts/$lane.md"
case "$text" in "- 20"*) ;; *) text="- $(TZ=America/Los_Angeles date '+%Y-%m-%d %H:%M %Z') $text";; esac
# first line as is, later lines indented (so the view keeps them in this post's block)
body=$(printf '%s\n' "$text" | awk 'NR==1{print; next} {sub(/^[ \t]*/, "  "); print}')
printf '%s\n' "$body" >> "$C/$f"
tag=$(printf '%s' "$text" | awk 'NR==1{print $5}')
exec /bin/bash "$C/bin/coord-commit.sh" "$lane: $tag post" "$f" "$@"
