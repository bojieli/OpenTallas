import sys, json
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import schema as S
raw = json.load(open(sys.argv[2] + "/die_plan.json"))
P = S.Plan(raw)
names = [p for p in P.parts if p.startswith(sys.argv[3])]
for p in sorted(names, key=lambda p: (P.rect(p)[1], P.rect(p)[0])):
    r = P.rect(p)
    nm = len(S.placed_macro_boxes(P.ptype(p), halo=0))
    print(f"{p:12s} x {r[0]:8.1f}-{r[2]:8.1f} y {r[1]:8.1f}-{r[3]:8.1f}  type {P.parts[p]['type'] if isinstance(P.parts[p], dict) else ''} macros {nm}")
