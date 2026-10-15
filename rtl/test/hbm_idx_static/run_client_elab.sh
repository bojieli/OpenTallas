#!/usr/bin/env bash
# Full elaboration of the SW IDX client top (INDEX parent + static TOPK + 4-leaf share) with every real child.
set -eu
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-client}"); mkdir -p "$out"
src=(rtl/hbm_accel/index/ot_hbm_idx_client_static.sv rtl/hbm_accel/index/ot_hbm_idx_scheduled_static.sv rtl/hbm_accel/index/ot_hbm_idx_calendar_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_parent_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv
 rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv rtl/hbm_accel/index/ot_hbm_idx_score_static.sv rtl/hbm_accel/index/ot_hbm_idx_engine_static.sv rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv
 rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
/usr/bin/time -v iverilog -g2012 -tnull -s ot_hbm_idx_client_static "${src[@]}" > "$out/elab.log" 2>&1
grep -iE 'error|warning: Port' "$out/elab.log" | head -20 || true
grep 'Maximum resident' "$out/elab.log"
sha256sum "${src[@]}" > "$out/sources.sha256"
echo "IDX_CLIENT_ELAB PASS (iverilog full hierarchy, no unresolved module/port errors)"
