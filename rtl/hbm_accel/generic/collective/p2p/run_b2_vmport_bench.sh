#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); shift; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
D=rtl/hbm_accel/generic/vm/b2
"$V" --binary --timing --hierarchical -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-LATCH -Wno-WIDTHCONCAT \
 --top-module tb_hgi_coll_b2_vmport --Mdir "$OUT/obj" "$@" "$P/b2_coll_hier.vlt" \
 "$P/tb_hgi_coll_b2_vmport.sv" "$P/ot_hgi_coll_b2_vmport.sv" "$P/ot_vms_slice_coll_sw.sv" "$P/ot_vms_slice_clocked.sv" "$P/ot_vms_slice_no_cq.sv" "$P/ot_hgi_coll_rgx_wtx.sv" "$P/ot_hgi_coll_crl.sv" \
 rtl/hbm_accel/generic/collective/rgx/ot_hgi_coll_rgx_snk.sv \
 "$D/ot_vms_slice.sv" "$D/ot_vms_bank.sv" "$D/ot_vms_hub.sv" "$D/ot_vms_rstop.sv" "$D/ot_vms_rcl.sv" "$D/ot_vms_star.sv" "$D/ot_vms_relay.sv" \
 rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_hgi_coll_b2_vmport" > "$OUT/run.log" 2>&1 || true
cat "$OUT/run.log"
grep -q '^B2_COLL_VMPORT PASS' "$OUT/run.log"
