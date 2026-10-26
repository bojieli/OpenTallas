#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=/home/ubuntu/.local/opentallas-tools/bin/verilator
B=../../../rtl/hbm_accel/generic/vm/static
M=../../../physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2
"$V" --binary --timing --top-module tb -Wno-fatal -j 2 --Mdir obj tb.sv "$B/ot_hbm_vm_lg_static_bank.sv" "$B/faces_q0/hfd_vms_bank_native_q0_faces.sv" "$B/faces_q0/ot_vms_bank_q0_faces_core.sv" "$B/faces_q0/ot_vms_bank_q0_faces_body.sv" "$B/ot_vms_ce_counter_pipe.sv" "$M/ot_sram_1r1w_1024x256_m2_r2c2.v" > build.log 2>&1
./obj/Vtb > run.log 2>&1
cat run.log
