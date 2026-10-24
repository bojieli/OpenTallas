#!/bin/bash
# KV-P7 10-23: boot image on a KV re-bind in one step: KST from the bind's bus_groups, run.sh (prep + pair image + compile),
# then the PV check against the entry-pad table the bind used.   run_rebind.sh BIND_DIR OUT_DIR PV_ENTRY_TABLE.json
set -eu
B=$(readlink -f "$1"); O=$(mkdir -p "$2" && readlink -f "$2"); PV=$(readlink -f "$3")
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../../.." && pwd)
BG=$B/bus_groups.json; [ -f "$BG" ] || { zcat "$B/bus_groups.json.gz" > "$O/bus_groups.json"; BG=$O/bus_groups.json; }
KST=$(python3 "$H/kst.py" "$BG"); echo "KST $KST"
( cd "$R" && S=$O BG=$BG KST=$KST bash physical/die_plan/qwen_kvsys/boot_v36/run.sh ) > "$O/run.log" 2>&1
tail -2 "$O/run.log"
python3 "$H/pv_check.py" "$O" "$PV" | tee "$O/pv_check.txt" | tail -1
( cd "$O/cmp_bound" && sha256sum target*.hex boot_bundle.json ../img_bnd/d2d_cal_image.svh > "$O/targets.sha256" )
echo "RECIPE: BIND=$B KST=$KST bash physical/die_plan/qwen_kvsys/boot_v36/run_rebind.sh BIND OUT $(basename "$PV")" > "$O/RECIPE"
