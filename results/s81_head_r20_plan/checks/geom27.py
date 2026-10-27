"""Own check: M9 clock straps (0.32 um 8w) vs die M9 PG stripes of a plan; short = overlap, spacing < 1.0 = spacing miss."""
import json, sys
D = sys.argv[1]; plan = json.load(open(f"{D}/plan_33029005.json"))
g = [x for x in plan["die"]["pg"]["grid"] if x["layer"] == "M9"][0]
W, P, O, nets = g["width_um"], g["pitch_um"], g["offset_um"], g["nets"]; step = P / len(nets)
print("PG M9", W, P, O, nets)
def cls(x, w=0.32):
    k = round((x - O) / step); c = O + k * step
    d = abs(x - c); gap = d - W / 2 - w / 2
    return ("SHORT" if gap < 0 else "SPACE" if gap < 1.0 - 1e-9 else "OK"), round(gap, 3), nets[k % len(nets)], round(c, 3)
sets = {}
for name in ("r17_e20c", "r17_1d8b", "r18", "r19", "r19_on_33029005"):
    S = [s for s in json.load(open(f"{D}/{name}.json")) if s[0] == "M9"]
    res = [(s[1], s[2], s[3]) + cls(s[1]) for s in S]
    bad = sorted(r for r in res if r[3] != "OK")
    sets[name] = {(r[1], r[2]): r for r in res}   # key by span (y0,y1) identity
    print(name, "M9", len(S), "SHORT", sum(r[3] == "SHORT" for r in res), "SPACE", sum(r[3] == "SPACE" for r in res),
          "min_gap", min(r[4] for r in res))
    sets[name + "_x"] = sorted(round(s[1], 3) for s in S)
    sets[name + "_bad"] = [round(r[0], 3) for r in bad]
# identity: match straps r18/r17 -> r19 by sorted order (same count, same spans)
for ref in ("r17_e20c", "r17_1d8b", "r18"):
    a, b = sets[ref + "_x"], sets["r19_x"]
    moved = [(x, y) for x, y in zip(a, b) if abs(x - y) > 1e-6]
    mv = sorted(x for x, _ in moved); bad = sorted(sets[ref + "_bad"])
    print(ref, "->r19 moved", len(moved), "deltas", sorted(set(round(y - x, 3) for x, y in moved)),
          "| moved set == shorted set:", mv == bad, "(shorted %d)" % len(bad))
