import sys,json,collections
d=sys.argv[1]
T=json.load(open(d+"/tree.json"))
R=json.load(open(sys.argv[2]))["part_region"]
port2reg={t["port"]:R[t["part"]] for t in T["taps"]}
for C in ("TT","FF"):
    a=collections.defaultdict(list)
    for l in open(f"{d}/arr_{C}.txt"):
        f=l.split()
        if f[0]=="T": a[port2reg[f[1]]].append(float(f[2]))
    print(C)
    for r in sorted(a):
        v=sorted(a[r]); n=len(v)
        print(f"  {r:18s} n={n} min/p50/max {v[0]:.0f}/{v[n//2]:.0f}/{v[-1]:.0f} spread {v[-1]-v[0]:.0f}")
