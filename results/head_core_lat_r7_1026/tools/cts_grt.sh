#!/bin/bash
# HEAD-CORE-LAT-R7 elemB clock-structure build (plan r7b_f5_24444_b0, uf_phys3 window <=14 UNCHECKED): CTS (plan-built tree, TritonCTS off) + GRT only; then per-sink clock arrival at TT/FF on
# GRT parasitics (meas_ck.tcl, rc_cal 0.8,0.9 = the uf_phys basis).  No DRT.  Non-gating (12.9d calibration of uf_phys for HEAD).
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); MEM=${1:-32}
IMG=openroad/orfs:asap7lock
R=/work/run/results/asap7/hd_elemB_rb/base
rc=0; docker run --rm --name hcl7-cal-$(basename $K)-$$ --cpus=16 --memory=${MEM}g --memory-swap=${MEM}g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMG bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16"; $M do-cts && $M do-5_1_grt' > "$K/cts_grt.log" 2>&1 || rc=$?
echo "FLOW rc $rc" >> "$K/cts_grt.log"
if [ $rc = 0 ]; then
  for C in TT FF; do
    docker run --rm --name hcl7-meas-$(basename $K)-$C-$$ --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -w /work -e OT_CORNER=$C -e ODB=$R/5_1_grt.odb -e SDC=$R/5_1_grt.sdc -e OUT=/work/meas_ck_$C.tsv $IMG bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 4 -exit /work/meas_ck.tcl' > "$K/meas_$C.log" 2>&1 &
  done; wait
fi
docker run --rm -v "$K":/work $IMG chown -R $(id -u):$(id -g) /work/run /work >/dev/null 2>&1
grep -h "Total overflow\|overflow" "$K"/run/logs/asap7/hd_elemB_rb/base/5_1_grt.log 2>/dev/null | tail -2
exit $rc
