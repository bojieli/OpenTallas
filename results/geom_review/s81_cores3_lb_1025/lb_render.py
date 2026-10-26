"""S81-CORES3/LB post-CTS render: FF CK arrival map (placement RC probe; shape/spread only -- absolute I from the CTS log),
clock buffers, macros + macro CK, pin->reg distance (pinreg rows) with >20 um pins marked.
python3 lb_render.py KIT ck.csv placed.csv OUT.png OUT.json TOOL_I_TXT"""
import csv, json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
kit, ckf, plf, out, oj, tooli = sys.argv[1:7]
fz = json.load(open(f"{kit}/freeze.json")); W, H = fz["outline_um"]
ck = list(csv.DictReader(open(ckf)))
regs = [r for r in ck if r["kind"] == "ff" and float(r["ck_ps"]) >= 0]
mac = [r for r in ck if r["kind"] == "macro"]
bufs = [r for r in ck if r["kind"] == "ckbuf"]
pr = [r for r in ck if r["kind"] == "pinreg" and float(r["ck_ps"]) < 1e8]
d = sorted(float(r["ck_ps"]) for r in pr)
a = sorted(float(r["ck_ps"]) for r in regs)
pl = list(csv.DictReader(open(plf)))
macs = [r for r in pl if r["kind"] == "macro"]
ma = [float(r["ck_ps"]) for r in mac if float(r["ck_ps"]) >= 0]
st = dict(kit=fz["kit"], outline_um=[W, H], regs=len(a), ck_probe_min_ps=a[0], ck_probe_max_ps=a[-1], ck_probe_p50_ps=a[len(a)//2],
          ck_probe_spread_ps=a[-1]-a[0], ckbufs=len(bufs), macros=len(macs), macro_ck_probe_ps=[min(ma), max(ma)] if ma else None,
          cts_tool=tooli, pin_flop_um=dict(n=len(d), p50=d[len(d)//2], p90=d[int(len(d)*.9)], max=d[-1], over20=sum(x > 20 for x in d)))
fig, ax = plt.subplots(figsize=(12, max(4, 12*H/W) + 1), dpi=100)
ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1))
for r in macs:
    ax.add_patch(plt.Rectangle((float(r["x"]), float(r["y"])), float(r["w"]), float(r["h"]), fc="lightblue", ec="b", alpha=.5))
sc = ax.scatter([float(r["x"]) for r in regs], [float(r["y"]) for r in regs], c=[float(r["ck_ps"]) for r in regs], s=1, cmap="viridis")
ax.scatter([float(r["x"]) for r in bufs], [float(r["y"]) for r in bufs], s=5, marker="^", c="red", label=f"clk bufs {len(bufs)}")
far = [r for r in pr if float(r["ck_ps"]) > 20]
ax.scatter([float(r["x"]) for r in far], [float(r["y"]) for r in far], s=25, marker="x", c="magenta", label=f"pins with reg >20um: {len(far)}")
for r in pl:
    if r["kind"] == "pin" and r["name"].split("[")[0] in ("clk", "ck", "rst_n", "rst", "rs"):
        ax.plot(float(r["x"]), float(r["y"]), "k*", ms=12)
plt.colorbar(sc, ax=ax, label="FF CK arrival, probe (placement RC) ps")
ax.set_xlim(-3, W+3); ax.set_ylim(-3, H+3); ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=7)
ax.set_title(f"{fz['kit']} {W}x{H} post-CTS | CTS tool: {tooli} | probe spread {st['ck_probe_spread_ps']:.0f} ps | "
             f"pin->reg p90 {st['pin_flop_um']['p90']:.1f} max {st['pin_flop_um']['max']:.1f} um", fontsize=8)
fig.savefig(out, bbox_inches="tight"); json.dump(st, open(oj, "w"), indent=1)
print(json.dumps(st))
