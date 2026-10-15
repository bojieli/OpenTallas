#!/usr/bin/env bash
# el1011-hbm-hcvm/vm: lockstep bench of ot_hgi_vm_tunit (+ ot_hgi_vm_btile) vs ot_hgi_vm_unit, under Verilator.
# usage: run_vm_tunit_full_lock.sh <outdir> [MUTS] [SEED] [CFG: die (NC 9 RP 96 W2 96 LQ 32 AP 1) | small (NC 8, no lanes)]
set -euo pipefail
OUT=$(realpath -m "$1"); MUTS=${2:-0}; SEED=${3:-11}; CFG=${4:-die}; mkdir -p "$OUT"
cd "$(dirname "$0")/../../../../.."
P=tb_hgi_vm_tunit_full_lock
PP=""; [ "$CFG" = small ] && PP="-GNC=8 -GRP=0 -GW2=0 -GLQ=8 -GAP=0"
M=physical/asap7_memory_macros
V=rtl/hbm_accel/generic/vm
O="$OUT/obj_${CFG}_$MUTS"
verilator --binary --timing -O1 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module $P $PP -GMUTS=$MUTS \
  -Mdir "$O" rtl/lib/ot_rst_relay.sv rtl/link/ot_fifo_sram_fwft.sv $V/ot_hgi_vm_core.sv $V/ot_hgi_vm_unit.sv \
  rtl/lib/ot_hdly.sv $V/ot_hgi_vm_btile.sv $V/ot_hgi_vm_tunit.sv $V/tb/$P.sv $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$OUT/build_${CFG}_$MUTS.log" 2>&1
"$O/V$P" +SEED=$SEED | tee "$OUT/flock_${CFG}_$MUTS.log" | tail -9
grep -q '^PASS VM tunit full lockstep' "$OUT/flock_${CFG}_$MUTS.log"
