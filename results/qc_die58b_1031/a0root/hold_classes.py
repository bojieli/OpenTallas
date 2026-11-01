import sys, re, collections
rows=[l.rstrip("\n").split("\t") for l in open(sys.argv[1])][1:]
def cls(n):
    n=re.sub(r"\[\d+\]","[*]",n); n=re.sub(r"\\\[\d+\\\]","[*]",n); n=re.sub(r"_\d+(?=[/.$])","_#",n)
    return n.rsplit("/",1)[0][:70]
g=collections.defaultdict(list)
for r in rows:
    s=float(r[0]); g[(cls(r[1]),cls(r[2]))].append((s,r[3],r[4]))
lim=float(sys.argv[2]) if len(sys.argv)>2 else 0
items=sorted(g.items(), key=lambda kv: min(x[0] for x in kv[1]))
print("total", len(rows), "< -100:", sum(float(r[0])< -100 for r in rows))
for (a,b),v in items[:25]:
    w=min(v); print(f"{len(v):5d} ws {w[0]:8.1f} nlt100 {sum(x[0]< -100 for x in v):4d}  sp_ck {w[1]:>7} ep_ck {w[2]:>7}  {a} -> {b}")
