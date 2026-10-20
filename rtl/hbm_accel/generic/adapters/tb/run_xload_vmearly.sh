#!/usr/bin/env bash
# HBM-VMEARLY-XL 10-19: x-load ISSUE_AHEAD (compiler early issue into x_xb slots) on the current ctlx (tb_hgi_xload_vmearly.sv).
# usage: run_xload_vmearly.sh <outdir> [BMUT] [MVD]   -> XLOAD_VMEARLY PASS / FAIL
#   BMUT 0 PASS; 1 slot index ignored, 2 read before the producer's write retired, 3 ISSUE_AHEAD ignored: must FAIL
#   MVD = SM matvec edges per record (default 800)
# Sources read: rtl/lib/ot_rst_relay.sv, rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv,
#   rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv, rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv,
#   rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv, rtl/hdc/ot_hdc_delay.sv,
#   physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv, physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv,
#   physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v,
#   rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_vmearly.sv
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "$1"); BM=${2:-0}; MV=${3:-800}; mkdir -p "$OUT"; cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
T="m${BM}_mv${MV}"; B="$OUT/obj_$T"
verilator --version
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -j ${JOBS:-8} -DBMUT=$BM -DMVD=$MV --top-module tb_xload_vmearly --Mdir "$B" \
  rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv \
  rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv \
  rtl/hdc/ot_hdc_delay.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_vmearly.sv > "$OUT/build_$T.log" 2>&1 || { tail -30 "$OUT/build_$T.log"; exit 2; }
"$B/Vtb_xload_vmearly" > "$OUT/vmearly_$T.log" 2>&1 || true
grep -E "ERR|XLOAD_VMEARLY" "$OUT/vmearly_$T.log" | tail -14
grep -q '^XLOAD_VMEARLY PASS' "$OUT/vmearly_$T.log"
