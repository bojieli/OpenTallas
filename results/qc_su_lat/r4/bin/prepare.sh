#!/bin/bash
set -euo pipefail
SRC=$1; DST=$2; SPEC=$3; BIN=$(dirname "$(readlink -f "$0")")
mkdir -p "$DST"
rsync -a --exclude 'run/results/*/*/base/4_*' --exclude 'run/results/*/*/base/5_*' --exclude 'run/results/*/*/base/6_*' --exclude 'run/logs' --exclude 'run/reports' --exclude '*.log' --exclude 'lat_*' --exclude 'summary.json' --exclude 'summary.txt' --exclude 'r4_native_collection.json' "$SRC/" "$DST/"
cp "$SPEC" "$DST/mscts_spec.tcl"
cp "$BIN/mscts_h.tcl" "$DST/cf/mscts_h.tcl"
# The retained 3_place contains old unconnected entry buffers. Remove them before the new tree, with no placement.
cat > "$DST/r4_cleanup.tcl" <<'TCL'
set b [ord::get_db_block]
foreach i [$b getInsts] {
 if {[string match ot_ms_entry* [$i getName]]} { $i setDoNotTouch 0; odb::dbInst_destroy $i }
}
TCL
PRE=$(awk '/^export PRE_CTS_TCL/{print $4}' "$DST/config.mk" | tail -1 | sed 's#/work/##')
sed -i '1i source /work/r4_cleanup.tcl' "$DST/$PRE"
printf '\n# R4 immutable-placement clock-structure diagnostic; no route/release\nexport OT_MSCTS_ITERS = 0\nexport OT_H_NO_TRITON = 1\n' >> "$DST/config.mk"
