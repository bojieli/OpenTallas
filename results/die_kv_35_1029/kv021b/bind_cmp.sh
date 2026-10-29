#!/bin/bash
# DIE-KV-35 KV-021: strict bind event27f with the eA2 sidecar vs the control (recipe_kv27f) on copies of the
# die-kv-32-kits bind_fix elab; then kit-rtl of the 9 re-tied types in both -> per-type kit RTL diff (expect identical:
# K straps are parent ties) + bind_count_strap_audit / tie audit.
set -u
S=/srv/opentallas-scratch2/claude/die-kv-35-1029; cd /srv/opentallas-scratch2/claude/die-kv-35-1029/bindroot
P=results/die_kv_29_1029/event27f/plan.json
for v in bindA2; do
  if [ $v = bindOld ]; then A=physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv27f.json; else A=$S/eventA2/recipe_kv27f_eA2.json; fi
  R=$S/$v
  /usr/bin/time -v python3 tools/die_plan/bind.py bind "$P" --out "$R" --asbuilt "$A" --strict > "$R/bind.log" 2> "$R/bind.time"; echo "$v BIND_RC $? $(date)"
  for T in kv3_hg_v1 kv3_hg_v1p3 kv3_hg_v1p6 kv3_hroot kv3_hub_Wo kv3_pc_v1__cl23f6a148 kv3_pc_v1__cl4ea58a5c kv3_pc_v1__cl7f648944 kv3_pc_v3; do
    python3 tools/die_plan/bind.py kit-rtl "$P" --out "$R" --asbuilt "$A" --type "$T" --kit "$R/kit_rtl/$T" > "$R/kit_rtl_${T}.log" 2>&1; echo "$v $T KITRTL_RC $?"
  done
done
diff -rq $S/bindOld/kit_rtl $S/bindA2/kit_rtl > $S/kitrtl_diff.txt; echo "KITRTL_DIFF_FILES $(wc -l < $S/kitrtl_diff.txt)"
diff <(python3 -m json.tool $S/bindOld/bind_count_strap_audit.json) <(python3 -m json.tool $S/bindA2/bind_count_strap_audit.json) > $S/strap_audit_diff.txt; echo AUDIT_DIFF_RC $?
echo BIND_CMP_DONE $(date)
