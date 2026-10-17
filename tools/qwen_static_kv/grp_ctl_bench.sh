#!/bin/bash
# KVJ-D 2026-10-17: per-group control tile bench (tb_kv_grp_ctl).  grp_ctl_bench.sh OUT [MUT]
set -euo pipefail
OUT=${1:?output}; MUT=${2:-0}; mkdir -p "$OUT"
S=rtl/qwen_sys/static_kv_20261014
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GMUT="$MUT" --top-module tb_kv_grp_ctl -Mdir "$OUT/obj_$MUT" \
 rtl/test/qwen_static_kv/tb_kv_grp_ctl.sv $S/qkd_kv_grp_ctl.sv $S/qkd_static_kv_phase_launch.sv $S/qkd_static_kv_ownership.sv \
 $S/qkd_static_kv_boot_cdc.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv > "$OUT/build_$MUT.log" 2>&1
"$OUT/obj_$MUT/Vtb_kv_grp_ctl" > "$OUT/run_$MUT.log" 2>&1 || { cat "$OUT/run_$MUT.log"; exit 1; }
cat "$OUT/run_$MUT.log"
