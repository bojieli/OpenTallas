import csv, json, sys, statistics as st
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
ck, pl, kit, out, title = sys.argv[1:6]
W, H = json.load(open(kit + "/freeze.json"))["outline_um"]
rows = list(csv.DictReader(open(ck)))
ff = [r for r in rows if r["kind"] == "ff" and float(r["ck_ps"]) >= 0]
cb = [r for r in rows if r["kind"] == "ckbuf"]; pr = [r for r in rows if r["kind"] == "pinreg"]
mac = [r for r in rows if r["kind"] == "macro"]
pins = json.load(open(kit + "/pins.json"))
a = [float(r["ck_ps"]) for r in ff]; d = sorted(float(r["ck_ps"]) for r in pr)
fig, ax = plt.subplots(figsize=(11, 11 * H / W + 1))
sc = ax.scatter([float(r["x"]) for r in ff], [float(r["y"]) for r in ff], c=a, s=2, cmap="viridis")
ax.scatter([float(r["x"]) for r in cb], [float(r["y"]) for r in cb], s=10, c="red", marker="^", label="clock buffers")
ax.scatter([p["x"] for p in pins], [p["y"] for p in pins], s=3, c="k", marker="s", label="pins")
ckp = [p for p in pins if p["bus"] in ("clk", "ck")]
ax.scatter([p["x"] for p in ckp], [p["y"] for p in ckp], s=120, c="magenta", marker="*", label="clock pin")
try:
    for ln in open(kit + "/macro_place.tcl"):
        if ln.strip().startswith("foreach {master x y orient"):
            t = ln.split("{")[2].split(); x, y = float(t[1]), float(t[2])
            import re
            lef = open([f for f in __import__("glob").glob(kit + "/macros/*.lef")][0]).read(); mw, mh = map(float, re.search(r"SIZE ([\d.]+) BY ([\d.]+)", lef).groups())
            ax.add_patch(plt.Rectangle((x, y), mw, mh, fill=False, ec="orange", lw=2))
except Exception as e: print("macro", e)
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); plt.colorbar(sc, label="CK arrival ps (TT, placement RC)")
s = dict(ff=len(a), ck_min=min(a), ck_max=max(a), ck_spread=max(a) - min(a), ck_mean=st.mean(a), clkbufs=len(cb),
         pinreg_n=len(d), pinreg_max_um=d[-1] if d else None, pinreg_p90_um=d[int(.9 * len(d))] if d else None,
         macro_ck=[(m["inst"], float(m["ck_ps"])) for m in mac])
ax.set_title(f"{title}: CK {s['ck_min']:.0f}-{s['ck_max']:.0f} ps (spread {s['ck_spread']:.1f}), {len(cb)} clk bufs, pin-reg max {s['pinreg_max_um']:.1f} um"); ax.legend(loc="upper right", fontsize=7)
plt.savefig(out, dpi=110, bbox_inches="tight"); json.dump(s, open(out.replace(".png", ".json"), "w"), indent=1); print(json.dumps(s))
