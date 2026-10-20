#!/bin/bash
set -euo pipefail
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_su8 rtl/qwen_dv/s5/qfd_dv_s5_suvm7.sv rtl/qwen_dv/s5/qfd_dv_s5_su8.sv rtl/test/qwen_dv/s5/su8/su7_control_projection.sv rtl/test/qwen_dv/s5/su8/tb_su8.sv --Mdir obj > build.log 2>&1
./obj/Vtb_su8 > run.log
cat run.log
grep -q 'SU8_EQ PASS' run.log
