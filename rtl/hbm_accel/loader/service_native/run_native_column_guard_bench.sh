#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
controller="$d/ot_hbm_svc_native_stream_pc.sv"
iverilog -g2012 -s tb_hbm_svc_native_column_guard -o "$out/directed.vvp" "$controller" "$d/tb_hbm_svc_native_column_guard.sv"
vvp "$out/directed.vvp" > "$out/directed.log"
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_swizzled_bank.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$controller" "$d/ot_hbm_svc_native_sector_guarded_stack.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/ot_hbm_svc_prefetch_burst_owner.sv" "$d/ot_hbm_svc_prefetch_swizzled_cdc.sv" "$d/tb_hbm_svc_prefetch_guarded_native.sv")
iverilog -g2012 -s tb_hbm_svc_prefetch_guarded_native -o "$out/guarded.vvp" "${sources[@]}" > "$out/build.log" 2>&1
fails=0
for phase in 137 773;do
 for case_id in 1 2;do
  if ! vvp "$out/guarded.vvp" +PHASE=$phase +CASE=$case_id +ALLOW_PERF_FAIL > "$out/phase_${phase}_case_${case_id}.log";then fails=$((fails+1));continue;fi
  grep -q 'PASS PREFETCH_GUARDED_NATIVE native_command_only_DRAM' "$out/phase_${phase}_case_${case_id}.log"
  if grep -q 'PREFETCH_BURST_CDC_PERFORMANCE FAIL' "$out/phase_${phase}_case_${case_id}.log";then fails=$((fails+1));fi
 done
done
# Disable only the new column-close guard; unchanged strict command oracle must catch it.
python3 - "$d/tb_hbm_svc_prefetch_guarded_native.sv" "$out/guard0_tb.sv" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();old='ot_hbm_svc_native_sector_guarded_stack u_native';assert s.count(old)==1
Path(sys.argv[2]).write_text(s.replace(old,'ot_hbm_svc_native_sector_guarded_stack #(.COLUMN_CLOSE_GUARD(0)) u_native'))
PY
mut_sources=("${sources[@]:0:${#sources[@]}-1}" "$out/guard0_tb.sv")
iverilog -g2012 -s tb_hbm_svc_prefetch_guarded_native -o "$out/guard0.vvp" "${mut_sources[@]}" > "$out/mutant_build.log" 2>&1
if vvp "$out/guard0.vvp" +PHASE=137 +CASE=2 +ALLOW_PERF_FAIL > "$out/guard0.log";then echo 'guard0 mutant unexpectedly passed';exit 1;fi
grep -q 'native command column timing p20 b12' "$out/guard0.log"
cat "$out/directed.log" "$out"/phase_*.log "$out/guard0.log"
echo 'NATIVE_COLUMN_GUARD MUTANT rejected original PRE/RD collision'
if ((fails));then echo "NATIVE_COLUMN_GUARD PERFORMANCE FAIL cases=$fails unchanged_gates";exit 2;fi
