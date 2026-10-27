#!/bin/bash
# QC-SU-PROG-L2: DRT + fill + finish (ORFS RCX 6_final.spef) on the h3_d55_s95 CTS+GRT (GRT overflow 0); clock-latency measurement
# only (no hold repair, no clock edits; 12.3a: core slightly outside the design target goes to sign-off, die STA decides).
# Then read-only meas_ck TT/FF on 6_final ODB/SDC/SPEF.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); B=run/results/asap7/kq_qfd_dv_s8x_prog_mif0k2/base
docker run --rm --name qcsupl2-rt-$$ --cpus=8 --memory=12g --memory-swap=12g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 $t || { rc=$?; echo STAGE_FAIL $t rc $rc; break; }; done; exit $rc' > "$K/route_l2.log" 2>&1
rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run
if [ $rc -eq 0 ] && [ -f $K/$B/6_final.spef ]; then
  mkdir -p $K/meas_rcx
  for C in TT FF; do
    docker run --rm --memory=4g --memory-swap=4g --cpus=1 -v $K:/work:ro -v $K/meas_rcx:/out -v $K/meas_tools/meas_ck.tcl:/m.tcl:ro \
      -e ODB=/work/$B/6_final.odb -e SDC=/work/$B/6_final.sdc -e SPEF=/work/$B/6_final.spef -e OT_CORNER=$C -e OUT=/out/meas_rcx_$C.tsv \
      openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /m.tcl" > $K/meas_rcx/meas_rcx_$C.log 2>&1 &
  done; wait
  docker run --rm -v $K/meas_rcx:/out openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /out
fi
echo "ROUTE_L2_DONE rc $rc"; exit $rc
