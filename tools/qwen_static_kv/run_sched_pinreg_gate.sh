#!/usr/bin/env bash
# sched_s8 (KV-SCHED8 2026-10-17) flop-first pins: qkd_ctrl_pc_sched PINREG=1 bit-exact vs the closed sched_s7b reference
# (listed outputs one hclk later, the rest same-cycle; PINREG=0 same-cycle), and the mutants must FAIL.
# mut: the D-form idle veto drops the p_em_v pin flop; esec_mut (sched_s9): e_sec / e_row drop the late p_kv_v pin-flop select.
# usage: run_sched_pinreg_gate.sh OUTDIR [exact|mut|esec_mut]
set -euo pipefail
out=${1:?outdir}; mode=${2:-exact}
mkdir -p "$out"
srcs="rtl/qwen_sys/static_kv_20261014/ot_qkd_static_emb_cdc.sv rtl/qwen_sys/static_kv_20261014/qkd_static_kv_write_observer.sv rtl/qwen_sys/static_kv_20261014/ot_qkd_static_ctrl_pc_emb.sv rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static_core.sv"
def=""; [ "$mode" = mut ] && def="+define+OT_SCHED_PINREG_MUT"; [ "$mode" = esec_mut ] && def="+define+OT_SCHED_ESEC_MUT"
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD $def \
  --top-module tb_sched_pinreg_equiv --Mdir "$out/obj_$mode" $srcs \
  rtl/test/qwen_static_kv/ref_qkd_ctrl_pc_sched_s7b.sv rtl/test/qwen_static_kv/tb_sched_pinreg_equiv.sv \
  > "$out/build_$mode.log" 2>&1 || { tail -20 "$out/build_$mode.log"; exit 1; }
"$out/obj_$mode/Vtb_sched_pinreg_equiv" | tee "$out/run_$mode.log"
grep -q '^PASS sched pinreg equiv' "$out/run_$mode.log"
