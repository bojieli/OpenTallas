#!/usr/bin/env python3
"""OSS-CLOCK-2: QC slice -> opentools.mscts trunk spec (adapter; the tool itself stays generic).

    qc_slice_spec.py PLAN.json.gz REGIONS.json ROWS.json TOOLS_DIE_PLAN_DIR SLICE OUT.json

sinks     = the die-tree clock taps of every partition of the slice region, die frame (schema.Plan.to_die): the R4 tap
            grid (schema.tap_grid, insertion = common latency schema.common_latency_ps 250 TT / 202.5 FF) + the merged
            EARLY core taps (schema.core_taps, insertion = schema.core_tap_insertion_ps, FF absent -> 0.81 x TT)
crossings = REAL slice traffic: every plan port with both partitions in the slice (the same port list
            tools/die_plan/locality.py load_plan/traffic use), mapped to the launch / capture tap of each partition that is
            nearest the other partition (bits summed per tap pair)
keepouts  = die_trial.SiteMap(P).forb (hard cores + 2.16-um halo, PHY domains) intersecting the slice
trunk     = the INFRA-FIRST-QC-R35 reservation (claude/qc-infra-r35-1027@c2b1eb75be qc_slice_rows.json): slice entry at
            the TOP tap (spine x, root row), bisection node rows L1..L3 on the spine pair-cols, leg rows (L4) at the
            strip centres, legs to the strip centre x (cb); leaves = leg ends, rect = the strip
"""
import collections
import re
import gzip
import json
import sys
from pathlib import Path

plan, regp, rowsp, tools, SL, outp = sys.argv[1:7]
sys.path.insert(0, tools)
import schema as S  # noqa: E402
import die_trial as DT  # noqa: E402
import locality as LO  # noqa: E402

raw = json.load(gzip.open(plan)) if plan.endswith(".gz") else json.load(open(plan))
P = S.Plan(raw, Path(plan))
R = json.load(open(regp))["part_region"]
rows = json.load(open(rowsp))
sl = next(s for s in rows["slices"] if s["slice"] == SL)
reg = sl["region"]
parts = [p for p in raw["partitions"] if R[p["name"]] == reg]
pn = {p["name"] for p in parts}
sinks, tap_of = [], collections.defaultdict(list)
for p in parts:
    t = P.ptype(p["name"])
    # the die tree reaches the partition's R4 tap grid (schema.tap_grid: THE method on every die, CP1 r8; the
    # partition CTS below each grid tap = the common latency) + the merged EARLY core taps (schema.core_taps)
    com = dict(insertion_ps=S.common_latency_ps(P, "TT"), insertion_ff_ps=S.common_latency_ps(P, "FF"))
    tl = [(port, (x, y), com, "grid") for port, x, y in S.tap_grid(P, p["type"])]
    tl += [(f"{port}:{tp['name']}", (x, y), tp, "core") for port, x, y, tp in S.core_taps(P, p["type"])]
    for tn, xy0, tp, kind in tl:
        xy = P.to_die(p["name"], xy0)
        nm = re.sub(r"[^A-Za-z0-9_]", "_", f"{p['name']}__{tn.split(':')[-1]}")       # netlist-safe
        ins = {"TT": S.core_tap_insertion_ps(tp, "TT"), "FF": S.core_tap_insertion_ps(tp, "FF")}
        sinks.append(dict(name=nm, xy=[round(xy[0], 3), round(xy[1], 3)], insertion_ps=ins, part=p["name"], kind=kind))
        tap_of[p["name"]].append(sinks[-1])
D = LO.load_plan(raw)
xing = collections.Counter()
outside = collections.Counter()
for q in D["ports"]:
    a, b = q["src"], q["dst"]
    if a in pn and b in pn:
        ra, rb = D["parts"][a]["rect"], D["parts"][b]["rect"]

        def near(part, r):
            def dist(s):
                x, y = s["xy"]
                return max(r[0] - x, 0, x - r[2]) + max(r[1] - y, 0, y - r[3])
            return min(tap_of[part], key=dist)["name"] if tap_of[part] else None
        sa, sb = near(a, rb), near(b, ra)
        if sa and sb and sa != sb:
            xing[(sa, sb)] += q["width"]
    elif (a in pn) != (b in pn):
        outside[R.get(b if a in pn else a)] += q["width"]
site = DT.SiteMap(P)
x0, x1 = sl["x_range"]
H = float(raw["die"]["outline_um"][1])
keep = [list(map(lambda v: round(v, 3), r[:4])) for r in site.forb if r[0] < x1 and r[2] > x0]
sx = sl["spine_x"]
nrow = {k: [r["y"] for r in v] for k, v in sl["node_rows"].items()}
ry = sl["root"]["y"]
nodes = [dict(id="L0", xy=[sx, ry], parent=None)]
prev = [("L0", ry)]
for lv in ("L1", "L2", "L3"):
    cur = []
    for y in nrow[lv]:
        par = min(prev, key=lambda p: abs(p[1] - y))[0]
        nodes.append(dict(id=f"{lv}_{y:.0f}", xy=[sx, y], parent=par))
        cur.append((nodes[-1]["id"], y))
    prev = cur
strip_h = H / len(sl["leg_rows"])
for lg in sl["leg_rows"]:
    y = lg["y"]
    par = min(prev, key=lambda p: abs(p[1] - y))[0]
    nodes.append(dict(id=f"L4_{lg['strip']}", xy=[sx, y], parent=par))
    nodes.append(dict(id=f"leg_{lg['strip']}", xy=[lg["x"][1], y], parent=f"L4_{lg['strip']}",
                      rect=[x0, lg["strip"] * strip_h, x1, (lg["strip"] + 1) * strip_h]))
spec = dict(name=f"qc_{SL}_{reg}_r35", period_ps=float(raw["die"]["period_ps"]), entry=[sx, ry],
            note=__doc__.strip().splitlines()[0], slice=sl["slice"], region=reg, x_range=[x0, x1],
            sinks=sinks, crossings=[[a, b, w] for (a, b), w in sorted(xing.items())],
            keepouts=keep, trunk=dict(entry=[sx, ry], nodes=nodes),
            traffic=dict(intra_bits=sum(xing.values()), intra_pairs=len(xing), ports_in_slice=sum(1 for q in D["ports"] if q["src"] in pn and q["dst"] in pn),
                         cross_slice_bits=dict(outside)))
Path(outp).write_text(json.dumps(spec, indent=0) + "\n")
print(json.dumps(dict(slice=SL, region=reg, parts=len(parts), sinks=len(sinks), crossings=len(xing), bits=sum(xing.values()),
                      keepouts=len(keep), trunk_nodes=len(nodes), cross_slice_bits=dict(outside))))
