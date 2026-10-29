#!/bin/bash
# DIE-KV-35 KV-021: strict bind of event28 (event27f + eA2 landing cycles) with the eA2 sidecar; kit-rtl of the 9 re-tied
# types; normalized diff vs control bindOld (event27f + event26 sidecar).
set -u
S=/srv/opentallas-scratch2/claude/die-kv-35-1029; cd $S/bindroot
P=kv35/event28/plan.json; A=$S/eventA2/recipe_kv27f_eA2.json; R=$S/bind28
mkdir -p $R; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json die_bound_native_mission_lc.v elab.log; do cp $S/bindOld/$f $R/; done
/usr/bin/time -v python3 tools/die_plan/bind.py bind "$P" --out "$R" --asbuilt "$A" --strict > "$R/bind.log" 2> "$R/bind.time"; echo "bind28 BIND_RC $? $(date)"
for T in kv3_hg_v1 kv3_hg_v1p3 kv3_hg_v1p6 kv3_hroot kv3_hub_Wo kv3_pc_v1__cl23f6a148 kv3_pc_v1__cl4ea58a5c kv3_pc_v1__cl7f648944 kv3_pc_v3; do
  python3 tools/die_plan/bind.py kit-rtl "$P" --out "$R" --asbuilt "$A" --type "$T" --kit "$R/kit_rtl/$T" > "$R/kit_rtl_${T}.log" 2>&1; echo "bind28 $T KITRTL_RC $?"
done
n=0; for f in $(cd $S/bindOld/kit_rtl && find . -type f | sort); do
  if ! diff -q <(sed "s#bindOld#BIND#g;s#die-kv-32-kits-1029/bindroot#ROOT#g" $S/bindOld/kit_rtl/$f) <(sed "s#bind28#BIND#g;s#die-kv-35-1029/bindroot#ROOT#g" $R/kit_rtl/$f) >/dev/null; then echo "KITDIFF $f"; n=$((n+1)); fi; done
echo "KITRTL_NORMALIZED_DIFF_FILES $n"
cat $R/bind_count_strap_audit.json; echo; tail -n 1 $R/bind.log
echo BIND28_DONE $(date)
