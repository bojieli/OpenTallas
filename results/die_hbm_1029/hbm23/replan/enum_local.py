#!/usr/bin/env python3
"""DIE-HBM-23 LOCAL re-plan estimate: permute only the partitions fully east of the b0xx/hub boundary (under the hub)
in row A {spu1 su30 b100 b110 su31 b101} and row C {spu0 su10 su11 b112}; the west segment stays.  Every hub lane of a
permuted partition stays ADJ by construction (they stay under the hub).  Exhaustive; cost = opt3 cost."""
import sys, json, itertools
sys.argv = ["opt3.py", "1", "1", "3", sys.argv[1] if len(sys.argv) > 1 else "300"]
import opt3 as O
R = O.R
A0, C0 = list(R.A0), list(R.C0)
fa = A0[:5]; pa = A0[5:]
fc = C0[:3]; pc = C0[3:]
res = []
for a in itertools.permutations(pa):
    for c in itertools.permutations(pc):
        A, C = fa + list(a), fc + list(c)
        cst, d = O.cost(R.apply_rows({"A": A, "C": C}), True)
        res.append(dict(cost=round(cst), A=A, C=C, **d))
res.sort(key=lambda x: x["cost"])
base = O.cost(R.apply_rows({"A": A0, "C": C0}), True)
print("base", base)
for r in res[:6]:
    print(r)
json.dump(dict(base=base[1], top=res[:20]), open("enum_local_M%s.json" % O.MOVEPEN, "w"), indent=1)
