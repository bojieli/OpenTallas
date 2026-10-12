#!/usr/bin/env bash
# el1011-hbm-hcvm/vm: lockstep bench of ot_hgi_vm_tunit vs the pre-change unit.  usage: run_vm_tunit_lock.sh <outdir> [MUTS] [SEED]
set -euo pipefail
OUT=$(realpath -m "$1"); MUTS=${2:-0}; SEED=${3:-11}; mkdir -p "$OUT"
cd "$(dirname "$0")/../../../../.."
M=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
V=rtl/hbm_accel/generic/vm
iverilog -g2012 -P tb_hgi_vm_tunit_lock.MUTS=$MUTS -s tb_hgi_vm_tunit_lock -o "$OUT/tlock_$MUTS.vvp" \
  rtl/lib/ot_rst_relay.sv $V/ot_hgi_vm_core.sv $V/ot_hgi_vm_tunit.sv $V/tb/ot_hgi_vm_unit_ref.sv $V/tb/tb_hgi_vm_tunit_lock.sv $M
vvp "$OUT/tlock_$MUTS.vvp" +SEED=$SEED | tee "$OUT/tlock_$MUTS.log" | tail -6
grep -q '^PASS VM tunit lockstep' "$OUT/tlock_$MUTS.log"
