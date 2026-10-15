#!/usr/bin/env bash
# hgi-unitrate: tb_hgi_vm_lanes (client wide lane groups under concurrent DMA / packet load).  usage: run_vm_lanes.sh <out>
# env VMMUT=n (ot_hgi_vm_core MUT: 5 response group, 6 client write over a group write)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd); O=$(realpath -m "$1"); mkdir -p "$O"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; T=m${VMMUT:-0}
$V --binary --timing -O2 -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-LATCH \
  -Wno-WIDTHCONCAT --top-module tb_hgi_vm_lanes -DVMMUT=${VMMUT:-0} --Mdir "$O/obj_$T" rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv \
  rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  rtl/hbm_accel/generic/vm/tb_hgi_vm_lanes.sv > "$O/build_$T.log" 2>&1 || { tail -20 "$O/build_$T.log"; exit 2; }
"$O/obj_$T/Vtb_hgi_vm_lanes" | tee "$O/run_$T.log" | tail -8
