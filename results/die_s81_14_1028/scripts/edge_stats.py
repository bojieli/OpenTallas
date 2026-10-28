# go13 built tree: measured TT edge delay (node buffer late - parent node buffer late, OpenSTA combo GRT) per tree edge,
# split by kind (feed / region DME, DME core-tap hang leaf vs other) + hang-parent fanout (stars)
import json,collections,sys
O=sys.argv[1] if len(sys.argv)>1 else "/srv/opentallas-scratch2/claude/die-s81-13"
T=json.load(open(f"{O}/clk/tree.json")); nodes=T["nodes"]
ct=collections.defaultdict(list)
for t in T["taps"]: ct[t["node"]].append(t["tap"])
N={}
for l in open(f"{O}/out_TT/arr_TT.txt"):
    p=l.split()
    if p[0]=="N" and p[1].startswith("b") and p[1][1:].isdigit(): N[int(p[1][1:])]=float(p[2])
c=collections.Counter(); hk=collections.Counter()
for k,nd in nodes.items():
    i=int(k); par=nd["parent"]
    if par is None or i not in N or par not in N: continue
    d=N[i]-N[par]; h=(not nd["kids"]) and any(x.startswith("clk_c") for x in ct[i])
    kind="feed" if not nd.get("dme") else ("dme-core-hang" if h else "dme-other")
    for lim in (350,420,450,550):
        if d>lim: c[f"{kind} >{lim}"]+=1
    if h: hk[par]+=1
print(json.dumps(dict(sorted(c.items())),indent=0))
print("hang-parent nodes",len(hk),"hangs/parent hist",sorted(collections.Counter(min(v,8) for v in hk.values()).items()))
