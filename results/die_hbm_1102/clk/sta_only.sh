#!/bin/bash
set -euo pipefail
W=/home/ubuntu/scratch-root/claude/die-hbm-58-clk; V=$1; TS=$2
if [ "$TS" = main ]; then T=$W/main/tools/die_plan; else T=/srv/opentallas-scratch2/claude/codex-hbm-clock/tools/die_plan; fi
PLAN=$W/i1/hbm-clkloc-1/in/d44g/die_plan.json; O=$W/gate_${V}_${TS}
python3 "$T/die_sta_related.py" "$O/proof" --plan $PLAN --out "$O/sta" --core-latency-ff 202.5 --count-align "$O/bind.json" --cppr-lca --hold-buffers HB4 --clock-cell buf --nominal-arrival single > "$O/sta.log" 2>&1
echo "GATE_DONE $V $TS $(date)"
