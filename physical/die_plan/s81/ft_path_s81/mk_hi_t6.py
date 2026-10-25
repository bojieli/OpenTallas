"""hi t6 (svc_15) FT re-plan: ft1/ft2 split into 9+9 contiguous 123-bit groups whose vertical legs DRIFT east in the
row gaps (diamond: +d/4 per gap for 4 gaps, back over the next 3) so the 2208-bit descent and its mid-hop repeaters
use columns 1-5 / channels x~200,372,545,718,890 instead of only x~200,372; ft0/ft3 jog legs keep a real band (no
lane collapse). Depths: ft1 9, ft2 11 (= the priced trial +1 each), all others unchanged."""
import json, sys
sys.path.insert(0, "tools/die_plan"); sys.path.insert(0, ".")
import numpy as np, schema as S
from gen_phys import type_pins
plan, out_plan, out_routes = sys.argv[1:4]
raw = json.load(open(plan)); m = S.Plan(raw); tn = "svc_hi_dsdv_svc_rs__t6"; ty = m.types[tn]
for s in ty["ft_slots"]:
    if s["name"] == "ft1": s["stations"] = 9
    if s["name"] == "ft2": s["stations"] = 11
json.dump(raw, open(out_plan, "w"))
pins = {(bn, i): (x, y) for bn, i, _, x, y, _ in type_pins(m, tn)}
GAPS = [2142.8, 1866.2, 1589.8, 1313.3, 1131.8, 855.4, 578.9, 302.4]
SPLIT = 123
groups = []
for name in ("ft1", "ft2"):
    s = [s for s in ty["ft_slots"] if s["name"] == name][0]; wd = s["width"] + 1
    a = np.array([pins[(name + "_i", i)] for i in range(wd)]); b = np.array([pins[(name + "_o", i)] for i in range(wd)])
    for st in range(0, wd, SPLIT):
        groups.append((name, a[st:st + SPLIT].mean(0), b[st:st + SPLIT].mean(0)))
order = sorted(range(len(groups)), key=lambda i: groups[i][1][0])
X0, X1 = groups[order[0]][1][0], 884.0
routes = {"ft1": [], "ft2": []}
for rank, gi in enumerate(order):
    name, ca, cb = groups[gi]
    x = float(ca[0]); X = X0 + rank * (X1 - X0) / (len(groups) - 1); d = max(0.0, X - x)
    up = [x + d * k / 4 for k in range(1, 5)]          # after gaps 0..3
    dn = [x + d * k / 3 for k in (2, 1, 0)]            # after gaps 4..6
    xs = up + dn
    wp = []
    cur = x
    for gy, nx in zip(GAPS[:7], xs):
        wp += [[round(cur, 2), gy], [round(nx, 2), gy]]
        cur = nx
    if name == "ft2":
        wp += [[round(cur, 2), GAPS[7]]]
    wp += [[round(cur, 2), round(float(cb[1]), 2)]]
    routes[name].append((gi, [wp, 26.0]))
rj = {"_order": {tn: ["ft1", "ft2", "ft0", "ft3"]},
      f"{tn}/ft1": [r for _, r in sorted(routes["ft1"])], f"{tn}/ft2": [r for _, r in sorted(routes["ft2"])],
      f"{tn}/ft0": [[[[36.0, 1262.0], [1408.4, 1262.0]], 40.0]],
      f"{tn}/ft3": [[[[666.3, 1205.0], [1353.4, 1205.0]], 12.0]]}
json.dump(rj, open(out_routes, "w"), indent=0)
for name in routes: print(name, [round(r[1][0][7][0]) for r in sorted(routes[name])])
