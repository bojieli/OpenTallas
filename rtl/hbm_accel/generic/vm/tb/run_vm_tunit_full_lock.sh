#!/usr/bin/env bash
# el1011-hbm-hcvm/vm: lockstep bench of ot_hgi_vm_tunit vs ot_hgi_vm_unit.
# usage: run_vm_tunit_full_lock.sh <outdir> [MUTS] [SEED] [CFG: die (NC 9 RP 96 W2 96 LQ 32 AP 1) | small (NC 8, no lanes)] [XR 0|1]
set -euo pipefail
OUT=$(realpath -m "$1"); MUTS=${2:-0}; SEED=${3:-11}; CFG=${4:-die}; XR=${5:-1}; mkdir -p "$OUT"
cd "$(dirname "$0")/../../../../.."
P=tb_hgi_vm_tunit_full_lock
if [ "$CFG" = small ]; then PP="-P $P.NC=8 -P $P.RP=0 -P $P.W2=0 -P $P.LQ=8 -P $P.AP=0"; else PP=""; fi
M=physical/asap7_memory_macros
V=rtl/hbm_accel/generic/vm
iverilog -g2012 $PP -P $P.XR=$XR -P $P.MUTS=$MUTS -s $P -o "$OUT/flock_${CFG}_x${XR}_$MUTS.vvp" \
  rtl/lib/ot_rst_relay.sv rtl/link/ot_fifo_sram_fwft.sv $V/ot_hgi_vm_core.sv $V/ot_hgi_vm_unit.sv $V/ot_hgi_vm_btile.sv $V/ot_hgi_vm_tunit.sv \
  $V/tb/$P.sv $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
vvp "$OUT/flock_${CFG}_x${XR}_$MUTS.vvp" +SEED=$SEED | tee "$OUT/flock_${CFG}_x${XR}_$MUTS.log" | tail -9
grep -q '^PASS VM tunit full lockstep' "$OUT/flock_${CFG}_x${XR}_$MUTS.log"
