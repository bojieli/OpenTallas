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
# FLOW-FLEET-R2 S1 11-22: a post that is not valid UTF-8 (one 0x94 byte made every autopilot tick skip hold recompile / tree switch / UNBLOCK / LOOP-GAPS for ~1 h) is refused here
_g="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/utf8_guard.py"
if [ -f "$_g" ]; then printf '%s' "$text" | python3 -I "$_g" --text || { echo "post.sh: refused, fix the text (invalid UTF-8)" >&2; exit 1; }; fi
mkdir -p "$C/lanes/posts"
# FLOW-FIX-0100 (FABLE-FLOW-2350 b): one resolve_lane() with case folding (tools/post_redirect.py --resolve): a lowercase twin of an existing lane file is the same lane
if [ -f "$C/tools/post_redirect.py" ]; then
  canon=$(python3 -I "$C/tools/post_redirect.py" --resolve "$lane" "$C" 2>/dev/null) && [[ "$canon" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] && lane="$canon"
fi
# FLOW-PROC-B 11-21 (FABLE-FLOW-0800 class b): a post filed under a stood-down lane (ot-run DONE/DIED lines carry the launching lane's name, hand-written
# handoff lines "after stand-down") goes to the live end of its successor chain, with a [filed under] line naming the chain.  POST_NO_RESOLVE=1 keeps the name.
via=""
if [ -f "$C/tools/post_redirect.py" ] && [ "${POST_NO_RESOLVE:-0}" != 1 ]; then
  lv=$(python3 -I "$C/tools/post_redirect.py" --live "$lane" "$C" 2>/dev/null) || lv=""
  live=${lv%%$'\t'*}; chainx=${lv#*$'\t'}
  if [[ "$live" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] && [ "$live" != "$lane" ]; then
    via="  [filed under] $live: $lane stood down (chain $chainx)"; lane="$live"
  fi
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
[ -z "$via" ] || text=$(printf '%s\n%s\n' "$text" "$via")
# first line as is, later lines indented (so the view keeps them in this post's block)
body=$(printf '%s\n' "$text" | awk 'NR==1{print; next} {sub(/^[ \t]*/, "  "); print}')
printf '%s\n' "$body" >> "$C/$f"
tag=$(printf '%s' "$text" | awk 'NR==1{print $5}')
exec /bin/bash "$C/bin/coord-commit.sh" "$lane: $tag post" "$f" "$@"
