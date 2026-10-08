#!/bin/bash
# Re-STA an existing routed loop job (no re-route) with an extra SDC read after the loop's own sign-off SDC.
# Reuses the job's own w18_sta_{ss,ff}.tcl verbatim (same libs/odb/spef/sdc, same OT_* reductions) and inserts
# `read_sdc /tri/extra.sdc` before the reports.  Evidence files of the job are mounted read-only and never touched.
# usage: resta.sh ORFS_DIR SRC_DIR OUTDIR EXTRA_SDC
set -u
ORFS=$1; SRC=$2; OUT=$3; X=$4
mkdir -p $OUT; cp $X $OUT/extra.sdc
for c in ss ff; do
  T=$ORFS/w18_sta_$c.tcl
  awk '/^puts "OT_CORNER/{print "read_sdc /tri/extra.sdc"} {print}' $T > $OUT/resta_$c.tcl
  sed -i 's#^report_checks -path_delay \(max\|min\) -group_path_count 1 -format full_clock_expanded#report_checks -path_delay \1 -group_path_count 3 -endpoint_path_count 1 -unique_paths_to_endpoint -format full_clock_expanded#' $OUT/resta_$c.tcl
  timeout 7200 docker run --rm -v $ORFS:/work:ro -v $SRC:/src:ro -v $OUT:/tri openroad/orfs:asap7lock bash -lc \
    "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /tri/resta_$c.tcl" > $OUT/resta_$c.log 2>&1 &
done
wait
for c in ss ff; do echo "== $c"; grep -E "^OT_|OT_SELT|WARNING STA-(0391|1554)" $OUT/resta_$c.log; done
