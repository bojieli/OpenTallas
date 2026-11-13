#!/bin/bash
# usage: pa_run.sh TYPE TAG [REORIENT...]   (LEAF-DRT73-1 private pin-access proof)
R=/srv/opentallas-scratch2/claude/leaf-drt73-1
t=$1; tag=$2; shift 2
ODB=$R/kits/$t/run/results/asap7/dp_ot_s81sl_leaf__$t/base/4_cts.odb
mkdir -p $R/proof
docker run --rm --name leafdrt73-$t-$tag -u $(id -u):$(id -g) -v $R:$R -e ODB=$ODB -e REORIENT="$*" \
  ${OUTODB:+-e OUT=$OUTODB} openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit $R/pa.tcl > $R/proof/pa_${t}_${tag}.log 2>&1
rc=$?
echo "rc=$rc" >> $R/proof/pa_${t}_${tag}.log
grep -E "REORIENT|DRT-0073|PIN_ACCESS_DONE|^rc=|Error" $R/proof/pa_${t}_${tag}.log | head -20
