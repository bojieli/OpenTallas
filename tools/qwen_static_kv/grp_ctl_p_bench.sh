#!/bin/bash
# KV-NATIVE 2026-10-17: qkd_kv_grp_ctl_p (pin-registered successor) vs qkd_kv_grp_ctl fed one ck edge later (tb_kv_grp_ctl_p).
# grp_ctl_p_bench.sh OUT [MUT]: MUT 0 PASS; 1 cdc2 addr / 2 phase meta / 3 cfg_we bypasses its pin flop must FAIL
set -euo pipefail
OUT=${1:?output}; MUT=${2:-0}; mkdir -p "$OUT"
S=rtl/qwen_sys/static_kv_20261014
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GMUT="$MUT" --top-module tb_kv_grp_ctl_p -Mdir "$OUT/obj_$MUT" \
 rtl/test/qwen_static_kv/tb_kv_grp_ctl_p.sv $S/qkd_kv_grp_ctl.sv $S/qkd_static_kv_phase_launch.sv $S/qkd_static_kv_ownership.sv \
 $S/qkd_static_kv_boot_cdc.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv > "$OUT/build_$MUT.log" 2>&1
"$OUT/obj_$MUT/Vtb_kv_grp_ctl_p" > "$OUT/run_$MUT.log" 2>&1 || { cat "$OUT/run_$MUT.log"; exit 1; }
cat "$OUT/run_$MUT.log"
