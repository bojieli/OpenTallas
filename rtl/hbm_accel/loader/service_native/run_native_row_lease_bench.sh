#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
controller="$d/ot_hbm_svc_native_stream_pc_lease.sv"
iverilog -g2012 -s tb_hbm_svc_native_row_lease -o "$out/directed.vvp" "$controller" "$d/tb_hbm_svc_native_row_lease.sv"
vvp "$out/directed.vvp" > "$out/directed.log"
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_swizzled_bank.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$controller" "$d/ot_hbm_svc_native_sector_lease_stack.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/ot_hbm_svc_prefetch_burst_owner.sv" "$d/ot_hbm_svc_prefetch_swizzled_cdc.sv" "$d/tb_hbm_svc_prefetch_leased_native.sv")
iverilog -g2012 -s tb_hbm_svc_prefetch_leased_native -o "$out/guarded.vvp" "${sources[@]}" > "$out/build.log" 2>&1
fails=0
for phase in 137 773;do
 for case_id in 1 2;do
  if ! vvp "$out/guarded.vvp" +PHASE=$phase +CASE=$case_id +ALLOW_PERF_FAIL > "$out/phase_${phase}_case_${case_id}.log";then fails=$((fails+1));continue;fi
  grep -q 'PASS PREFETCH_LEASED_NATIVE native_command_only_DRAM' "$out/phase_${phase}_case_${case_id}.log"
  if grep -q 'PREFETCH_BURST_CDC_PERFORMANCE FAIL' "$out/phase_${phase}_case_${case_id}.log";then fails=$((fails+1));fi
 done
done
# Behavior control disables only the row lease, retaining the correctness guard.
python3 - "$d/tb_hbm_svc_prefetch_leased_native.sv" "$out/lease0_tb.sv" <<'PYCONTROL'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();assert s.count('.AQ_ROW_LEASE(1)')==1
Path(sys.argv[2]).write_text(s.replace('.AQ_ROW_LEASE(1)','.AQ_ROW_LEASE(0)'))
PYCONTROL
control_sources=("${sources[@]:0:${#sources[@]}-1}" "$out/lease0_tb.sv")
iverilog -g2012 -s tb_hbm_svc_prefetch_leased_native -o "$out/lease0.vvp" "${control_sources[@]}" > "$out/control_build.log" 2>&1
vvp "$out/lease0.vvp" +PHASE=137 +CASE=2 +ALLOW_PERF_FAIL > "$out/lease0.log"
grep -q 'measured_HBM_cycles=426.432633' "$out/lease0.log"
cat "$out/directed.log" "$out"/phase_*.log "$out/lease0.log"
if ((fails));then echo "NATIVE_ROW_LEASE PERFORMANCE FAIL cases=$fails unchanged_gates";exit 2;fi
