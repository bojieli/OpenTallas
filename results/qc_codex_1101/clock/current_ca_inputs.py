#!/usr/bin/env python3
"""Recover the current rich CA timing input from its committed native source.

The runtime sidecar deliberately strips STA interval fields. Its current START
and partition graphs must match the rich source exactly; this never uses a
newer or older START graph merely because its paths have the same names.
Only the already approved per-port K/schedule +/-1 event is replayed here.
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

w=Path(sys.argv[1]).resolve();out=Path(sys.argv[2])
sys.path.insert(0,str(w/'physical/die_plan/qwen_compute/bind'))
import ca_pair_rule
source=w/'results/token_pass/qc_functional_0845/inputs/native_ca.json.gz'
sidecar=w/'results/qc_die57_1031/bind/sidecar.json'
s=json.loads(sidecar.read_text());current=s['count_aligned']
rich=json.loads(gzip.decompress(source.read_bytes()))
assert rich['root']==current['root'] and rich['period_ps']==current['period_ps']
for field in ('regions','start_ports','parts'):
    assert set(rich[field])==set(current[field]),field
    for name,record in current[field].items():
        assert all(rich[field][name].get(k)==v for k,v in record.items()),(field,name)
ca_pair_rule.apply(rich,s)
assert set(rich['ports'])==set(current['ports'])
changed=[]
for name,record in current['ports'].items():
    r=rich['ports'][name];delta=record['K']-r['K']
    assert record['depth']==r['depth'] and record['tree']==r['tree'],name
    assert record['sched_lat']-r['sched_lat']==delta,name
    if delta:
        assert delta in (-1,1),(name,delta)
        changed.append(dict(port=name,delta=delta))
        for field in ('L_lo_ps','L_hi_ps'):
            r[field]=round(r[field]+delta*rich['period_ps'],1)
        r['margin_lo_ps']=round(r['margin_lo_ps']+delta*rich['period_ps'],1)
        r['margin_hi_ps']=round(r['margin_hi_ps']-delta*rich['period_ps'],1)
    r.update(record)
assert len(changed)==186,len(changed)
rich['root_settle_cycles']=current['root_settle_cycles']
rich['input_reconstruction']=dict(source=str(source.relative_to(w)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),sidecar_sha256=hashlib.sha256(sidecar.read_bytes()).hexdigest(),exact_start_graph=True,start_edges=len(rich['start_ports']),approved_count_shifts=changed,scope='Current runtime schedule with original rich STA reference intervals; current proof remeasurement is separate. No token-cycle change introduced.')
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rich)+'\n')
print(json.dumps(dict(start_edges=len(rich['start_ports']),crossings=len(rich['ports']),count_shifts=len(changed),exact_topology=True)))
