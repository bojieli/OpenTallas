#!/bin/bash
# fe-push-qwen-1010 (2026-10-10): Verilator lockstep bench tb_qfd_tt_ctlm_i_psram (u0 = PSRAM 0 / HQ2 0 vs u1).
# usage: run_tt_ctlm_i_lockstep.sh <outdir> <tag> [-G...]   (run from the repo root; prints the tb's PASS / FAIL line)
# Verilator, not Icarus (Icarus stales the ICUT readiness function; see run_seq_su_bi_lockstep.sh).
set -e
O=$1; T=$2; shift 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=verilator
mkdir -p "$O"
L="rtl/test/tb_qfd_tt_ctlm_i_psram.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/qwen_sys/redesign_qwen/ot_qfd_tt_split.sv rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/qwen_sys/redesign_qwen/ot_qfd_tt_ctlm_i.sv rtl/hdc/ot_hdc_dyn_ttiles.sv rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_cg.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
"$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS -O1 --x-assign fast --x-initial fast \
    +define+OT_ICUT_NONFATAL --top-module tb_qfd_tt_ctlm_i_psram "$@" --Mdir "$O/$T" $L > "$O/build_$T.log" 2>&1
"$O/$T/Vtb_qfd_tt_ctlm_i_psram" > "$O/$T.log" 2>&1 || true
grep -E '^(PASS|FAIL) tt_ctlm_i_psram' "$O/$T.log" | tail -1
grep -q '^PASS tt_ctlm_i_psram' "$O/$T.log"
