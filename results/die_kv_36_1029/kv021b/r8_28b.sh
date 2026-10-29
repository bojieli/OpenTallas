#!/bin/bash
# DIE-KV-36 KV-021b: R8 landing table regen on the event28b bind (= codex-kv-25 r8_26.sh recipe, land_r8_note pipeline)
set -euo pipefail
cd /srv/opentallas-scratch2/claude/die-kv-35-1029/bindroot
P=kv36/event28b/plan.json
B=/srv/opentallas-scratch2/claude/die-kv-36-1029/${1:-bindB1}
O=/srv/opentallas-scratch2/claude/die-kv-35-1029/bindroot/kv36/r8_28b
mkdir -p "$O"
K=physical/die_plan/qwen_kvsys/r8
python3 "$K/r8_invariant_split.py" "$P" "$B/bus_groups.json" "$O/bg_split.json"
python3 "$K/r8_write_groups.py" prep "$O/bg_split.json" "$O/bus_groups.json"
python3 tools/die_plan/r8.py pads "$P" "$O/bus_groups.json" --replica type --bus leaf --exempt "^kreq$" --exempt "^krsp$" --out "$O" > "$O/pads.log" 2>&1
python3 tools/die_plan/r8.py check "$P" "$O/bus_groups.json" --replica type --bus leaf --exempt "^kreq$" --exempt "^krsp$" --landing "$O/qwen_kvsys_r8_landing.json" --strap-pads --json "$O/check_strap.json" > "$O/check.log" 2>&1
python3 "$K/r8_write_groups.py" check "$O/qwen_kvsys_r8_landing.json" > "$O/write_groups.log" 2>&1
python3 "$K/r8_write_groups.py" bindview "$O/qwen_kvsys_r8_landing.json" "$O/qwen_kvsys_r8_landing_bind.json" > "$O/bindview.log" 2>&1
tail -n 3 "$O/pads.log" "$O/check.log" "$O/write_groups.log"
