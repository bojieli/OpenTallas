#!/bin/bash
# CTS-only experiment on a routed loop job's placement: re-runs ORFS do-4_1_cts from its 3_place.odb with modified
# CTS_ARGS (SKIP_CTS_REPAIR_TIMING=1 unless TRI_REPAIR=1) and measures macro/ICG clock arrival vs registers.
# usage: cts_exp.sh ORFS_DIR SRC_DIR OUTDIR "CTS_ARGS"      (run on the host holding the route)
set -u
ORFS=$1; SRC=$2; OUT=$3; ARGS=$4
mkdir -p $OUT/hooks
base=$(ls -d $ORFS/results/asap7/*/base); nick=$(basename $(dirname $base))
mkdir -p $OUT/results/asap7/$nick/base $OUT/logs/asap7/$nick/base $OUT/reports/asap7/$nick/base $OUT/objects/asap7/$nick/base
cp $base/3_place.odb $base/3_place.sdc $OUT/results/asap7/$nick/base/
cp -r $ORFS/objects/asap7/$nick/base/. $OUT/objects/asap7/$nick/base/ 2>/dev/null
cp $ORFS/hooks/* $OUT/hooks/ 2>/dev/null; cp $ORFS/*.sdc $ORFS/io_constraints.tcl $OUT/ 2>/dev/null
cp $(dirname $0)/cts_measure.tcl $OUT/hooks/tri_cts_measure.tcl
orig=$(grep -m1 '^export POST_CTS_TCL' $ORFS/config.mk | sed 's/.*= *//')
opre=$(grep -m1 '^export PRE_CTS_TCL' $ORFS/config.mk | sed 's/.*= *//')
grep -v '^export CTS_ARGS\|^export POST_CTS_TCL\|^export SKIP_CTS_REPAIR_TIMING' $ORFS/config.mk > $OUT/config.mk
if [ -n "${TRI_PRE_EXTRA:-}" ]; then   # extra PRE_CTS hook (repo-relative under /src), chained after the block's own
  mkdir -p $OUT/tri_extra
  { [ -n "$opre" ] && echo "source $opre"; for x in $TRI_PRE_EXTRA; do cp $x $OUT/tri_extra/; echo "source /tri_extra/$(basename $x)"; done; } > $OUT/hooks/tri_pre_cts.tcl
  grep -v '^export PRE_CTS_TCL' $OUT/config.mk > $OUT/config.mk.t && mv $OUT/config.mk.t $OUT/config.mk
  echo "export PRE_CTS_TCL = /work/hooks/tri_pre_cts.tcl" >> $OUT/config.mk
  sed -i "s#/tri_extra/#/work/tri_extra/#" $OUT/hooks/tri_pre_cts.tcl
fi
echo "export CTS_ARGS = $ARGS" >> $OUT/config.mk
echo "export POST_CTS_TCL = /work/hooks/tri_cts_measure.tcl" >> $OUT/config.mk
echo "export TRI_ORIG_POST_CTS = $orig" >> $OUT/config.mk
[ "${TRI_REPAIR:-0}" = 1 ] || echo "export SKIP_CTS_REPAIR_TIMING = 1" >> $OUT/config.mk
img=${OPENTALLAS_ORFS_IMAGE:-openroad/orfs:asap7lock}
timeout 14400 docker run --rm --name tri_cts_$(basename $OUT) -v $SRC:/src:ro -v $OUT:/work -w /OpenROAD-flow-scripts/flow $img bash -lc \
 "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 do-4_1_cts" > $OUT/make.log 2>&1
echo "TRI_CTS_RC $?" >> $OUT/make.log
grep -h "OT_CG_PUSHDOWN\|TRI_CTS\|CTS-0029\|CTS-0101\|RSZ-0047" $OUT/logs/asap7/$nick/base/4_1_cts.log $OUT/make.log 2>/dev/null
