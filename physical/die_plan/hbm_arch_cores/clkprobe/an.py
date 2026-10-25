import csv,collections,statistics as st,sys,numpy as np
def nm(s): return s.replace('\\','')
def inst(p): return nm(p.rsplit('/',1)[0])
for d in sys.argv[1:]:
    S={nm(r['inst']):r for r in csv.DictReader(open(d+"/sinks.csv"))}
    H=list(csv.DictReader(open(d+"/hold.csv")))
    rr=[h for h in H if h['io']=='0']
    rows=[];kinds=collections.Counter()
    for h in rr:
        a=S.get(inst(h['start']));b=S.get(inst(h['end']))
        if a and b and a['arr_max'] and b['arr_max']:
            L=float(a['arr_min'])/1e12;C=float(b['arr_max'])/1e12
            dist=abs(float(a['x'])-float(b['x']))+abs(float(a['y'])-float(b['y']))
            rows.append((float(h['slack'])/1e12,C-L,a['kind'],b['kind'],dist,h['start'],h['end'],L,C))
            kinds[(a['kind'],b['kind'])]+=1
        else: kinds['unk']+=1
    rows.sort()
    print("==",d,"rr",len(rr),dict(kinds))
    for r in rows[:8]: print("  slack %.1f skew %.1f %s->%s dist %.0f L %.0f C %.0f  %s -> %s"%(r[0],r[1],r[2],r[3],r[4],r[7],r[8],r[5][-50:],r[6][-50:]))
    sk=np.array([r[1] for r in rows]); sl=np.array([r[0] for r in rows])
    print("  skew(C-L) p10/50/90",np.percentile(sk,[10,50,90]).round(1)," slack+skew (data margin w/o skew) p50",np.percentile(sl+sk,50).round(1))
    print("  pairs with slack<-50:",(sl<-50).sum()," of which skew>slack deficit:",((sl<-50)&(sk>-sl)).sum())
    io=[h for h in H if h['io']=='1']
    print("  io",len(io),"worst",min(float(h['slack'])/1e12 for h in io) if io else None)
