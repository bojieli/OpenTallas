import sys,re,statistics as S,collections
f=sys.argv[1]; g=collections.defaultdict(list); tin={}
for l in open(f):
    t=l.rstrip('\n').split('\t')
    if len(t)!=4 or not t[3]: continue
    if t[0].startswith('TAPIN:'): tin[re.search(r'ot_(?:lane|pv)_tap_\d+',t[0]).group(0)]=float(t[3]); continue
    m=re.search(r'ot_(?:lane|pv)_tap_\d+',t[2]); g[m.group(0) if m else 'root'].append(float(t[3]))
rows=sorted(((S.mean(v),k,len(v),tin.get(k)) for k,v in g.items()),reverse=True)
for r in rows[:8]+[None]+rows[-5:]:
    if r is None: print("..."); continue
    m,k,n,ti=r
    print(f"{k} n={n} mean={m:.1f} tapin={ti} sub={m-ti if ti else None}")
