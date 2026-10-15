#!/bin/bash
set -euo pipefail
out=${1:?out};mut=${2:-0};mkdir -p "$out"
m=physical/asap7_memory_macros
iverilog -g2012 -s tb_vm_delivery_invalid_payload -Ptb_vm_delivery_invalid_payload.MUT=$mut -o "$out/proof.vvp" rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv "$m/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$m/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" rtl/hbm_accel/loader/service_native/split/tb_vm_delivery_invalid_payload.sv
vvp "$out/proof.vvp" >"$out/proof.log" 2>&1 || { cat "$out/proof.log";exit 1; }
cat "$out/proof.log"
grep -q 'VM_INVALID_DQ PASS' "$out/proof.log"
