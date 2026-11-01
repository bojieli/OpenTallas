"""render l48w-st stage legs/buffers (snapped) on a dense and a sparse 500-um window. usage: st_render.py PLAN SITES_DIR ORIG_PATCH SSE OUTPREFIX"""
import json, re, sys, collections
from pathlib import Path
plan, sd, op, sse, pre = sys.argv[1:6]
sys.path.insert(0, sse)
import die_trial as T, schema as S
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
T.DME_ACTUAL_MAX_UM = 405.0
P = S.Plan(S.load(plan), Path(plan)); site = T.clock_site(P); site0 = T.SiteMap(P)
st = json.loads((Path(sd) / "start_stages_l48w_st.json").read_text())["stages"]
ct = (Path(sd) / "ctree.tcl").read_text(); ct0 = (Path(op) / "ctree.tcl").read_text()
rx = r"place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\}"
loc = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(rx, ct)}; loc0 = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(rx, ct0)}
mine = {s["entry_buffer"]["inst"] for s in st} | {c["inst"] for s in st for c in s.get("chain", ())}
G = 500.0; cnt = collections.Counter((int(loc[q][0] // G), int(loc[q][1] // G)) for q in mine)
mv = collections.Counter((int(loc[q][0] // G), int(loc[q][1] // G)) for q in mine if abs(loc[q][0]-loc0[q][0])+abs(loc[q][1]-loc0[q][1]) > 2)
dense = max(cnt, key=lambda k: (mv[k] > 0, cnt[k]))
sparse = min((k for k in cnt if mv[k] > 0 and cnt[k] >= 3), key=lambda k: cnt[k])
for tag, (i, j) in (("dense", dense), ("sparse", sparse)):
    x0, y0, x1, y1 = i * G - 50, j * G - 50, (i + 1) * G + 50, (j + 1) * G + 50
    f, ax = plt.subplots(figsize=(11, 11))
    for r in site0.forb:
        if r[2] > x0 and r[0] < x1 and r[3] > y0 and r[1] < y1:
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#f4c7c3", ec="#c0392b", lw=.6))
    for r in site.parts:
        if r[2] > x0 and r[0] < x1 and r[3] > y0 and r[1] < y1:
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="none", ec="#bbbbbb", lw=.4))
    tx = [v for k, v in loc.items() if k not in mine and x0 < v[0] < x1 and y0 < v[1] < y1]
    ax.scatter([v[0] for v in tx], [v[1] for v in tx], s=2, c="#888888", label=f"tree cells ({len(tx)})")
    nb = nm = 0
    for s in st:
        seq = [s["entry_buffer"]["inst"]] + [c["inst"] for c in s.get("chain", ())]
        pts = [tuple(s["node_xy_um"])] + [loc[q] for q in seq] + [tuple(s["clock_pin_xy_um"])]
        if not any(x0 < p[0] < x1 and y0 < p[1] < y1 for p in pts): continue
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", c="#2e86c1", lw=.7)
        ax.plot(*s["clock_pin_xy_um"], "^", c="#27ae60", ms=5)
        for q in seq:
            a, b = loc0[q], loc[q]; d = abs(a[0]-b[0]) + abs(a[1]-b[1])
            if not (x0 < b[0] < x1 and y0 < b[1] < y1): continue
            nb += 1
            if d > 2:
                nm += 1; ax.plot(*a, "x", c="#c0392b", ms=6); ax.annotate("", b, a, arrowprops=dict(arrowstyle="->", color="#e67e22", lw=1))
            ax.plot(*b, "s", c="#e67e22" if d > 2 else "#1b4f72", ms=3.5)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    ax.set_title(f"l48w-st g snapped, {tag} window ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}): {nb} stage buffers, {nm} moved >2um (x=old, orange=new); red=core+halo; blue=stage legs; green=stage pin")
    ax.title.set_fontsize(8); ax.legend(loc="upper right", fontsize=7)
    f.savefig(f"{pre}_{tag}.png", dpi=110, bbox_inches="tight"); print(tag, (x0, y0, x1, y1), nb, nm)
