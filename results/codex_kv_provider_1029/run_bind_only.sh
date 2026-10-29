#!/bin/bash
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/codex-kv-0822
R=/srv/opentallas-scratch2/claude/codex-kv-0822/bind_fast
cd "$W"
python3 tools/die_plan/bind.py bind results/die_kv_29_1029/event27f/plan.json --out "$R" --asbuilt physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv27f.json --strict > "$R/bind.log" 2>&1
printf 'STRICT_BIND_DONE\n'
