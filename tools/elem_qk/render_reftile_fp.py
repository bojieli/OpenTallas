#!/usr/bin/env python3
"""ELEM-QK 10-24: contact sheet of ref_tile kit floorplans (floorplan.json at the closed commit): die/core outline,
macros / hard children with halos, pin groups per face (names + count), std-cell area and fill.  Pre-route review aid.
    render_reftile_fp.py OUT.png KIT@COMMIT [KIT@COMMIT ...]"""
import json
import math
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def fp(kit, sha):
    t = subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:physical/ref_tile/{kit}/floorplan.json"],
                       capture_output=True, text=True)
    return json.loads(t.stdout) if t.returncode == 0 else None


def main(out, items):
    n = len(items)
    c = min(4, n)
    r = math.ceil(n / c)
    fig, axs = plt.subplots(r, c, figsize=(5 * c, 5 * r))
    axs = [axs] if n == 1 else list(getattr(axs, "flat", axs))
    rows = []
    for ax, it in zip(axs, items):
        kit, sha = it.split("@")
        d = fp(kit, sha)
        if not d:
            ax.set_title(f"{kit}: no floorplan.json"); continue
        x0, y0, x1, y1 = d["die"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=1.5))
        cx0, cy0, cx1, cy1 = d["core"]
        ax.add_patch(Rectangle((cx0, cy0), cx1 - cx0, cy1 - cy0, fill=False, lw=0.5, ls="--"))
        mac = 0.0
        for b in d.get("blocks", []):
            ax.add_patch(Rectangle((b["x"], b["y"]), b["w"], b["h"], fc="lightgrey", ec="k", lw=0.5))
            mac += b["w"] * b["h"]
        area = (x1 - x0) * (y1 - y0)
        fill = (mac + (d.get("std_area_um2") or 0)) / area
        for f, names in d.get("pins", {}).items():
            if not names:
                continue
            lab = f"{len(names)}: " + ",".join(names[:6]) + ("..." if len(names) > 6 else "")
            pos = dict(N=((x0 + x1) / 2, y1, "center", "bottom", 0), S=((x0 + x1) / 2, y0, "center", "top", 0),
                       E=(x1, (y0 + y1) / 2, "left", "center", 90), W=(x0, (y0 + y1) / 2, "right", "center", 90))[f]
            ax.text(pos[0], pos[1], lab, ha=pos[2], va=pos[3], rotation=pos[4], fontsize=5, color="tab:blue")
            if f in "NS":
                ax.plot([x0, x1], [pos[1]] * 2, color="tab:blue", lw=3, alpha=0.4)
            else:
                ax.plot([pos[0]] * 2, [y0, y1], color="tab:blue", lw=3, alpha=0.4)
        ax.set_xlim(x0 - 0.15 * (x1 - x0), x1 + 0.15 * (x1 - x0))
        ax.set_ylim(y0 - 0.15 * (y1 - y0), y1 + 0.15 * (y1 - y0))
        ax.set_aspect("equal")
        ax.set_title(f"{kit}\n{x1 - x0:.0f}x{y1 - y0:.0f} um, {len(d.get('blocks', []))} macros, fill {fill:.2f}",
                     fontsize=7)
        nf = len(d.get("findings", []))
        rows.append(dict(kit=kit, sha=sha, w=x1 - x0, h=y1 - y0, macros=len(d.get("blocks", [])), fill=round(fill, 3),
                         std_um2=d.get("std_area_um2"), findings=d.get("findings", []),
                         pins={f: len(v) for f, v in d.get("pins", {}).items()}))
    for ax in axs[len(items):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(json.dumps(rows))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
