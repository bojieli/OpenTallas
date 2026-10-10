#!/bin/bash
# PREROUTE-GATE calibration (2026-10-08): run tools/preroute_gate.tcl offline on an existing route's placed design
# (3_place.odb + 3_place.sdc, ideal clocks, placement parasitics), at TT, exactly the state the in-flow POST DETAIL_PLACE
# hook sees.  The job's own w18_sta_ss.tcl supplies the LEF / liberty set (SS libraries swapped for TT as tt_resta.sh).
# Writes OUT_DIR/preroute_gate_dump.json and OUT_DIR/timing.json (load / parasitics / dump wall seconds).
# usage: preroute_offline.sh ORFS_DIR GATE_TCL OUT_DIR [SRC_DIR]   (SRC_DIR default: the closure-loop job's src, ORFS/../../../../src)
set -u
ORFS=$1; GATE=$2; D=$3; mkdir -p "$D"; D=$(realpath "$D")
SRC=${4:-$(realpath -m "$ORFS/../../../../src")}
SRCMNT=(); [ -d "$SRC" ] && SRCMNT=(-v "$SRC:/src:ro")
T=$ORFS/w18_sta_ss.tcl
if [ ! -f "$T" ]; then echo "{\"error\": \"no $T\"}" > "$D/timing.json"; exit 3; fi
RES=$(sed -n 's#^read_db \(/work/results/.*\)/6_final.odb#\1#p' "$T" | head -1)
if [ -z "$RES" ] || [ ! -f "$ORFS/${RES#/work/}/3_place.odb" ]; then echo "{\"error\": \"no 3_place.odb\"}" > "$D/timing.json"; exit 3; fi
cp "$GATE" "$D/preroute_gate.tcl"
{
  sed -n '/^read_db /q;p' "$T" | sed -e 's/_\(R\|L\|SL\)VT_SS_nldm/_\1VT_TT_nldm/g' -e 's/_ss\.lib/_tt.lib/g'
  cat <<EOF
set ot_t0 [clock milliseconds]
read_db $RES/3_place.odb
read_sdc $RES/3_place.sdc
set ot_t1 [clock milliseconds]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
sta::worst_slack_cmd max
set ot_t2 [clock milliseconds]
source /g/preroute_gate.tcl
ot_preroute_dump /g/preroute_gate_dump.json
set ot_t3 [clock milliseconds]
puts "OT_PRG_TIMES [expr {(\$ot_t1-\$ot_t0)/1000.0}] [expr {(\$ot_t2-\$ot_t1)/1000.0}] [expr {(\$ot_t3-\$ot_t2)/1000.0}]"
exit
EOF
} > "$D/run.tcl"
s0=$(date +%s)
timeout 3600 docker run --rm -v "$ORFS:/work:ro" "${SRCMNT[@]}" -v "$D:/g" openroad/orfs:asap7lock bash -lc \
  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /g/run.tcl" > "$D/run.log" 2>&1
rc=$?
s1=$(date +%s)
t=$(sed -n 's/^OT_PRG_TIMES //p' "$D/run.log" | tail -1)
set -- $t
echo "{\"rc\": $rc, \"wall_s\": $((s1 - s0)), \"load_s\": ${1:-null}, \"parasitics_sta_s\": ${2:-null}, \"dump_s\": ${3:-null}}" > "$D/timing.json"
cat "$D/timing.json"
