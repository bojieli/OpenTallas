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
# FLOW-FIX-0100 (FABLE-FLOW-2350 b): one resolve_lane() with case folding (tools/post_redirect.py --resolve): a lowercase twin of an existing lane file is the same lane
if [ -f "$C/tools/post_redirect.py" ]; then
  canon=$(python3 -I "$C/tools/post_redirect.py" --resolve "$lane" "$C" 2>/dev/null) && [[ "$canon" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] && lane="$canon"
fi
f="lanes/posts/$lane.md"
# FLOW-HEALTH-1 11-15 (FABLE-FLOW-1000 class 10: 48 wrong stamps): the stamp is always the America/Los_Angeles clock.  A hand-written
# leading "- YYYY-MM-DD HH:MM [TZ]" that is more than 10 min off that clock is replaced; bin/pst prints the stamp.
PST=$(TZ=America/Los_Angeles date '+%Y-%m-%d %H:%M %Z')
case "$text" in
  "- 20"*)
    lead=$(printf '%s\n' "$text" | sed -n '1s/^- \([0-9]\{4\}-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]\).*$/\1/p')
    if [ -n "$lead" ]; then
      d=$(( $(date -d "$PST" +%s 2>/dev/null || echo 0) - $(TZ=America/Los_Angeles date -d "$lead" +%s 2>/dev/null || echo 0) )); [ $d -lt 0 ] && d=$((-d))
      if [ "$d" -gt 600 ]; then
        text="- $PST$(printf '%s\n' "$text" | sed '1s/^- [0-9-]\{10\} [0-9:]\{5\}\( \(PST\|PDT\|UTC\|GMT\|CET\|CEST\)\)\{0,1\}//')"
        echo "post.sh: stamp '$lead' is ${d}s off the Los Angeles clock; restamped $PST" >&2
      fi
    fi;;
  *) text="- $PST $text";;
esac
# POST-ROUTE-2200 11-20: a post addressed [X -> Y] where Y is stood down (lanes/LANE-STATUS.tsv) also goes to Y's successor chain end.
if [ -f "$C/tools/post_redirect.py" ]; then
  text=$(printf '%s\n' "$text" | python3 -I "$C/tools/post_redirect.py" "$C" 2>/tmp/post-redirect.$$.err) || true
  [ -s /tmp/post-redirect.$$.err ] && cat /tmp/post-redirect.$$.err >&2
  rm -f /tmp/post-redirect.$$.err
fi
# first line as is, later lines indented (so the view keeps them in this post's block)
body=$(printf '%s\n' "$text" | awk 'NR==1{print; next} {sub(/^[ \t]*/, "  "); print}')
printf '%s\n' "$body" >> "$C/$f"
tag=$(printf '%s' "$text" | awk 'NR==1{print $5}')
exec /bin/bash "$C/bin/coord-commit.sh" "$lane: $tag post" "$f" "$@"
