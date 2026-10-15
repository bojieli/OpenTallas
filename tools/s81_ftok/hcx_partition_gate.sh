#!/usr/bin/env bash
# Run inside the admitted closure-loop/ot-run environment, at the pinned source.
# modes pass/mut are separate gate entries; mut must fail with HCX_PROJECTION.
set -euo pipefail
out=$(realpath -m "$1")
mode=${2:-pass}
mkdir -p "$out/input" "$out/vec"
tar -xzf results/rtl/s81_hcx_home_1014/fixture_L00_row0.tar.gz -C "$out/input"
python3 tools/s81_ftok/hcx_projection_vectors.py --src "$out/input" --out "$out/vec" --row 0
src=(
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv
 physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_hcp_partition.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_projection_partition.sv rtl/dsrom_sys/s81_hcx/test/tb_s81_hcx_projection_partition.sv
)
defs=()
if [[ "$mode" == mut ]]; then defs=(+define+MUT_BANK); elif [[ "$mode" != pass ]]; then exit 2; fi
verilator --binary --timing -O3 -CFLAGS -O2 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT \
 "${defs[@]}" --top-module tb_s81_hcx_projection_partition --Mdir "$out/obj" -j 8 "${src[@]}" > "$out/build.log" 2>&1
"$out/obj/Vtb_s81_hcx_projection_partition" +DIR="$out/vec" +OT_ROM_DIR="$out/vec" | tee "$out/run.log"
