#!/usr/bin/env bash
# Equivalence gate of the systolic hardened HCX partition vs the flat leaf (tb_s81_hcx_projection_sys_clocked).
# usage: hcx_sys_gate.sh <out> <pass|mut> <vecdir> <romdir> [layer] [nrand]
# pass: must print HCX_SYS_EQUIV PASS; mut (+define+MUT_BANK): must fail.
set -euo pipefail
out=$(realpath -m "$1"); mode=${2:-pass}; vec=$3; rom=$4; layer=${5:-0}; nrand=${6:-4}
mkdir -p "$out"
src=(
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv
 physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_projection_leaf.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_sys_tiles.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_sys_clocked.sv
 rtl/dsrom_sys/s81_hcx/test/tb_s81_hcx_projection_sys_clocked.sv
)
defs=()
if [[ "$mode" == mut ]]; then defs=(+define+MUT_BANK); elif [[ "$mode" != pass ]]; then exit 2; fi
verilator --binary --timing -O3 -CFLAGS -O2 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
 "${defs[@]}" --top-module tb_s81_hcx_projection_sys_clocked --Mdir "$out/obj" -j 8 "${src[@]}" > "$out/build.log" 2>&1
"$out/obj/Vtb_s81_hcx_projection_sys_clocked" +DIR="$vec" +OT_ROM_DIR="$rom" +LAYER="$layer" +NRAND="$nrand" | tee "$out/run.log"
