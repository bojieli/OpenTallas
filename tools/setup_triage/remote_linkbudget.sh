#!/bin/bash
# usage: remote_linkbudget.sh JOB ORFS_DIR SRC_DIR OUTDIR  -- SS re-STA of a routed job with the consistent link budget
set -u
JOB=$1; ORFS=$2; SRC=$3; OUT=$4
mkdir -p "$OUT"; T="$ORFS/w18_sta_ss.tcl"
[ -f "$T" ] || { echo "TRI_ERR no w18_sta_ss.tcl" > $OUT/lb.log; exit 3; }
odb=$(grep -m1 '^read_db' "$T" | awk '{print $2}' | sed "s#^/work#$ORFS#"); [ -f "$odb" ] || { echo "TRI_ERR odb gone" > $OUT/lb.log; exit 4; }
awk '/^puts "OT_CORNER/{print "read_sdc /tri/link_budget_consistent.sdc"} /^exit/{print "report_checks -path_delay max -from [all_inputs -no_clocks] -group_path_count 1 -format full_clock_expanded"; print "report_checks -path_delay max -to [all_outputs] -group_path_count 1 -format full_clock_expanded"} {print}' "$T" > $OUT/lb.tcl
timeout 3600 docker run --rm --name "trilb_${JOB//[^A-Za-z0-9_]/_}" -v "$ORFS:/work:ro" -v "$SRC:/src:ro" -v "$OUT:/tri" openroad/orfs:asap7lock bash -lc \
  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /tri/lb.tcl" > $OUT/lb.log 2>&1
echo "TRI_RC $?" >> $OUT/lb.log
grep -E "^OT_LINK_BUDGET|^OT_WS |^OT_WS_|TRI_RC|^Error" $OUT/lb.log
