import sys,re,collections
pats=[re.compile(p) for p in sys.argv[2:]]
agg=collections.defaultdict(list)
for ln in open(sys.argv[1]):
    f=ln.rstrip('\n').split('\t')
    if f[0]!='C': continue
    for p in pats:
        if p.search(f[8]):
            x=(float(f[4])+float(f[6]))/2; y=(float(f[5])+float(f[7]))/2
            agg[p.pattern].append((x,y))
for k,v in agg.items():
    xs=sorted(a for a,b in v); ys=sorted(b for a,b in v); n=len(v)
    print(f"{k:45s} n={n:5d} x[min/med/max]={xs[0]:.0f}/{xs[n//2]:.0f}/{xs[-1]:.0f} y={ys[0]:.0f}/{ys[n//2]:.0f}/{ys[-1]:.0f}")
