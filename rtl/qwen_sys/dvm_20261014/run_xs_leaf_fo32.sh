#!/bin/bash
# Equivalence bench of ot_qfd_xs_leaf_fo32 vs the closed w130 leaf configuration (Verilator 5.050 --timing).
# Usage (repository root): run_xs_leaf_fo32.sh <out_dir> [-Gparam=value ...]   (-GMUT=2: swapped-tile mutant, must FAIL)
out=$1; shift
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/dvm_20261014
mkdir -p $out
$V --binary --timing -j ${JOBS:-8} -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --x-assign 0 --x-initial 0 \
   --top-module tb_qfd_xs_leaf_fo32 --Mdir $out/obj "$@" $D/tb_qfd_xs_leaf_fo32.sv $D/ot_qfd_xs_leaf_fo32.sv \
   $D/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv -o tb > $out/build.log 2>&1 || { echo BUILD_FAIL; grep -m20 -i "%Error" $out/build.log; exit 2; }
$out/obj/tb > $out/run.log 2>&1; rc=$?
grep -E "^(PASS|FAIL|MISMATCH)" $out/run.log | head -8
exit $rc
