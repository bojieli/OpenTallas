import sys,collections,re
f=sys.argv[1]
for corner in ('tt','ff'):
    rows=[]
    for l in open(f):
        p=l.split()
        if p[0]!=corner or p[1]!='OT_CKX': continue
        rows.append((int(p[2]),p[3],float(p[4]),int(p[5])/1000,int(p[6])/1000))
    b=[r for r in rows if r[0]==1]
    a=sorted(r[2] for r in b)
    print(f"== {corner} boundary n={len(b)} arr {a[0]:.1f}..{a[-1]:.1f} p1 {a[len(a)//100]:.1f} p99 {a[-len(a)//100-1]:.1f}  all n={len(rows)}")
    grp=collections.defaultdict(list)
    for r in b:
        n=r[1].lstrip('\\')
        parts=re.split(r'[./]',n)
        key='.'.join(parts[:3]) if parts[0].startswith('u_ot_pr') else parts[0]
        key=re.sub(r'\[\d+\]','[*]',key); key=re.sub(r'_reg.*|\$.*','',key)
        grp[key].append(r)
    for k,v in sorted(grp.items(),key=lambda t:-max(x[2] for x in t[1]))[:18]:
        ar=[x[2] for x in v]
        print("  %-48s %5d arr %6.1f..%6.1f mean %6.1f x %5.0f..%5.0f y %5.0f..%5.0f"%(k[:48],len(v),min(ar),max(ar),sum(ar)/len(ar),min(x[3] for x in v),max(x[3] for x in v),min(x[4] for x in v),max(x[4] for x in v)))
    # grid
    grid=collections.defaultdict(list)
    for r in b: grid[(int(r[3]//40),int(r[4]//40))].append(r[2])
    ys=sorted({k[1] for k in grid},reverse=True); xs=sorted({k[0] for k in grid})
    for yy in ys: print("   y%3d "%(yy*40)+" ".join(("%4.0f"%(sum(grid[(xx,yy)])/len(grid[(xx,yy)])) if (xx,yy) in grid else "   .") for xx in xs))
    print("        "+" ".join("x%3d"%(xx*40) for xx in xs))
