import sys,json,collections
T=json.load(open(sys.argv[1]+"/tree.json"))
N={int(k):v for k,v in T["nodes"].items()}
L={}
for i in sorted(N):
    n=N[i]; p=n["parent"]
    L[i]=0 if p is None else L[p]+abs(N[p]["x"]-n["x"])+abs(N[p]["y"]-n["y"])
Lreq={}
for i in sorted(N):
    n=N[i]; p=n["parent"]; a=n.get("req_xy",[n["x"],n["y"]])
    Lreq[i]=0 if p is None else Lreq[p]+abs(N[p].get("req_xy",[N[p]["x"],N[p]["y"]])[0]-a[0])+abs(N[p].get("req_xy",[N[p]["x"],N[p]["y"]])[1]-a[1])
reg=sys.argv[2]
def regof(i):
    while i is not None:
        if N[i].get("region_root"): return N[i]["region_root"]
        i=N[i]["parent"]
leafL=collections.defaultdict(list); leafReq=collections.defaultdict(list); leg=collections.defaultdict(list)
for t in T["taps"]:
    i=t["node"]; r=regof(i)
    leafL[r].append(L[i]); leafReq[r].append(Lreq[i]); leg[r].append(abs(N[i]["x"]-t["xy"][0])+abs(N[i]["y"]-t["xy"][1]))
for r in sorted(leafL):
    f=lambda v:(round(min(v)),round(max(v)))
    print(r,"leaf placed",f(leafL[r]),"leaf requested",f(leafReq[r]),"leaf->tap leg",f(leg[r]),"n",len(leg[r]))
tap=collections.defaultdict(list)
for t in T["taps"]:
    i=t["node"]; tap[regof(i)].append(L[i]+abs(N[i]["x"]-t["xy"][0])+abs(N[i]["y"]-t["xy"][1]))
for r in sorted(tap):
    v=sorted(tap[r]); n=len(v)
    print(r,"root->tap min/p5/p50/p95/max",[round(v[int(q*(n-1))]) for q in (0,.05,.5,.95,1)])
