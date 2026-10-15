#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_burst_bank.sv" "$mem" rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv "$d/ot_hbm_svc_native_sector_pipeline_stack.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/ot_hbm_svc_prefetch_burst_owner.sv" "$d/ot_hbm_svc_prefetch_burst_cdc.sv" "$d/tb_hbm_svc_prefetch_native_command.sv")
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_prefetch_native_command --Mdir "$out/obj" -o positive "${sources[@]}" > "$out/build.log" 2>&1
fails=0
for phase in 137 773;do
 for case_id in 1 2;do
  "$out/obj/positive" +PHASE=$phase +CASE=$case_id +ALLOW_PERF_FAIL > "$out/phase_${phase}_case_${case_id}.log"
  grep -q 'PASS PREFETCH_NATIVE_COMMAND native_command_only_DRAM' "$out/phase_${phase}_case_${case_id}.log"
  if grep -q 'PREFETCH_BURST_CDC_PERFORMANCE FAIL' "$out/phase_${phase}_case_${case_id}.log";then fails=$((fails+1));fi
 done
done
"$out/obj/positive" +DUPBEAT > "$out/duplicate_beat.log"
grep -q 'duplicate response beat rejected' "$out/duplicate_beat.log"
cat "$out"/phase_*.log "$out/duplicate_beat.log"
if ((fails));then echo "PREFETCH_NATIVE_COMMAND PERFORMANCE FAIL cases=$fails unchanged_84.7_134.2_HBM_gates";exit 2;fi
echo 'PREFETCH_NATIVE_COMMAND PASS both_phases unchanged_84.7_134.2_HBM_gates'
