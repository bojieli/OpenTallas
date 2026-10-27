#!/usr/bin/env python3
"""CLOCK-KV-R25: die-frame check + render of the island ft ports.  For EVERY instance of every core_islands module:
map its pins_file ft ports through the core transform to the die and check that (1) the in-port lies left / out-port
right of the die body of the pushdown group in the core frame and on its row, (2) the die cells of that group
(m24c place.json) are exactly the core_islands rects (1 nm).  Renders core-frame views + die zooms."""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, sys.argv[4])
import schema as S
import die_clock_mesh as DCM
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plan, mesh_dir, outdir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
outdir.mkdir(exist_ok=True)
raw = json.loads(plan.read_text()); raw.pop("plan_deltas", None)
P = S.Plan(raw)
ci = raw["clock"]["mesh"]["core_islands"]
M = json.loads((mesh_dir / "mesh.json").read_text())
C = json.loads((mesh_dir / "place.json").read_text())
cache = {}
def pins(f):
    if f not in cache:
        cache[f] = json.loads((plan.parent / f).read_text())
    return cache[f]
def grp(name):
    return [name] if name in C else [k for k in C if k.startswith(name + "_") and k[len(name) + 1:].isdigit()]
bad, n_inst, n_ports = [], collections.Counter(), 0
by_core = collections.defaultdict(list)
for r in M["pushdown"]:
    by_core[r["core"]].append(r)
examples = {}
for key, recs in by_core.items():
    part, inst = key.split("/", 1)
    core = next(c for c in P.ptype(part)["hard_cores"] if c["inst"] == inst)
    mod = core["module"]
    if mod not in ci:
        continue
    d = pins(core["pins_file"])
    arcs = d["island_ft"]["arcs"]
    pp = {p["name"]: p for p in d["pins"]}
    n_inst[mod] += 1
    for r in recs:
        cells = grp(r["name"])
        rects = []
        for n in cells:
            c = C[n]; w = DCM.cell_width(c)
            a = DCM.core_frame(P, part, core, (c["x"], c["y"])); b = DCM.core_frame(P, part, core, (c["x"] + w, c["y"] + 0.27))
            rects.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
        bb = (min(q[0] for q in rects), min(q[1] for q in rects), max(q[2] for q in rects), max(q[3] for q in rects))
        arc = [a_ for a_ in arcs if max(abs(u - v) for u, v in zip(a_["rect_um"], bb)) < 1e-3]
        if len(arc) != 1:
            bad.append((key, r["name"], "no arc for body", [round(v, 3) for v in bb]))
            continue
        pi, po = pp[arc[0]["source"]], pp[arc[0]["sink"]]
        n_ports += 2
        ok = (pi["x"] < bb[0] - 1.0 and po["x"] > bb[2] + 1.0 and bb[1] <= pi["y"] <= bb[3] and bb[1] <= po["y"] <= bb[3]
              and pi["layer"] == po["layer"] == "M5")
        if not ok:
            bad.append((key, r["name"], "port placement", pi, po, bb))
        ex = examples.setdefault((mod, core["pins_file"], core.get("orient", "R0")), (part, core))
# render core frame views
for mod in ci:
    files = sorted({f for (m, f, o) in examples if m == mod})
    fig, axs = plt.subplots(1, len(files), figsize=(7 * len(files), 6), squeeze=False)
    for ax, f in zip(axs[0], files):
        d = pins(f)
        w, h = (float(v) for v in d["frame"].split("outline ")[1].split(" x "))
        ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.2))
        cx, cy = (round(w / 2 / 4.32) * 4.32, round(h / 2 / 4.32) * 4.32)
        ax.add_patch(Rectangle((cx - 4.32, cy - 4.32), 8.64, 8.64, fc="#ffe9a8", ec="orange", lw=0.8))
        xs = [p["x"] for p in d["pins"] if not p["name"].startswith("ft_ck")]
        ys = [p["y"] for p in d["pins"] if not p["name"].startswith("ft_ck")]
        ax.scatter(xs, ys, s=0.3, c="#999")
        for p in d["pins"]:
            if "rst" in p["name"] or "clk" in p["name"] or p["name"] in ("ck[0]",):
                ax.plot(p["x"], p["y"], "s", ms=3, c="purple")
        for a in d["island_ft"]["arcs"]:
            r = a["rect_um"]
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], max(r[3] - r[1], 1.5), fc="green", ec="green"))
            for nm, col in ((a["source"], "blue"), (a["sink"], "red")):
                p = next(q for q in d["pins"] if q["name"] == nm)
                ax.plot(p["x"], p["y"], "o", ms=5, c=col)
                ax.annotate(nm, (p["x"], p["y"]), fontsize=6, xytext=(2, 4), textcoords="offset points")
        ax.set_xlim(-5, w + 5); ax.set_ylim(-5, h + 5); ax.set_aspect("equal")
        ax.set_title(f"{mod}\n{f} (green=island cells, blue=ft_ck_i, red=ft_ck_o, purple=clk/rst)", fontsize=7)
    fig.tight_layout(); fig.savefig(outdir / f"core_{mod}.png", dpi=130); plt.close(fig)
# die zoom: one instance per (module, pins_file, orient): die cells + mapped ports
items = sorted(examples.items(), key=str)
fig, axs = plt.subplots(3, 6, figsize=(24, 12)); axs = axs.ravel()
for ax, ((mod, f, o), (part, core)) in zip(axs, items):
    d = pins(f); pp = {p["name"]: p for p in d["pins"]}
    key = f"{part}/{core['inst']}"
    for r in by_core[key][:1]:
        cells = grp(r["name"])
        xs = []
        for n in cells:
            c = C[n]; w = DCM.cell_width(c)
            ax.add_patch(Rectangle((c["x"], c["y"]), w, 0.27, fc="green", ec="k", lw=0.3)); xs.append(c["x"])
        a = DCM.core_frame(P, part, core, (C[cells[0]]["x"] + 0.1, C[cells[0]]["y"] + 0.1))
        arc = min(d["island_ft"]["arcs"], key=lambda q: abs(q["rect_um"][0] - a[0]) + abs(q["rect_um"][1] - a[1]))
        for nm, col in ((arc["source"], "blue"), (arc["sink"], "red")):
            p = pp[nm]; X, Y = DCM.core_frame(P, part, core, (p["x"], p["y"]), inverse=True)
            ax.add_patch(Rectangle((X - 0.024, Y - 0.24), 0.048, 0.48, fc=col)); ax.annotate(nm, (X, Y), fontsize=6)
        x0 = min(xs)
        ax.set_xlim(x0 - 4, x0 + 8); ax.set_ylim(C[cells[0]]["y"] - 2, C[cells[0]]["y"] + 2.3); ax.set_aspect("equal")
        ax.set_title(f"{mod} {Path(f).name}\n{o} {key} {r['name']}", fontsize=6)
fig.tight_layout(); fig.savefig(outdir / "die_zoom.png", dpi=120); plt.close(fig)
res = dict(instances=dict(n_inst), ports_checked=n_ports, bad=len(bad), bad_examples=[str(b) for b in bad[:10]],
           views=sorted(f"{m}|{f}|{o}" for m, f, o in examples))
(outdir / "verify.json").write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(res, indent=1))
