#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
python3 generate_fixture.py >fixture.log
read -r nd np < <(python3 -c 'import json;j=json.load(open("fixture.json"));print(j["descriptors"],j["beats"])')
verilator --binary --timing -O2 -j 8 --x-initial unique --x-assign unique -DOT_MEM_NO_INIT -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_stream -GND="$nd" -GNP="$np" --Mdir obj tb_stream.sv candidate.sv ot_hdc_ingest_fp8q.sv ot_sram_1r1w_32x128_m1.v >build.log 2>&1
for seed in 31 997 3187; do
 ./obj/Vtb_stream +MUT=0 +verilator+rand+reset+2 +verilator+seed+"$seed" >"seed${seed}.log" 2>&1
 python3 check.py >"seed${seed}.check.log"
 cp result.json "seed${seed}.json"
done
for mut in 1 2 3 4; do
 if ./obj/Vtb_stream +MUT="$mut" +verilator+rand+reset+2 +verilator+seed+997 >"mut${mut}.log" 2>&1; then
  if python3 check.py >"mut${mut}.check.log" 2>&1; then echo "SPIPE6_MUTANT_SURVIVED mut=$mut";exit 1;fi
 else
  grep -Eq 'STALLED_WRITE_CHANGED|STREAM_TIMEOUT|STREAM_ACCOUNTING|PREP_AGE_EARLY' "mut${mut}.log"
 fi
 echo "SPIPE6_MUTANT_CAUGHT mut=$mut"
done
printf '%s\n' SPIPE6_MIXED_COLD_AND_CAUSAL_PASS
