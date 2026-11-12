#!/usr/bin/env python3
"""QC-S28-DIEVIEW: check a hand floorplan (rects.json {hand, cur}: part -> [x0,y0,x1,y1]) against the s28 audit.

    python3 -P -E qc_hf_check.py AUDIT.json FACES.json RECTS.json OUT_DIR [--tag hf1]
Per reshaped type (all instances of a type must get the same new size, else SPLIT is flagged):
  new W x H, aspect, soft fill at the new size, E/W and N/S face bits per um (all buses + ft in/out on that face,
  per face max), hard-core extents vs the new outline (cores keep shape and relative origin: FIT / NO-FIT),
  landing bands outside the new outline, and the content-natural height.  Also overlaps between hand rects and
  rects outside the die.  Renders <tag>_die.png: s28 slots coloured by the NEW fill, hand rects outlined
  (red = reshaped, cyan = moved), and a mid-row zoom."""
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


def main():
    a = sys.argv[1:]
    A = json.loads(Path(a[0]).read_text())
    F = json.loads(Path(a[1]).read_text())
    R = json.loads(Path(a[2]).read_text())
    out = Path(a[3])
    out.mkdir(parents=True, exist_ok=True)
    tag = a[a.index("--tag") + 1] if "--tag" in a else "hf1"
    rows, geom = A["rows"], A["geom"]
    hand, cur = R["hand"], R["cur"]
    ptype = {p["name"]: p["type"] for p in A["parts"]}
    sizes = defaultdict(set)
    moved = set()
    for pn, r in hand.items():
        if pn not in ptype:
            continue
        w, h = round(r[2] - r[0], 2), round(r[3] - r[1], 2)
        sizes[ptype[pn]].add((w, h))
        c = cur.get(pn)
        if c and [round(v, 2) for v in c] != [round(v, 2) for v in r]:
            moved.add(pn)
    missing = [p for p in ptype if p not in hand]
    res = []
    for tn, ss in sorted(sizes.items()):
        r = rows[tn]
        if len(ss) > 1:
            res.append(dict(type=tn, flag="SPLIT", sizes=sorted(ss)))
            continue
        W, H = next(iter(ss))
        if abs(W - r["W"]) < 0.01 and abs(H - r["H"]) < 0.01:
            continue
        soft = W * H - r["macro_um2"]
        ca = (r.get("fill_est") or 0) * (r["W"] * r["H"] - r["macro_um2"])
        f = F[tn]["face_bits"]
        ew = max(sum(v for k, v in f.items() if k.startswith(s)) for s in "EW")
        ns = max(sum(v for k, v in f.items() if k.startswith(s)) for s in "NS")
        cores = geom[tn]["cores"]
        cx = max([c["r"][2] for c in cores] + [0])
        cy = max([c["r"][3] for c in cores] + [0])
        bands_out = sum(1 for b in geom[tn]["bands"] if b["r"][2] > W + 0.01 or b["r"][3] > H + 0.01)
        taps_out = sum(1 for t in geom[tn]["taps"] if t["x"] > W or t["y"] > H)
        res.append(dict(type=tn, inst=r["instances"], old=f"{r['W']}x{r['H']}", new=f"{W}x{H}",
                        aspect=round(max(W, H) / min(W, H), 2), fill_old=r.get("fill_est"),
                        fill_new=round(ca / soft, 3) if soft > 0 else None,
                        ew_b_per_um_old=round(ew / r["H"], 2), ew_b_per_um_new=round(ew / H, 2),
                        ns_b_per_um_old=round(ns / r["W"], 2), ns_b_per_um_new=round(ns / W, 2),
                        cores_fit="FIT" if (cx <= W + 0.01 and cy <= H + 0.01) else f"NO-FIT core ext {cx:.1f}x{cy:.1f}",
                        bands_outside=bands_out, taps_outside=taps_out, route_p99_s28=r.get("route_p99")))
    # overlaps
    rects = [(pn, r) for pn, r in hand.items()]
    ov = []
    rects.sort(key=lambda x: x[1][0])
    for i, (pa, ra) in enumerate(rects):
        for pb, rb in rects[i + 1:]:
            if rb[0] >= ra[2] - 0.01:
                break
            if min(ra[3], rb[3]) - max(ra[1], rb[1]) > 0.01 and min(ra[2], rb[2]) - max(ra[0], rb[0]) > 0.01:
                ov.append((pa, pb))
    DW, DH = A["die"]
    outside = [pn for pn, r in hand.items() if r[0] < -0.01 or r[1] < -0.01 or r[2] > DW + 0.01 or r[3] > DH + 0.01]
    rep = dict(reshaped_types=[x for x in res if "new" in x], split=[x for x in res if x.get("flag") == "SPLIT"],
               moved_parts=len(moved), parts_missing=missing, overlaps=ov[:50], n_overlaps=len(ov), outside_die=outside)
    (out / f"{tag}_check.json").write_text(json.dumps(rep, indent=1) + "\n")
    with open(out / f"{tag}_types.tsv", "w") as f:
        cols = ["type", "inst", "old", "new", "aspect", "fill_old", "fill_new", "ew_b_per_um_old", "ew_b_per_um_new",
                "ns_b_per_um_old", "ns_b_per_um_new", "cores_fit", "bands_outside", "taps_outside", "route_p99_s28"]
        f.write("\t".join(cols) + "\n")
        for x in rep["reshaped_types"]:
            f.write("\t".join(str(x.get(c, "")) for c in cols) + "\n")
    print(f"reshaped types {len(rep['reshaped_types'])}, split {len(rep['split'])}, moved parts {len(moved)}, "
          f"missing {len(missing)}, overlaps {len(ov)}, outside {len(outside)}")
    # render
    cmap = matplotlib.colormaps["viridis"]
    newfill = {x["type"]: x["fill_new"] for x in rep["reshaped_types"]}
    for name, box, size in (("die", (0, 0, DW, DH), (30, 25)), ("strip", (1500, 9900, 9300, 16000), (16, 12.5))):
        fig, ax = plt.subplots(figsize=size, dpi=110)
        fig.patch.set_facecolor("#0b0d12")
        ax.set_facecolor("#0b0d12")
        for pn, r in hand.items():
            tn = ptype.get(pn)
            if r[0] > box[2] or r[2] < box[0] or r[1] > box[3] or r[3] < box[1]:
                continue
            row = rows.get(tn, {})
            macro = row.get("macro_frac", 0) > 0.2
            fv = newfill.get(tn, row.get("fill_est")) if not macro else row.get("fill_est_total")
            c = cur.get(pn)
            reshaped = c and (abs((c[2] - c[0]) - (r[2] - r[0])) > 0.01 or abs((c[3] - c[1]) - (r[3] - r[1])) > 0.01)
            ec = "#ff3030" if reshaped else ("#00e5ff" if pn in moved else "#202020")
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=cmap(min(1, (fv or 0) / 0.7)),
                                   ec=ec, lw=1.4 if (reshaped or pn in moved) else 0.4, hatch="//" if macro else None))
            if c and (reshaped or pn in moved):
                ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fill=False, ec="#ffffff", lw=0.5,
                                       ls=":"))
            if name == "strip" and tn:
                x = next((y for y in rep["reshaped_types"] if y["type"] == tn), None)
                lab = tn.split("__")[0]
                if x:
                    lab += f"\n{x['new']}\nf{100 * (x['fill_new'] or 0):.0f}% EW {x['ew_b_per_um_new']}b/um"
                ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, lab, ha="center", va="center", fontsize=6,
                        color="white", bbox=dict(fc="black", alpha=0.5, lw=0, pad=0.3))
        ax.set_xlim(box[0], box[2])
        ax.set_ylim(box[1], box[3])
        ax.set_aspect("equal")
        ax.tick_params(colors="#bbb")
        ax.set_title(f"[{tag}] hand rects (red = reshaped, cyan = moved; dotted = s28 rect); colour = fill at the new size",
                     color="white")
        fig.savefig(out / f"{tag}_{name}.png", facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    main()
