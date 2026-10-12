#!/bin/bash
# Closure-loop post-record hook for the layout viewer's static export (owner 2026-10-11).  The loop calls
#   lv_post_record.sh <job>        (detached, after a CLOSED verdict is recorded)
# It waits for the element page export of the job (~/.local/state/viz-elem/<job>.json leaves "running", at most 12 h),
# then cuts, verifies and publishes the closure into the static layout store (~/.local/share/fleet-viz/layout_store.py
# export --job <job>).  Never fails the caller; output in ~/.local/state/layout-viewer/post_record.log.
job="$1"; [ -n "$job" ] || exit 0
log=$HOME/.local/state/layout-viewer/post_record.log; mkdir -p "$(dirname "$log")"
(
  mark=$HOME/.local/state/viz-elem/$job.json
  for i in $(seq 1 1440); do
    grep -q '"state": *"running"' "$mark" 2>/dev/null || break
    sleep 30
  done
  echo "$(date -Is) $job: export"
  nice -n 19 python3 "$HOME/.local/share/fleet-viz/layout_store.py" export --job "$job"
) >> "$log" 2>&1 < /dev/null &
disown
exit 0
