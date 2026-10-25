#!/usr/bin/env python3
"""PLAN-DELTA/S81: type-frame render of the types a delta changes, BEFORE | AFTER side by side.
Outline, bus windows on their faces (blue in / green out), ft slots (orange in/out windows joined by a line), hard
cores (grey), and every bus / slot whose bit order differs from the BEFORE panel's type in red with its order.
usage: render_types.py BASE.json AFTER.json PROV.json OUTDIR"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


def seg(face, win, w, h, d=6.0):
    a, b = win
    return {"N": ((a, h - d), (b, h - d)), "S": ((a, d), (b, d)),
            "W": ((d, a), (d, b)), "E": ((w - d, a), (w - d, b))}[face]


def mid(s):
    return ((s[0][0] + s[1][0]) / 2, (s[0][1] + s[1][1]) / 2)


def panel(ax, t, title, ref=None):
    w, h = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.2))
    for c in t.get("hard_cores", []):
        (x, y), (cw, ch) = c["origin_um"], c["outline_um"]
        if c.get("orient") in ("R90", "R270"):
            cw, ch = ch, cw
        ax.add_patch(Rectangle((x, y), cw, ch, color="0.75", lw=0))
    rb = {b["name"]: b.get("order", "lsb_low") for b in (ref or {}).get("buses", [])}
    rs = {s["name"]: s.get("order", "lsb_low") for s in (ref or {}).get("ft_slots", [])}
    for b in t.get("buses", []):
        if "face" not in b or "window_um" not in b:
            continue
        s = seg(b["face"], b["window_um"], w, h)
        chg = ref is not None and rb.get(b["name"], b.get("order", "lsb_low")) != b.get("order", "lsb_low")
        col = "red" if chg else ("tab:blue" if b["dir"] == "in" else "tab:green")
        ax.plot(*zip(*s), color=col, lw=4 if chg else 2.5, solid_capstyle="butt")
        x, y = mid(s)
        ax.text(x, y, b["name"] + (" " + b.get("order", "lsb_low") if chg else ""), fontsize=5, color=col)
    for f in t.get("ft_slots", []):
        si = seg(f["in_face"], f["in_window_um"], w, h, 14)
        so = seg(f["out_face"], f["out_window_um"], w, h, 14)
        chg = ref is not None and rs.get(f["name"], f.get("order", "lsb_low")) != f.get("order", "lsb_low")
        col = "red" if chg else "tab:orange"
        ax.plot(*zip(*si), color=col, lw=3)
        ax.plot(*zip(*so), color=col, lw=3)
        ax.plot(*zip(mid(si), mid(so)), color=col, lw=0.6, ls="--")
        x, y = mid(si)
        ax.text(x, y, "%s %db x%d%s" % (f["name"], f["width"], f.get("stations", 0),
                                        " " + f.get("order", "lsb_low") if chg else ""), fontsize=5, color=col)
    ax.set_xlim(-30, w + 30)
    ax.set_ylim(-30, h + 30)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=7)
    ax.tick_params(labelsize=5)


def main():
    base, after, prov, out = sys.argv[1:5]
    B = json.load(open(base))
    A = json.load(open(after))
    P = json.load(open(prov))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    inst = {}
    for p in A["partitions"]:
        inst.setdefault(p["type"], []).append("%s@%s" % (p["name"], p.get("orient", "R0")))
    jobs = []
    for m, v in P["merged"].items():
        jobs.append((m, v["into"], "merged %s -> %s" % (m, v["into"])))
    for t in P["pin_table_touched_types"]:
        jobs.append((t, t, "bit-order repair only"))
    for tb, ta, why in jobs:
        fig, ax = plt.subplots(1, 2, figsize=(11, 5), dpi=150)
        panel(ax[0], B["partition_types"][tb], "BEFORE %s (%s)" % (tb, ", ".join("%s@%s" % (p["name"], p.get("orient", "R0")) for p in B["partitions"] if p["type"] == tb)))
        panel(ax[1], A["partition_types"][ta], "AFTER %s (%s)\n%s" % (ta, ", ".join(inst.get(ta, [])), why), ref=B["partition_types"][tb])
        fig.tight_layout()
        fig.savefig(out / ("%s.png" % tb))
        plt.close(fig)
        print(out / ("%s.png" % tb))


if __name__ == "__main__":
    main()
