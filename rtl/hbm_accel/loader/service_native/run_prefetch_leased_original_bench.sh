#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
controller="$d/ot_hbm_svc_native_stream_pc_lease.sv"
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_burst_bank.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$controller" "$d/ot_hbm_svc_native_sector_lease_stack.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/ot_hbm_svc_prefetch_burst_owner.sv" "$d/ot_hbm_svc_prefetch_burst_cdc.sv" "$d/tb_hbm_svc_prefetch_leased_original.sv")
iverilog -g2012 -s tb_hbm_svc_prefetch_leased_original -o "$out/guarded.vvp" "${sources[@]}" > "$out/build.log" 2>&1
fails=0
for phase in 137 773;do
 for case_id in 1 2;do
  if ! vvp "$out/guarded.vvp" +PHASE=$phase +CASE=$case_id +ALLOW_PERF_FAIL > "$out/phase_${phase}_case_${case_id}.log";then fails=$((fails+1));continue;fi
  grep -q 'PASS PREFETCH_LEASED_ORIGINAL native_command_only_DRAM' "$out/phase_${phase}_case_${case_id}.log"
  if grep -q 'PREFETCH_BURST_CDC_PERFORMANCE FAIL' "$out/phase_${phase}_case_${case_id}.log";then fails=$((fails+1));fi
 done
done
cat "$out"/phase_*.log
if ((fails));then echo "NATIVE_LEASE_ORIGINAL_LAYOUT PERFORMANCE FAIL cases=$fails unchanged_gates";exit 2;fi
