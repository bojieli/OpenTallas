#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
controller=rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
fixture="$d/tb_hbm_svc_command_dram_pipeline_fixture.sv"
tb="$d/tb_hbm_svc_native_sector_pipeline.sv"
source="$d/ot_hbm_svc_native_sector_pipeline_stack.sv"
iverilog -g2012 -s tb -o "$out/positive.vvp" "$controller" "$mem" "$source" "$fixture" "$tb"
vvp "$out/positive.vvp" > "$out/positive.log"
vvp "$out/positive.vvp" +stalls > "$out/stalls.log"
python3 - "$source" "$out" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();out=Path(sys.argv[2])
for name,old,new in [('wrong_beat','pending_identity[pending_wp]<=head[308:288]','pending_identity[pending_wp]<={head[308:292],4\'b0}'),('unbounded_read','read_reserved<32',"1'b1"),('wrong_SRAM_row','r_addr_in({2\'b0,response_read_address})','r_addr_in({2\'b0,(response_read_address^5\'d1)})')]:
 assert s.count(old)==1
 (out/(name+'.sv')).write_text(s.replace(old,new))
PY
for mutant in wrong_beat unbounded_read wrong_SRAM_row;do
  iverilog -g2012 -s tb -o "$out/$mutant.vvp" "$controller" "$mem" "$out/$mutant.sv" "$fixture" "$tb"
  if vvp "$out/$mutant.vvp" +stalls > "$out/$mutant.log";then echo "mutant unexpectedly passed: $mutant";exit 1;fi
done
grep -q 'burst read identity/data' "$out/wrong_beat.log"
grep -q 'native read pipeline fault' "$out/unbounded_read.log"
grep -q 'burst read identity/data' "$out/wrong_SRAM_row.log"
cat "$out/positive.log" "$out/stalls.log"
echo 'NATIVE_READ_PIPELINE_MUTANTS PASS wrong_beat unbounded_read wrong_SRAM_row'
