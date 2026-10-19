#!/usr/bin/env bash
# HBM-BANKLAT-XL 10-19: x-load ctlx per-bank RD_LAT on faces banks behind unequal die lanes (tb_hgi_xload_banklat.sv).
# usage: run_xload_banklat.sh <outdir> [CFG] [BMUT]   -> XLOAD_BANKLAT PASS / FAIL
#   CFG 0 NE lanes / 1 NW lanes (exact vectors), 2 / 3 budget vector + die rq pads on NE / NW lanes, 4 scalar 6 reference
#   BMUT 1 old RD_LAT 6, 2 scalar max (no stagger), 3 ctl MUT 7 (stagger ignored), 4 vector element off by one: must FAIL
# Sources read: rtl/lib/ot_rst_relay.sv, rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv,
#   rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv, rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv,
#   rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv, rtl/hdc/ot_hdc_delay.sv,
#   physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv, physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv,
#   physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v,
#   rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_banklat.sv
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "$1"); CFG=${2:-0}; BM=${3:-0}; mkdir -p "$OUT"; cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
T="c${CFG}_m${BM}"; B="$OUT/obj_$T"
verilator --version
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -j ${JOBS:-8} -DCFG=$CFG -DBMUT=$BM --top-module tb_xload_banklat --Mdir "$B" \
  rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv \
  rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv \
  rtl/hdc/ot_hdc_delay.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_banklat.sv > "$OUT/build_$T.log" 2>&1 || { tail -30 "$OUT/build_$T.log"; exit 2; }
"$B/Vtb_xload_banklat" > "$OUT/banklat_$T.log" 2>&1 || true
grep -E "SEED|ERR|PASS|FAIL|XLOAD_BANKLAT" "$OUT/banklat_$T.log" | tail -12
grep -q '^XLOAD_BANKLAT PASS' "$OUT/banklat_$T.log"
