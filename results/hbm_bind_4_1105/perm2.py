import json,collections,random,re
R="/srv/opentallas-scratch2/claude/hbm-bind-4/"
L=json.load(open(R+"g3/bind_latency.json"))["buses"]
r=json.load(open(R+"g3/bind_report.json"))
P=json.load(open(R+"tstage2/die_plan.json")); T=P["partition_types"]
pos={}
for p in P["partitions"]:
    w,h=T[p["type"]]["outline_um"]; pos[p["name"]]=[p["origin_um"][0],p["origin_um"][1],w,h]
W=collections.Counter(); U=collections.Counter()
for b in L:
    if b["src"].startswith("NE") or b["dst"].startswith("NE"): continue
    W[(b["src"],b["dst"])]+=b["width"]
for e in r["errors"]:
    m=re.match(r"UNPLANNED (\S+) -> (\S+): (\d+)",e)
    if m and not m.group(1).startswith("NE") and not m.group(2).startswith("NE"): U[(m.group(1),m.group(2))]+=int(m.group(3))
print("planned bits",sum(W.values()),"U bits",sum(U.values()))
rows={"r2":[n for n,x in sorted(pos.items(),key=lambda a:a[1][0]) if n.startswith("NW_") and abs(x[1]-4510)<2],
      "r1":[n for n,x in sorted(pos.items(),key=lambda a:a[1][0]) if n.startswith("NW_") and abs(x[1]-10385)<2]}
print(rows)
base={k:pos[v[0]][0] for k,v in rows.items()}
def place(order):
    q=dict()
    for k,v in order.items():
        x=base[k]
        for n in v: q[n]=(x+pos[n][2]/2,pos[n][1]+pos[n][3]/2); x+=pos[n][2]
    return q
def ctr(n,q): 
    return q[n] if n in q else (pos[n][0]+pos[n][2]/2,pos[n][1]+pos[n][3]/2)
def cost(order,table):
    q=place(order); s=0
    for (a,b),w in table.items():
        A,B=ctr(a,q),ctr(b,q); s+=w*(abs(A[0]-B[0])+abs(A[1]-B[1]))
    return s
A=collections.Counter(W); A.update(U)
SP={"NW_spu0":5901,"NW_spu1":6117}; TOL=300
_cost=cost
def cost(o,t):
    c=_cost(o,t)
    q=place(o)
    for n,x in SP.items():
        c+=1e7*max(0,abs(q[n][0]-pos[n][2]/2-x)-TOL)
    return c
def rep(tag,o):
    print(tag,"all b*mm",round(cost(o,A)/1e3),"U b*mm",round(cost(o,U)/1e3),"planned b*mm",round(cost(o,W)/1e3))
    q=place(o); print({k:v for k,v in o.items()})
    print({n:round(q[n][0]-pos[n][2]/2) for n in q if "sp" in n})
    t=sorted(((w*(abs(ctr(a,q)[0]-ctr(b,q)[0])+abs(ctr(a,q)[1]-ctr(b,q)[1]))/1e3,a,b,w) for (a,b),w in U.items()),reverse=True)[:10]
    print([(round(x),a,b,w) for x,a,b,w in t])
o0={k:list(v) for k,v in rows.items()}
rep("now",o0)
best=None
random.seed(1)
for trial in range(40):
    o={k:list(v) for k,v in rows.items()}
    for k in o: random.shuffle(o[k])
    c=cost(o,A); imp=True
    while imp:
        imp=False
        for k in o:
            n=len(o[k])
            for i in range(n):
                for j in range(i+1,n):
                    o[k][i],o[k][j]=o[k][j],o[k][i]
                    d=cost(o,A)
                    if d<c-1: c=d; imp=True
                    else: o[k][i],o[k][j]=o[k][j],o[k][i]
    if best is None or c<best[0]: best=(c,{k:list(v) for k,v in o.items()})
rep("best",best[1])
o=best[1]
json.dump(o,open("/tmp/hb4best_%d.json"%TOL,"w"))

q=place(o)
def dd(a,b,z): A,B=ctr(a,z),ctr(b,z); return abs(A[0]-B[0])+abs(A[1]-B[1])
print("worse",sorted([(round(w*(dd(a,b,q)-dd(a,b,{}))/1e3),a,b,w) for (a,b),w in W.items()],reverse=True)[:6])
print("su positions",{n:round(q[n][0]-pos[n][2]/2-pos[n][0]) for n in q})
