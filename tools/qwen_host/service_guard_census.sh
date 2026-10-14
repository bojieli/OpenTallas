#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mkdir -p "$out"
yosys -Q -T -p "read_verilog -sv $root/rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv $root/rtl/qwen_sys/host_20261013/qkd_host_service_guard.sv; hierarchy -top qkd_host_service_guard; proc; opt; memory_map; opt; flatten; opt; write_json $out/guard.json; stat" > "$out/census.log"
python3 - "$out/guard.json" <<'PY'
import json,sys,collections
m=json.load(open(sys.argv[1]))['modules']['qkd_host_service_guard']
c=collections.Counter()
for cell in m['cells'].values():
 if 'dff' in cell['type'].lower():c[cell['type']]+=len(cell['connections']['Q'])
print('FF census',dict(c),'total',sum(c.values()))
print('pins',sum(len(p['bits']) for p in m['ports'].values()),'clock ck_guard; parent logic not applicable standalone leaf')
PY
