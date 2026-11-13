#!/bin/bash
# LEAF-DRT73-1 private route proof: saved CTS DB of a crashed S81 leaf kit, the DRT-0073 hcpost lane re-oriented the way
# tools/die_plan/orient_realize.py fixes the plan (R180 -> MX, y on the MX track phase), then the kit's own GRT (hooks +
# grt183 wrapper) and detailed route.   usage: route_proof.sh TYPE inst:orient:dx_nm:dy_nm ...
set -u
R=/srv/opentallas-scratch2/claude/leaf-drt73-1; t=$1; shift
K=$R/kits/$t; B=$K/run/results/asap7/dp_ot_s81sl_leaf__$t/base; IMG=openroad/orfs:asap7lock; CPUS=${CPUS:-32}
[ -f $B/4_cts.orig.odb ] || mv $B/4_cts.odb $B/4_cts.orig.odb
docker run --rm -u $(id -u):$(id -g) -v $R:$R -e ODB=$B/4_cts.orig.odb -e OUT=$B/4_cts.odb -e SKIP_PA=1 -e REORIENT="$*" $IMG \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit $R/pa.tcl > $R/proof/route_${t}_patch.log 2>&1 || { echo PATCH_FAIL; exit 3; }
grep REORIENT $R/proof/route_${t}_patch.log
rm -f $B/5_* ; rm -f $K/run/logs/asap7/dp_ot_s81sl_leaf__$t/base/5_*
docker run --rm --name leafdrt73-route-$t -e CPUS=$CPUS -v $K:/work -w /OpenROAD-flow-scripts/flow $IMG bash -lc '
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
  M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS"
  bash /work/grt183_make.sh $M do-5_1_grt && $M do-5_2_route' > $R/proof/route_${t}.log 2>&1
rc=$?
docker run --rm -v $K:/work $IMG chown -R "$(id -u):$(id -g)" /work >/dev/null 2>&1
echo "ROUTE_PROOF $t rc=$rc $(date -Is)" | tee -a $R/proof/route_${t}.log
grep -h "DRT-0073\|DRT-0418\|Number of violations\|Total wire length\|Elapsed time" $R/proof/route_${t}.log | tail -8
