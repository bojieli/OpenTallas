#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -Wno-fatal --top-module tb_producer -j 4 --Mdir obj_producer tb_producer.sv qkd_static_kv_boot_dispatch_nc32.sv qkd_kv_ctl_c32_tpre.sv ot_s32_sel.sv ot_s32_and.sv qkd_d2d_cal_seq_bc4_rom64.sv ot_qwen_d2d_cal_seq_rom64_core.sv ot_rom_64x32_m2.v > build_producer.log 2>&1
./obj_producer/Vtb_producer > sim_producer.log 2>&1
cat sim_producer.log
