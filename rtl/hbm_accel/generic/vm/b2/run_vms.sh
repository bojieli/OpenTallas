#!/usr/bin/env bash
# HBM B2 VM slice benches (el1011-hbm-b2-vm).  usage: run_vms.sh <out> <tb_vms_slice|tb_vms_ring4> [-G overrides...]
# PASS line: VMS_SLICE_BENCH PASS / VMS_RING4_BENCH PASS.  Verilator pinned to 5.050 (5.032 miscompiles push_back).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); O=$(realpath -m "$1"); TB=$2; shift 2; mkdir -p "$O"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
T=${TB}$(echo "$@" | tr -c 'A-Za-z0-9=' '_')
D=rtl/hbm_accel/generic/vm/b2
$V --binary --timing -O2 -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-LATCH \
  -Wno-WIDTHCONCAT -Wno-CASEINCOMPLETE --top-module $TB "$@" --Mdir "$O/obj_$T" \
  $D/ot_vms_bank.sv $D/ot_vms_hub.sv $D/ot_vms_rstop.sv $D/ot_vms_rcl.sv $D/ot_vms_star.sv $D/ot_vms_relay.sv $D/ot_vms_slice.sv \
  rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/link/ot_fifo_sram_fwft.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $D/$TB.sv > "$O/build_$T.log" 2>&1 \
  || { tail -30 "$O/build_$T.log"; exit 2; }
"$O/obj_$T/V$TB" > "$O/run_$T.log" 2>&1 || true
grep -E "VMS_|MISMATCH|TIMEOUT|FAULT" "$O/run_$T.log" | head -20
grep -qE "^VMS_(SLICE|RING4)_BENCH PASS" "$O/run_$T.log"   # rc 0 only on PASS
