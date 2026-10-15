#!/usr/bin/env bash
set -euo pipefail
kind=$1; arg=${2:-0}
python3 - <<'PY'
import json,hashlib,pathlib
for p,h in json.load(open('source_hashes.json')).items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
print('VERIFIED_PINNED_INPUTS',pathlib.Path('SOURCE_COMMIT').read_text().strip())
PY
if [[ $kind == measure ]]; then
 mkdir -p measure
 yosys -l measure/yosys.log residual_bits.ys > measure/stdout.log 2>&1
 python3 - <<'PY'
import json,collections,hashlib
p='measure/residual_bits.json';d=json.load(open(p));m=d['modules']['qfd_tile_nk_banked_v1'];c=collections.Counter(x['type']for x in m['cells'].values());n=sum(v for k,v in c.items()if 'DFF'in k.upper());r={'source_commit':open('SOURCE_COMMIT').read().strip(),'actual_bitmapped_FF_count':n,'original_FF_count':2278,'reduction':2278-n,'cell_types':dict(c),'netlist_sha256':hashlib.sha256(open(p,'rb').read()).hexdigest()};open('measure/receipt.json','w').write(json.dumps(r,indent=2)+'\n');print('MEASURED_ACTUAL_DFF',n,'REDUCTION',2278-n)
PY
elif [[ $kind == bench ]]; then
 bash physical/qwen_tile_glue_banks_1015/run_parent_bench.sh "$arg" "bench_m$arg"
else
 top=tb_parent_banked_$kind; out=bench_$kind; mkdir -p "$out"
 sed '/physical\/qwen_tile_glue_banks_1015\/tb_parent_banked.sv/d' sim_sources.list > "$out/sources.list"
 echo "physical/qwen_tile_glue_banks_1015/$top.sv" >> "$out/sources.list"
 verilator --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DOT_QWEN_LSL_FP1 -CFLAGS -O0 --output-split 20000 --output-split-cfuncs 2000 --top-module "$top" --Mdir "$out/obj" -f "$out/sources.list" > "$out/build.log" 2>&1
 "$out/obj/V$top" +OT_ROM_DIR=masks > "$out/run.log" 2>&1
 cat "$out/run.log"
 grep -q '^PASS actual full old-parent' "$out/run.log"
fi
