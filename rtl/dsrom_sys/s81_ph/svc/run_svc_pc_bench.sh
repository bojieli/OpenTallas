#!/bin/bash
# run_svc_pc_bench.sh <out> <tag> [defines] [plusargs]: Verilator gate of dsfd_svc_pc (from the repo root); exit 0 iff PASS
set -u
command -v verilator >/dev/null || { echo "NO_VERILATOR on $(hostname)"; exit 3; }
O=$1; T=$2; D=${3:-}; A=${4:-}
mkdir -p $O
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_dsfd_svc_pc $D --Mdir $O/obj_$T \
  rtl/dsrom_sys/s81_ph/svc/tb_dsfd_svc_pc.sv rtl/dsrom_sys/s81_ph/svc/dsfd_svc_pc.sv > $O/build_$T.log 2>&1 || { echo BUILD_FAIL; grep -m5 -i error $O/build_$T.log; exit 2; }
$O/obj_$T/Vtb_dsfd_svc_pc $A > $O/run_$T.log 2>&1
grep -E "requests|TB_SVC_PC" $O/run_$T.log
grep -q "TB_SVC_PC PASS" $O/run_$T.log
