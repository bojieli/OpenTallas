import sys, re, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d, meta, out, title = sys.argv[1:5]
M = json.load(open(meta)); ox, oy = M["origin"]
txt = open(d + "/tree.def").read()
dbu = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", txt).group(1))
pos = {}
for m in re.finditer(r"^\s*-\s+(\S+)\s+(\S+)\s.*?\+\s+(?:PLACED|FIXED|FIRM)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)", txt, re.M):
    pos[m.group(1)] = (int(m.group(3)) / dbu, int(m.group(4)) / dbu, m.group(2))
pins = re.search(r"^PINS.*?END PINS", txt, re.M | re.S).group(0)
pm = re.search(r"(?:PLACED|FIXED) \( (-?\d+) (-?\d+) \)", pins); pos["PIN"] = (int(pm.group(1)) / dbu, int(pm.group(2)) / dbu, "PIN")
nets = re.search(r"^NETS.*?END NETS", txt, re.M | re.S).group(0)
fig, ax = plt.subplots(figsize=(7, 11))
for c in M.get("cores", []):
    x0, y0, x1, y1 = c["rect"]; ax.add_patch(plt.Rectangle((x0 - ox, y0 - oy), x1 - x0, y1 - y0, fc="#ddd", ec="k"))
for blk in re.split(r"\n\s*-\s+", nets)[1:]:
    conns = re.findall(r"\(\s*(\S+)\s+(\S+)\s*\)", blk)
    drv = [i for i, p in conns if p in ("Y",) or i == "PIN"]
    if not drv: continue
    a = pos.get(drv[0])
    for i, p in conns:
        if i == drv[0] or i not in pos or a is None: continue
        b = pos[i]; ax.plot([a[0], b[0], b[0]], [a[1], a[1], b[1]], lw=0.6, c="tab:blue")
bx = [v for k, v in pos.items() if v[2].startswith("BUF")]
ax.scatter([v[0] for v in bx], [v[1] for v in bx], s=4, c="tab:red", label=f"buffers ({len(bx)})")
sk = [v for k, v in pos.items() if v[2].startswith("DFF")]
ax.scatter([v[0] for v in sk], [v[1] for v in sk], s=30, marker="s", c="green", label=f"sinks ({len(sk)})")
ax.scatter([pos["PIN"][0]], [pos["PIN"][1]], s=80, marker="*", c="k", label="region root")
ax.set_aspect("equal"); ax.set_title(title, fontsize=9); ax.legend(fontsize=7, loc="upper right"); fig.savefig(out, dpi=110, bbox_inches="tight")
