"""DIE-HBM-3 C20f render: (a) root W / NW_hub E shared face windows after the L12s insert + ripple, with the root
L12s_o internal station routes; (b) NW_b101 L12x1 5-station route; (c) q_hub_nw vms_glue grown cores + moved
neighbours.  usage: render_c20f.py C20F_DIR C20E_DIR"""
import json, sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D, E = sys.argv[1:3]
raw = json.load(open(D + "/die_plan.json")); T = raw["partition_types"]; parts = {p["name"]: p for p in raw["partitions"]}
old = json.load(open(E + "/die_plan.json")); TO = old["partition_types"]
fig, ax = plt.subplots(1, 3, figsize=(24, 11))
# (a) shared face
a = ax[0]; R = parts["root"]; rx, ry = R["origin_um"]; H = parts["NW_hub"]
a.add_patch(Rectangle((rx, ry), 1684.8, T["root"]["outline_um"][1], fc="#f4f4ff", ec="b"))
a.add_patch(Rectangle((rx - 1200, H["origin_um"][1]), 1200, T["q_hub_nw"]["outline_um"][1], fc="#f4fff4", ec="g"))
for c in T["root"]["hard_cores"]:
    x, y = c["origin_um"]; w, h = c["outline_um"]
    if y < 5600: a.add_patch(Rectangle((rx + x, ry + y), w, h, fc="#ddd", ec="k", lw=.4))
oldw = {p["id"]: p["window_um"] for p in old["ports"] if p.get("window_um")}
for p in raw["ports"]:
    if p.get("window_um") and {p["src"]["part"], p["dst"]["part"]} == {"root", "NW_hub"}:
        w = p["window_um"]; new = p["id"] == "L12s_0"
        a.add_patch(Rectangle((rx - 40, w[0]), 80, w[1] - w[0], fc="r" if new else "c", alpha=.7, ec="k", lw=.3))
        o = oldw.get(p["id"])
        if o and o != w: a.add_patch(Rectangle((rx - 120, o[0]), 60, o[1] - o[0], fc="none", ec="gray", ls="--"))
        a.text(rx + 50, (w[0] + w[1]) / 2, f"{p['id']} {p['width']}b", fontsize=7, va="center", color="r" if new else "k")
for e in T["root"]["internal_stations"]:
    if e.get("conn") == "bus:L12s_o":
        pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
        a.plot([rx + q[0] for q in pts], [ry + q[1] for q in pts], "r-o", ms=3, lw=1)
for e in T["root"]["internal_stations"]:
    if e.get("conn") == "bus:L12_o":
        pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
        a.plot([rx + q[0] for q in pts], [ry + q[1] for q in pts], "b-o", ms=3, lw=1)
a.set_xlim(rx - 1250, rx + 1750); a.set_ylim(ry, ry + 5600); a.set_aspect("equal")
a.set_title("root W | NW_hub E: windows (cyan, dashed = C20e position), L12s_0 red;\nred = root L12s_o station routes, blue = L12_o routes", fontsize=9)
# (b) NW_b101
a = ax[1]; p = parts["NW_b101"]; tb = T[p["type"]]; x0, y0 = p["origin_um"]; W, Hh = tb["outline_um"]
a.add_patch(Rectangle((x0, y0), W, Hh, fc="#eef", ec="b"))
for c in tb.get("hard_cores", []):
    x, y = c["origin_um"]; w, h = c["outline_um"]; a.add_patch(Rectangle((x0 + x, y0 + y), w, h, fc="#ddd", ec="k", lw=.4))
pw = {q["id"]: q for q in raw["ports"]}
wi = pw["L12_0"]["window_um"]; wo = pw["L12_1"]["window_um"]
a.add_patch(Rectangle((x0 + W - 10, wi[0]), 20, wi[1] - wi[0], fc="r", alpha=.6)); a.add_patch(Rectangle((wo[0], y0 + Hh - 10), wo[1] - wo[0], 20, fc="r", alpha=.6))
s = next(s for s in tb["ft_slots"] if s["name"] == "L12x1"); so = next(s for s in TO[p["type"]]["ft_slots"] if s["name"] == "L12x1")
pts = [[W, (wi[0] + wi[1]) / 2 - y0]] + s["regs_um"] + [[(wo[0] + wo[1]) / 2 - x0, Hh]]
a.plot([x0 + q[0] for q in pts], [y0 + q[1] for q in pts], "r-o", ms=5)
for q in so["regs_um"]: a.plot(x0 + q[0], y0 + q[1], "kx", ms=7)
a.set_xlim(x0 - 60, x0 + W + 60); a.set_ylim(y0 - 30, y0 + Hh + 60); a.set_aspect("equal")
a.set_title("NW_b101 L12x1 (1980 b): red = C20f 5 stations + E-in / N-out windows; x = C20e 4 stations", fontsize=9)
# (c) q_hub_nw vms + neighbours
a = ax[2]; th = T["q_hub_nw"]; tho = {c["inst"]: c for c in TO["q_hub_nw"]["hard_cores"]}
for c in th["hard_cores"]:
    x, y = c["origin_um"]; w, h = c["outline_um"]
    if not (1800 < x < 7800 and y < 3600): continue
    o = tho[c["inst"]]; mv = o["origin_um"] != c["origin_um"] or o["outline_um"] != c["outline_um"]
    fc = "#f99" if "vms_Q" in c["inst"] else ("#fd8" if mv else "#ddd")
    a.add_patch(Rectangle((x, y), w, h, fc=fc, ec="k", lw=.4))
    if mv: a.add_patch(Rectangle(tuple(o["origin_um"]), *o["outline_um"], fc="none", ec="gray", ls="--", lw=.6))
    if "vms_Q" in c["inst"]: a.text(x + w / 2, y + h / 2, c["inst"] + f"\n{w:.1f}x{h:.1f}", fontsize=7, ha="center")
a.set_xlim(1800, 7800); a.set_ylim(0, 3600); a.set_aspect("equal")
a.set_title("q_hub_nw: vms_glue grown (red), moved neighbours (orange, dashed = C20e)", fontsize=9)
plt.tight_layout(); plt.savefig(D + "/c20f_render.png", dpi=90)
