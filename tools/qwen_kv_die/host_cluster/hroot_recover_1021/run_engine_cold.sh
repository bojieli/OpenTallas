#!/usr/bin/env bash
set -euo pipefail
cd cold_engine
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version > verilator.version
gzip -dc models.v.gz > models.v
python3 - <<'INNER'
import gzip,hashlib,json,pathlib,re
p=pathlib.Path('.');sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
registry=json.load(open('native_liberty_hashes.json'));actual={q.name:sha(q) for q in pathlib.Path('../libs').glob('*.lib')}
assert len(actual)==5 and all(registry[k]==v for k,v in actual.items())
s=p.joinpath('qkd_host_native_engine_n32.sv').read_text();used=set(re.findall(r'\(\* keep \*\)\s+(\S+) u_cell',s));assert used
models=set(re.findall(r'^module (\S+)\(',p.joinpath('models.v').read_text(),re.M));macros={'ot_sram_1r1w_32x128_m1'}
assert used<=models|macros,('missing exact model',used-models-macros)
log=gzip.open('models.log.gz','rt').read();ignored=set(re.findall(r'Ignoring cell (\S+)',log));assert not used&ignored
assert not re.search(r'^Warning:|^ERROR:',log,re.M), 'model semantic warning requires review'
json.dump(dict(qualified=False,reused_repository_artifact='results/arch/kv_attn_safe_control_1019/models.v.gz',liberty_sha256=actual,models_sha256=sha(p/'models.v'),generator_log_sha256=sha(p/'models.log.gz'),native_engine_sha256=sha(p/'qkd_host_native_engine_n32.sv'),rtl_engine_sha256=sha(p/'qkd_host_native_engine.sv'),macro_sha256=sha(p/'ot_sram_1r1w_32x128_m1.v'),bench_sha256=sha(p/'tb_engine_cold.sv'),runner_sha256=sha(pathlib.Path('../run_engine_cold.sh')),reset_held_edges=8,postrelease_burnin_edges=0,used_masters=sorted(used),ignored_unused_masters=sorted(ignored),scope='bounded sampled cold/occupied reset; not universal convergence or mapped-source CDC admission'),open('model_binding.json','w'),indent=2)
INNER
python3 tools/qwen_host/native_fixture.py . 2 edge > fixture.log
read -r nd np ns < <(python3 -c "import json;j=json.load(open('fixture.json'));print(j['descriptors'],j['beats'],j['sectors'])")
verilator --binary --timing -O2 -j 8 --x-initial unique --x-assign unique -DOT_MEM_NO_INIT -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_engine_cold -GND="$nd" -GNP="$np" -GNS="$ns" --Mdir obj tb_engine_cold.sv models.v qkd_host_native_engine_n32.sv qkd_host_native_engine.sv ot_hdc_ingest_fp8q.sv ot_sram_1r1w_32x128_m1.v > build.log 2>&1
for seed in 31 997 3187;do
 ./obj/Vtb_engine_cold +verilator+rand+reset+2 +verilator+seed+"$seed" +MUT_CLOCK=0 > "seed${seed}.log" 2>&1
 grep -q 'ENGINE_COLD_SAMPLE PASS' "seed${seed}.log"
done
if ./obj/Vtb_engine_cold +verilator+rand+reset+2 +verilator+seed+997 +MUT_CLOCK=1 > wrong_clock.log 2>&1;then
 echo WRONG_CLOCK_MUTANT_SURVIVED;exit 1
fi
grep -q ENGINE_COLD_MISMATCH wrong_clock.log
echo ENGINE_COLD_SAMPLING_AND_WRONG_CLOCK_WITNESS_DONE
