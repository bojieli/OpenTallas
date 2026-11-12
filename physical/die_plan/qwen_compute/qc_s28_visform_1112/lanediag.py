"""lanediag.py TREE PLAN lane,lane,... : print the pin-hop chain (check.lane_pin_hops walk) for each lane."""
import sys, json
from pathlib import Path
tree, plan, lanes = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
sys.path.insert(0, f"{tree}/tools/die_plan")
import schema as S, check as C
raw = json.load(open(plan))
pd = Path(plan).parent
sc = pd / "die_io.json"
if not raw.get("die", {}).get("io") and sc.exists():
    raw = dict(raw, die=dict(raw["die"], io=json.loads(sc.read_text())))
P = S.Plan(raw, pd / "die_plan.json")
for lid in lanes:
    pts, regs, xs = C.lane_geometry(P, lid)
    print(f"== {lid} reach {P.lanes[lid].get('reach_um', P.reach)} ports {P.lanes[lid]['ports'][0]} -> {P.lanes[lid]['ports'][-1]}")
    prev = regs[0]; L = 0.0; idx = 1; h = 0
    print(f"   start {prev}")
    for part, slot, a, b in P.lane_crossings(lid):
        pa, pb = P.port_point(a), P.port_point(b)
        tn = P.parts[part]["type"]
        L += abs(prev[0]-pa[0]) + abs(prev[1]-pa[1]); prev = pa
        s = P.slot(part, slot) or {}
        k = int(s.get("stations", 1))
        print(f"   cross {part} [{tn}] slot {slot} stations {k} in {a}@{tuple(round(v,1) for v in pa)} out {b}@{tuple(round(v,1) for v in pb)} org {P.parts[part].get('origin_um')} orient {P.parts[part].get('orient')}")
        for j, pt in enumerate(regs[idx:idx+k]):
            L += abs(prev[0]-pt[0]) + abs(prev[1]-pt[1])
            print(f"      hop {h}: {L:.1f} -> reg{j} {tuple(round(v,1) for v in pt)}")
            h += 1; prev = pt; L = 0.0
        idx += k
        L += abs(prev[0]-pb[0]) + abs(prev[1]-pb[1]); prev = pb
    end = regs[-1]; L += abs(prev[0]-end[0]) + abs(prev[1]-end[1])
    print(f"      hop {h}: {L:.1f} -> end {end}")
