#!/bin/bash
# hardcore-1010 (2026-10-10): Verilator lockstep bench tb_qfd_seq_su_bi_psram (u0 = PSRAM 0 / HQ2 0 vs u1).
# usage: run_seq_su_bi_lockstep.sh <outdir> <tag> [-G...]   (run from the repo root; prints the tb's PASS / FAIL line)
# Verilator, not Icarus: Icarus re-evaluates `wire x = f(args)` only when the ARGUMENTS change, so the ICUT readiness
# function (it reads module nets inside rdy_x) goes stale and the controllers' own ICUT assertion fires spuriously.
set -e
O=$1; T=$2; shift 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=verilator
mkdir -p "$O"
L="rtl/test/tb_qfd_seq_su_bi_psram.sv rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv rtl/rom/ot_qwen_tp_seq_w12.sv rtl/rom/ot_rom_pkg_link.sv rtl/rom/ot_rom_pkg_ctrl.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_dyn_ttiles.sv rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_cg.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
"$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS -O1 --x-assign fast --x-initial fast \
    --top-module tb_qfd_seq_su_bi_psram "$@" --Mdir "$O/$T" $L > "$O/build_$T.log" 2>&1
"$O/$T/Vtb_qfd_seq_su_bi_psram" > "$O/$T.log" 2>&1 || true
grep -E '^(PASS|FAIL) seq_su_bi_psram' "$O/$T.log" | tail -1
grep -q '^PASS seq_su_bi_psram' "$O/$T.log"
