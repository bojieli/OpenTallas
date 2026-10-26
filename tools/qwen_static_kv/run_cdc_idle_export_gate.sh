#!/usr/bin/env bash
# cdc_s7c idle_core single export flop: bit-exact vs the closed cdc_s7b reference, and the mutant must FAIL.
# usage: run_cdc_idle_export_gate.sh OUTDIR [exact|mut]
set -euo pipefail
out=${1:?outdir}; mode=${2:-exact}
mkdir -p "$out"
srcs="rtl/qwen_sys/static_kv_20261014/ot_qkd_static_emb_cdc.sv rtl/qwen_sys/static_kv_20261014/qkd_static_kv_write_observer.sv rtl/qwen_sys/static_kv_20261014/ot_qkd_static_ctrl_pc_emb.sv rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static_core.sv"
def=""; [ "$mode" = mut ] && def="+define+OT_CDC_IDLE_EXPORT_MUT"
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD $def \
  --top-module tb_cdc_idle_export_equiv --Mdir "$out/obj_$mode" $srcs \
  rtl/test/qwen_static_kv/ref_qkd_ctrl_pc_cdc_child_s7b.sv rtl/test/qwen_static_kv/tb_cdc_idle_export_equiv.sv \
  > "$out/build_$mode.log" 2>&1 || { tail -20 "$out/build_$mode.log"; exit 1; }
"$out/obj_$mode/Vtb_cdc_idle_export_equiv" | tee "$out/run_$mode.log"
grep -q '^PASS cdc idle export equiv' "$out/run_$mode.log"
