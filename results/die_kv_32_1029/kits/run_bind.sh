#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/die-kv-32-kits-1029
R=$D/bind_fix
cd $D/bindroot
P=results/die_kv_29_1029/event27f/plan.json
A=physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv27f.json
/usr/bin/time -v python3 tools/die_plan/bind.py bind "$P" --out "$R" --asbuilt "$A" --strict > "$R/bind.log" 2> "$R/bind.time"
for T in kv3_io_cor kv3_io_cor_v1 kv3_io_ft kv3_io_ft_v1 kv3_hub_Ei; do
  python3 tools/die_plan/bind.py kit-rtl "$P" --out "$R" --asbuilt "$A" --type "$T" --kit "$R/kit_rtl/$T" > "$R/kit_rtl_${T}.log" 2>&1
done
echo BIND_KITRTL_DONE
