#!/bin/bash
# build.sh RUN KIND(walker|static): Verilator build of a bf_asbuilt_1101 bench (flags as the 11-01 as-built BF runs)
set -u
run=$1; kind=$2
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
cd $run || exit 4
/usr/bin/time -v $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
  -DFRAME=bf_asbuilt_frame -DTB_BFTRACE -DTB_XO_LAT=2 -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 --top-module tb_s81dv_frame \
  -Mdir $run/obj_$kind -f $run/$kind.f --build-jobs 2 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > $run/build_$kind.log 2>&1
rc=$?
echo "BUILD $kind rc=$rc $( [ -x $run/obj_$kind/Vtb_s81dv_frame ] && echo BIN_OK || echo NO_BIN )" | tee -a $run/build_$kind.log
exit $rc
