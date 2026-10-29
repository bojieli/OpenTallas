#!/bin/bash
# DIE-KV-36 KV-021b: strict bind of event28b (eA2 + ECTL equalisation) with recipe $2 into $1; kit-rtl of the re-tied types
set -u
S=/srv/opentallas-scratch2/claude/die-kv-36-1029; cd /srv/opentallas-scratch2/claude/die-kv-35-1029/bindroot
P=kv36/event28b/plan.json; R=$S/$1; A=$S/$2
mkdir -p $R; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json die_bound_native_mission_lc.v elab.log; do cp /srv/opentallas-scratch2/claude/die-kv-35-1029/bindOld/$f $R/; done
/usr/bin/time -v python3 tools/die_plan/bind.py bind "$P" --out "$R" --asbuilt "$A" --strict > "$R/bind.log" 2> "$R/bind.time"; echo "$1 BIND_RC $? $(date)"
tail -n 2 $R/bind.log
if [ "${3:-}" = kit ]; then
for T in kv3_hg_v1 kv3_hg_v1p3 kv3_hg_v1p6 kv3_hroot kv3_hub_Wo kv3_pc__cl254f2e73 kv3_pc__cl5a95b461 kv3_pc_v1__cl23f6a148 kv3_pc_v1__cl4ea58a5c kv3_pc_v1__cl7f648944 kv3_pc_v3; do
  python3 tools/die_plan/bind.py kit-rtl "$P" --out "$R" --asbuilt "$A" --type "$T" --kit "$R/kit_rtl/$T" > "$R/kit_rtl_${T}.log" 2>&1; echo "$1 $T KITRTL_RC $?"
done
OLD=/srv/opentallas-scratch2/claude/die-kv-36-1029/bindCtl
n=0; for f in $(cd $R/kit_rtl && find . -type f | sort); do
  if [ ! -f $OLD/kit_rtl/$f ]; then echo "KITNEW $f"; n=$((n+1)); continue; fi
  if ! diff -q <(sed "s#bindOld#BIND#g;s#bindCtl#BIND#g;s#die-kv-36-1029/#die-kv-35-1029/#g;s#die-kv-32-kits-1029/bindroot#ROOT#g" $OLD/kit_rtl/$f) <(sed "s#$1#BIND#g;s#die-kv-35-1029/bindroot#ROOT#g;s#die-kv-36-1029/#die-kv-35-1029/#g" $R/kit_rtl/$f) >/dev/null; then echo "KITDIFF $f"; n=$((n+1)); fi; done
echo "KITRTL_NORMALIZED_DIFF_FILES $n"
fi
echo $1 DONE $(date)
