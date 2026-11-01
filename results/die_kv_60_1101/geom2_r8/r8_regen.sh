#!/bin/bash
# DIE-KV-59/geom2: R8 landing table regen on the geom2 bind (= DIE-KV-36 r8_28b.sh recipe)
set -euo pipefail
cd /srv/opentallas-scratch2/claude/wt/die-kv-59-geom
P=physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json
B=/srv/opentallas-scratch2/claude/die-kv-59/geom2/bind
O=/srv/opentallas-scratch2/claude/die-kv-59/geom2/r8
mkdir -p "$O"
K=physical/die_plan/qwen_kvsys/r8
python3 "$K/r8_invariant_split.py" "$P" "$B/bus_groups.json" "$O/bg_split.json"
python3 "$K/r8_write_groups.py" prep "$O/bg_split.json" "$O/bus_groups.json"
python3 tools/die_plan/r8.py pads "$P" "$O/bus_groups.json" --replica type --bus leaf --exempt "^kreq$" --exempt "^krsp$" --out "$O" > "$O/pads.log" 2>&1
python3 tools/die_plan/r8.py check "$P" "$O/bus_groups.json" --replica type --bus leaf --exempt "^kreq$" --exempt "^krsp$" --landing "$O/qwen_kvsys_r8_landing.json" --strap-pads --json "$O/check_strap.json" > "$O/check.log" 2>&1
python3 "$K/r8_write_groups.py" check "$O/qwen_kvsys_r8_landing.json" > "$O/write_groups.log" 2>&1
python3 "$K/r8_write_groups.py" bindview "$O/qwen_kvsys_r8_landing.json" "$O/qwen_kvsys_r8_landing_bind.json" > "$O/bindview.log" 2>&1
tail -n 3 "$O/pads.log" "$O/check.log" "$O/write_groups.log"
