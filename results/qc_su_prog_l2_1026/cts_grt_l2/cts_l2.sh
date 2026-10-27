#!/bin/bash
# QC-SU-PROG-L2: CTS (plan-built 3-level H-tree mscts_spec_l2.tcl, TritonCTS off, ITERS 0 report only) + GRT; no DRT.
# then read-only TT/FF sink (meas_ck) + stage/netcap (meas_stage) dumps on 5_1_grt.odb (model-refit2 tools, GRT RC 0.8/0.9).
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
rc=0; docker run --rm --name qcsupl2-cts-$$ --cpus=8 --memory=8g --memory-swap=8g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-cts && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt' > "$K/cts_grt.log" 2>&1 || rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run
python3 "$K/../collect_native.py" "$K" || true
if [ $rc -eq 0 ]; then
  B=run/results/asap7/kq_qfd_dv_s8x_prog_mif0k2/base; mkdir -p "$K/meas"
  for C in TT FF; do for M in meas_stage meas_ck; do
    docker run --rm --memory=4g --memory-swap=4g --cpus=1 -v "$K":/work:ro -v "$K/meas":/out -v "$K/meas_tools/$M.tcl":/m.tcl:ro \
      -e ODB=/work/$B/5_1_grt.odb -e SDC=/work/$B/5_1_grt.sdc -e OT_CORNER=$C -e OUT=/out/${M}_$C.tsv openroad/orfs:asap7lock \
      bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /m.tcl" > "$K/meas/${M}_$C.log" 2>&1 &
  done; done; wait
  docker run --rm -v "$K/meas":/out openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /out
fi
echo "CTS_L2_DONE rc $rc"
exit $rc
