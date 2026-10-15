#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
M=physical/asap7_memory_macros
defs=()
if [ "${RNE_MUTANT:-0}" = 1 ];then defs+=(-DOT_SFU_VM_BF16_MUTANT);fi
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" "${defs[@]}" --binary --timing -O1 -j 4 -CFLAGS -O0 -Wno-fatal --top-module tb_hgi_sfu_vm_round_static --Mdir "$OUT/obj" \
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_vm_static_bridge.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_vm_round_static.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_operand_store.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv \
 "$M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" \
 "$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" \
 "$M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_vm_round_static" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
