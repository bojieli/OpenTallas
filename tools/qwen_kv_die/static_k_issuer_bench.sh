#!/bin/bash
set -euo pipefail
OUT=${1:?output}; MUT=${2:-0}; mkdir -p "$OUT"
# KISS=1 (KVJ-D 2026-10-17): the fused ECTL A + K issuer tile qkd_static_ectla_kiss in its A|B|C parent.
KX=(); if [ "${KISS:-0}" = 1 ]; then KX=(+define+OT_KISS rtl/qwen_sys/static_kv_20261014/qkd_static_ectla_kiss.sv); fi
# KISS_RC=1 (ECTLA-2 2026-10-17): the same tile with its two regional clock roots (ck body, ck_k issuer) tied to one die clock.
if [ "${KISS_RC:-0}" = 1 ]; then KX=(+define+OT_KISS +define+OT_KISS_RC rtl/qwen_sys/static_kv_20261014/qkd_static_ectla_kiss.sv); fi
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GMUT="$MUT" --top-module tb_qkd_static_k_issuer -Mdir "$OUT/obj_$MUT" "${KX[@]}" \
 rtl/test/qwen_static_kv/tb_qkd_static_k_issuer.sv rtl/qwen_sys/static_kv_20261014/qkd_static_k_issuer.sv \
 rtl/qwen_sys/split_20261014/qkd_ectl3_epoch_direct_s.sv rtl/qwen_sys/split_20261014/qkd_ectl_a_tp8_epoch_direct.sv rtl/qwen_sys/split_20261014/qkd_ectl_native_direct_tp8.sv rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv rtl/hdc/ot_hdc_delay.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$OUT/build_$MUT.log" 2>&1
"$OUT/obj_$MUT/Vtb_qkd_static_k_issuer" > "$OUT/run_$MUT.log" 2>&1
cat "$OUT/run_$MUT.log"
