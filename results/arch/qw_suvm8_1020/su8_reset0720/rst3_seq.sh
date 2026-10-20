#!/bin/bash
set -euo pipefail
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --x-initial unique -j 4 -Wno-fatal --top-module tb_su8_rst3_seq rtl/qwen_dv/s5/qfd_dv_s5_suvm7.sv rtl/qwen_dv/s5/qfd_dv_s5_su8.sv rtl/qwen_dv/s5/qfd_dv_s5_su8_rst3.sv rtl/test/qwen_dv/s5/su8/su7_control_projection.sv rtl/test/qwen_dv/s5/su8/tb_su8_rst3_seq.sv --Mdir rst3_seq_obj > rst3_seq_build.log 2>&1
for seed in 7 53 311;do
 ./rst3_seq_obj/Vtb_su8_rst3_seq +verilator+rand+reset+2 +verilator+seed+$seed > rst3_seq_seed$seed.log
 cat rst3_seq_seed$seed.log
 grep -q 'SU8_EQ PASS' rst3_seq_seed$seed.log
done
