#!/bin/bash
set -euo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
MUT=${2:-0}
EXTRA=()
[[ ${QWEN_GLUE_HARD:-0} == 1 ]] && EXTRA+=(+define+OT_QWEN_GLUE_HARD_BENCH)

V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mapfile -t SRC < <(python3 - <<'PY'
import json
s=json.load(open('tools/qwen_romleaf/rc14_2000/baseline/parent_component_sources.json'))['sources']
for p in s:
 if p.endswith('_bb.v'):continue
 print(p)
PY
)
mapfile -t ALLSRC < <(printf '%s\n' "${SRC[@]}" rtl/lib/ot_rst_relay.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv rtl/physical/ot_qwen_tile_node.sv rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_45.sv rtl/physical/qfd_tile_nk_rp2_romleaf.sv rtl/physical/ot_qwen_tile_romleaf.sv rtl/physical/ot_qwen_tile_operand.sv rtl/physical/ot_qwen_tile_rqr_half.sv rtl/test/tb_qwen_romleaf_parent_nk_native.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
HASH=$( { sha256sum "${ALLSRC[@]}" "$0"; printf "%s\n" "${EXTRA[@]}"; "$V" --version; } | sha256sum | cut -d' ' -f1)
if [[ ! -f "$OUT/build.sha256" || $(cat "$OUT/build.sha256") != "$HASH" ]]; then
  rm -rf -- "$OUT/obj"
"$V" --binary --timing -j 8 -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN +define+OT_QWEN_LSL_FP1 "${EXTRA[@]}" --top-module tb_qwen_romleaf_parent_nk_native -Mdir "$OUT/obj" \
 "${SRC[@]}" rtl/lib/ot_rst_relay.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv rtl/physical/ot_qwen_tile_node.sv rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_45.sv rtl/physical/qfd_tile_nk_rp2_romleaf.sv rtl/physical/ot_qwen_tile_romleaf.sv rtl/physical/ot_qwen_tile_operand.sv rtl/physical/ot_qwen_tile_rqr_half.sv rtl/test/tb_qwen_romleaf_parent_nk_native.sv \
 physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$OUT/build_$MUT.log" 2>&1
  sha256sum "${ALLSRC[@]}" "$0" > "$OUT/sources.sha256"
  printf '%s\n' "$HASH" > "$OUT/build.sha256"
fi
"$OUT/obj/Vtb_qwen_romleaf_parent_nk_native" +MUT="$MUT" | tee "$OUT/run_$MUT.log"
# Legacy RTL diagnostics may print FAIL and call $finish (exit0). A native
# qualification needs the completed positive marker, never only process status.
grep -q '^ROMLEAF_PARENT_NK_NATIVE_PASS ' "$OUT/run_$MUT.log"
! grep -q '^FAIL\|ROMLEAF_PARENT_NK_NATIVE_FAIL\|ROMLEAF_PARENT_NK_MISMATCH\|%Fatal\|%Error' "$OUT/run_$MUT.log"
