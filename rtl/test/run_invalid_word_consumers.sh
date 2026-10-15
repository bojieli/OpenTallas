#!/bin/bash
# el1011-q-seq: consumer-side proof that p_f_e2 / scale_addr are unused while their valids are low (see the tb header).
# usage: run_invalid_word_consumers.sh <outdir> <tag> [-G...]
set -e
O=$1; T=$2; shift 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=verilator
mkdir -p "$O"
L="rtl/test/tb_invalid_word_consumers.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_qwen_rt_rom_bank.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/hdc/ot_hdc_sfu.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
"$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign fast --x-initial fast --top-module tb_invalid_word_consumers "$@" --Mdir "$O/$T" $L > "$O/build_$T.log" 2>&1 || { grep -m5 '%Error' "$O/build_$T.log"; exit 1; }
"$O/$T/Vtb_invalid_word_consumers" > "$O/$T.log" 2>&1 || true
grep -E '^(PASS|FAIL) invalid_word_consumers' "$O/$T.log" | tail -1
grep -q '^PASS invalid_word_consumers' "$O/$T.log"
