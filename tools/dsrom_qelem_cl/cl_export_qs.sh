#!/bin/bash
# Closure-loop export / pin-access check of a routed PQ q-element (2026-10-06; close_qz.sh steps 1-2):
#   cl_export_qs.sh <route job dir> <out dir>      (cwd = the job's source snapshot)
# (1) abstract LEF from 6_final.odb (tools/dsrom_q_abstract.tcl) -> <out>/q_elem.lef; (2) single-instance pin access
# (physical/abi3/dsrom_q_pin_access.tcl) -> <out>/pa/, DRT-0073 count in <out>/pa/drt0073.count.  Exit 0 only when
# both ran and no pin lacks an access point.
J=$1; O=$2; mkdir -p $O/pa
B=$(ls -d $J/work/orfs/results/asap7/*/base | head -1)
docker run --rm -v $B:$B:ro -v $O:$O -v $PWD:/src:ro -e ODB=$B/6_final.odb -e OUT=$O/q_elem.lef \
  openroad/orfs:latest bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tools/dsrom_q_abstract.tcl" > $O/abstract.log 2>&1 || exit 3
M=$(awk '/^MACRO/{print $2; exit}' $O/q_elem.lef); [ -n "$M" ] || exit 4
docker run --rm -v $O:$O -v $PWD:/src:ro -e Q_LEF=$O/q_elem.lef -e Q_MASTER=$M -e OUT_DIR=$O/pa \
  openroad/orfs:latest bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/physical/abi3/dsrom_q_pin_access.tcl" > $O/pa/pa.log 2>&1 || exit 5
n=$(grep -c "DRT-0073" $O/pa/pa.log); echo $n > $O/pa/drt0073.count
grep -h "OT_PA" $O/pa/pa.log | tail -3
[ "$n" = 0 ] && grep -q "OT_PA DONE" $O/pa/pa.log
