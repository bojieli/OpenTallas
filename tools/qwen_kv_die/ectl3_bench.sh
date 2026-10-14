#!/bin/bash
# q13-kvleaves 2026-10-13: three-leaf qkd_ectl3 vs the one-tile qkd_ectl (rtl/test/qwen_kv_die/tb_qkd_ectl3.sv), Verilator
# (iverilog does not re-evaluate klast() when T changes: its runs of this stack are not valid).
#   ectl3_bench.sh OUT [MUT]     MUT = A | B | C (leaf mutants) | "" (positive);  env S / E / NL override the straps / layers
# exit 0 iff the bench prints "ECTL3 PASS" (so a mutant job expects FAIL).
set -u
OUT=$(mkdir -p "$1" && readlink -f "$1"); MUT=${2:-}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
DEF="+define+KVD_ECTL_SLOT"; [ -n "$MUT" ] && DEF="$DEF +define+KVD_ECTL3_MUT_$MUT"
N=ectl3${MUT:+_$MUT}
$V --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 $DEF \
  -GS=${S:-1} -GE=${E:-3} -GNL=${NL:-4} --top-module tb_qkd_ectl3 -Mdir "$OUT/obj_$N" \
  rtl/test/qwen_kv_die/tb_qkd_ectl3.sv rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv rtl/hdc/nearhbm/qkd_ectl.sv \
  rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv rtl/hdc/ot_hdc_delay.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$OUT/build_$N.log" 2>&1 || { tail -8 "$OUT/build_$N.log"; echo BUILD_FAIL; exit 3; }
"$OUT/obj_$N/Vtb_qkd_ectl3" | tee "$OUT/$N.log" | tail -12
grep -q "^ECTL3 PASS" "$OUT/$N.log"
