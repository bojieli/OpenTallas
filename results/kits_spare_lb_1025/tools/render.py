"""KITS-SPARE/LB post-CTS render: density | TT CK arrival | FF CK arrival (placement RC setRC_rcx), pin->reg, reset entry.
python3 render.py REVDIR FACEFLOPS.txt W H TITLE OUT.png OUT.json [BOUND_TT BOUND_FF]"""
import csv, json, sys, math, re, statistics as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
rv, ffl, W, H, title, out, oj = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], sys.argv[6], sys.argv[7]
btt, bff = (float(sys.argv[8]), float(sys.argv[9])) if len(sys.argv) > 9 else (None, None)
pl = list(csv.DictReader(open(f"{rv}/placed.csv")))
pins = {r["name"]: (float(r["x"]), float(r["y"])) for r in pl if r["kind"] == "pin"}
def ck(c):
    d = {}
    for r in csv.DictReader(open(f"{rv}/ck_{c}.csv")):
        try: d[r["name"].replace("\\", "")] = (float(r["x"]), float(r["y"]), float(r["ck"]))
        except ValueError: pass
    return d
CT, CF = ck("tt"), ck("ff")
pr = []
for ln in open(ffl):
    f = ln.rstrip("\n").split("\t")
    if len(f) < 5: continue
    inst, port = f[0].replace("\\", ""), f[4]
    if port not in pins or inst not in CT: continue
    px, py = pins[port]; x, y, _ = CT[inst]
    pr.append(dict(inst=inst, port=port, face=f[1], dist=abs(x - px) + abs(y - py)))
dist = sorted(p["dist"] for p in pr)
far = [p for p in pr if p["dist"] > 20]
rst = [(n, v) for n, v in CT.items() if re.search(r"u_rst.*sync_q", n)]
rpin = pins.get("rst_n")
def grp(C, names):
    v = [C[n][2] for n in names if n in C]
    return dict(n=len(v), mean=round(st.mean(v), 1), min=round(min(v), 1), max=round(max(v), 1)) if v else None
prn = {p["inst"] for p in pr}
faces = sorted({p["face"] for p in pr})
stats = dict(title=title, outline_um=[W, H], flops=len(CT), pin_regs=len(pr),
             pin_reg_um=dict(p50=dist[len(dist)//2], p90=dist[int(len(dist)*.9)], max=dist[-1], over20=len(far)) if dist else None,
             far=[(p["port"], round(p["dist"], 1)) for p in sorted(far, key=lambda p: -p["dist"])[:15]],
             rst_entry=[(n, round(abs(CT[n][0]-rpin[0]) + abs(CT[n][1]-rpin[1]), 1)) for n, _ in rst] if rpin else None,
             bound=dict(tt=btt, ff=bff))
for c, C in (("tt", CT), ("ff", CF)):
    stats[f"ck_{c}"] = dict(all=grp(C, C.keys()), pin_regs=grp(C, prn), core=grp(C, [n for n in C if n not in prn]),
                           faces={fc: grp(C, [p["inst"] for p in pr if p["face"] == fc]) for fc in faces})
fig, axs = plt.subplots(1, 3, figsize=(18, max(5, 6 * H / W) + 1), dpi=100)
# density (std cell area per 5 um bin)
B = 5.0; nx, ny = int(math.ceil(W / B)), int(math.ceil(H / B)); g = [[0.0] * nx for _ in range(ny)]
for r in pl:
    if r["kind"] in ("std", "ff", "buf"):
        x, y, w, h = float(r["x"]), float(r["y"]), float(r["w"]), float(r["h"])
        i, j = min(nx - 1, int((x + w / 2) / B)), min(ny - 1, int((y + h / 2) / B)); g[j][i] += w * h / (B * B)
im = axs[0].imshow(g, origin="lower", extent=(0, W, 0, H), cmap="magma", vmin=0, vmax=1)
plt.colorbar(im, ax=axs[0], label="cell area / bin (5 um)")
stats["max_bin"] = round(max(max(row) for row in g), 3)
for ax, C, c in ((axs[1], CT, "TT"), (axs[2], CF, "FF")):
    xs = [v[0] for v in C.values()]; ys = [v[1] for v in C.values()]; cs = [v[2] for v in C.values()]
    sc = ax.scatter(xs, ys, c=cs, s=0.3, cmap="viridis"); plt.colorbar(sc, ax=ax, label=f"{c} CK arrival ps")
    s = stats[f"ck_{c.lower()}"]
    ax.set_title(f"{c} CK: all {s['all']['min']}-{s['all']['max']}\npin-reg mean {s['pin_regs']['mean']} | core mean {s['core']['mean']}"
                 + (f" | bound {btt if c == 'TT' else bff}" if btt else ""), fontsize=8)
for ax in axs:
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1))
    ax.scatter([pins[p["port"]][0] for p in far], [pins[p["port"]][1] for p in far], s=30, marker="x", c="magenta")
    for nm in ("clk", "rst_n"):
        if nm in pins: ax.plot(*pins[nm], "r*" if nm == "clk" else "c*", ms=12)
    for n, _ in rst: ax.plot(CT[n][0], CT[n][1], "co", ms=5, mfc="none")
    ax.set_xlim(-3, W + 3); ax.set_ylim(-3, H + 3); ax.set_aspect("equal")
axs[0].set_title(f"{title} density max {stats['max_bin']}\npin->reg p90 {stats['pin_reg_um']['p90']:.1f} max {stats['pin_reg_um']['max']:.1f} (>20: {len(far)} x) | rst sync o, clk*/rst*", fontsize=8)
fig.savefig(out, bbox_inches="tight"); json.dump(stats, open(oj, "w"), indent=1)
print(json.dumps(stats)[:3000])
