#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
pc="$d/ot_hbm_svc_native_stream_pc_intent.sv"
source="$d/ot_hbm_svc_native_sector_intent_stack.sv"
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
fixture="$d/tb_hbm_svc_command_dram_pipeline_fixture.sv"
tb="$d/tb_hbm_svc_native_intent_head.sv"
iverilog -g2012 -s tb -o "$out/identity.vvp" "$pc" "$mem" "$source" "$fixture" "$tb" > "$out/identity_build.log" 2>&1
vvp "$out/identity.vvp" > "$out/identity.log"
vvp "$out/identity.vvp" +stalls > "$out/stalls.log"
python3 - "$source" "$out" <<'MUTATE'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();out=Path(sys.argv[2])
mutants=[('wrong_head',"head_payload<=dram_rdata[p*256+:256]","head_payload<=dram_rdata[p*256+:256]^256'd1"),('wrong_beat','pending_identity[pending_wp]<=head[308:288]',"pending_identity[pending_wp]<={head[308:292],4'b0}"),('wrong_SRAM_row',"r_addr_in({2'b0,response_read_address})","r_addr_in({2'b0,(response_read_address^5'd1)})")]
for name,old,new in mutants:
 assert s.count(old)==1
 (out/(name+'.sv')).write_text(s.replace(old,new))
MUTATE
for mutant in wrong_head wrong_beat wrong_SRAM_row; do
 iverilog -g2012 -s tb -o "$out/$mutant.vvp" "$pc" "$mem" "$out/$mutant.sv" "$fixture" "$tb" > "$out/${mutant}_build.log" 2>&1
 if vvp "$out/$mutant.vvp" +stalls > "$out/$mutant.log"; then echo "mutant unexpectedly passed: $mutant"; exit 1; fi
 grep -q 'burst read identity/data' "$out/$mutant.log"
done
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_burst_bank.sv" "$mem" "$pc" "$source" "$fixture" "$d/ot_hbm_svc_prefetch_burst_owner.sv" "$d/ot_hbm_svc_prefetch_burst_cdc.sv" "$d/tb_hbm_svc_prefetch_intent_head.sv")
iverilog -g2012 -s tb_hbm_svc_prefetch_intent_head -o "$out/prefetch.vvp" "${sources[@]}" > "$out/prefetch_build.log" 2>&1
fails=0
for phase in 137 773; do
 for case_id in 1 2; do
  if ! vvp "$out/prefetch.vvp" +PHASE=$phase +CASE=$case_id +ALLOW_PERF_FAIL > "$out/phase_${phase}_case_${case_id}.log"; then fails=$((fails+1));continue;fi
  grep -q 'PASS PREFETCH_INTENT_HEAD native_command_only_DRAM' "$out/phase_${phase}_case_${case_id}.log"
  if grep -q 'PREFETCH_BURST_CDC_PERFORMANCE FAIL' "$out/phase_${phase}_case_${case_id}.log"; then fails=$((fails+1));fi
 done
done
cat "$out/identity.log" "$out/stalls.log" "$out"/phase_*.log
if ((fails)); then echo "NATIVE_INTENT_HEAD PERFORMANCE FAIL cases=$fails unchanged_gates";exit 2;fi
