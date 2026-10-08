#!/bin/bash
# usage: remote_paths.sh JOB ORFS_DIR SRC_DIR OUTDIR  (runs on the host that holds the route)
set -u
JOB=$1; ORFS=$2; SRC=$3; OUT=$4
mkdir -p "$OUT"
T="$ORFS/w18_sta_ss.tcl"
if [ ! -f "$T" ]; then echo "TRI_ERR no w18_sta_ss.tcl" > "$OUT/paths.log"; exit 3; fi
odb=$(grep -m1 '^read_db' "$T" | awk '{print $2}' | sed "s#^/work#$ORFS#")
if [ ! -f "$odb" ]; then echo "TRI_ERR odb gone $odb" > "$OUT/paths.log"; exit 4; fi
awk '/^puts "OT_CORNER/{exit} {print}' "$T" | sed 's#/work/w18_extra.sdc#/work/w18_extra.sdc#' > "$OUT/tri.tcl"
cat "$OUT/paths_tcl.tcl" >> "$OUT/tri.tcl"
# collect SDC text for exception inspection
for f in $(grep -o '/work/[^ ]*\.sdc' "$T"); do echo "### $f"; cat "${f/\/work/$ORFS}"; done > "$OUT/sdc_all.txt" 2>/dev/null
timeout 3600 docker run --rm --name "tri_${JOB//[^A-Za-z0-9_]/_}" -v "$ORFS:/work:ro" -v "$SRC:/src:ro" -v "$OUT:/tri" openroad/orfs:asap7lock bash -lc \
  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /tri/tri.tcl" > "$OUT/paths.log" 2>&1
echo "TRI_RC $?" >> "$OUT/paths.log"
