#!/bin/bash
# PLAN-ROUTE-1 FLAGS watcher (ADVISORY ranking, never a gate; DO_NOT_COUNT).
# Every 30 min: read the plans of record from ~/coord/tools/release_tree_plan.py (PLANS), and on epyc4 re-run
# route_supply.py for every die whose plan file sha changed on origin/main; append the rows to FLAGS-1110.tsv and
# commit lanes/FLAGS-1110.tsv + one queue line through coord-commit.sh.  Heavy work runs niced on epyc4 only.
# Disable: remove the "plan-route-1/flags_cron.sh" line from the localhost crontab.
set -u
cd /
R=/srv/opentallas-scratch2/claude/plan-route-1
C=/home/ubuntu/coord
LOG=/home/ubuntu/.local/state/plan-route-1-flags.log
LOCK=/home/ubuntu/.local/state/plan-route-1-flags.lock
mkdir -p /home/ubuntu/.local/state
exec 9>"$LOCK"; flock -n 9 || exit 0
S="$(date '+%Y-%m-%d %H:%M %Z')"
PL=$(python3 -I - <<'EOF'
import ast, json
src = open('/home/ubuntu/coord/tools/release_tree_plan.py').read()
env = {'_HBM_POR': 'physical/die_plan/hbm/plan_of_record/'}
for n in ast.parse(src).body:
    if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'PLANS' for t in n.targets):
        for die, _ref, plan, refs in eval(compile(ast.Expression(n.value), 'PLANS', 'eval'), env):
            print(json.dumps({'die': die, 'plan': plan, 'refs': list(refs)}))
EOF
)
[ -n "$PL" ] || { echo "$S no PLANS parsed" >> "$LOG"; exit 0; }
timeout 60 ssh -o ControlPath=none epyc4 "cat > $R/release_cache.json" < /home/ubuntu/.local/state/fleet-viz/release_tree_plan_cache.json
OUT=$(echo "$PL" | timeout 1700 ssh -o ControlPath=none epyc4 "cd /; git -C $R/repo fetch -q origin main 2>/dev/null; \
  git -C $R/watch checkout -q --detach origin/main && nice -n 10 python3 -I $R/tools/route_supply_watch.py --repo $R/watch \
  --tsv $R/FLAGS-1110.tsv --out-root $R/watch_out --release-cache $R/release_cache.json --stamp '$S' \
  --main \$(git -C $R/watch rev-parse --short HEAD)" 2>&1)
echo "$S $(echo "$OUT" | tr '\n' '|')" >> "$LOG"
echo "$OUT" | grep -q 're-run' || exit 0
timeout 120 ssh -n -o ControlPath=none epyc4 "cat $R/FLAGS-1110.tsv" > "$C/lanes/FLAGS-1110.tsv.new" && \
  [ -s "$C/lanes/FLAGS-1110.tsv.new" ] && mv "$C/lanes/FLAGS-1110.tsv.new" "$C/lanes/FLAGS-1110.tsv" || exit 0
RR=$(echo "$OUT" | grep 're-run' | sed 's/^/    /')
cat >> "$C/lanes/COORD-REVIEW-QUEUE.md" <<EOT
- $(date '+%Y-%m-%d %H:%M %Z') RESULT [PLAN-ROUTE-1 -> DIE-S81-85, HEAD-92, DIE-QC-97, DIE-KV-97, DIE-HBM-97, COORD] plan event -> route_supply re-run, rows appended to lanes/FLAGS-1110.tsv (stamp $S; ADVISORY ranking, never a gate; DO_NOT_COUNT; automatic, lanes/plan-route-1/flags_cron.sh):
$RR
EOT
cd "$C" && timeout 280 "$C/bin/coord-commit.sh" "PLAN-ROUTE-1 FLAGS re-run $S" lanes/COORD-REVIEW-QUEUE.md lanes/FLAGS-1110.tsv >> "$LOG" 2>&1
