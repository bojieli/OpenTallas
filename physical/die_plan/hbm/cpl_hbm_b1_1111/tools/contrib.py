"""station-net RUDY contributors at a point (same fan grouping as route_supply). usage: contrib.py TYPE.json X Y [N]"""
import json, sys
from collections import defaultdict
T = json.load(open(sys.argv[1])); X, Y = float(sys.argv[2]), float(sys.argv[3]); N = int(sys.argv[4]) if len(sys.argv) > 4 else 12
b = 10.8; fan = defaultdict(list); out = []
for s in T.get("internal_stations", []):
    pts = [tuple(s["from_um"])] + [tuple(r) for r in s.get("regs_um", [])] + [tuple(s["to_um"])]
    fan[(str(s.get("launch")), tuple(round(v, 1) for v in s["from_um"]))].append((pts, s.get("bits", 1), s))
def add(pts, n, tag):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, y0 = min(xs), min(ys); w, h = max(max(xs) - x0, b), max(max(ys) - y0, b)
    if x0 <= X <= x0 + w and y0 <= Y <= y0 + h:
        aw, ah = max(xs) - x0, max(ys) - min(ys)
        out.append((n * aw / (w * h) * b, n * ah / (w * h) * b, tag, round(x0), round(y0), round(w), round(h)))
for (la, fr), lst in fan.items():
    bits = max(n for _, n, _ in lst)
    add([lst[0][0][0]] + [p[1] for p, _, _ in lst], bits, f"FAN {la[-30:]} x{len(lst)}")
    for pts, n, s in lst:
        for a, c in zip(pts[1:], pts[2:]): add([a, c], n, f"hop {s['conn'][-14:]}->{s['capture'][-26:]}")
for f in T.get("ft_slots", []):
    pass
tot = sum(o[0] for o in out); print("station H tracks/um-row at point: %.1f" % tot)
for o in sorted(out, reverse=True)[:N]: print("H %.1f V %.1f %s box %s,%s %sx%s" % o)
