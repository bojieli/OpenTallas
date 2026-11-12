#!/bin/bash
# WEBVIEW-1 2026-11-03: fleet-viz current-data refresh, cron */30 (crontab tag WEBVIEW-1).
#  1. sparse trunk checkout (OUR clone at $R, objects shared read-only from the owner's repo): fetch origin main,
#     reset to it (own clone only; never touches /home/ubuntu/OpenTallas), sparse patterns = static list + current plan paths
#  2. plan_now.py  -> ~/.local/state/fleet-viz/plan_now.json (+ explorer_dies.json plan entries)
#  3. plan_dataflow.py -> explorer/dataflow/data/plan_<die>.links.json.gz when a plan geometry changed
#  4. design_index.py -> ~/.local/state/fleet-viz/design_index.json (one die/type/core node index; EXPLORER-2)
set -u
R=/srv/opentallas-scratch/claude/fleet-viz-repo
H=/home/ubuntu/.local/share/fleet-viz
LOG=$HOME/.local/state/fleet-viz/refresh.log
exec 9>/tmp/fleet-viz-refresh.lock
flock -n 9 || exit 0
exec >>"$LOG" 2>&1
echo "== $(date '+%F %T %Z') refresh"
cd "$R" || exit 1
timeout 300 git fetch -q origin || echo "fetch failed rc $?"
{ grep -v '^#' "$H/repo_sync/sparse-patterns.txt"
  FLEET_VIZ_REPO=$R python3 -c "import sys; sys.path.insert(0, '$H'); import plan_now; [print('/' + p) for _, p in plan_now.plans_of_record()[0]]" 2>/dev/null
} | sort -u > .git/info/sparse-checkout.new && mv .git/info/sparse-checkout.new .git/info/sparse-checkout
git reset -q --hard origin/main && git sparse-checkout reapply 2>/dev/null
echo "trunk $(git log -1 --format='%h %cI' origin/main)"
FLEET_VIZ_REPO=$R timeout 1500 nice -n 15 python3 "$H/plan_now.py"
FLEET_VIZ_REPO=$R timeout 1500 nice -n 15 python3 "$H/plan_dataflow.py"
FLEET_VIZ_REPO=$R timeout 600 nice -n 15 python3 "$H/design_index.py"   # the one node index (die/type/core) every explorer page reads
tail -n 4000 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
