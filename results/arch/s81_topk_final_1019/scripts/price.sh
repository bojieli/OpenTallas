#!/bin/bash
set -euo pipefail
cd src
mkdir -p ../price
for m in 6692 1037; do
 python3 tools/throughput/accepted_cost.py compute s81 --unit S81.TOPK_FINAL --match 'attn.idx.topk_final$' --price 178 --measured "$m" --node-delta "$((m-178))" --evidence results/arch/s81_topk_final_1019/record.json > ../price/cost_$m.json
 done
python3 - <<'PY'
import json
from pathlib import Path
for wl in ('ds_rom','ds_rom_mtp'):
 d=json.loads(Path('results/arch/token_path_20261009/'+wl+'.json').read_text())
 ns=[{k:n.get(k) for k in ('id','op','layer','cycles','group')} for n in d['nodes'] if n.get('op')=='attn.idx.topk_final']
 print(wl,ns)
PY
