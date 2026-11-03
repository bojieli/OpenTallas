#!/bin/bash
# DIE-HBM-58/CLK 12.25 die clock gate on DRC-clean full-hub DRT mesh (NW_v2 DRC0, NE_v1 DRC2 n_root) + physical feeds.
# = Codex physical_ca.sh with the new matched mesh; TOOLS=main (origin/main a8b1824c6) or codex (reference control).
set -euo pipefail
W=/home/ubuntu/scratch-root/claude/die-hbm-58-clk
V=$1; TS=$2
if [ "$TS" = main ]; then T=$W/main/tools/die_plan; else T=/srv/opentallas-scratch2/claude/codex-hbm-clock/tools/die_plan; fi
B=$W/i1/hbm-clkloc-1/C12e; PLAN=$W/i1/hbm-clkloc-1/in/d44g/die_plan.json
O=$W/gate_${V}_${TS}; mkdir -p "$O"
python3 "$W/i1/codex-hbm-clock/compose_physical_feeds.py" "$B/t7proof" "$W/data" "$V" "$O/proof" > "$O/composite.log" 2>&1
python3 "$T/count_align_plan.py" "$B/ca7_t5/landed_ocv.json" --mc-chips 2000 --sta-proof "$O/proof" --sta-plan $PLAN --sta-cppr-lca --sta-core-latency-ff 202.5 --start-tree clock --start-clean phase --sta-clock-cell buf --start-retime-up --start-native-clocks --start-retime-max 16 --max-depth 16 --start-prev "$B/ca7_t5/plan.json" --out "$O/plan.json" > "$O/plan.log" 2>&1
python3 "$T/count_align_bind.py" "$O/plan.json" --parts region --out "$O/bind.json" > "$O/bind.log" 2>&1
python3 "$T/die_sta_related.py" "$O/proof" --plan $PLAN --out "$O/sta" --core-latency-ff 202.5 --count-align "$O/bind.json" --cppr-lca --hold-buffers HB4 --clock-cell buf --nominal-arrival single > "$O/sta.log" 2>&1
echo "GATE_DONE $V $TS $(date)"
