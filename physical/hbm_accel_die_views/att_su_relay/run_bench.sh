#!/bin/bash
# hfd_att_su_relay chain bench: positive (must PASS) and MUT_RELAY negative (must FAIL).  usage: run_bench.sh ROOT OUT [N]
set -uo pipefail
R=$1; OUT=$2; N=${3:-8}; mkdir -p $OUT; cd $OUT
D=$R/physical/hbm_accel_die_views/att_su_relay
verilator --binary --timing -O2 -Wno-fatal -Wno-WIDTH --top-module tb_hfd_att_su_relay -GN=$N -Mdir obj \
  $D/rtl/hfd_att_su_relay.sv $D/tb/tb_hfd_att_su_relay.sv > build.log 2>&1 || { echo BUILD_FAIL; tail build.log; exit 2; }
./obj/Vtb_hfd_att_su_relay > pos.log 2>&1; ./obj/Vtb_hfd_att_su_relay +MUT_RELAY > neg.log 2>&1
grep RELAYCHAIN pos.log neg.log
grep -q RELAY_PASS pos.log && grep -q RELAY_FAIL neg.log && { echo RELAY_BENCH PASS; exit 0; }
echo RELAY_BENCH FAIL; exit 1
