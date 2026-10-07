#!/bin/bash
# run_svc_stn_bench.sh <out> <tag> [defines] [plusargs]: Verilator gate of a dsfd_svc_stn chain (repo root); exit 0 iff PASS
set -u
O=$1; T=$2; D=${3:-}; A=${4:-}
mkdir -p $O
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_dsfd_svc_stn $D --Mdir $O/obj_$T \
  rtl/dsrom_sys/s81_ph/svc/tb_dsfd_svc_stn.sv rtl/dsrom_sys/s81_ph/svc/dsfd_svc_stn.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv > $O/build_$T.log 2>&1 || { echo BUILD_FAIL; grep -m5 -i error $O/build_$T.log; exit 2; }
$O/obj_$T/Vtb_dsfd_svc_stn $A > $O/run_$T.log 2>&1
grep -E "^q |TB_SVC_STN" $O/run_$T.log
grep -q "TB_SVC_STN PASS" $O/run_$T.log
