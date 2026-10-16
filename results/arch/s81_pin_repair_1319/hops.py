import gzip, hashlib, json, sys
from pathlib import Path
BASE=Path('/srv/opentallas-scratch/claude/s81-die-r10/src19')
OUT=Path('/srv/opentallas-scratch/codex/s81-pin-repair-1319')
sys.path[:0]=[str(BASE/'tools'),str(BASE/'tools/s81'),str(BASE/'tools/hier_contract')]
import dsrom_s81_fulldie as G
import die_hop_gate as HG
import pair_check as PC

def audit(plan_path, lef_path):
    plan=json.load(gzip.open(plan_path,'rt'))
    insts=[G.Inst(*row)for row in plan['insts']];by={i.name:i for i in insts}
    aliases=plan['port_aliases'];pins=HG.read_pins([gzip.open(lef_path,'rt').read()])
    pair=PC.Gate(default_um=500,buses=[(bid,cls,n,[(i,G.pslice(p)[0])for i,p in eps])for bid,cls,n,eps in plan['buses']])
    bad={};native_bad={};count=missing=0;longest=0.0
    def names(it,port,n):
        base,lo,_=G.pslice(port);lo=lo or 0
        exact=aliases.get(it.master,{}).get(base)
        return exact[lo:lo+n] if exact is not None else [f'{base}[{lo+j}]'for j in range(n)]
    for bid,cls,n,eps in plan['buses']:
        if cls in HG.EXEMPT_CLS or len(eps)<2 or eps[0][0]not in by:continue
        an,ap=eps[0];a=by[an];ab=G.pslice(ap)[0];aa=names(a,ap,n)
        for bn,bp in eps[1:]:
            if bn not in by:continue
            b=by[bn];bb=G.pslice(bp)[0];bs=names(b,bp,n)
            lim=min(500,pair.limit(an,a.master,ab,bn,b.master,bb))
            for j in range(n):
                pa=HG._loc(a,pins,aa[j]);pb=HG._loc(b,pins,bs[j])
                if pa is None or pb is None:missing+=1;continue
                count+=1;length=abs(pa[0]-pb[0])+abs(pa[1]-pb[1]);longest=max(longest,length)
                if length>500+1e-6 or length>lim+1e-6:
                    key=f'{bid}|{an}.{aa[j]}|{bn}.{bs[j]}'
                    if length>500+1e-6:bad[key]=length
                    if length>lim+1e-6:native_bad[key]=length
    return dict(checked=count,missing=missing,max_um=longest,bad=bad,native_bad=native_bad,table_masters=len(pair.t),hold_pairs=len(pair.hold),plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),pins_sha256=hashlib.sha256(lef_path.read_bytes()).hexdigest())

baseline=audit(Path('/srv/opentallas-scratch/claude/s81-die-r10/gen19rb/canonical_plan.json.gz'),Path('/srv/opentallas-scratch/claude/s81-die-r10/gen19rb/exact_pins.lef.gz'))
print('BASE_HOPS',baseline['checked'],len(baseline['bad']),len(baseline['native_bad']),flush=True)
candidate=audit(OUT/'candidate-final-plan.json.gz',OUT/'candidate-exact-pins.lef.gz')
result={'scope':'FROZEN_GEN19RB_ALL_BIT_GEOMETRY_AND_ORIGINAL_PAIR_TABLE_NOT_ROUTE_OR_STA','native_qualified':False}
for label,r in [('baseline',baseline),('candidate',candidate)]:
    result[label]={k:v for k,v in r.items()if k not in('bad','native_bad')}
    result[label].update(flat_bad_bits=len(r['bad']),pair_bad_bits=len(r['native_bad']))
for k in ('bad','native_bad'):
    new=set(candidate[k])-set(baseline[k]);fixed=set(baseline[k])-set(candidate[k]);worse=[(i,candidate[k][i]-baseline[k][i])for i in set(candidate[k])&set(baseline[k]) if candidate[k][i]>baseline[k][i]+1e-6]
    result[k+'_delta']=dict(new_count=len(new),fixed_count=len(fixed),worsened_existing_count=len(worse),new_examples=[(i,candidate[k][i])for i in sorted(new)[:20]],worst_existing_worsening=sorted(worse,key=lambda r:-r[1])[:20])
(OUT/'all_bit_hops.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
