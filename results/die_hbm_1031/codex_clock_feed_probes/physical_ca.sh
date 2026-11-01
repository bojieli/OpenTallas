#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-hbm-clock
B=/srv/opentallas-scratch2/claude/hbm-clkloc-1/C12e
T=$R/tools/die_plan
V=$1;O=$R/physical_ca_$V;mkdir -p "$O"
python3 "$R/compose_physical_feeds.py" "$B/t7proof" "$R" "$V" "$O/proof" > "$O/composite.log" 2>&1
python3 "$T/count_align_plan.py" "$B/ca7_t5/landed_ocv.json" --mc-chips 2000 --sta-proof "$O/proof" --sta-plan /srv/opentallas-scratch2/claude/hbm-clkloc-1/in/d44g/die_plan.json --sta-cppr-lca --sta-core-latency-ff 202.5 --start-tree clock --start-clean phase --sta-clock-cell buf --start-retime-up --start-native-clocks --start-retime-max 16 --max-depth 16 --start-prev "$B/ca7_t5/plan.json" --out "$O/plan.json" > "$O/plan.log" 2>&1
python3 "$T/count_align_bind.py" "$O/plan.json" --parts region --out "$O/bind.json" > "$O/bind.log" 2>&1
python3 "$R/ca_impact.py" "$B/ca7_t5/plan.json" "$O/plan.json" > "$O/impact.json"
python3 "$T/die_sta_related.py" "$O/proof" --plan /srv/opentallas-scratch2/claude/hbm-clkloc-1/in/d44g/die_plan.json --out "$O/sta" --core-latency-ff 202.5 --count-align "$O/bind.json" --cppr-lca --hold-buffers HB4 --clock-cell buf --nominal-arrival single > "$O/sta.log" 2>&1
