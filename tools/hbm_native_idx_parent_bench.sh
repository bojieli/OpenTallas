#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1")
mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
src=(rtl/test/hbm_idx_chunk_el/tb_hbm_idx_parent_owned_native.sv
 rtl/test/hbm_idx_chunk_el/native_idx_parent.vlt
 rtl/hbm_accel/index/ot_hbm_idx_parent_owned_native.sv
 rtl/hbm_accel/index/ot_hbm_idx_score_owned_native.sv
 rtl/hbm_accel/index/ot_hbm_idx_ordered_candidate.sv
 rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv
 physical/hbm_accel_die_views/index/rtl/hfd_idx_sel_native_qend.sv
 physical/hbm_accel_die_views/index/rtl/hfd_idx_sel.sv
 physical/hbm_accel_die_views/index/rtl/hfd_idx_lib.sv
 physical/hbm_accel_die_views/index/rtl/hfd_qsel_tiles.sv
 rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hbm_accel/index/ot_hbm_accel_index_query.sv
 rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv
 rtl/hdc/v41x/ot_hdc_v41x_sel.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv
 rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv
 rtl/hdc/v41/ot_hdc_actquant.sv rtl/common/ot_secded.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fpu.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/link/ot_fifo_sram_fwft.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
"$vl" --hierarchical --binary --timing -Irtl/common -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_idx_parent_owned_native --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1
python3 tools/hbm_idx_die_bench.py prepare --work "$out/vectors" > "$out/vectors.log"
(cd "$out/vectors" && "$out/obj/Vtb_hbm_idx_parent_owned_native") > "$out/run.log" 2>&1
cat "$out/run.log"
python3 tools/hbm_idx_die_bench.py compare --work "$out/vectors" > "$out/verdict.log"
cat "$out/verdict.log"
sha256sum "${src[@]}" "$out/obj/Vtb_hbm_idx_parent_owned_native" > "$out/source_binary.sha256"
