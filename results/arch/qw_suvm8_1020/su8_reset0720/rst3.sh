#!/bin/bash
set -euo pipefail
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --x-initial unique -j 4 -Wno-fatal --top-module tb_su8_rst3 rtl/qwen_dv/s5/qfd_dv_s5_su8.sv rtl/qwen_dv/s5/qfd_dv_s5_su8_rst3.sv rtl/test/qwen_dv/s5/su8/tb_su8_rst3.sv --Mdir rst3_obj > rst3_build.log 2>&1
for seed in 7 53 311;do
 ./rst3_obj/Vtb_su8_rst3 +verilator+rand+reset+2 +verilator+seed+$seed > rst3_seed$seed.log
 cat rst3_seed$seed.log
 grep -q 'SU8_RST3 PASS' rst3_seed$seed.log
done
