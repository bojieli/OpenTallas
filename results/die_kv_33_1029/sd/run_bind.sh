#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/die-kv-32-kits-1029; S=/srv/opentallas-scratch2/claude/die-kv-33-1029/sd; R=$S/bind
cd $D/bindroot
A=physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv27f.json
/usr/bin/time -v python3 tools/die_plan/bind.py bind $S/bplan/bind_plan_sd33.json --out "$R" --asbuilt "$A" --strict > "$R/bind.log" 2> "$R/bind.time"
echo BIND_DONE
