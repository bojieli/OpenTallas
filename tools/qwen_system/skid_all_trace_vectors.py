"""Replay every pinned trace word on one queue component, one tile at a time.
The source trace has no numerical payload: supplied512-bit tags test transport,
not released arithmetic. No array simulation or invented trace arrival records.
"""
import argparse,gzip,hashlib,json
from collections import defaultdict
from pathlib import Path
from qwen_kv_landing_fabric import placement_m
p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();events=defaultdict(list);pos=placement_m();ordinal=0
with gzip.open(a.trace,'rt') as f:
    for line in f:
        cy,fo,pc,n,t0,t1=map(int,line.split())
        for tile in [t0,t1][:max(n,0)]:
            events[tile].append((fo,pc,ordinal));ordinal+=1
with a.out.open('w') as f:
    f.write(f'{len(events)} {ordinal}\n')
    for tile,es in sorted(events.items()):
        es.sort();col=pos[tile][0]%32;origin=es[0][0]
        f.write(f'{tile} {len(es)} {col+11} {col+3}\n')
        for offer,pc,seq in es:f.write(f'{offer-origin} {pc} {seq}\n')
print(json.dumps(dict(trace_sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest(),tiles=len(events),words=ordinal,
 output_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(),scope='every trace offer/order, synthetic512-bit transport tags; no numerical payload in original trace')))
