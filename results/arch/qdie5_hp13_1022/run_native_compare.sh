#!/bin/bash
T=$(readlink -f $1); cd $T
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --binary -j 8 --timing -I. -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTHCONCAT -O1 --top-module tb_qfd_tt_ctlm_dv_lpf_lp -f native_compare.f -Mdir obj_hp13_native > native_compare_build.log 2>&1 || { echo BUILD_FAIL; exit 3; }
for mode in 1 2; do ./obj_hp13_native/Vtb_qfd_tt_ctlm_dv_lpf_lp +CALRDIR=$mode +CALR_ROM_DIR=calr10 > native_compare_calr$mode.log 2>&1; grep -hE "LP_LOCKSTEP|TLOAD_PRODUCER|MISMATCH" native_compare_calr$mode.log | head -4; done
