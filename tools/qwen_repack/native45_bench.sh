#!/bin/bash
set -euo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
MUT=${2:-0}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mapfile -t SRC < <(python3 - <<'PY'
import json
s=json.load(open('tools/ref_tile/specs_q_tile_repack/qfd_tile_nk_rp1_a1.json'))['sources']
for p in s:
 if p.endswith('_bb.v'):continue
 print(p)
PY
)
"$V" --binary --timing -j 8 -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN +define+OT_QWEN_LSL_FP1 -GMUT="$MUT" --top-module tb_qwen_repack45_native -Mdir "$OUT/obj_$MUT" \
 "${SRC[@]}" rtl/lib/ot_rst_relay.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv rtl/physical/ot_qwen_tile_node.sv rtl/physical/qfd_tile_nk_rp2_45.sv rtl/test/tb_qwen_repack45_native.sv \
 physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$OUT/build_$MUT.log" 2>&1
"$OUT/obj_$MUT/Vtb_qwen_repack45_native" | tee "$OUT/run_$MUT.log"
# Legacy RTL diagnostics may print FAIL and call $finish (exit0). A native
# qualification needs the completed positive marker, never only process status.
grep -q '^REPACK45_NATIVE_PASS ' "$OUT/run_$MUT.log"
! grep -q '^FAIL\|REPACK45_NATIVE_FAIL\|REPACK45_MISMATCH\|%Fatal\|%Error' "$OUT/run_$MUT.log"
