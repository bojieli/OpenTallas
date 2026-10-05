#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
run_dir=$(mktemp -d)
trap 'rm -rf "$run_dir"' EXIT
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing \
  --top-module tb_hdc_matvec_memory_tile_wide -Wno-fatal -Wno-WIDTH -j 4 \
  --Mdir "$run_dir/obj" \
  rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
  rtl/hdc/ot_hdc_fpu.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
  rtl/hdc/ot_hdc_matvec.sv rtl/dft/ot_rom_secded_dec.sv \
  physical/asap7_memory_macros/ot_rom_8192x266_m8/ot_rom_8192x266_m8.v \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  rtl/hdc/physical/ot_hdc_matvec_memory_tile_wide.sv \
  tests/rtl/tb_hdc_matvec_memory_tile_wide.sv > "$run_dir/build.log" 2>&1 || {
    cat "$run_dir/build.log"; exit 1;
  }
"$run_dir/obj/Vtb_hdc_matvec_memory_tile_wide"
