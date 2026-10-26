#!/usr/bin/env bash
# KV-NATIVE sched_s10 (2026-10-17): qkd_ctrl_pc_sched PINREG=2 + qkd_ctrl_pc_ecc_child_sl bit-exact vs the s9 pair
# (PINREG=1 + qkd_ctrl_pc_ecc_child): e_sec / e_row one hclk later, every other sched output and every landed ECC output on
# the same edge (tb_sched_esecreg_equiv).  mut: the ECC child's section / row skip their P1 entry (must FAIL).
# usage: run_sched_esecreg_gate.sh OUTDIR [exact|mut]
set -euo pipefail
out=${1:?outdir}; mode=${2:-exact}
mkdir -p "$out"
srcs="rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_children.sv rtl/qwen_sys/static_kv_20261014/ot_qkd_static_emb_cdc.sv rtl/qwen_sys/static_kv_20261014/qkd_static_kv_write_observer.sv rtl/qwen_sys/static_kv_20261014/ot_qkd_static_ctrl_pc_emb.sv rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static_core.sv"
m=0; [ "$mode" = mut ] && m=1
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD -GMUT=$m \
  --top-module tb_sched_esecreg_equiv --Mdir "$out/obj_$mode" $srcs \
  rtl/test/qwen_static_kv/tb_sched_esecreg_equiv.sv \
  > "$out/build_$mode.log" 2>&1 || { tail -20 "$out/build_$mode.log"; exit 1; }
"$out/obj_$mode/Vtb_sched_esecreg_equiv" | tee "$out/run_$mode.log"
grep -q '^PASS sched esecreg equiv' "$out/run_$mode.log"
