#!/bin/bash
# PG-ACTIVITY-KVHBM: run kv_core_power_meas.tcl / core_below_m7.tcl in the ORFS docker with a memory cap.
#   run_power.sh BASE_RESULTS_DIR ACT.txt MACRO_DIR|- OUTDIR TCL [MEM_GB]
set -eu
B=$1; A=$2; M=$3; O=$4; T=$5; MEM=${6:-24}
mkdir -p $O/out; cp $A $O/act.txt; cp $T $O/run.tcl
MM=(); [ "$M" != - ] && MM=(-v $M:/work/macros:ro)
docker run --rm --name pgact_$(basename $O)_$$ --memory ${MEM}g --cpus 4 -u $(id -u):$(id -g) -v $B:/work/odb:ro "${MM[@]}" \
  -v $O/act.txt:/work/act.txt:ro -v $O/run.tcl:/work/run.tcl:ro -v $O/out:/work/out openroad/orfs:asap7lock \
  bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/run.tcl' > $O/power.log 2>&1
grep -E "^OT_REG|^Total|^Sequential|^Combinational|^Clock|^Macro|BM7_" $O/power.log
