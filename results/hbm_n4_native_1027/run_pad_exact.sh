#!/bin/bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel);HERE=$ROOT/results/hbm_n4_native_1027;OUT=${1:?out}
mkdir -p "$OUT/source";tar -xzf "$HERE/source_snapshot.tar.gz" -C "$OUT/source"
cp "$HERE/tb_pad_exact.sv" "$HERE/pad_original_control_mutant.sv" "$OUT/source/"
cp "$ROOT/rtl/hbm_next/fused/ot_hnx_fused_tree.sv" "$OUT/source/rtl/hbm_next/fused/"
cd "$OUT/source";export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -O1 -j 1 -Wno-fatal --top-module tb_pad_exact -Mdir "$OUT/obj" -o native tb_pad_exact.sv pad_original_control_mutant.sv rtl/hbm_next/fused/ot_hnx_fused_tree.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v > "$OUT/build.log" 2>&1
"$OUT/obj/native" > "$OUT/positive.log" 2>&1;cat "$OUT/positive.log"
if "$OUT/obj/native" +MUT_ORIGINAL > "$OUT/mutant.log" 2>&1;then echo ORIGINAL_BUG_ESCAPED;exit 1;else echo ORIGINAL_BUG_CAUGHT;fi
