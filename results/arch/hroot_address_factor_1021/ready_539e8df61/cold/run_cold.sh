#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
python3 extend_fixture.py > fixture_extension.log
verilator --version > verilator.version
gzip -dc models.v.gz > models.v
python3 - <<'INNER'
from pathlib import Path
import json,re,hashlib
p=Path('.');s=(p/'qkd_host_native_engine_n32.sv').read_text();used=set(re.findall(r'\(\* keep \*\)\s+(\S+) u_cell',s));models=set(re.findall(r'^module (\S+)\(', (p/'models.v').read_text(),re.M));assert used<=models|{'ot_sram_1r1w_32x128_m1'}
log=__import__('gzip').open('models.log.gz','rt').read();ignored=set(re.findall(r'Ignoring cell (\S+)',log));assert not used&ignored;assert not re.search(r'^Warning:|^ERROR:',log,re.M)
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest();j={q.name:sha(q) for q in p.iterdir() if q.is_file() and q.suffix in ['.sv','.v','.mem','.py','.sh','.json','.gz']};j.update(scope='bounded3seed independent initialization sampling and occupied reset; not universal convergence',reset_held_edges=8,postrelease_burnin_edges=0,gold='frozen original production RTL',native='fresh address successor35resetports',used_masters=sorted(used));(p/'model_binding.json').write_text(json.dumps(j,indent=2)+'\n')
INNER
read -r nd np ns < <(python3 -c 'import json;j=json.load(open("fixture.json"));print(j["descriptors"],j["beats"],j["sectors"])')
verilator --binary --timing -O2 -j 8 --x-initial unique --x-assign unique -DOT_MEM_NO_INIT -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_engine_cold -GND="$nd" -GNP="$np" -GNS="$ns" --Mdir obj tb_engine_cold.sv models.v qkd_host_native_engine_n32.sv qkd_host_native_engine.sv ot_hdc_ingest_fp8q.sv ot_sram_1r1w_32x128_m1.v > build.log 2>&1
for seed in 31 997 3187;do
 ./obj/Vtb_engine_cold +verilator+rand+reset+2 +verilator+seed+"$seed" +MUT_CLOCK=0 > "seed${seed}.log" 2>&1
 grep -q 'ENGINE_COLD_SAMPLE PASS' "seed${seed}.log"
done
if ./obj/Vtb_engine_cold +verilator+rand+reset+2 +verilator+seed+997 +MUT_CLOCK=1 > wrong_clock.log 2>&1;then echo WRONG_CLOCK_MUTANT_SURVIVED;exit 1;fi
grep -q ENGINE_COLD_MISMATCH wrong_clock.log
printf '%s\n' ENGINE_COLD_SUCCESSOR_SAMPLING_AND_WRONG_CLOCK_DONE
