"""DIEVIEW-QC-1113 read-only die render: floorplan / clock (forwarded hops) / route supply.  python3 -I dv_render.py SRC OUT"""
import sys, json, re, csv, collections
from pathlib import Path
SRC = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SRC / "tools/die_plan"))
import schema as S
import check as C
import site; sys.path.append(site.getusersitepackages())
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
pp = SRC / "physical/die_plan/qwen_compute/plan_of_record/zz_gates_ev2st.json"
raw = S.load(str(pp))
P = S.Plan(raw, pp.parent / "die_plan.json")
W, H = P.W, P.H
def fam(t): return re.sub(r"__(cl|pv).*", "", t)
def grp(t):
    f = fam(t)
    if f.startswith("cb"): return f[:3]
    if f.startswith("sl"):
        return re.sub(r"_v\d$", "", f[4:])
    return f
groups = sorted({grp(p["type"]) for p in P.parts.values()})
cm = plt.get_cmap("tab20")
gcol = {g: cm(i % 20) for i, g in enumerate(groups)}
geo = {}
for lid in P.lanes:
    try: geo[lid] = C.lane_geometry(P, lid)
    except Exception as e: pass
print("lanes", len(P.lanes), "geo", len(geo))
def base(ax, fc=None, label=True, fs=4.5, alpha=0.45):
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2, ec="black"))
    for c in P.die.get("channels", []):
        x0, y0, x1, y1 = P.channel_rect(c)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="grey", hatch="//", lw=0.4))
    for n, p in P.parts.items():
        x0, y0, x1, y1 = P.rect(n)
        col = fc(n, p) if fc else gcol[grp(p["type"])]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=col, alpha=alpha, ec="black", lw=0.3))
        if label:
            o = P.orient(n)
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, n + "\n" + fam(p["type"]) + ("" if o == "R0" else " " + o),
                    ha="center", va="center", fontsize=fs, zorder=6, clip_on=True)
    ax.set_aspect("equal"); ax.tick_params(labelsize=6)
def lanes(ax, col="teal", a=0.6):
    wmax = max(P.ports[P.lanes[l]["ports"][0]]["width"] for l in geo)
    segs, lws = [], []
    sx, sy = [], []
    for lid, (pts, regs, _) in geo.items():
        w = P.ports[P.lanes[lid]["ports"][0]]["width"]
        segs.append(pts); lws.append(0.3 + 2.2 * (w / wmax) ** 0.5)
        for q in regs[1:-1]: sx.append(q[0]); sy.append(q[1])
    ax.add_collection(LineCollection(segs, linewidths=lws, colors=col, alpha=a, zorder=3))
    ax.scatter(sx, sy, s=1.5, c="k", zorder=4, linewidths=0)
def save(fig, ax, name, title, views=None):
    ax.set_title(title, fontsize=9)
    ax.set_xlim(-0.01 * W, 1.01 * W); ax.set_ylim(-0.01 * H, 1.01 * H)
    fig.savefig(OUT / (name + ".png")); print(OUT / (name + ".png"))
    for vn, (xa, xb, ya, yb) in (views or {}).items():
        ax.set_xlim(xa, xb); ax.set_ylim(ya, yb)
        fig.savefig(OUT / (name + "_" + vn + ".png")); print(OUT / (name + "_" + vn + ".png"))
    plt.close(fig)
views = {"SW": (-100, 9500, -100, 7900), "W_mid": (-100, 9500, 7500, 16500), "C_low": (8500, 20500, -100, 9500),
         "C_mid": (9500, 21500, 8000, 17500), "E_low": (20500, 31400, -100, 9500), "NW": (-100, 11500, 15500, 25800)}
# ---- A floorplan + lanes
fig, ax = plt.subplots(figsize=(24, 20), dpi=110)
base(ax); lanes(ax)
root = P.clock.get("spine", {}).get("root_um")
if root: ax.plot([root[0]], [root[1]], marker="P", ms=12, color="crimson", zorder=7)
hs = [Rectangle((0, 0), 1, 1, fc=gcol[g], alpha=0.45, ec="k", lw=0.3) for g in groups]
ax.legend(hs, groups, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=7, frameon=False)
save(fig, ax, "A_floorplan", f"QC qwen_compute s28 head 736058c458ee: {len(P.parts)} parts / {len(P.types)} types, lanes teal (width ~ sqrt bits), stations black, spine root +",
     views)
# ---- B clock: taps, landing clock edges, forwarded over-reach
rows = [l.rstrip("\n").split("\t") for l in open(SRC / "resid/OPEN-FWDHOP.tsv") if not l.startswith("#")][1:]
byt = collections.defaultdict(list)
for r in rows: byt[r[0]].append(r)
nmax = max(len(v) for v in byt.values())
hot = plt.get_cmap("YlOrRd")
def fcB(n, p):
    k = len(byt.get(p["type"], ()))
    return hot(0.15 + 0.85 * k / nmax) if k else (0.9, 0.9, 0.9, 1)
fig, ax = plt.subplots(figsize=(24, 20), dpi=110)
base(ax, fc=fcB, label=True, fs=4, alpha=0.75)
tx, ty = [], []
tapxy = {}
for tn in P.types:
    try: tapxy[tn] = {n: (x, y) for n, x, y in S.tap_grid(P, tn)}
    except Exception as e: tapxy[tn] = {}
for n, p in P.parts.items():
    for (x, y) in tapxy[p["type"]].values():
        a = P.to_die(n, (x, y)); tx.append(a[0]); ty.append(a[1])
ax.scatter(tx, ty, s=1.2, c="purple", zorder=5, linewidths=0)
# over-reach lines: source tap -> pin (type frame bus window centre)
def bus_pt(tn, bus):
    t = P.types[tn]
    for b in t.get("buses", []) + t.get("infra_ports", []) if isinstance(t.get("infra_ports"), list) else t.get("buses", []):
        if b.get("name") == bus and b.get("face") and b.get("window_um"):
            w, h = t["outline_um"]; lo, hi = b["window_um"]; m = (lo + hi) / 2
            return {"E": (w, m), "W": (0, m), "N": (m, h), "S": (m, 0)}[b["face"]]
    return None
segs = []; miss = 0
for n, p in P.parts.items():
    for r in byt.get(p["type"], ()):
        tp = tapxy[p["type"]].get(r[2] if r[2] != "clk_t0" else "clk"); bp = bus_pt(p["type"], re.sub(r"^fclk_out_", "", r[1]))
        if tp and bp: segs.append([P.to_die(n, tp), P.to_die(n, bp)])
        else: miss += 1
print("fwd segs", len(segs), "miss", miss)
ax.add_collection(LineCollection(segs, linewidths=0.5, colors="red", alpha=0.6, zorder=6))
ce = []
for e in P.clock.get("landing_network", {}).get("edges", []):
    if e.get("kind") != "clock": continue
    try:
        a = P.rect(e["src"]["part"]); b = P.rect(e["dst"]["part"])
        ce.append([((a[0] + a[2]) / 2, (a[1] + a[3]) / 2), ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)])
    except Exception: pass
ax.add_collection(LineCollection(ce, linewidths=0.35, colors="blue", alpha=0.35, zorder=4))
if root: ax.plot([root[0]], [root[1]], marker="P", ms=12, color="crimson", zorder=7)
save(fig, ax, "B_clock_fwdhop", f"QC clock: taps (purple), landing clock edges centre-to-centre (blue, {len(ce)}), forwarded-clock source tap -> face pin over 405 um (red, {len(segs)} drawn / {miss} not locatable); fill = over-reach rows per type (max {nmax})",
     views)
# ---- C route supply
rs = {}
for r in csv.DictReader(open(SRC / "out_vf/rs/route_supply_qwen_compute.tsv"), delimiter="\t"):
    try: rs[r["type"]] = (float(r["p99_ratio"]), r["verdict"], r["worst_region"], float(r.get("cells") or 0))
    except Exception: pass
cmap = plt.get_cmap("RdYlGn_r")
def fcC(n, p):
    v = rs.get(p["type"])
    return cmap(min(1.0, v[0] / 1.6)) if v else (0.8, 0.8, 0.8, 1)
fig, ax = plt.subplots(figsize=(24, 20), dpi=110)
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2, ec="black"))
for n, p in P.parts.items():
    x0, y0, x1, y1 = P.rect(n); v = rs.get(p["type"])
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fcC(n, p), alpha=0.8, ec="black", lw=0.3))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, fam(p["type"]) + ("\n%.2f %s\n%dk" % (v[0], v[2], v[3] / 1000) if v else "\n?"), ha="center", va="center", fontsize=4.2, clip_on=True)
ax.set_aspect("equal"); lanes(ax, col="navy", a=0.35)
save(fig, ax, "C_route_supply", "QC route supply per type (plan estimate, out_vf 11-12): p99 demand/supply of worst region, green <0.8, red >=1.6; text = p99 region cells", views)
