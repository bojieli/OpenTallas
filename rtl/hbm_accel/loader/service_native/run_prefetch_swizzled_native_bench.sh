#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_swizzled_bank.sv" "$mem" rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv "$d/ot_hbm_svc_native_sector_pipeline_stack.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/ot_hbm_svc_prefetch_burst_owner.sv" "$d/ot_hbm_svc_prefetch_swizzled_cdc.sv" "$d/tb_hbm_svc_prefetch_swizzled_native.sv")
if [[ ${SKIP_BUILD:-0} != 1 ]];then
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_prefetch_swizzled_native --Mdir "$out/obj" -o positive "${sources[@]}" > "$out/build.log" 2>&1
fi
fails=0
for phase in 137 773;do
 for case_id in 1 2;do
  if ! "$out/obj/positive" +PHASE=$phase +CASE=$case_id +ALLOW_PERF_FAIL > "$out/phase_${phase}_case_${case_id}.log";then fails=$((fails+1));continue;fi
  grep -q 'PASS PREFETCH_SWIZZLED_NATIVE native_command_only_DRAM' "$out/phase_${phase}_case_${case_id}.log"
  if grep -q 'PREFETCH_BURST_CDC_PERFORMANCE FAIL' "$out/phase_${phase}_case_${case_id}.log";then fails=$((fails+1));fi
 done
done
"$out/obj/positive" +CASE=3 +TAILTOTAL=73 +PHASE=137 > "$out/tail_73.log"
grep -q 'exact_vectors=73' "$out/tail_73.log"
"$out/obj/positive" +DUPBEAT > "$out/duplicate_beat.log"
grep -q 'duplicate response beat rejected' "$out/duplicate_beat.log"
# Mutate only the inverse SRAM read permutation, preserving landed bytes.
python3 - "$d/ot_hbm_svc_prefetch_swizzled_cdc.sv" "$out/read_mutant.sv" <<'PYMUT'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();old="group_data[g^{1'b0,read_swizzle_q}]";assert s.count(old)==1
Path(sys.argv[2]).write_text(s.replace(old,"group_data[g]"))
PYMUT
mutant_sources=()
for source in "${sources[@]}";do
 if [[ "$source" == "$d/ot_hbm_svc_prefetch_swizzled_cdc.sv" ]];then mutant_sources+=("$out/read_mutant.sv");else mutant_sources+=("$source");fi
done
iverilog -g2012 -s tb_hbm_svc_prefetch_swizzled_native -o "$out/read_mutant.vvp" "${mutant_sources[@]}" > "$out/mutant_build.log" 2>&1
if vvp "$out/read_mutant.vvp" +CASE=3 +TAILTOTAL=73 > "$out/read_mutant.log";then echo 'inverse read mutant unexpectedly passed';exit 1;fi
grep -q 'payload' "$out/read_mutant.log"
cat "$out"/phase_*.log "$out/tail_73.log" "$out/duplicate_beat.log" "$out/read_mutant.log"
if ((fails));then echo "PREFETCH_SWIZZLED_NATIVE PERFORMANCE FAIL cases=$fails unchanged_84.7_134.2_HBM_gates";exit 2;fi
echo 'PREFETCH_SWIZZLED_NATIVE PASS both_phases unchanged_84.7_134.2_HBM_gates'
