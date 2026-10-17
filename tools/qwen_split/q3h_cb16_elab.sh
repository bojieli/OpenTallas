#!/bin/bash
# q3h C_B16 full-cluster elaboration + port-bind check with the REAL tile RTL (Q-DIEPLAN3-CB 2026-10-16).
#   tools/qwen_split/q3h_cb16_elab.sh SRC_ROOT OUTDIR
# SRC_ROOT = a tree holding the A0 parent RTL (origin/codex/romleaf-native-1621: qfd_tile_n[kl]_rp2_romleaf, RPH 3 tile)
# plus rtl/physical/q3h.  Verilator --lint-only elaborates qfd_c_b16 (16 tiles, 16 qfd_xcst_n, fabric); every
# PINMISSING / PINCONNECTEMPTY / PINNOTFOUND / UNDRIVEN / width warning on a q3h file fails the check.
set -uo pipefail
SR=$(realpath "$1"); OUT=$(mkdir -p "$2" && realpath "$2")
V=${VERILATOR:-verilator}
cd "$SR"
SRC=(rtl/physical/ot_qwen_rom_tile_die.sv rtl/hdc/kv/ot_qwen_kv_land_merge.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
     rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_matvec.sv rtl/hdc/ot_qwen_me_array_w12.sv
     rtl/hdc/ot_qwen_rom_tile_w12.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv
     rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv
     rtl/physical/ot_qwen_rom_tile_nk.sv rtl/lib/ot_rst_relay.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv rtl/physical/ot_qwen_tile_node.sv
     rtl/physical/ot_qwen_tile_romleaf.sv rtl/physical/qfd_tile_nk_rp2_45.sv rtl/physical/qfd_tile_nl_rp2_45.sv
     rtl/physical/qfd_tile_nk_rp2_romleaf.sv rtl/physical/qfd_tile_nl_rp2_romleaf.sv
     physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
     physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
     rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv
     rtl/physical/q3h/qfd_q3h_stn.sv rtl/physical/q3h/qfd_c_b16_fabric.sv rtl/physical/q3h/qfd_c_b16.sv)
{ cat SOURCE_COMMIT 2>/dev/null; sha256sum "${SRC[@]}"; "$V" --version; } > "$OUT/elab_sources.txt"
"$V" --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTITOP -Wwarn-PINMISSING -Wwarn-PINCONNECTEMPTY -Wwarn-PINNOTFOUND -Wwarn-WIDTH -Wwarn-UNDRIVEN +define+OT_QWEN_LSL_FP1 \
    --top-module qfd_c_b16 "${SRC[@]}" > "$OUT/elab.log" 2>&1
st=$?
grep -E '%(Error|Warning)' "$OUT/elab.log" | grep -E 'rtl/physical/q3h/' > "$OUT/q3h_warnings.log"
grep -E '%Warning-(PINMISSING|PINCONNECTEMPTY|PINNOTFOUND)' "$OUT/elab.log" > "$OUT/pin_warnings.log"
grep -E '%Error' "$OUT/elab.log" | head -20
echo "verilator_status $st"
echo "q3h_warnings $(wc -l < "$OUT/q3h_warnings.log")"
echo "pin_warnings_any_file $(wc -l < "$OUT/pin_warnings.log")"
if [[ $st -eq 0 ]] && ! grep -q '%Error' "$OUT/elab.log" && [[ ! -s "$OUT/q3h_warnings.log" ]] && ! grep -q 'q3h\|qfd_c_b16\|u_t_\|u_x_' "$OUT/pin_warnings.log"; then
  echo "Q3H_CB16_ELAB_PASS"; exit 0; fi
echo "Q3H_CB16_ELAB_FAIL"; exit 1
