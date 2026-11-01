import sys, collections
G=sys.argv[1]; pins={}; cells={}; clk=None
for l in open(G):
    f=l.rstrip("\n").split("\t")
    if f[0]=="P" and (f[2]=="clk" or f[2].startswith("clk_t") or f[2].startswith("fclk_in")): pins[f[2]]=(float(f[6]),float(f[7]))
    elif f[0]=="C": cells[f[1]]=((float(f[4])+float(f[6]))/2,(float(f[5])+float(f[7]))/2,f[3],f[8])
    elif f[0]=="N" and f[1]=="CLOCK" and len(f)>3000 and clk is None: clk=[x for x in f[2:] if x.endswith("c")]
S=[cells[x[1:-1]] for x in clk if x[1:-1] in cells]
tp={k:v for k,v in pins.items() if not k.startswith("fclk")}
grp=collections.defaultdict(list)
for s in S:
    n=min(tp,key=lambda k:abs(tp[k][0]-s[0])+abs(tp[k][1]-s[1])); grp[n].append(s)
for k in sorted(grp,key=lambda k:-len(grp[k]))[:6]:
    xs=sorted(s[0] for s in grp[k]); ys=sorted(s[1] for s in grp[k])
    print(k,tp[k],len(grp[k]),"x p10/50/90",[round(xs[int(len(xs)*q)]) for q in (.1,.5,.9)],"y",[round(ys[int(len(ys)*q)]) for q in (.1,.5,.9)])
