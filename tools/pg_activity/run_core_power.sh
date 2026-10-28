#!/usr/bin/env bash
# PG-ACTIVITY-KVHBM: run core_power_meas.tcl in the ORFS docker (memory-capped) on a host that holds the kit.
#   run_core_power.sh KITDIR ODB_REL SDC_REL ACT.txt OUTDIR TAG PLACED(0/1) [MEM_GB]
set -eu
K=$1; ODB=$2; SDC=$3; ACT=$(realpath $4); OUT=$(realpath -m $5); TAG=$6; PL=$7; MEM=${8:-32}
mkdir -p $OUT; TCL=$(realpath $(dirname $0)/core_power_meas.tcl)
docker run --rm --name pgact_${TAG}_$$ -m ${MEM}g --cpus 4 -u $(id -u):$(id -g) -v $K:/kit:ro $( [ -d $K/macros ] && echo -v $K/macros:/work/macros:ro ) \
  -v $OUT:/work/out -v $ACT:/work/act.txt:ro -v $TCL:/work/meas.tcl:ro \
  -e OT_ODB=/kit/$ODB -e OT_SDC=/kit/$SDC -e OT_TAG=$TAG -e OT_PREFIX= -e OT_PLACED=$PL openroad/orfs:asap7lock \
  bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/meas.tcl" > $OUT/power_$TAG.log 2>&1
grep -E "OT_REG|^Total|^Sequential|^Combinational|^Clock|^Macro" $OUT/power_${TAG}_vectorless.rpt $OUT/power_${TAG}_meas.rpt $OUT/power_$TAG.log
