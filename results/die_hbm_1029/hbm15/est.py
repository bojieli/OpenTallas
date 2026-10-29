"""DIE-HBM-15 12.14b estimate: S1 158 unplanned pairs -> lane demand vs shared-face track supply on plan c25c_d15."""
import json, sys, collections, copy
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import schema as S
from pathlib import Path
pd = Path(sys.argv[2]); raw = json.loads((pd / "die_plan.json").read_text())
P = S.Plan(copy.deepcopy(raw), pd / "die_plan.json")
U = json.load(open(sys.argv[3]))["rows"]
die = raw["die"]; reach = die.get("reach_um"); print("die reach_um", reach, "budget", die.get("layer_budget"))
R = {n: P.rect(n) for n in P.parts}
def shared(a, b):
    ax0, ay0, ax1, ay1 = R[a]; bx0, by0, bx1, by1 = R[b]
    if abs(ax1 - bx0) < 1 or abs(bx1 - ax0) < 1:
        return "V", max(0, min(ay1, by1) - max(ay0, by0))
    if abs(ay1 - by0) < 1 or abs(by1 - ay0) < 1:
        return "H", max(0, min(ax1, bx1) - max(ax0, bx0))
    return None, 0
def cdist(a, b):
    ax0, ay0, ax1, ay1 = R[a]; bx0, by0, bx1, by1 = R[b]
    dx = max(0, bx0 - ax1, ax0 - bx1); dy = max(0, by0 - ay1, ay0 - by1)
    return dx + dy
# existing port usage per unordered pair
used = collections.Counter()
for pid, pr in P.ports.items():
    s, d = pr["src"]["part"], pr["dst"]["part"]
    used[frozenset((s, d))] += pr.get("width", 0)
TPU = {"V": 1 / 0.048 + 1 / 0.064, "H": 1 / 0.048 + 1 / 0.064}   # M4+M6 across a vertical edge / M5+M7 across horizontal
rows = []
agg = collections.Counter()
for r in U:
    a, b = r["src"], r["dst"]
    if a not in R or b not in R:
        rows.append((r, "MISSING-PART", 0, 0, 0)); agg["missing"] += 1; continue
    o, L = shared(a, b)
    if o and L > 0:
        sup = 0.5 * L * TPU[o]       # 50% of M4-M7 tracks for signal lanes
        u = used[frozenset((a, b))]
        free = sup - u
        ok = r["unplanned_bits"] <= free
        rows.append((r, "ADJ " + ("FITS" if ok else "OVER"), round(L), round(free), u)); agg["adj_fit" if ok else "adj_over"] += 1
    else:
        dd = cdist(a, b)
        rows.append((r, "HOP", round(dd), 0, 0)); agg["hop"] += 1
        agg["hop_bits"] += r["unplanned_bits"]
print(dict(agg))
over = collections.Counter(); hopd = []
for r, k, L, free, u in sorted(rows, key=lambda x: -x[0]["unplanned_bits"]):
    print(f'{r["src"]:>10} -> {r["dst"]:<10} {r["unplanned_bits"]:6d} b  {k:10s} edge/dist {L:6d} um  free {free:7d}  existing {u}')
