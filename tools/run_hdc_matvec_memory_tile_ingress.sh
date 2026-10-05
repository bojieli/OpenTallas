#!/usr/bin/env bash
# Reproduce the reduced adopted-HDC compute-plus-memory ASAP7 proxy gate.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/run_abi3_physical.py \
  --view asap7 --top ot_hdc_matvec_memory_tile \
  --source rtl/hdc/ot_hdc_delay.sv \
  --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
  --source rtl/hdc/ot_hdc_fpu.sv \
  --source rtl/proto/ot_fp32_add_rne_pipe.sv \
  --source rtl/hdc/ot_hdc_sfu.sv \
  --source rtl/hdc/ot_hdc_fastfp.sv \
  --source rtl/hdc/ot_hdc_matvec.sv \
  --source rtl/dft/ot_rom_secded_dec.sv \
  --source physical/asap7_memory_macros/ot_rom_8192x266_m8/ot_rom_8192x266_m8_bb.v \
  --source physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v \
  --source rtl/hdc/physical/ot_hdc_matvec_memory_tile.sv \
  --clock-period-ns 1.5 --stages pnr --corner TT \
  --core-utilization 15 --place-density 0.55 \
  --macro-view ot_rom_8192x266_m8=physical/asap7_memory_macros/ot_rom_8192x266_m8 \
  --macro-view ot_sram_1r1w_1024x256_m2_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 \
  --macro-place-halo 5 5 \
  --output results/physical_hdc/asap7/matvec_memory_tile_ingress/physical.json \
  --nickname-tag hdc_mem_tile_ingress "$@"
