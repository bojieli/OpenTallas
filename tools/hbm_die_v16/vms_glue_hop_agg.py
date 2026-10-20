import sys, re, collections
H=collections.defaultdict(list); K=collections.Counter()
for ln in open(sys.argv[1]):
    p = ln.split(None, 3)
    if len(p) < 4: K["other"] += 1; continue
    k, dep, d, n = p; K[k] += 1
    if k!='pure': continue
    s=re.sub(r'\[\d+\]','',n.strip().replace(chr(92),'')); s=re.sub(r'\$.*','',s); s=s.replace('\\','')
    a=s.split('.'); g='.'.join(a[:3]) if a[0]=='u_core' else a[0]
    H[g].append(float(d))
print(dict(K))
allv=sorted(x for v in H.values() for x in v)
def q(v,p): return v[min(len(v)-1,int(p*len(v)))]
for lim in (20,50,100,200,405):
    print(f'pure hops <= {lim} um: {sum(1 for x in allv if x<=lim)} of {len(allv)}')
for g,v in sorted(H.items(), key=lambda kv:-len(kv[1]))[:70]:
    v.sort(); print(f'{len(v):6d} p10 {q(v,.1):7.1f} p50 {q(v,.5):7.1f} p90 {q(v,.9):7.1f} max {v[-1]:7.1f} <=50um {sum(1 for x in v if x<=50):6d}  {g}')
