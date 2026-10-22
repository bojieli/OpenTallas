#!/usr/bin/env bash
# STW-S81-TOPK-VMUX (10-21): build + run tb_dsdv_idx_vmux_n32 for VM_MUT / DL_MUT 0..3 (run from the source root).
# usage: run_vmux_n32.sh <out>.  Verilator = the closure daemon's pinned 5.050 (VL overrides).
set -u -o pipefail
OUT=$1; mkdir -p "$OUT"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv
rtl/dsrom_sys/s81_dv/idx/dsdv_idx_vmux_n32.sv
rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_vmux_n32.sv"
( sha256sum $SRC; $VL --version ) > "$OUT/sources.sha256"
for c in "0 0" "1 0" "2 0" "3 0" "0 1" "0 2"; do
  set -- $c; B=$OUT/vm$1_dl$2; mkdir -p $B
  $VL --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -DVM_MUT=$1 -DDL_MUT=$2 --top-module tb_dsdv_idx_vmux_n32 \
    $SRC -Mdir $B/obj > $B/build.log 2>&1 || { tail -5 $B/build.log; echo "BUILD FAIL $c"; continue; }
  $B/obj/Vtb_dsdv_idx_vmux_n32 +SEED=${SEED:-7} > $B/run.log 2>&1
  echo "vm_mut $1 dl_mut $2: $(grep VMUX_N32 $B/run.log)"
done
