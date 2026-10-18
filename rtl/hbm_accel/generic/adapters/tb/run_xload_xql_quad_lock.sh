#!/usr/bin/env bash
# RBH-XQL 2026-10-18: d4g quadrant x-load (xql NP 2 per quadrant, ctlx unchanged) locked to today's xql NP 4.
# usage: run_xload_xql_quad_lock.sh <outdir> [QMUT]   -> XQL_QUAD_LOCK PASS / FAIL   (QMUT 1..5 must FAIL)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "$1"); QM=${2:-0}; mkdir -p "$OUT"; cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
B="$OUT/obj_q$QM"
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -j 8 -DQMUT=$QM --top-module tb_xload_xql_quad_lock --Mdir "$B" \
  rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv \
  rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv \
  rtl/hdc/ot_hdc_delay.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_xql_quad_lock.sv > "$OUT/build_q$QM.log" 2>&1 || { tail -30 "$OUT/build_q$QM.log"; exit 1; }
"$B/Vtb_xload_xql_quad_lock" > "$OUT/qlock_q$QM.log" 2>&1 || true
grep -E "ERR|PASS|FAIL|quadrant vs" "$OUT/qlock_q$QM.log" | tail -12
grep -q 'XQL_QUAD_LOCK PASS' "$OUT/qlock_q$QM.log"
