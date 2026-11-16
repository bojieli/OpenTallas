import json, sys, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import die_trial as D, schema as S
P = S.Plan(S.load(sys.argv[2]), Path(sys.argv[2])); site = D.clock_site(P)
T = json.load(open(sys.argv[3])); N = {int(k): v for k, v in T["nodes"].items()}
inst = [n for n, p in P.parts.items() if p["type"] == sys.argv[4]]
def tile(x, y):
    for n in inst:
        r = P.rect(n)
        if r[0] <= x < r[2] and r[1] <= y < r[3]: return n
bad = collections.Counter(); tot = collections.Counter(); ex = []
for i, v in N.items():
    pl = v.get("physical_leg")
    if not pl: continue
    n = tile(v["x"], v["y"]); o = P.orient(n) if n else "-"
    for q in pl["chain"]:
        tot[o] += 1
        if not site.legal(tuple(q)):
            bad[o] += 1
            if len(ex) < 4 and o != "-": ex.append((o, n, q))
print("illegal chain points by orient:", dict(bad), "of", dict(tot)); print(ex)
