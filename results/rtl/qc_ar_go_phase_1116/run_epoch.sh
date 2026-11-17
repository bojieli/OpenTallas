#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --top-module tb -j 1 -DOT_S8_SIM -DOT_QC_AR_ROUND96 -Wno-fatal -Wno-lint -Wno-style -Wno-PINMISSING --Mdir obj_epoch tb_epoch.sv packet/qfd_dv_ar_go_phase.sv packet/coupon_actual.sv packet/tap.sv packet/tap_helpers.sv packet/head.sv packet/leaf_fo32.sv packet/leaf_fo32_w.sv packet/rst.sv >build_epoch.log 2>&1
./obj_epoch/Vtb +sid=0 +ncy=2039 +raw=packet/epoch_0_raw.hex +gold=packet/epoch_0_gold.hex >epoch_0.log 2>&1
./obj_epoch/Vtb +sid=11 +ncy=851 +raw=packet/epoch_11_raw.hex +gold=packet/epoch_11_gold.hex >epoch_11.log 2>&1
for m in 1 2 3;do ./obj_epoch/Vtb +sid=0 +ncy=2039 +mut=$m +negative=1 +raw=packet/epoch_0_raw.hex +gold=packet/epoch_0_gold.hex >mutant_$m.log 2>&1;done
cat epoch_0.log epoch_11.log mutant_1.log mutant_2.log mutant_3.log
