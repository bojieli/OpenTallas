#!/bin/bash
# DIE-KV-36: control kit-rtl (event27f + recipe_kv27f, copy of DIE-KV-35 bindOld) of the 2 types newly re-tied by the ECTL krq pads
cd /srv/opentallas-scratch2/claude/die-kv-35-1029/bindroot
P=results/die_kv_29_1029/event27f/plan.json; A=physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv27f.json; R=/srv/opentallas-scratch2/claude/die-kv-36-1029/bindCtl
for T in kv3_pc__cl254f2e73 kv3_pc__cl5a95b461; do python3 tools/die_plan/bind.py kit-rtl "$P" --out "$R" --asbuilt "$A" --type "$T" --kit "$R/kit_rtl/$T" > "$R/kit_rtl_${T}.log" 2>&1; echo "ctl $T KITRTL_RC $?"; done
