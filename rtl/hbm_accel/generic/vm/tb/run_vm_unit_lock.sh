#!/usr/bin/env bash
# hardcore-1010/c: lockstep bench of ot_hgi_vm_unit vs the pre-change unit.  usage: run_vm_unit_lock.sh <outdir> [MUTS]
set -euo pipefail
OUT=$(realpath -m "$1"); MUTS=${2:-0}; mkdir -p "$OUT"
cd "$(dirname "$0")/../../../../.."
M=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
V=rtl/hbm_accel/generic/vm
iverilog -g2012 -P tb_hgi_vm_unit_lock.MUTS=$MUTS -s tb_hgi_vm_unit_lock -o "$OUT/lock_$MUTS.vvp" \
  $V/ot_hgi_vm_core.sv $V/ot_hgi_vm_unit.sv $V/tb/ot_hgi_vm_unit_ref.sv $V/tb/tb_hgi_vm_unit_lock.sv $M
vvp "$OUT/lock_$MUTS.vvp" | tee "$OUT/lock_$MUTS.log" | tail -6
grep -q '^PASS VM unit lockstep' "$OUT/lock_$MUTS.log"
