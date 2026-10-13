#!/bin/bash
# usage: diag_run.sh ORFS SRC OUT
set -u; ORFS=$1; SRC=$2; OUT=$3
mkdir -p $OUT/hooks
base=$(ls -d $ORFS/results/asap7/*/base); nick=$(basename $(dirname $base))
mkdir -p $OUT/results/asap7/$nick/base $OUT/logs/asap7/$nick/base $OUT/reports/asap7/$nick/base $OUT/objects/asap7/$nick/base
cp $base/3_place.odb $base/3_place.sdc $OUT/results/asap7/$nick/base/
cp -r $ORFS/objects/asap7/$nick/base/. $OUT/objects/asap7/$nick/base/ 2>/dev/null
cp $ORFS/hooks/* $OUT/hooks/; cp $ORFS/*.sdc $ORFS/io_constraints.tcl $OUT/ 2>/dev/null
cp $(dirname $0)/hold_class_diag.tcl $OUT/hooks/q13_diag.tcl
orig=$(grep '^export POST_CTS_TCL' $ORFS/config.mk | tail -1 | sed 's/.*= *//')
grep -v '^export POST_CTS_TCL\|^export SKIP_CTS_REPAIR_TIMING' $ORFS/config.mk > $OUT/config.mk
echo "export POST_CTS_TCL = /work/hooks/q13_diag.tcl" >> $OUT/config.mk
echo "export TRI_ORIG_POST_CTS = $orig" >> $OUT/config.mk
echo "export SKIP_CTS_REPAIR_TIMING = 1" >> $OUT/config.mk
img=${OPENTALLAS_ORFS_IMAGE:-openroad/orfs:asap7lock}
docker run --rm --name q13_diag_$(basename $OUT) -v $SRC:/src:ro -v $OUT:/work -w /OpenROAD-flow-scripts/flow $img bash -lc \
 "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 do-4_1_cts" > $OUT/make.log 2>&1
echo "Q13_RC $?" >> $OUT/make.log
