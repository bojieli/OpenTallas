#!/bin/bash
# FALLBACK-LAND 10-26: S81 / KV / HBM re-prices (light analytical python, ~4-25 s each). Run from a main checkout.
set -euo pipefail; O=${O:-/tmp/fallback_land_1026}; mkdir -p $O
python3 - "$O" <<'PY'
import json,sys
O=sys.argv[1]
d=json.load(open('physical/die_plan/s81/lat/s81_latency.json'))
k=json.load(open('physical/die_plan/qwen_kvsys/lat_v39r/qwen_kvsys_latency.json'))
for K in (2,3):
  for m in ('port','face'):
    e=json.loads(json.dumps(d))
    for v in e['lanes'].values():
      a=K*(v['faces'] if m=='face' else 1); v['cycles']+=a; v['natural']+=a
    json.dump(e,open(f'{O}/s81_lat_k{K}_{m}.json','w'))
    L=[dict(lane=n,src=v['src']['part']+'.'+v['src']['bus'],dst=v['dst']['part']+'.'+v['dst']['bus'],width=v['width'],delta=K*(v['faces'] if m=='face' else 1)) for n,v in k['lanes'].items()]
    json.dump(dict(note=f'all KV lanes +{K} per {m}',lanes=L),open(f'{O}/kv_k{K}_{m}.json','w'))
PY
python3 tools/s81_dv/tokfunc/compose_tok_ds.py --out $O/s81_base
for K in 2 3; do for m in port face; do
  python3 tools/s81_dv/tokfunc/compose_tok_ds.py --lat $O/s81_lat_k${K}_$m.json --out $O/s81_k${K}_$m
  python3 results/token_pass/toksched_1025/kv_v39r_price.py $O/kv_k${K}_$m.json $O/kv_k${K}_${m}_price.json
done; done
for d in 16 42; do python3 tools/throughput/accepted_cost.py --ledger $O/scratch_ledger.json compute r25gq --unit FALLBACK.ALL --op '*' --op-delta $d --price 1 --measured 1 > $O/hbm_opdelta$d.json; done
