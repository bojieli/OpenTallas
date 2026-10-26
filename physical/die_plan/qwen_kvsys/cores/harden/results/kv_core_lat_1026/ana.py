import sys,re,statistics as S,collections,json,glob,os
out={}
for f in sorted(glob.glob(sys.argv[1]+'/*/*.ins.tsv')+glob.glob(sys.argv[1]+'/*/ins.tsv')):
    g=collections.defaultdict(list); pf=[]; al=[]
    for l in open(f):
        t=l.rstrip('\n').split('\t')
        if len(t)!=4: continue
        i,fc,n,a=t
        if not a: continue
        a=float(a); al.append(a)
        m=re.search(r'ot_(?:lane|pv)_tap_\d+',n); g[m.group(0) if m else 'root'].append(a)
        if fc=='P': pf.append(a)
    st=lambda v: dict(n=len(v),min=round(min(v),1),mean=round(S.mean(v),1),max=round(max(v),1)) if v else None
    tm=[S.mean(v) for v in g.values()]
    out[f]=dict(pinflops=st(pf),all=st(al),taps=len(g),tap_mean_min=round(min(tm),1),tap_mean_max=round(max(tm),1))
    print(f.replace(sys.argv[1],''),json.dumps(out[f]))
