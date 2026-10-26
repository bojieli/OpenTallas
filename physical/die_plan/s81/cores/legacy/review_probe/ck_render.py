"""S81-CORES/LEGACY post-CTS clock render: register CK arrival (TT, placement RC) map + clock buffers + pin->flop distances.
python3 ck_render.py KIT ck.csv placed.csv OUT.png OUT.json"""
import csv, json, sys, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
kit, ckf, plf, out, oj = sys.argv[1:6]
fz = json.load(open(f"{kit}/freeze.json")); W, H = fz["outline_um"]
ck = list(csv.DictReader(open(ckf)))
regs = [r for r in ck if r["kind"] in ("ff", "macro") and float(r["ck_ps"]) >= 0]
bufs = [r for r in ck if r["kind"] == "ckbuf"]
pl = list(csv.DictReader(open(plf)))
loc = {r["name"]: (float(r["x"]) + float(r["w"]) / 2, float(r["y"]) + float(r["h"]) / 2) for r in pl if r["kind"] != "pin"}
pr = [r for r in ck if r["kind"] == "pinreg"]
d = sorted(float(r["ck_ps"]) for r in pr if float(r["ck_ps"]) < 1e8)
far = sorted(((float(r["ck_ps"]), r["inst"]) for r in pr if float(r["ck_ps"]) < 1e8), reverse=True)[:8]
a = sorted(float(r["ck_ps"]) for r in regs if r["kind"] == "ff")
mac = [(r["inst"], float(r["ck_ps"])) for r in regs if r["kind"] == "macro"]
st = dict(kit=fz["kit"], regs=len(a), ck_min_ps=a[0] if a else None, ck_max_ps=a[-1] if a else None,
          ck_p50_ps=a[len(a) // 2] if a else None, ck_spread_ps=(a[-1] - a[0]) if a else None, ckbufs=len(bufs),
          macro_ck_ps=mac, pin_flop_um=dict(n=len(d), p50=d[len(d) // 2] if d else None, p90=d[int(len(d) * .9)] if d else None,
                                            max=d[-1] if d else None, over20=sum(x > 20 for x in d), unreg=sum(float(r["ck_ps"]) >= 1e8 for r in pr), worst=far))
fig, ax = plt.subplots(figsize=(12, 12 * H / W + 1), dpi=110)
ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1))
for r in pl:
    if r["kind"] == "macro":
        ax.add_patch(plt.Rectangle((float(r["x"]), float(r["y"])), float(r["w"]), float(r["h"]), fc="lightblue", ec="b", alpha=.5))
sc = ax.scatter([float(r["x"]) for r in regs if r["kind"] == "ff"], [float(r["y"]) for r in regs if r["kind"] == "ff"],
                c=[float(r["ck_ps"]) for r in regs if r["kind"] == "ff"], s=1.5, cmap="viridis")
ax.scatter([float(r["x"]) for r in bufs], [float(r["y"]) for r in bufs], s=8, marker="^", c="red", label=f"clk bufs {len(bufs)}")
for r in pl:
    if r["kind"] == "pin" and r["name"].split("[")[0] in ("clk", "ck", "rst_n", "rst", "rs"):
        ax.plot(float(r["x"]), float(r["y"]), "k*", ms=10)
plt.colorbar(sc, ax=ax, label="CK arrival TT ps (placement RC)")
ax.set_xlim(-2, W + 2); ax.set_ylim(-2, H + 2); ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=7)
ax.set_title(f"{fz['kit']} post-CTS: CK {st['ck_min_ps']:.0f}-{st['ck_max_ps']:.0f} ps (spread {st['ck_spread_ps']:.0f}), "
             f"pin->flop p90 {st['pin_flop_um']['p90']:.1f} max {st['pin_flop_um']['max']:.1f} um", fontsize=9)
fig.savefig(out, bbox_inches="tight"); json.dump(st, open(oj, "w"), indent=1)
print(json.dumps(st)[:600])
