import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
P = json.load(open(sys.argv[1])); led = {(r["type"], r["slot"]) for r in json.load(open(sys.argv[2]))}
fig, axs = plt.subplots(1, 2, figsize=(16, 6))
for ax, tn in zip(axs, sys.argv[4:6]):
    t = P["partition_types"][tn]; w, h = t["outline_um"]
    ax.add_patch(plt.Rectangle((0, 0), w, h, fill=False))
    for c in t["hard_cores"]:
        x, y = c["origin_um"]; dx, dy = c.get("track_offset_um") or [0, 0]; cw, ch = c["outline_um"]
        ax.add_patch(plt.Rectangle((x + dx, y + dy), cw, ch, color="0.75"))
    for s in t["ft_slots"]:
        moved = (tn, s["name"]) in led
        for st in s.get("bit_sites_um") or []:
            xs = [p[0] for p in st]; ys = [p[1] for p in st]
            ax.plot(xs, ys, ".", ms=1, color="r" if moved else "b")
        if s.get("regs_um"):
            ax.plot([p[0] for p in s["regs_um"]], [p[1] for p in s["regs_um"]], "o-" if moved else ".", ms=4, lw=.6, color="r" if moved else "g")
    ax.set_title(f"{tn}: grey cores, red = R12 re-sited stations"); ax.set_aspect("equal"); ax.set_xlim(0, w); ax.set_ylim(0, h)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=90)
