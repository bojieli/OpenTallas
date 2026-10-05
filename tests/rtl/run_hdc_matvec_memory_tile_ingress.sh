#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git show 4ca61a20:rtl/hdc/physical/ot_hdc_matvec_memory_tile.sv | \
  sed 's/module ot_hdc_matvec_memory_tile (/module ot_hdc_matvec_memory_tile_baseline (/' > "$tmp/baseline.sv"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing --top-module tb_hdc_matvec_memory_tile_ingress \
  -Wno-fatal -Wno-WIDTH -j 4 --Mdir "$tmp/obj" \
  rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
  rtl/hdc/ot_hdc_fpu.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
  rtl/hdc/ot_hdc_matvec.sv rtl/dft/ot_rom_secded_dec.sv \
  physical/asap7_memory_macros/ot_rom_8192x266_m8/ot_rom_8192x266_m8.v \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  rtl/hdc/physical/ot_hdc_matvec_memory_tile.sv "$tmp/baseline.sv" \
  tests/rtl/tb_hdc_matvec_memory_tile_ingress.sv > "$tmp/build.log" 2>&1 || { cat "$tmp/build.log"; exit 1; }
"$tmp/obj/Vtb_hdc_matvec_memory_tile_ingress"
