import json,sys
from pathlib import Path
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/codex-hbm-1030/tools/die_plan")
import schema as S
import check as C
def lane_pin_hops(P, lid, regs):
    """FF-to-FF reach through mandatory slot pins, including inter-partition seams.

    Manhattan distance between FF centres can shortcut a required output/input
    pin detour. Each intervening declared pin is part of the actual net route.
    This remains a geometric lower bound; routed wire may be longer.
    """
    if not regs:
        return []
    hops = []
    previous = regs[0]
    length = 0.0
    index = 1
    for part, slot, a, b in P.lane_crossings(lid):
        pa, pb = P.port_point(a), P.port_point(b)
        length += abs(previous[0] - pa[0]) + abs(previous[1] - pa[1])
        previous = pa
        count = int((P.slot(part, slot) or {}).get("stations", 1))
        for point in regs[index:index + count]:
            length += abs(previous[0] - point[0]) + abs(previous[1] - point[1])
            hops.append(length)
            previous, length = point, 0.0
        index += count
        length += abs(previous[0] - pb[0]) + abs(previous[1] - pb[1])
        previous = pb
    endpoint = regs[-1]
    length += abs(previous[0] - endpoint[0]) + abs(previous[1] - endpoint[1])
    hops.append(length)
    return hops
out=[]
for variant in ("hh_coherent2","hh_seams2"):
 pth=Path("/srv/opentallas-scratch2/claude/codex-hbm-1030")/variant/"die_plan.json"
 P=S.Plan(json.loads(pth.read_text()),pth)
 for lid in ("L700","L701"):
  pts,regs,xs=C.lane_geometry(P,lid)
  direct=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(regs,regs[1:])]
  via=lane_pin_hops(P,lid,regs)
  out.append(dict(variant=variant,lane=lid,stations=sum(x["stations"] for x in xs),direct_max=max(direct),via_max=max(via),via_hops=via))
print(json.dumps(out,indent=1))
