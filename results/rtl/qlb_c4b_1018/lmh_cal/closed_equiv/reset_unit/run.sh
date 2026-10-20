#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
O="$PWD/results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv/reset_unit"
python3 "$O/prepare.py"
verilator --version > "$O/verilator.version"
verilator --cc --exe --build -j 8 -O2 -Wno-fatal -Wno-WIDTH --top-module tb --prefix Vtb --Mdir "$O/obj"  "$O/tb_reset.sv" "$O"/gold_*.sv  rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv  rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue_pw.sv  rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue_dense_pw.sv "$O/main_reset.cpp" > "$O/build.log" 2>&1
"$O/obj/Vtb" > "$O/run.log" 2>&1
