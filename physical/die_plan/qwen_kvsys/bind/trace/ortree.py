import json,re,collections,sys,pickle
sys.path.insert(0,'.')
import netidx
r=netidx.load(); I=r['insts']; drv=r['drv']; sinks=r['sinks']; pins=r['pins']
PASS=re.compile(r'^(qkd_rlys(h0?)?_\d+|qkd_landsh0?_\d+|qkd_astk_rly_296_fl|qkd_rst_region)$')
def src(nb,depth=0):
    d=drv.get(nb)
    if d is None: return None
    if PASS.match(I[d[0]]) and d[1]=='b':
        for p in ('a','i','y'):
            b=pins.get((d[0],p))
            if b: return src(b[d[2]] if len(b)>d[2] else b[-1],depth+1)
    return d
def snk(nb,out):
    for (s,p,idx) in sinks.get(nb,[]):
        if PASS.match(I[s]) and p in ('a','y','i'):
            ob=pins.get((s,'b'))
            if ob: snk(ob[len(ob)-1-idx] if False else ob[-1-idx] if idx<len(ob) else ob[-1],out)
        else: out.append((s,p))
ors=[n for n,m in I.items() if m=='qkd_hp_or2']
G={}
for n in ors:
    ins={p:src(pins[(n,p)][0]) for p in ('a','b')}
    out=[]; snk(pins[(n,'q')][0],out)
    G[n]=dict(ins={p:(v[0],v[1]) if v else None for p,v in ins.items()}, outs=out)
json.dump(G,open('ortree_rtl6.json','w'))
kinds=collections.Counter()
for n,g in G.items():
    for p,v in g['ins'].items(): kinds[I[v[0]] if v else None]+=1
print(len(G), kinds.most_common(15))
roots=[n for n,g in G.items() if not any(I[s]=='qkd_hp_or2' for s,_ in g['outs'])]
print('roots',len(roots), [(n,G[n]['outs'][:3]) for n in roots[:5]])
