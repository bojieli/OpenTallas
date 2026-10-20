#!/usr/bin/env bash
# HBM-XLP10 10-20: pipelined x-load bench (tb_hgi_xload_xpipe.sv): XP ctlx (ot_hgi_sm_xload_static_xqlp) vs cl2 xql.
# usage: [SEED=n] run_xload_xpipe.sh <outdir> [EARLY] [DMUT] [NCMD]  -> XLOAD_XPIPE PASS / FAIL (default SEED 11)
#   EARLY 1 = compiler slots one edge before the law (must FAIL); DMUT 8 = RTL egress xb does not ride (must FAIL)
# Sources read: rtl/lib/ot_rst_relay.sv, rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv,
#   rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv, rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2xp.sv, rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xqlp.sv,
#   rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv, rtl/hdc/ot_hdc_delay.sv,
#   physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv, physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv,
#   physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v,
#   rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_xpipe.sv
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "$1"); EA=${2:-0}; DM=${3:-0}; NC=${4:-24}; mkdir -p "$OUT"; cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
T="e${EA}_m${DM}_n${NC}"; B="$OUT/obj_$T"
verilator --version
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -j ${JOBS:-8} -DEARLY=$EA -DDMUT=$DM -DNCMD=$NC --top-module tb_xload_xpipe --Mdir "$B" \
  rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv \
  rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2xp.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xqlp.sv \
  rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv \
  rtl/hdc/ot_hdc_delay.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_xpipe.sv > "$OUT/build_$T.log" 2>&1 || { tail -30 "$OUT/build_$T.log"; exit 2; }
"$B/Vtb_xload_xpipe" +SEED=${SEED:-11} > "$OUT/xpipe_$T.log" 2>&1 || true
grep -E "SEED|ERR|PASS|FAIL|XLOAD_XPIPE|^ref " "$OUT/xpipe_$T.log" | tail -40
grep -q '^XLOAD_XPIPE PASS' "$OUT/xpipe_$T.log"
