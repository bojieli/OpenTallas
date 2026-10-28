import json,sys
RD=sys.argv[1]; t=json.load(open(RD+"/clk/tree.json")); po=t["parent_of"]; S=t["sites"]
N=t["nodes"]; N={("b%d"%n["id"] if isinstance(n,dict) and "id" in n else k):n for k,n in (N.items() if isinstance(N,dict) else enumerate(N))}
k0=next(iter(N)); print("node keys", list(N[k0].keys()) if isinstance(N[k0],dict) else N[k0])
def ch(x):
    c=[x]
    while x in po: x=po[x]; c.append(x)
    return c
for leaf in sys.argv[3:]:
    c=ch(leaf); c=c[:c.index(sys.argv[2])+1]
    print(leaf, " <- ".join("%s%s(%.0f,%.0f)%s"%(n, "" , S[n][0],S[n][1], (" imb=%s"%N[n].get("balance_imbalance_um")) if n in N and isinstance(N[n],dict) and N[n].get("balance_imbalance_um") else "") for n in c))
