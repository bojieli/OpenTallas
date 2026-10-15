#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-static-parent-proof}")
mkdir -p "$out"
OPENBLAS_NUM_THREADS=1 python3 tools/hbm_idx_static_parent_vectors.py "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
[ -x "$vl" ]||vl=verilator
src=(rtl/hbm_accel/index/ot_hbm_idx_parent_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv
 rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv rtl/hbm_accel/index/ot_hbm_idx_score_static.sv rtl/hbm_accel/index/ot_hbm_idx_engine_static.sv rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv
 rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 rtl/test/hbm_idx_static/tb_idx_parent_static.sv rtl/test/hbm_idx_static/parent.vlt)
"$vl" --hierarchical --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx_parent_static --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1
(cd "$out"&&"$out/obj/Vtb_idx_parent_static") > "$out/run.log" 2>&1
cat "$out/run.log"
