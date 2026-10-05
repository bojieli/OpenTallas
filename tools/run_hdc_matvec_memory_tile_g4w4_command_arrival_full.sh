#!/usr/bin/env bash
# Explicit same-phase arrivals for every command and ingress input.
# Full-route sensitivity probe using an assumed IO contract, not a production IO spec.
set -euo pipefail
cd "$(dirname "$0")/.."
core_inputs=(
  rst_n go
  i_nout i_tiles i_k i_wsrc i_wbase i_ts i_ks i_js
  i_xbase i_xks i_xjs i_xcs i_jsh i_split i_wcs i_round
  i_obase i_ots i_ojs i_mmode i_oen i_amax i_rmax i_mbase
)
core_args=()
for port in "${core_inputs[@]}"; do
  core_args+=(--core-input-port "$port")
done
python3 tools/run_abi3_physical.py \
  --view asap7 --top ot_hdc_matvec_memory_tile_wide --param W=4 --param SEPARATE_INGRESS_CLOCK=1 \
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
  --source rtl/hdc/physical/ot_hdc_matvec_memory_tile_wide.sv \
  --clock-period-ns 1.5 --stages pnr --corner TT \
  --ingress-clock-port ingress_clk \
  --ingress-input-port kv_load --ingress-input-port x_load \
  --ingress-input-port kv_load_addr --ingress-input-port x_load_addr \
  --ingress-input-port kv_load_data --ingress-input-port x_load_data \
  --ingress-input-delay-min-ns 0.75 --ingress-input-delay-max-ns 1.15 \
  "${core_args[@]}" \
  --core-input-delay-min-ns 0.75 --core-input-delay-max-ns 1.15 \
  --max-transition-ns --slew-margin-percent 60 \
  --core-utilization 15 --place-density 0.55 \
  --macro-view ot_rom_8192x266_m8=physical/asap7_memory_macros/ot_rom_8192x266_m8 \
  --macro-view ot_sram_1r1w_1024x256_m2_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 \
  --macro-place-halo 5 5 \
  --nickname-tag hdc_mem_tile_g4w4_command_arrival_full \
  --output results/physical_hdc/asap7/matvec_memory_tile_g4w4_command_arrival_full/physical.json "$@"
