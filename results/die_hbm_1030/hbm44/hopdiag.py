# DIE-HBM-44: per-hop detail for the G0 hop-error lanes of a die plan (read-only)
import sys, json
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan")
import check as C
S = C.S
plan = sys.argv[1]; lanes = sys.argv[2].split(",")
raw = json.load(open(plan))
P = S.Plan(raw, Path(plan))
for lid in lanes:
    pts, regs, xs = C.lane_geometry(P, lid)
    hops = C.lane_pin_hops(P, lid, regs)
    print("==", lid, "hops", [round(h) for h in hops])
    prev = P.port_point(P.lanes[lid]["ports"][0])
    print("  src", P.lanes[lid]["ports"][0], [round(v,1) for v in prev])
    i = 1
    for part, slot, a, b in P.lane_crossings(lid):
        s = P.slot(part, slot) or {}
        k = int(s.get("stations", 1))
        print("  ", part, P.parts[part]["type"], slot, "in", a, [round(v,1) for v in P.port_point(a)], "out", b, [round(v,1) for v in P.port_point(b)],
              "st", k, [[round(v,1) for v in r] for r in regs[i:i+k]], "regs_um" in s, s.get("in_face"), s.get("out_face"))
        i += k
    print("  dst", P.lanes[lid]["ports"][-1], [round(v,1) for v in regs[-1]])
