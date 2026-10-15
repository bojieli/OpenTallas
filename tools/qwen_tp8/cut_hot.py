# Per-bus breakdown of a cut window: python3 tools/qwen_tp8/cut_hot.py OUTDIR/rom_tp8b.json ax:pos:winlo ...
import json,sys,collections
sys.path.insert(0,'results/arch/qwen_tp8_1012')
import numpy as np
d=json.load(open(sys.argv[1])); I={i['n']:i for i in d['insts']}
cen=lambda i:(i['x']+i['w']/2,i['y']+i['h']/2)
cl=lambda i,P:(min(max(P[0],i['x']),i['x']+i['w']),min(max(P[1],i['y']),i['y']+i['h']))
segs=[]
for b,c,bits,eps in d['buses']:
    p=[I[e] for e in eps if e in I]
    if len(p)<2 or c=='clock_trunk': continue
    for a,q in (list(zip(p,p[1:])) if len(p)==2 else [(p[0],t) for t in p[1:]]):
        A,Q=cl(a,cen(q)),cl(q,cen(a)); segs.append((b,c,bits,A,Q,a['n'],q['n']))
for spec in sys.argv[2:]:
    ax,cp,lo=spec.split(':'); cp=float(cp); lo=float(lo); hi=lo+260
    p,o=(0,1) if ax=='x' else (1,0)
    agg=collections.Counter(); ex={}
    for b,c,bits,A,Q,an,qn in segs:
        if min(A[p],Q[p])<cp<max(A[p],Q[p]):
            oc=A[o]+(Q[o]-A[o])*(cp-A[p])/(Q[p]-A[p])
            if lo<=oc<hi:
                k=b.split('_r')[0] if '_r' in b else b
                agg[(c,k)]+=bits; ex[(c,k)]=(an,qn,[round(v) for v in A+Q])
    print(spec, sum(agg.values()))
    for k,v in agg.most_common(14): print('  ',v,k,ex[k])
blks=[i for i in d['insts'] if i['w']*i['h']>4e4 and i['x']<14560 and i['x']+i['w']>14300 and i['y']<15600 and i['y']+i['h']>15400]
print([(i['n'],i['m'],round(i['x']),round(i['y']),round(i['w']),round(i['h'])) for i in blks])
