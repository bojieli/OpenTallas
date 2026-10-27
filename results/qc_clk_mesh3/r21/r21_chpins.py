"""R21 diag: die-frame pin points of every channel port bit (src side vs dst side) -> json + summary."""
import json, sys
from collections import Counter
import die_trial as DT, gen_phys, schema as S
P = S.Plan(S.load(sys.argv[1]))
cp = DT.channel_ports(P)
tp = {}
for _, a, ba, b, bb, k in cp:
    for part in (a, b):
        tn = P.parts[part]["type"]
        if tn not in tp:
            tp[tn] = {(bus, bit): (ln, x, y) for bus, bit, ln, x, y, _ in gen_phys.type_pins(P, tn)}
rows, st = [], Counter()
for pid, a, ba, b, bb, k in cp:
    for bit in range(k):
        pa, pb = tp[P.parts[a]["type"]].get((ba, bit)), tp[P.parts[b]["type"]].get((bb, bit))
        if not pa or not pb:
            st["missing"] += 1
            continue
        xa, ya = P.to_die(a, pa[1:]); xb, yb = P.to_die(b, pb[1:])
        d = abs(xa - xb) + abs(ya - yb)
        st[f"dist_{round(d, 1)}"] += 1
        st[f"layers_{pa[0]}_{pb[0]}"] += 1
        if bit == 0:
            rows.append((pid, a, b, pa[0], round(xa, 3), round(ya, 3), pb[0], round(xb, 3), round(yb, 3)))
print(json.dumps(dict(st.most_common(20)), indent=0))
for r in rows[:8]: print(r)
json.dump(rows, open(sys.argv[2], "w"))
