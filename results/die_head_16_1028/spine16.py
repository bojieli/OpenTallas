#!/usr/bin/env python3
"""DIE-HEAD-16 (kit-local DIAGNOSTIC planner): hd_tile register clock as a plan-placed BUFx24 spine + local trees
(METHODOLOGY 12.13b / 12.16e local form). Inputs: sinks.txt (3_place.odb clk sinks), optional pad json from pass 1.
Outputs: plan16.json (trunk nodes, taps, model arrivals) and h16_plan.tcl (data for h16_spine.tcl), assign16.txt.
Deterministic: fixed trunk (plan geometry), k-means seeded from fixed grid bins, ties broken by name/index."""
import json, math, sys, collections

SINKS, OUT = sys.argv[1], sys.argv[2]
PAD = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}

# Hard cores (CHECKED probe of 3_place.odb) and the island row y 349.92-358.56 at the channel cross.
MACROS = [(17.292, 8.676, 336.972, 328.356), (371.556, 8.676, 691.236, 328.356),
          (17.292, 380.172, 336.972, 699.852), (371.556, 380.172, 691.236, 699.852),
          (216.012, 734.412, 501.132, 1019.532)]
# Trunk: name, x, y, parent. Channel x 354 (337-371), cross row y 368 (above the island row), strip y 717 (700-734),
# columns beside eB at x 110 / 598. Hops <= 140 um, every node a BUFx24 (slew <= ~100 ps by construction).
TRUNK_V1 = [("R", 354.0, 368.0, None),
         ("D1", 354.0, 232.0, "R"), ("D2", 354.0, 100.0, "D1"),
         ("U1", 354.0, 500.0, "R"), ("U2", 354.0, 625.0, "U1"), ("S0", 354.0, 717.0, "U2"),
         ("WL1", 226.0, 368.0, "R"), ("WL2", 96.0, 368.0, "WL1"),
         ("ER1", 482.0, 368.0, "R"), ("ER2", 612.0, 368.0, "ER1"),
         ("SL1", 230.0, 717.0, "S0"), ("SL2", 110.0, 717.0, "SL1"), ("CL1", 110.0, 845.0, "SL2"),
         ("SR1", 478.0, 717.0, "S0"), ("SR2", 598.0, 717.0, "SR1"), ("CR1", 598.0, 830.0, "SR2")]
# V2 (pass 2): one root driver per direction straight off the clk entry net (no shared root net), shortest paths to the
# upper columns beside eB (x 205 / 512 = the column edges next to eB, not their centres), hops 115-175 um.
TRUNK_V2 = [("R", 354.0, 368.0, None),
         ("RU", 356.0, 374.0, "CLK"), ("U1", 356.0, 545.0, "RU"), ("S0", 356.0, 717.0, "U1"),
         ("RD", 352.0, 340.0, "CLK"), ("D1", 354.0, 205.0, "RD"), ("D2", 354.0, 70.0, "D1"),
         ("RL", 340.0, 368.0, "CLK"), ("WL1", 200.0, 368.0, "RL"), ("WL2", 60.0, 368.0, "WL1"),
         ("RR", 368.0, 368.0, "CLK"), ("ER1", 510.0, 368.0, "RR"), ("ER2", 650.0, 368.0, "ER1"),
         ("SLa", 205.0, 717.0, "S0"), ("SLb", 80.0, 717.0, "SLa"), ("CLa", 205.0, 860.0, "SLa"), ("CLb", 120.0, 950.0, "CLa"),
         ("SRa", 512.0, 717.0, "S0"), ("SRb", 640.0, 717.0, "SRa"), ("CRa", 512.0, 860.0, "SRa")]
# V3 (pass 3): V2 local trunk for the channel / cross row / near strip, plus EXPRESS chains (names X*, no taps attach)
# from the entry to region hubs H* in the far upper regions; express hops 120-220 um, hubs feed taps by short stubs.
TRUNK_V3 = [("R", 354.0, 368.0, None),
         ("RU", 356.0, 374.0, "CLK"), ("U1", 356.0, 545.0, "RU"), ("S0", 356.0, 717.0, "U1"),
         ("RD", 352.0, 340.0, "CLK"), ("D1", 354.0, 205.0, "RD"), ("D2", 354.0, 70.0, "D1"),
         ("RL", 340.0, 368.0, "CLK"), ("WL1", 200.0, 368.0, "RL"), ("WL2", 60.0, 368.0, "WL1"),
         ("RR", 368.0, 368.0, "CLK"), ("ER1", 510.0, 368.0, "RR"), ("ER2", 650.0, 368.0, "ER1"),
         ("XU0", 349.0, 380.0, "CLK"), ("XU1", 349.0, 600.0, "XU0"), ("XU2", 345.0, 726.0, "XU1"),
         ("HL1", 180.0, 726.0, "XU2"), ("HL2", 190.0, 860.0, "HL1"), ("HL3", 150.0, 960.0, "HL2"), ("HL0", 60.0, 726.0, "HL1"),
         ("HR1", 560.0, 726.0, "XU2"), ("HR2", 560.0, 850.0, "HR1"), ("HR0", 660.0, 690.0, "HR1")]
import os
TRUNK = {"v1": TRUNK_V1, "v2": TRUNK_V2, "v3": TRUNK_V3}[os.environ.get("H16_TRUNK", "v1")]
ENTRY_PS = 35.0          # clk port -> root split (DIE-HEAD-15 measured)
HOP_PS = lambda d: 15.0 + 0.19 * d   # BUFx24 + repeated M7 (DIE-HEAD-15: 182 um hop = 49-50 ps)
LOCAL_PS = 120.0         # local tree estimate (radius <= ~120 um, 3-4 levels), replaced by pass-1 measurement
BUF4_PS = 22.0           # BUFx4 delay stage (DIE-HEAD-15 measured)
T_TT = 450.0

sinks = []
for l in open(SINKS):
    f = l.split()
    if f[0] == "clk" and f[3] == "CLK":
        sinks.append((f[1], float(f[4]), float(f[5])))
sinks.sort()

def inside(x, y):
    return any(a <= x <= c and b <= y <= d for a, b, c, d in MACROS)

# seeds: 118 x 115.2 bins with >= 250 sinks, at the bin's sink mean
bins = collections.defaultdict(list)
for n, x, y in sinks:
    bins[(int(x // 118), int(y // 115.2))].append((x, y))
seeds = [(sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in sorted(bins.items()) if len(v) >= 250]
RADIUS_UM = float(os.environ.get("H16_RADIUS", "150"))   # local tree radius cap (Manhattan, sink to tap centroid)

def kmeans(cent):
    for it in range(40):
        groups = [[] for _ in cent]
        for n, x, y in sinks:
            j = min(range(len(cent)), key=lambda i: (abs(cent[i][0] - x) + abs(cent[i][1] - y), i))
            groups[j].append((x, y))
        new = [(sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)) if g else c for g, c in zip(groups, cent)]
        if new == cent:
            break
        cent = new
    keep = [i for i, g in enumerate(groups) if g]
    return [cent[i] for i in keep], [groups[i] for i in keep]

cent, groups = kmeans(seeds[:])
for rnd in range(40):
    worst = None
    for c, g in zip(cent, groups):
        far = max(g, key=lambda p: (abs(p[0] - c[0]) + abs(p[1] - c[1]), p))
        r = abs(far[0] - c[0]) + abs(far[1] - c[1])
        if r > RADIUS_UM and (worst is None or r > worst[0]):
            worst = (r, far)
    if worst is None:
        break
    cent, groups = kmeans(cent + [worst[1]])
# merge clusters below 20 sinks into the nearest other cluster
while True:
    small = [i for i, g in enumerate(groups) if len(g) < 20]
    if not small or len(cent) == 1:
        break
    i = small[0]
    cent, groups = kmeans(cent[:i] + cent[i + 1:])

def snap_out(x, y):
    # tap driver site: the sink centroid, moved just outside a hard core if it falls inside one
    for a, b, c, d in MACROS:
        if a <= x <= c and b <= y <= d:
            opts = [(x - a + 2, a - 2, y), (c - x + 2, c + 2, y), (y - b + 2, x, b - 2), (d - y + 2, x, d + 2)]
            _, x, y = min(opts)
    return x, y

trunk = {t[0]: t for t in TRUNK}
arr = {}
for name, x, y, par in TRUNK:
    arr[name] = ENTRY_PS if par in (None, "CLK") else arr[par] + HOP_PS(abs(x - trunk[par][1]) + abs(y - trunk[par][2]) if par in trunk else 0)

taps, assign = [], {}
for i, (cx, cy) in enumerate(cent):
    tx, ty = snap_out(cx, cy)
    node = min([t for t in TRUNK if t[3] is not None and not t[0].startswith("X")], key=lambda t: (abs(t[1] - tx) + abs(t[2] - ty), t[0]))
    taps.append(dict(id=i, x=round(tx, 2), y=round(ty, 2), node=node[0]))
for n, x, y in sinks:
    j = min(range(len(taps)), key=lambda i: (abs(taps[i]["x"] - x) + abs(taps[i]["y"] - y), i))
    assign[n] = j
cnt = collections.Counter(assign.values())
for t in taps:
    pts = [(x, y) for n, x, y in sinks if assign[n] == t["id"]]
    t["sinks"] = cnt[t["id"]]
    t["radius_um"] = round(max(abs(x - t["x"]) + abs(y - t["y"]) for x, y in pts), 1)
    stub = abs(trunk[t["node"]][1] - t["x"]) + abs(trunk[t["node"]][2] - t["y"])
    t["stub_um"] = round(stub, 1)
    t["model_ps"] = round(arr[t["node"]] + HOP_PS(stub) + LOCAL_PS, 1)
    t["pad"] = int(PAD.get(str(t["id"]), 0))
json.dump(dict(trunk=TRUNK, trunk_arr_ps=arr, taps=taps, sinks=len(sinks), trunk_form=os.environ.get("H16_TRUNK", "v1"), radius_um=RADIUS_UM, model=dict(entry=ENTRY_PS, hop="15+0.19*um",
          local=LOCAL_PS, buf4=BUF4_PS, T=T_TT)), open(OUT + "/plan16.json", "w"), indent=1)
with open(OUT + "/assign16.txt", "w") as f:
    for n in sorted(assign):
        f.write(f"{n} {assign[n]}\n")
with open(OUT + "/h16_plan.tcl", "w") as f:
    f.write("# GENERATED by spine16.py (DIE-HEAD-16 DIAGNOSTIC). trunk: name x y parent; taps: id x y node pad\n")
    f.write("set h16_trunk {\n" + "".join(f"  {{{n} {x} {y} {p or '-'}}}\n" for n, x, y, p in TRUNK) + "}\n")
    f.write("set h16_taps {\n" + "".join(f"  {{{t['id']} {t['x']} {t['y']} {t['node']} {t['pad']}}}\n" for t in taps) + "}\n")
print(f"sinks {len(sinks)} taps {len(taps)} max_sinks {max(cnt.values())} min_sinks {min(cnt.values())}")
for t in taps:
    print(f"tap {t['id']:2d} ({t['x']:6.1f},{t['y']:6.1f}) node {t['node']:4s} sinks {t['sinks']:5d} r {t['radius_um']:6.1f} stub {t['stub_um']:6.1f} model {t['model_ps']:6.1f} pad {t['pad']}")
print("trunk arrivals (model ps):", {k: round(v, 1) for k, v in arr.items()})
