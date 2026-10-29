#!/usr/bin/env python3
"""Book existing per-sid RSTD release holds for source HEAD publication.

Uses exact bound links and the real ring-stop input/output edge chains.
Outputs are an unadopted source-calendar candidate, never physical START.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def compile_book(network, returns, dates, slots):
    from head_publication_probe import publication_closure
    missing = publication_closure(network)
    if missing:
        raise ValueError('actual middle-column V-body closure required: '+json.dumps(missing,sort_keys=True))
    for doc in (network, returns):
        for key in ('source_asbuilt_sha256','die_sha256'):
            if doc[key] != dates[key]:
                raise ValueError('one exact selected source graph required')
    links = {(r['from_sid'],r['from_port']):(r['sid'],r['age_edges'])
             for r in network['transport']['nx_boundary'] if r['status']=='PASS'}
    ids = {r['slice']:r['sid'] for r in network['transport']['nx_boundary']}
    ret = {(r['slice'],r['leaf']):r for r in returns['leaves']}
    fwd = {(r['slice'],r['leaf']):r for r in network['transport']['xf_forward']}
    rstd = {int(k):v for k,v in dates['slice_rstd_edges'].items()}
    if sorted(slots)!=list(range(5)) or set(rstd)!=set(range(16)):
        raise ValueError('all16dated slices and five existing timing slots required')
    stencils={}; ends={}
    for sl,sid in ids.items():
        use=defaultdict(list); arrivals=[]
        def put(resource,edge,leaf):use[(resource,edge)].append(leaf)
        def packet(node,edge,leaf):
            col,tier=node//2,node%2
            put(('assemble',node),edge-1,leaf)
            for direction,distance in [('E',7-col),('W',col)]:
                if distance==0:
                    if direction=='W' and node==1:
                        put(('lineW',node),edge,leaf);arrivals.append(edge)
                    continue
                current=node;t=edge
                put(('line'+direction,current),t,leaf)
                for hop in range(1,distance+1):
                    current,age=links[current,'ro_'+direction.lower()];t+=age+2
                    if hop<distance or (direction=='W' and current==1):
                        put(('line'+direction,current),t,leaf)
                        if direction=='W' and current==1:arrivals.append(t)
        for k in range(5):
            a=ret[sl,k];f=fwd[sl,k]
            if a['status']!='PASS' or f['status']!='PASS':raise ValueError('unqualified source transport')
            first=rstd[sid]+a['rb_broadcast_edges']+f['xf_forward_edges']+4*slots[k]
            for j in range(4):
                put(('fragment',sid),first+j,k);put(('vo',sid),first+2+j,k)
            packet(sid,first+5,k)
            peer,age=links[sid,'vo']
            if peer!=sid^1:raise ValueError('actual V partner differs from publication path')
            packet(peer,first+age+7,k)
        bad={str(k):v for k,v in use.items() if len(v)>1}
        if bad:raise ValueError('within-slice publication stencil overlaps: '+str(bad))
        stencils[sid]=set(use);ends[sid]=max(arrivals)
    occupied=set();holds={}
    # Earliest sources book first; preserve all five leaves' relative timing.
    for sid in sorted(stencils,key=lambda s:(ends[s],s)):
        for delay in range(256):
            candidate={(r,e+delay)for r,e in stencils[sid]}
            if not candidate&occupied:
                occupied|=candidate;holds[sid]=delay;break
        else:raise ValueError('existing8bit release field cannot book this source cohort')
    return dict(schema='opentallas.head.publication_book.v1',status='UNQUALIFIED_SOURCE_CANDIDATE',
                slots=slots,qdelays=[holds[s]for s in range(16)],
                qdelays_parameter_hex=f'{sum(holds[s]<<(8*s)for s in range(16)):032x}',
                max_extra_edges=max(holds.values()),resources=len(occupied),
                source_asbuilt_sha256=network['source_asbuilt_sha256'],die_sha256=network['die_sha256'],
                arithmetic_and_payloads_unchanged=True,physical_START_qualified=False,adoption=False,
                next_gate='real80VQ16ring-stop publication with actualRSTDrelease and header/payload controls')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('network','returns','dates','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--slots',default='2,0,1,3,4');a=p.parse_args()
    result=compile_book(json.loads(a.network.read_text()),json.loads(a.returns.read_text()),json.loads(a.dates.read_text()),[int(v)for v in a.slots.split(',')])
    with a.out.open('x')as f:f.write(json.dumps(result,indent=1)+'\n')
    print(json.dumps(result,indent=1))
