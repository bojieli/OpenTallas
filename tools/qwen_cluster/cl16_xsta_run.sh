#!/bin/bash
# usage: run.sh GATE_DIR CORNER OUTDIR [DB SDC]
set -e
G=$1; C=$2; O=$3; DB=${4:-4_1_cts.odb}; SDC=${5:-4_cts.sdc}
B=$G/routes/gate/work/orfs/results/asap7/opentallas_qfd_c_b16_dv_asap7_ref_gate/base
docker run --rm -v $B:/base:ro -v $G/src:/src:ro -v $O:/o -e OT_C=$C -e OT_DB=$DB -e OT_SDC=$SDC \
  -e OT_PAIRS=/o/${OT_PAIRSF:-pairs_all.txt} -e OT_OUT=/o/${OT_OUTN:-xpaths}_$C.txt ${OT_DETAIL:+-e OT_DETAIL=/o/$OT_DETAIL} openroad/orfs:latest \
  bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -no_init /o/cl16_xsta.tcl" > $O/${OT_OUTN:-xpaths}_$C.log 2>&1
