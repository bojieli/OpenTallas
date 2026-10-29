#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/die-kv-32-kits-1029; S=/srv/opentallas-scratch2/claude/die-kv-33-1029/sd; R=$S/bind; cd $D/bindroot
A=physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv27f.json
for T in kv3_sys_SD kv3_sys_SD_v1; do
  python3 tools/die_plan/bind.py kit-rtl $S/bplan/bind_plan_sd33.json --out "$R" --asbuilt "$A" --type "$T" --kit "$S/kit_rtl/$T" > "$S/kit_rtl_$T.log" 2>&1; echo "$T kit-rtl rc=$?"
  python3 /srv/opentallas-scratch2/claude/wt/die-kv-33-sd/tools/die_plan/specialize_serdes_phy.py $S/kit_rtl/$T /srv/opentallas-scratch2/claude/wt/die-kv-33-sd/results/kv_serdes_pg_event33 > $S/spec_$T.json 2>&1; echo "$T specialize rc=$?"
done
