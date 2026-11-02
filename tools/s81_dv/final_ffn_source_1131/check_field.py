#!/usr/bin/env python3
"""Finish actual emitted down partial forests in canonical sibling order.

This checks source-plan numerical identity against saved checkpoint outputs.
It does not invent CAP delivery dates, assert RTL runtime, or grant leases.
"""
from pathlib import Path
import argparse
from collections import Counter
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/s81'))
from static_return_calendar import _f, norm, complete, sibling, parent, fadd


def finish(words,nseg):
    nodes={}
    coverage=[]
    for edge,tag,data,error in words:
        tag=norm(tag)
        if tag in nodes or error:raise ValueError('duplicate or faulted source partial')
        _,lo,k,n=_f(tag)
        if n!=nseg:raise ValueError('source reduction arity changed')
        coverage.extend(range(lo,min(lo+(1<<k),n)))
        nodes[tag]=data
    if sorted(coverage)!=list(range(nseg)):
        raise ValueError('source partial forest does not cover each K segment once')
    while len(nodes)>1:
        tags=sorted(nodes,key=lambda t:_f(t)[1])
        pairs=[(a,b) for i,a in enumerate(tags) for b in tags[i+1:] if sibling(a,b)]
        if not pairs:raise ValueError('source forest cannot finish by canonical sibling adds')
        a,b=pairs[0];value,error=fadd(nodes.pop(a),nodes.pop(b))
        p=parent(a,b)
        if error or p in nodes:raise ValueError('fault or duplicate source reduction parent')
        nodes[p]=value
    if not nodes or not complete(next(iter(nodes))):raise ValueError('unfinished source reduction')
    return next(iter(nodes.values()))


def canonical(values):
    """Independent left/right binary tree over actual K-segment dot products."""
    values=list(values)
    while len(values)>1:
        level=[]
        for i in range(0,len(values),2):
            if i+1==len(values):level.append(values[i]);continue
            value,error=fadd(values[i],values[i+1])
            if error:raise ValueError('invalid golden source segment')
            level.append(value)
        values=level
    return values[0]


def check(field,fixture):
    field=json.loads(Path(field).read_text());fixture=Path(fixture)
    files=json.loads((fixture/'files.json').read_text());cache={};checked=0;seen=set();endpoints=[]
    for ph in field['phases']:
        if ph['op']!='ffn.down':continue
        byrow={r:[] for r in range(ph['rows'])}
        for word in ph['ret']:
            local=_f(word[1])[0]&0x3fff
            if local not in byrow:raise ValueError('return row outside actual phase ownership')
            byrow[local].append(word)
        for local,words in byrow.items():
            key=(ph['mat'],ph['row_index'][local])
            if key in seen:raise ValueError('duplicate logical down row across field phases')
            seen.add(key)
            value=finish(words,ph['nseg'])
            if value!=canonical(ph['plan']['rows_vals'][str(local)]):
                raise ValueError('source return forest changed the exact FP32 sibling reduction')
            bf=((value+0x7fff+((value>>16)&1))&0xffff0000)
            name,index=ph['tie'][local];rel='ops/'+name+'.bin'
            if rel not in cache:
                spec=files[rel];cache[rel]=np.fromfile(fixture/rel,dtype=np.dtype(spec['dtype'])).reshape(-1).astype(np.float32).view(np.uint32)
            want=int(cache[rel][index])
            if bf!=want:raise ValueError(f'actual down row {key}: canonical BF16{bf:08x} != saved checkpoint{want:08x}')
            checked+=1
        endpoints.append(dict(phase=ph['phase'],mat=ph['mat'],rows=ph['row_index'],
                              first_return=min(w[0] for w in ph['ret']),last_return=max(w[0] for w in ph['ret'])))
    if not checked:raise ValueError('actual field has no down source rows')
    return dict(status='PASS_SOURCE_PLAN_GOLDEN',frame=field['frame'],checked_rows=checked,
                row_counts=dict(Counter(mat for mat,row in seen)),canonical_sibling_reduction=True,
                publication_basis='frame-bench GO-relative return plan; CAP input/global GO dates unqualified',
                relative_publications=endpoints,production_enabled=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--field',required=True);p.add_argument('--fixture',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('preserve prior source-plan verdict')
    try:result=check(a.field,a.fixture)
    except Exception as error:
        out.write_text(json.dumps(dict(status='FAIL',error=str(error)),indent=2)+'\n');raise
    out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['frame'],result['checked_rows'])
