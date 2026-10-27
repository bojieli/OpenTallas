#!/bin/bash
# QC-SU-SRAMHALO 2026-10-27: prog L2 with SRAM pin-column exclusion strips: floorplan(+strips) -> place -> strip check -> CTS (L2 spec,
# re-sited) + GRT -> meas_ck GRT -> DRT/fill/finish (RCX 6_final.spef) -> meas_ck RCX TT/FF.  No hold repair, no clock edits.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); B=run/results/asap7/kq_qfd_dv_s8x_prog_mif0k2/base; IMG=openroad/orfs:asap7lock
st() { echo "HALO $1 $(date -Is)" | tee -a $K/chain_halo.txt; }
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"
dk() { docker run --rm --name qcsuhalo-$1-$$ --cpus=8 --memory=$2 --memory-swap=$2 -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $3"; }
chown_run() { docker run --rm -v "$K":/work $IMG chown -R $(id -u):$(id -g) /work/run; }
st start
dk place 16g "$M floorplan && $M place" > $K/place_halo.log 2>&1; rc=$?; chown_run; st "place rc $rc"; [ $rc = 0 ] || exit 3
dk chk 4g "ODB=/work/$B/3_place.odb openroad -python -exit /work/strip_check.py" > $K/strip_check.log 2>&1; st "$(grep STRIP_CHECK $K/strip_check.log)"
dk cts 12g "$M do-cts && $M do-5_1_grt" > $K/cts_grt.log 2>&1; rc=$?; chown_run; st "cts+grt rc $rc $(grep -h "overflow" $K/run/logs/asap7/*/base/5_1_grt.log | tail -1)"; [ $rc = 0 ] || exit 4
mkdir -p $K/meas; for C in TT FF; do docker run --rm --memory=4g --memory-swap=4g --cpus=1 -v $K:/work:ro -v $K/meas:/out -v $K/meas_tools/meas_ck.tcl:/m.tcl:ro -e ODB=/work/$B/5_1_grt.odb -e SDC=/work/$B/5_1_grt.sdc -e OT_CORNER=$C -e OUT=/out/meas_ck_$C.tsv $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /m.tcl" > $K/meas/meas_ck_$C.log 2>&1 & done; wait; st "grt meas done"
dk drt 16g "rc=0; for t in do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report; do $M \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > $K/route_halo.log 2>&1; rc=$?; chown_run
st "route rc $rc $(grep -h "Number of violations" $K/run/logs/asap7/*/base/5_2_route*.log 2>/dev/null | tail -1)"
if [ $rc = 0 ] && [ -f $K/$B/6_final.spef ]; then
  mkdir -p $K/meas_rcx; for C in TT FF; do docker run --rm --memory=4g --memory-swap=4g --cpus=1 -v $K:/work:ro -v $K/meas_rcx:/out -v $K/meas_tools/meas_ck.tcl:/m.tcl:ro -e ODB=/work/$B/6_final.odb -e SDC=/work/$B/6_final.sdc -e SPEF=/work/$B/6_final.spef -e OT_CORNER=$C -e OUT=/out/meas_rcx_$C.tsv $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /m.tcl" > $K/meas_rcx/meas_rcx_$C.log 2>&1 & done; wait
  docker run --rm -v $K:/work $IMG chown -R $(id -u):$(id -g) /work/meas_rcx /work/meas
fi
st "CHAIN_DONE rc $rc"; exit $rc
