#!/usr/bin/env bash
# Connect to an existing app server only. Never start/restart a daemon or agent.
set -euo pipefail
MONITOR_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
MONITOR_STATE=${CAPACITY_MONITOR_STATE:-/home/ubuntu/claude-takeover-20261007/capacity-monitor}
MONITOR_LOCK=${CAPACITY_MONITOR_COORDINATOR_LOCK:-/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock}
if [[ $# -lt 1 ]]; then
  echo "usage: launch.sh ROOT_THREAD_UUID [--socket PATH] [--notify-coordinator] [--subscribe-loaded]" >&2
  exit 2
fi
MONITOR_ROOT=$1
shift
mkdir -p -- "$MONITOR_STATE"
chmod 700 -- "$MONITOR_STATE"
MONITOR_SINCE=$(python3 - "$MONITOR_LOCK" <<'PY'
import json,sys
with open(sys.argv[1]) as f:lock=json.load(f)
if lock.get('owner')!='codex':raise SystemExit('coordinator lock is not owned by Codex')
print(lock['since'])
PY
)
if [[ -e "$MONITOR_STATE/STOP" ]]; then
  echo "STOP marker present; remove it explicitly before restarting monitor" >&2
  exit 3
fi
nohup setsid flock -n "$MONITOR_STATE/launcher.lock" python3 -u "$MONITOR_DIR/monitor.py" \
  --root-thread "$MONITOR_ROOT" --state-dir "$MONITOR_STATE" \
  --lock "$MONITOR_LOCK" --lock-since "$MONITOR_SINCE" "$@" \
  >> "$MONITOR_STATE/runtime.log" 2>&1 < /dev/null &
MONITOR_LAUNCH_PID=$!
for MONITOR_TRY in {1..50}; do
  if [[ -s "$MONITOR_STATE/pid" ]]; then
    echo "capacity monitor pid=$(cat "$MONITOR_STATE/pid") launcher=$MONITOR_LAUNCH_PID state=$MONITOR_STATE"
    exit 0
  fi
  sleep 0.1
done
echo "capacity monitor failed to leave a verified pid; inspect $MONITOR_STATE/runtime.log" >&2
exit 1
