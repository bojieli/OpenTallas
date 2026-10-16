#!/bin/bash
# Production-shape functional VM port exercise, using actual mapped SRAM models.
# Historical dynamic write traffic is an adversarial safety test; no production schedule qualification.
set -eu
root=$1
name=$2
expect=$3
shift 3
cd "$root/src"
bash tools/qwen_tp8/vm_nox_bench.sh "$root" "$name" system "$expect" \
 -GELEMS=177808 -GNRB=64 -GSW=64 -GSMIN=7 -GSMAX=11 -GRETURN_LEAVES=1 -GNATIVE_BANKS=1 -GUSE_MACRO=1 \
 rtl/qwen_sys/vm_native_physical_20261015/qvm_bank_banked_native.sv \
 rtl/qwen_sys/vm_native_physical_20261015/qvm_su_bank_native.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v "$@"
