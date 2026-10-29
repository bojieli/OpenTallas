#!/bin/bash
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/codex-kv-0822
R=/srv/opentallas-scratch2/claude/codex-kv-0822/bind_fast
cd "$W"
for T in kv3_hroot kv3_io_cor kv3_io_cor_v1 kv3_io_ft kv3_io_ft_v1 kv3_hub_Ei kv3_sys_SD kv3_sys_SD_v1 kv3_sys_c kv3_phy kv3_phy_v1; do
 python3 tools/die_plan/bind.py kit-rtl results/die_kv_29_1029/event27f/plan.json --out "$R" --asbuilt physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv27f.json --type "$T" --kit "$R/kit_rtl/$T" > "$R/kit_rtl_${T}.log" 2>&1
done
printf 'ELEVEN_KIT_RTL_DONE\n'
