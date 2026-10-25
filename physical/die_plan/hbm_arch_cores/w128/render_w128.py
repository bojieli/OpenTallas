#!/usr/bin/env python3
"""HBM-W128 10-25: pre-route plan renders of the W128 HC core views (views_w128.json) for GEOM review.
    python3 render_w128.py OUTDIR   -> OUTDIR/<view>/{plan.png, stats.json}, OUTDIR/context_bank.png, OUTDIR/context_qhub.png
plan.png: outline, pins by layer, per-face pins/um (10-um windows) vs the 6 pins/um budget.  stats.json: per face pins,
max pins/um, max pins/track per layer (pins / available tracks in the 10-um window), lattice check.
context_bank.png: B2o Rh bank column (380.16 and 552.96 wide x 2419.2) with the 8 pair slots, face bands, row gaps,
left/right channels after the 8.64 halo, neighbour banks and the W->E sum chain; context_qhub.png: 734.4 qhub slot
with the 2x2 subtrees (mirrored so data faces outward) and the upper-adder centre."""
import collections, json, math, re, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow

HERE = Path(__file__).resolve().parent
COL = dict(M4="tab:blue", M5="tab:orange", M6="tab:green", M7="tab:red")
PITCH = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064)
LAT = dict(M4=0.024, M5=0.024, M6=0.032, M7=0.032)


def face_of(x, y, w, h):
    return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    V = json.load(open(HERE / "views_w128.json"))
    summary = []
    for v in V["view_list"]:
        w, h = v["outline_um"]
        pins = json.load(open(HERE / v["pins_file"]))
        od = out / re.sub(r"[^A-Za-z0-9_.-]", "_", v["view"]); od.mkdir(exist_ok=True)
        faces = collections.defaultdict(lambda: collections.defaultdict(list))
        offl = 0
        for p in pins:
            f = face_of(p["x"], p["y"], w, h)
            c = p["y"] if f in "EW" else p["x"]
            faces[f][p["layer"]].append(c)
            k = (c - LAT[p["layer"]]) / PITCH[p["layer"]]
            offl += abs(k - round(k)) > 0.05
        fst = {}
        fig, (ax, ax2) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw=dict(width_ratios=[1.1, 1]))
        ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
        for L in sorted({p["layer"] for p in pins}):
            ax.scatter([p["x"] for p in pins if p["layer"] == L], [p["y"] for p in pins if p["layer"] == L], s=2,
                       c=COL[L], label=f"{L} ({sum(p['layer'] == L for p in pins)})")
        for f, byl in faces.items():
            span = h if f in "EW" else w
            bins = int(math.ceil(span / 10)); cnt = [0] * bins; trk = {}
            for L, cs in byl.items():
                cl = [0] * bins
                for c in cs:
                    cnt[min(bins - 1, int(c // 10))] += 1; cl[min(bins - 1, int(c // 10))] += 1
                trk[L] = round(max(cl) / (10 / PITCH[L]), 3)
            mx = round(max(cnt) / 10, 2)
            fst[f] = dict(pins=sum(len(x) for x in byl.values()), span_um=span, max_per_um_10=mx, max_per_track=trk,
                          layers={L: len(x) for L, x in byl.items()},
                          buses=sorted({re.sub(r"\[\d+\]$", "", p["name"]) for p in pins if face_of(p["x"], p["y"], w, h) == f}))
            ax2.plot([i * 10 + 5 for i in range(bins)], [x / 10 for x in cnt], label=f"{f} max {mx}/um")
            ax.text(*dict(W=(-0.04 * w, h / 2), E=(1.01 * w, h / 2), N=(w / 2, 1.02 * h), S=(w / 2, -0.04 * h))[f],
                    ",".join(fst[f]["buses"])[:60], fontsize=6, rotation=90 if f in "EW" else 0, ha="center", va="center")
        ax2.axhline(6.0, color="r", ls="--", lw=1, label="face budget 6 pins/um"); ax2.legend(fontsize=8)
        ax2.set_xlabel("position along face (um)"); ax2.set_ylabel("pins/um (10-um bins)")
        ax.set_aspect("equal"); ax.set_xlim(-0.1 * w, 1.1 * w); ax.set_ylim(-0.1 * h, 1.1 * h); ax.legend(loc="center", fontsize=8)
        ax.set_title(f"{v['view']}\n{w:g} x {h:g} um, {len(pins)} pins, {v['placed']} per HC unit", fontsize=9)
        fig.tight_layout(); fig.savefig(od / "plan.png", dpi=110); plt.close(fig)
        st = dict(view=v["view"], outline_um=[w, h], pins=len(pins), off_lattice=offl, faces=fst,
                  face_budget_violations=[f for f, s in fst.items() if s["max_per_um_10"] > 6 or
                                          any(x > 0.6 for x in s["max_per_track"].values())])
        (od / "stats.json").write_text(json.dumps(st, indent=1) + "\n"); summary.append(st)
        print(v["view"], {f: (s["pins"], s["max_per_um_10"], s["max_per_track"]) for f, s in fst.items()}, "off", offl)
    # bank context: three banks side by side (q_b002-like 380.16 between two 552.96), Rh height 2419.2
    PW, PH, X0, GAP, BAND, HALO = 250.56, 267.84, 25.92, 34.56, 17.28, 8.64
    fig, ax = plt.subplots(figsize=(11, 15)); x = 0; chk = []
    for bi, bw in enumerate([552.96, 380.16, 552.96]):
        ax.add_patch(Rectangle((x, 0), bw, 2419.2, fill=False, lw=2))
        ax.text(x + 4, 2425, f"bank {bw:g} wide" + (" (narrowest q_b002/q_b011)" if bw < 400 else ""), fontsize=7)
        for r in range(8):
            y = BAND + r * (PH + GAP)
            ax.add_patch(Rectangle((x + X0, y), PW, PH, fc="tab:red" if bi == 1 else "0.85", ec="k", lw=0.5, alpha=0.6))
            ax.add_patch(Rectangle((x + X0 - HALO, y - HALO), PW + 2 * HALO, PH + 2 * HALO, fill=False, ls=":", lw=0.4))
            if bi < 2:
                ax.add_patch(FancyArrow(x + X0 + PW, y + PH / 2, (bw - X0 - PW) + X0, 0, width=6, length_includes_head=True,
                                        head_width=14, head_length=10, color="tab:green", alpha=0.7))
            ax.add_patch(FancyArrow(x + X0 + PW + 20, y + PH + GAP / 2, -PW / 2, 0, width=2, head_width=6,
                                    head_length=6, color="tab:purple", alpha=0.5, length_includes_head=True))
        lch, rch = X0 - HALO, bw - X0 - PW - HALO
        chk.append(dict(bank_w=bw, left_channel_um=round(lch, 2), right_channel_um=round(rch, 2),
                        sum_hop_um=round(bw - X0 - PW + X0, 2)))
        ax.text(x + X0 + PW + 4, 1200, f"right ch {rch:.2f}", rotation=90, fontsize=7)
        x += bw
    tot = 2 * BAND + 8 * PH + 7 * GAP
    ax.set_title(f"B2o Rh bank columns: 8 pairs {PW}x{PH} at x {X0}, row gaps {GAP}, face bands {BAND}: {tot:.2f} = 2419.2\n"
                 "green = sum_out(E) -> next bank sum_in(W), straight horizontal; purple = N-face write/control from the row gap",
                 fontsize=8)
    ax.set_aspect("equal"); ax.set_xlim(-20, x + 20); ax.set_ylim(-20, 2460)
    fig.tight_layout(); fig.savefig(out / "context_bank.png", dpi=90); plt.close(fig)
    # qhub context
    S, Q = 220.32, 734.4
    fig, ax = plt.subplots(figsize=(8, 8)); ax.add_patch(Rectangle((0, 0), Q, Q, fill=False, lw=2))
    m = (Q - 2 * S - 103.68) / 2
    for i, (sx, sy, o) in enumerate([(m, Q - m - S, "R0"), (Q - m - S, Q - m - S, "MY"), (m, m, "MX"), (Q - m - S, m, "R180")]):
        ax.add_patch(Rectangle((sx, sy), S, S, fc="tab:red", alpha=0.5, ec="k"))
        ax.text(sx + 5, sy + S / 2, f"subtree32 {i} {o}\ndata face {'N' if sy > Q / 2 else 'S'} (outward)", fontsize=7)
    ax.add_patch(Rectangle((m, m + S), Q - 2 * m, Q - 2 * (m + S), fc="0.8", ec="k"))
    ax.text(m + 5, Q / 2, "upper 3 adders + qhub control (soft, row channel 103.68 um)", fontsize=7)
    ax.set_title(f"q_hub u_hc_Q slot {Q}x{Q}: 4 x subtree32 {S}x{S}, results faces toward the centre row", fontsize=8)
    ax.set_xlim(-10, Q + 10); ax.set_ylim(-10, Q + 10)
    ax.set_aspect("equal"); fig.tight_layout(); fig.savefig(out / "context_qhub.png", dpi=100); plt.close(fig)
    (out / "summary.json").write_text(json.dumps(dict(views=summary, bank_context=chk, column_height_um=round(tot, 2)), indent=1) + "\n")
    print(chk, tot)


if __name__ == "__main__":
    main(sys.argv[1])
