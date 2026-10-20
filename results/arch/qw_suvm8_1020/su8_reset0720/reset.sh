#!/bin/bash
set -euo pipefail
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -j 2 -Wno-fatal --top-module tb_reset rtl/test/qwen_dv/s5/su8/tb_su8_reset.sv --Mdir reset_obj > reset_build.log 2>&1
./reset_obj/Vtb_reset > reset_run.log
cat reset_run.log
grep -q 'SU8_RESET PASS' reset_run.log
