#!/bin/bash
set -eu
cd "$(dirname "$0")/../../.."
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 0 1;do
 "$V" --binary --timing -j 4 -Wno-fatal --top-module tb_ovl_admission_launch -GEARLY=$m --Mdir "$PWD/obj$m" rtl/test/qwen_split/tb_ovl_admission_launch.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_ovl_seq.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv > build$m.log 2>&1
 ./obj$m/Vtb_ovl_admission_launch > run$m.log 2>&1
 cat run$m.log
done
