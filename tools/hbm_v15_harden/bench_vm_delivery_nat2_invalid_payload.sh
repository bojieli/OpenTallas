#!/bin/bash
set -euo pipefail
out=${1:?out};mut=${2:-0};capsule=${3:-results/physical/hsm_takeover_0825/nat2_exact};mkdir -p "$out"
S=("$capsule/ot_vms_ce_counter_pipe.sv" "$capsule/ot_vms_bank_static_strap.sv" "$capsule/ot_vms_bank_native_physical.sv" "$capsule/q0_core_renamed.sv" "$capsule/q1_core_renamed.sv" "$capsule/q2_core_renamed.sv" "$capsule/q0_wrapper.v" "$capsule/q1_wrapper.v" "$capsule/q2_wrapper.v" "$capsule/ot_sram_1r1w_1024x256_m2_r2c2.v")
iverilog -g2012 -s tb_vm_delivery_nat2_invalid_payload -Ptb_vm_delivery_nat2_invalid_payload.MUT="$mut" -o "$out/proof.vvp" "${S[@]}" rtl/hbm_accel/loader/service_native/split/tb_vm_delivery_nat2_invalid_payload.sv > "$out/build.log" 2>&1
vvp "$out/proof.vvp" > "$out/proof.log" 2>&1 || { cat "$out/proof.log";exit 1; }
cat "$out/proof.log";grep -q 'VM_NAT2_INVALID_DQ PASS' "$out/proof.log"
