#!/usr/bin/env python3
"""Check all native QKV cluster outputs against real fixture partials and a fixed compiled edge ledger."""
import argparse,json
from pathlib import Path

def check(inputs,log,edges,out):
    expected={cid:json.loads((inputs/f'cid{cid}'/'gold.json').read_text())['qkv']['words'] for cid in range(48)}
    ledger=json.loads(edges.read_text());actual={cid:[] for cid in range(48)};errors=[]
    if set(ledger)!=set(map(str,range(48))):raise ValueError('edge ledger must contain exactly48 cluster IDs')
    for cid in range(48):
        if len(ledger[str(cid)])!=len(expected[cid]):raise ValueError(f'edge count cid{cid}')
    target={int(t) for v in ledger.values() for t in v}
    low,high=min(target),max(target)
    for ln in log.read_text().splitlines():
        p=ln.split()
        if len(p)==5 and p[1]=='CLUSTER' and low<=int(p[0])<=high:
            cycle,cid,fault,payload=int(p[0]),int(p[2]),int(p[3]),int(p[4],16)
            if cid not in actual:errors.append(f'unknown cluster {cid}');continue
            if fault:errors.append(f'cluster{cid} fault at{cycle}')
            actual[cid].append((cycle,payload))
    matches=0
    for cid in range(48):
        exp=list(zip(map(int,ledger[str(cid)]),[int(w['word'],16) for w in expected[cid]]))
        got=actual[cid]
        if len(got)!=len(exp):errors.append(f'cluster{cid}: got{len(got)} expected{len(exp)} words')
        for i,(a,b) in enumerate(zip(got,exp)):
            if a==b:matches+=1
            else:errors.append(f'cluster{cid} word{i}: actualedge{a[0]} expected{b[0]}, payload_equal={a[1]==b[1]}')
    r=dict(verdict='PASS' if not errors and matches==384 else 'FAIL',exact_words=matches,expected_words=384,
           errors=errors,scope='Actual unscaled QKV cluster partials and exact fixed schedule only; PC1/QK/nativeKV/result and physical gates remain separate.')
    out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r));return r['verdict']=='PASS'
if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--inputs',type=Path,required=True);a.add_argument('--log',type=Path,required=True);a.add_argument('--expected-edges',type=Path,required=True);a.add_argument('--out',type=Path,required=True);p=a.parse_args();raise SystemExit(0 if check(p.inputs,p.log,p.expected_edges,p.out) else 1)
