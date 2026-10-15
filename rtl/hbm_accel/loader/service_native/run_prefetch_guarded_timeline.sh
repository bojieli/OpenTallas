#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
controller="$d/ot_hbm_svc_native_stream_pc.sv"
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_swizzled_bank.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$controller" "$d/ot_hbm_svc_native_sector_guarded_stack.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/ot_hbm_svc_prefetch_burst_owner.sv" "$d/ot_hbm_svc_prefetch_swizzled_cdc.sv" "$d/tb_hbm_svc_prefetch_guarded_timeline.sv")
iverilog -g2012 -s tb_hbm_svc_prefetch_guarded_timeline -o "$out/timeline.vvp" "${sources[@]}" > "$out/build.log" 2>&1
vvp "$out/timeline.vvp" +CASE=2 +PHASE=137 +ALLOW_PERF_FAIL > "$out/timeline.log"
