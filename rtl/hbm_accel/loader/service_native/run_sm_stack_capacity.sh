#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=${1:?output directory}; images=${2:?source-exact archived image directory}; stack=${3:-0}; rows=${4:-64}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
sources=(rtl/lib/ot_reset_sync.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_mapped4_owner.sv" "$d/ot_hbm_svc_prefetch_overlap_owner.sv" "$d/ot_hbm_svc_sm8_landing_bank.sv" "$d/ot_hbm_svc_sm4pc_cdc.sv" "$d/ot_hbm_svc_static_sm_packed136.sv" "$d/ot_hbm_svc_sm_feed_programmed.sv" "$d/ot_hbm_svc_sm_stack_programmed.sv" rtl/hbm_accel/sm/static/ot_smh_static_feed.sv rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv "$d/ot_hbm_svc_native_sector_pipeline_stack.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/ot_hbm_svc_sm_stack_native.sv" "$d/tb_hbm_svc_sm_stack_capacity.sv")
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_sm_stack_capacity -GSTACK="$stack" -GROWS="$rows" --Mdir "$out/obj" -o sim "${sources[@]}" > "$out/build.log" 2>&1
"$out/obj/sim" +IMAGES="$images" > "$out/positive.log"
grep -q 'SM_STACK_CAPACITY PASS' "$out/positive.log"
if "$out/obj/sim" +IMAGES="$images" +EARLY > "$out/early_mutant.log";then echo 'early fixed-calendar mutant survived';exit 1;fi
grep -q 'SM_STACK DUT fault' "$out/early_mutant.log"
cat "$out/positive.log"
echo 'SM_STACK_EARLY_CALENDAR_MUTANT rejected'
