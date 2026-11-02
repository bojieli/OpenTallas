#!/usr/bin/env python3
"""DIE-HBM-57/TAPS 11-01 (COORD 10:2x): explicit clock taps for single-root HBM hard cores.

Class: a core with ONE clock pin (one root) whose far pin-register columns sit > CLK_REACH_MAX (200 um, METHODOLOGY 12.8b)
from that root (d44o hfd_ep_static a6: root (220.3,25.9), W-edge register column x~5 y 0-180, reach 370 um).

Form: planned clock anchors (`clock_sites_um`) consumed by the existing density CTS hook (core_density_taps.tcl
OT_DTAP_SITES, gen_core_kit_hbm.py planned_clock_sites_text): port -> CTS trunk -> one BUFx24 tap per anchor -> local CTS
tree per tap, all taps aligned to the core's common latency (OT_TAP_TARGET_PS / OT_TAP_WINDOW_PS = the 12.3 budget,
same as the existing entry) by core_tap_align.tcl.  No port, RTL, ABI or die-plan change (the core keeps its single
clk pin; the die tree still taps the core at its plan entry).

Sites per view (deterministic, placement independent): free core area = core area minus every core_macros.json rect
(+ halo) sampled on a GRID um lattice; site 0 = the root (snapped legal); then greedy cover: while some free point is
farther than --reach from every site, add the legal lattice site within --reach of the farthest point that covers the
most uncovered points (= one tap at each far pin-register column / region).  Empty anchors are pruned by the hook.
Only views whose root-to-free-area reach exceeds the 220-um gate get sites; recipe clock_sites_um (e.g. pslice) win.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

CLK_RE = r"^(clk|clk_[a-z0-9_]+|[a-z0-9_]*_clk|ck|ck_[a-z0-9_]+|[a-z0-9_]*clk_[a-z0-9_]*)$"  # gen_core_kit_hbm.CLK_RE
PG = 4.32                 # PG / site lattice (planned_clock_sites_text)
EDGE = 8.64               # planned_clock_sites_text legal band
CLK_REACH_MAX = 200.0     # geom_rules.CLK_REACH_MAX
CLK_REACH_GATE = 220.0    # geom_rules CLK_REACH_MAX x CLK_REACH_TOL: views at or under it keep their single-root form
SITE_CLEAR = 1.08         # tap site clearance from a macro rect (um)
SCHEMA = "opentallas.hbm_single_root_taps.v1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pins_of(path):
    out = []
    for p in json.load(open(path)):
        if "name" not in p:
            p = dict(p, name=f"{p['bus']}[{p['bit']}]")
        out.append(p)
    return out


def clock_pins(pins):
    return [p for p in pins if re.match(CLK_RE, re.sub(r"\[\d+\]$", "", p["name"]))]


def free_points(w, h, rects, halo, grid):
    xs = np.arange(PG, w - PG + 1e-6, grid)
    ys = np.arange(PG, h - PG + 1e-6, grid)
    X, Y = np.meshgrid(xs, ys)
    P = np.stack([X.ravel(), Y.ravel()], 1)
    keep = np.ones(len(P), bool)
    for x0, y0, x1, y1 in rects:
        keep &= ~((P[:, 0] > x0 - halo) & (P[:, 0] < x1 + halo) & (P[:, 1] > y0 - halo) & (P[:, 1] < y1 + halo))
    return P[keep]


def legal_sites(w, h, rects):
    """4.32-lattice points in the legal band, >= SITE_CLEAR off every macro rect (the hook rejects a site ON a macro bbox;
    detailed_placement legalises the tap buffer next to it)"""
    xs = np.round(np.arange(EDGE, w - EDGE + 1e-6, PG), 2)
    ys = np.round(np.arange(EDGE, h - EDGE + 1e-6, PG), 2)
    X, Y = np.meshgrid(xs, ys)
    L = np.stack([X.ravel(), Y.ravel()], 1)
    # the exact float test of planned_clock_sites_text on the view outline (578.8799999999999 - 8.64 < 570.24)
    keep = np.array([EDGE <= x <= w - EDGE and EDGE <= y <= h - EDGE for x, y in L.tolist()], bool)
    for x0, y0, x1, y1 in rects:
        keep &= ~((L[:, 0] >= x0 - SITE_CLEAR) & (L[:, 0] <= x1 + SITE_CLEAR) & (L[:, 1] >= y0 - SITE_CLEAR) & (L[:, 1] <= y1 + SITE_CLEAR))
    return L[keep]


def mind(P, S):
    S = np.asarray(S, float).reshape(-1, 2)
    best = np.full(len(P), np.inf)
    for s in S:
        best = np.minimum(best, np.abs(P[:, 0] - s[0]) + np.abs(P[:, 1] - s[1]))
    return best


def plan_sites(P, L, root, reach, max_sites=64):
    """greedy cover of the free points P by sites from L, site 0 = legal point nearest the root.  A free sliver with no
    legal site within `reach` (e.g. a channel between hard children) gets the nearest legal site; points still beyond
    `reach` after that are reported (reach_after_um), never silently dropped."""
    d0 = np.abs(L[:, 0] - root[0]) + np.abs(L[:, 1] - root[1])
    sites = [L[int(d0.argmin())]]
    best = mind(P, sites)
    done = np.zeros(len(P), bool)                 # points that no further legal site can bring within reach
    while (best[~done] > reach).any() and len(sites) < max_sites:
        i = int(np.where(done, -1, best).argmax())
        far = P[i]
        dl = np.abs(L[:, 0] - far[0]) + np.abs(L[:, 1] - far[1])
        cand = L[dl <= reach]
        if not len(cand):
            cand = L[[int(dl.argmin())]]
        unc = P[(best > reach) & ~done]
        if len(cand) > 400:                       # coarse candidate subsample, deterministic
            cand = cand[:: int(np.ceil(len(cand) / 400))]
        gain = np.array([((np.abs(unc[:, 0] - c[0]) + np.abs(unc[:, 1] - c[1])) <= reach).sum() for c in cand])
        # tie-break: the candidate nearest the far point (a tap AT the far column, not between columns)
        dfar = np.abs(cand[:, 0] - far[0]) + np.abs(cand[:, 1] - far[1])
        c = cand[int(np.lexsort((dfar, -gain))[0])]
        nb = np.minimum(best, np.abs(P[:, 0] - c[0]) + np.abs(P[:, 1] - c[1]))
        if nb[i] > reach:
            done[i] = True                        # unreachable sliver point
        if not any((abs(c[0] - s[0]) < 1e-6 and abs(c[1] - s[1]) < 1e-6) for s in sites) and (nb < best).any():
            sites.append(c)
        best = nb
    return [[round(float(x), 2), round(float(y), 2)] for x, y in sites], float(best.max())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--views", required=True, help="views_b2r2.py core_views.json (its 'plan' names the plan dir)")
    ap.add_argument("--reach", type=float, default=180.0, help="target free-area reach to the nearest site (um)")
    ap.add_argument("--grid", type=float, default=4.32)
    ap.add_argument("--halo", type=float, default=None, help="macro halo (default core_macros.json halo_um)")
    ap.add_argument("--variant", default="A")
    ap.add_argument("--exclude", default="", help="comma list of modules left to their own recipe sites")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    V = json.load(open(a.views))
    pdir = Path(V["plan"]).parent
    cmf = pdir / "core_macros.json"
    CM = json.load(open(cmf)) if cmf.is_file() else {"cores": {}}
    halo = a.halo if a.halo is not None else float(CM.get("halo_um") or 0.0)
    excl = {m for m in a.exclude.split(",") if m}
    out, rows = {}, []
    for v in V["view_list"]:
        ck = clock_pins(pins_of(pdir / v["pins_file"]))
        if len(ck) != 1:
            continue                                   # multi-root views keep their own (reviewed) multi-port forms
        w, h = v["outline_um"]
        root = (ck[0]["x"], ck[0]["y"])
        e = (CM.get("cores") or {}).get(v["module"]) or {}
        same = [round(x, 2) for x in e.get("outline_um", [w, h])] == [round(w, 2), round(h, 2)]
        rects = [tuple(q["rect_um"]) for q in e.get("macros", []) if q.get("rect_um")] \
            if e.get("status") == "KNOWN" and same else []
        P = free_points(w, h, rects, halo, a.grid)
        before = float(mind(P, [root]).max())
        row = dict(view=v["view"], module=v["module"], outline_um=[w, h], root=[round(root[0], 3), round(root[1], 3)],
                   clock_pin=ck[0]["name"], macros_known=len(rects), reach_before_um=round(before, 1))
        if before <= CLK_REACH_GATE or v["module"] in excl:
            row["action"] = "none (reach <= 220)" if before <= CLK_REACH_GATE else "excluded (own recipe sites)"
            rows.append(row)
            continue
        sites, after = plan_sites(P, legal_sites(w, h, rects), root, a.reach)
        row.update(action="sites", sites_um=sites, taps=len(sites), reach_after_um=round(after, 1))
        rows.append(row)
        out[v["view"]] = dict(module=v["module"], outline_um=[w, h], pins_sha256=v["pins_sha256"], root=row["root"],
                              clock_sites_um=sites, reach_before_um=row["reach_before_um"],
                              reach_after_um=row["reach_after_um"])
    doc = dict(schema=SCHEMA, variant=a.variant, reach_target_um=a.reach, grid_um=a.grid, halo_um=halo,
               plan=str(V["plan"]), plan_sha256=V.get("plan_sha256"),
               core_macros_sha256=sha(cmf) if cmf.is_file() else None,
               basis="COORD 11-01 10:2x DIE-HBM-57/TAPS: single-root HBM cores, explicit tap per far pin-register column "
                     "(planned clock anchors -> core_density_taps.tcl OT_DTAP_SITES); greedy cover of the free core area",
               views=out, report=rows)
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    for r in rows:
        print(f"{r['view']:72s} {r['reach_before_um']:7.1f} -> {r.get('reach_after_um', '-'):>6} taps {r.get('taps', 0):2d} "
              f"macros {r['macros_known']} {r['action']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
