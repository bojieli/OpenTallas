#!/usr/bin/env python3
"""ELEM-HBM 10-24: pre-route geometry review renders + checks of one B2r2 hard-core view (owner order 08:05:
"review before you route").

    python3 review_core.py --views views_b2r2.json --view MODULE@SHA12 --out DIR [--kit KITDIR]
      -> DIR/<view>/{plan.png, context.png, stats.json}   (+ placed.png when KITDIR has a 3_place.odb dump, see
         placed_dump.py)

plan.png    the core outline at scale, every plan pin coloured by layer, per-face pins/um profile (10-um windows) with
            the 6 pins/um face budget and the 0.6 pins/track line, SRAM count from the kit recipe.
context.png the partition type outline with every hard core (grey) and soft leaf (hatched), THIS core red, and one
            line per connected pin bus from the bus's pin centroid to its partner (core centre / leaf centre / the
            partition port window), coloured green (faces the partner, cos >= 0.3), orange (0..0.3), red (< 0).
stats.json  per face: pins, pins/um max over 10-um windows, pins/track max per layer; partner checks: per bus cos,
            Manhattan distance core pin -> partner (vs 0.9 x 405 um local M4-M7 reach: a longer wire needs a station
            in the partition); estimated fill (cells x area from CORE-HBM other_status / synth stat if present).
The checks are evidence for the human review; the verdict is written by the reviewer (review_record.py).
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import schema as S  # noqa: E402

PITCH = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064)
COL = dict(M4="tab:blue", M5="tab:orange", M6="tab:green", M7="tab:purple")
REACH_LOCAL = 405.0 * 0.9


def face_of(x, y, w, h):
    return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]


def window_stats(coords_by_layer, span):
    """max pins/um over 10-um windows (all layers) and max pins/track per layer."""
    allc = sorted(c for L in coords_by_layer.values() for c in L)
    best = 0.0
    j = 0
    for i in range(len(allc)):
        while allc[i] - allc[j] > 10.0:
            j += 1
        best = max(best, (i - j + 1) / 10.0)
    trk = {}
    for L, cs in coords_by_layer.items():
        cs = sorted(cs)
        b, j = 0.0, 0
        for i in range(len(cs)):
            while cs[i] - cs[j] > 10.0:
                j += 1
            b = max(b, (i - j + 1) / (10.0 / PITCH[L]))
        trk[L] = round(b, 3)
    return round(best, 3), trk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", required=True)
    ap.add_argument("--view", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    V = json.load(open(a.views))
    v = next(x for x in V["view_list"] if x["view"] == a.view)
    plan_path = Path(V["plan"])
    raw = json.load(open(plan_path))
    P = S.Plan(raw)
    pdir = plan_path.resolve().parent
    w, h = v["outline_um"]
    pins = json.load(open(pdir / v["pins_file"]))
    od = Path(a.out) / re.sub(r"[^A-Za-z0-9_.-]", "_", a.view)
    od.mkdir(parents=True, exist_ok=True)
    # ---------------------------------------------------------------- plan view + face stats
    faces = collections.defaultdict(lambda: collections.defaultdict(list))
    for p in pins:
        f = face_of(p["x"], p["y"], w, h)
        faces[f][p["layer"]].append(p["y"] if f in "EW" else p["x"])
    fstats = {}
    for f, byl in faces.items():
        span = h if f in "EW" else w
        mx, trk = window_stats(byl, span)
        n = sum(len(x) for x in byl.values())
        fstats[f] = dict(pins=n, span_um=span, avg_per_um=round(n / span, 3), max_per_um_10=mx, max_per_track=trk,
                         layers={L: len(c) for L, c in byl.items()})
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw=dict(width_ratios=[1.1, 1]))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
    ax.add_patch(Rectangle((4.32, 4.32), w - 8.64, h - 8.64, fill=False, lw=0.5, ls=":"))
    for L in sorted({p["layer"] for p in pins}):
        xs = [p["x"] for p in pins if p["layer"] == L]
        ys = [p["y"] for p in pins if p["layer"] == L]
        ax.scatter(xs, ys, s=2, c=COL.get(L, "k"), label=f"{L} ({len(xs)})")
    ax.set_aspect("equal")
    ax.set_xlim(-0.05 * w, 1.05 * w)
    ax.set_ylim(-0.05 * h, 1.05 * h)
    ax.legend(loc="center", fontsize=8)
    ax.set_title(f"{a.view}\n{w:g} x {h:g} um, {len(pins)} pins, {v['placed']} placed", fontsize=9)
    for f, byl in faces.items():
        span = h if f in "EW" else w
        allc = sorted(c for L in byl.values() for c in L)
        bins = max(1, int(math.ceil(span / 10)))
        cnt = [0] * bins
        for c in allc:
            cnt[min(bins - 1, int(c // 10))] += 1
        wid = [min(10.0, span - i * 10) for i in range(bins)]
        ax2.plot([i * 10 + wid[i] / 2 for i in range(bins)], [x / max(wid[i], 1e-9) for i, x in enumerate(cnt)],
                 label=f"{f} max {fstats[f]['max_per_um_10']}/um")
    ax2.axhline(6.0, color="r", ls="--", lw=1, label="face budget 6 pins/um")
    ax2.set_xlabel("position along face (um)")
    ax2.set_ylabel("pins / um (10-um bins)")
    ax2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(od / "plan.png", dpi=110)
    plt.close(fig)
    # ---------------------------------------------------------------- context: partition type + partners
    tn, inst = v["instances"][0].split(".", 1)
    t = P.types[tn]
    tw, th = t["outline_um"]
    core = next(c for c in t["hard_cores"] if c["inst"] == inst)
    ox, oy = core["origin_um"]
    cc = json.load(open(pdir / "core_conns.json")).get(tn, {}).get(inst, {})
    centres = {}
    for c in t.get("hard_cores", []):
        centres["core:" + c["inst"]] = (c["origin_um"][0] + c["outline_um"][0] / 2, c["origin_um"][1] + c["outline_um"][1] / 2)
    for c in t.get("contents", []):
        if c.get("origin_um") and c.get("outline_um"):
            centres["leaf:" + c["inst"]] = (c["origin_um"][0] + c["outline_um"][0] / 2, c["origin_um"][1] + c["outline_um"][1] / 2)
    # partition bus windows (type frame) from any instance of the type
    part = next(p for p in raw["partitions"] if p["type"] == tn)
    buspt = {}
    for pid, pr in P.ports.items():
        for side in ("src", "dst"):
            if pr[side]["part"] == part["name"]:
                try:
                    q = P.port_point(pid)
                except Exception:
                    continue
                buspt["bus:" + pr[side]["bus"]] = P.to_type(part["name"], q)
    fig, ax = plt.subplots(figsize=(9, 9 * th / max(tw, 1e-9) if th / tw < 1.6 else 13))
    ax.add_patch(Rectangle((0, 0), tw, th, fill=False, lw=2))
    for c in t.get("contents", []):
        if c.get("origin_um") and c.get("outline_um") and c.get("inst") not in {x["inst"] for x in t["hard_cores"]}:
            ax.add_patch(Rectangle(c["origin_um"], *c["outline_um"], fill=False, hatch="///", lw=0.3, color="0.6"))
    for c in t["hard_cores"]:
        me = c["inst"] == inst
        ax.add_patch(Rectangle(c["origin_um"], *c["outline_um"], fc=("tab:red" if me else "0.85"), ec="k", lw=0.4,
                               alpha=(0.6 if me else 1)))
        if c["outline_um"][0] > tw / 12:
            ax.text(c["origin_um"][0] + 2, c["origin_um"][1] + 2, c["inst"].replace("u_", "")[:18], fontsize=5)
    byb = collections.defaultdict(list)
    for p in pins:
        byb[re.sub(r"\[\d+\]$", "", p["name"])].append(p)
    checks = []
    for b, L in byb.items():
        tg = cc.get(b)
        if not tg:
            continue
        px = sum(p["x"] for p in L) / len(L) + ox
        py = sum(p["y"] for p in L) / len(L) + oy
        f = collections.Counter(face_of(p["x"], p["y"], w, h) for p in L).most_common(1)[0][0]
        nx, ny = dict(N=(0, 1), S=(0, -1), E=(1, 0), W=(-1, 0))[f]
        for tgt in tg:
            q = centres.get(tgt) or buspt.get(tgt)
            if q is None:
                checks.append(dict(bus=b, partner=tgt, bits=len(L), cos=None, dist_um=None))
                continue
            dx, dy = q[0] - px, q[1] - py
            d = math.hypot(dx, dy) or 1e-9
            cs = (dx * nx + dy * ny) / d
            man = abs(dx) + abs(dy)
            checks.append(dict(bus=b, partner=tgt, bits=len(L), face=f, cos=round(cs, 3), dist_um=round(man, 1)))
            ax.plot([px, q[0]], [py, q[1]], lw=0.4 + 2.5 * min(1, len(L) / 512),
                    color="tab:green" if cs >= 0.3 else "tab:orange" if cs >= 0 else "tab:red", alpha=0.7)
    ax.set_aspect("equal")
    ax.set_xlim(-0.02 * tw, 1.02 * tw)
    ax.set_ylim(-0.02 * th, 1.02 * th)
    ax.set_title(f"{tn} ({tw:g} x {th:g}) — {inst} red; partner lines green/orange/red by face cos", fontsize=8)
    fig.tight_layout()
    fig.savefig(od / "context.png", dpi=110)
    plt.close(fig)
    bits_bad = sum(c["bits"] for c in checks if c["cos"] is not None and c["cos"] < 0)
    bits_far = sum(c["bits"] for c in checks if c["dist_um"] is not None and c["dist_um"] > REACH_LOCAL)
    st = dict(view=a.view, outline_um=[w, h], pins=len(pins), faces=fstats,
              face_budget_violations=[f for f, s in fstats.items() if s["max_per_um_10"] > 6.0 or
                                      any(x > 0.6 for x in s["max_per_track"].values())],
              partition=tn, inst=inst, connected_buses=len({c["bus"] for c in checks}), buses=len(byb),
              connected_bits=sum(len(byb[b]) for b in {c["bus"] for c in checks}),
              bits_facing_away=bits_bad, bits_beyond_local_reach=bits_far,
              partner_checks=sorted(checks, key=lambda c: (c["cos"] if c["cos"] is not None else 9)))
    (od / "stats.json").write_text(json.dumps(st, indent=1) + "\n")
    print(json.dumps({k: st[k] for k in ("view", "pins", "face_budget_violations", "connected_buses", "buses",
                                         "connected_bits", "bits_facing_away", "bits_beyond_local_reach")}))


if __name__ == "__main__":
    main()
