#!/usr/bin/env python3
"""TOK-QK-XD3 10-26: tp8 fx/lanes/coll_lane_latency.json from the regen_constants QC json (as XD2 finding 3: no GEN run has
written one; the tp8 sims take COLL_BENCH_ARGS, this file is only hashed + read by the collector).
usage: lanes_from_constants.py CONSTANTS_JSON OUT_JSON"""
import json, sys
c = json.load(open(sys.argv[1])); k = c['constants']
a = k['COLL_BENCH_ARGS']['value'].split()
def grab(flag, n):
    i = a.index(flag); return [int(x) for x in a[i + 1:i + 1 + n]]
rel, lanes, lx = grab('--relays', 4), grab('--lanes', 6), grab('--lx', 3)
json.dump(dict(source=f"regen_constants.py on QC v7 final bind (bound_sha {c['bound_sha']}) --peer KV B48 (codex/kv-land-1026@c01a6f445 b48)", LX=lx, RS=rel[1:],
               TX=lanes[:3], calendar=dict(LS=k['COLL_LS']['value']), bench_args=k['COLL_BENCH_ARGS']['value']),
          open(sys.argv[2], 'w'), indent=1)
print('LANES', open(sys.argv[2]).read().replace('\n', ' '))
