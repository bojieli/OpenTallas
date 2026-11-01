#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
cd "$(dirname "$0")"
verilator --binary --timing -Wno-fatal --top-module tb -j 2 --Mdir obj tb.sv wrappers.sv qkd_kv_ctl_nc32_face.sv qkd_kv_ctl_c32_boot.sv qkd_kv_ctl_c32_misc.sv ot_s32_cells.sv qkd_host_program_loader_target.sv ot_sram_1rw_256x64_m4_r2c2.v >build.log 2>&1
./obj/Vtb >sim.log 2>&1
cat sim.log
