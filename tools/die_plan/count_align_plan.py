#!/usr/bin/env python3
"""MESO-COUNT-1: count-aligned landed-crossing plan (K, DEPTH, start tree) from landed_phase_ocv rows.

    count_align_plan.py OCV_JSON [--corner TT_droop-regions_corelat250] [--period 833] [--aperture 104.125 (T/8)]
                        [--wander-frac 0.05] [--out JSON] [--cases TSV]

Input: the per-crossing rows of tools/s81_head/landed_phase_ocv.py (claude/land-head-2-1027@be648cbdd7): d = arr_dst -
arr_src (nominal), p_up / p_dn = derated growth / shrink of d (shared AOCV + droop model, no double count).

Model (results/meso_count_1027/README.md):
  * every region v has a count ORIGIN a_v (its start edge).  A count-aligned ring (ot_dp_clk_landing_ca) delivers sender
    word n at receiver count n + K; the word's lag is  L = (K + a_dst - a_src) * T + d.
  * correctness needs only  (GUARD_LO + 0.5) T + ap <= L <= (GUARD_HI - 0.5) T - ap  (guards fail closed outside).
  * origins come from a START WAVEFRONT over a spanning tree of crossings: child origin = 3-FF sync of the parent's
    forwarded start + PAD (ot_dp_landing_origin).  The sync adds j_e in {0,1,..} whole cycles per tree edge, a function
    of the edge's phase; j_e is CHIP-INVARIANT ("clean") when the edge's derated phase interval (+-ap) avoids the sampling
    boundary for one of the two sample edges (rise: d = 0 mod T, fall: d = T/2 mod T).  Otherwise it takes
    n_e = (#boundaries in the interval) + 1 values.
  * tree crossing:  L = sync window (width T) + post-start wander (+-w, w = wander_frac * unshared) + ap.
  * any other crossing u->v:  a_v - a_u = sum over the tree path of +-(PAD + j_e) = nominal + [-X, +Y] whole cycles with
    X + Y = sum (n_e - 1) on the path (conservative: ignores the correlation between j_e and d_uv), so
    L in [ (K + n0 - X) T + d - p_dn - ap , (K + n0 + Y) T + d + p_up + ap ].
  * K = smallest integer putting the low end at (GUARD_LO + 0.5) T; DEPTH 4 (guards 0,4) if the high end fits under
    3.5 T, else DEPTH 8 (guards 0,8), else FAIL.  Receiver latency in its own counts = K + 1 (RDREG), logical latency
    of the crossing = K + 1 + n0 (n0 = nominal origin difference, a compile-time constant).  Old ring = 3 (OFFSET 2 +
    RDREG) and requires the derated d inside +-T/2.
"""
import argparse
import json
import math
import sys
from collections import defaultdict


def interval_boundaries(lo, hi, T, off):
    """number of points off + k*T inside [lo, hi]"""
    return max(0, math.floor((hi - off) / T) - math.ceil((lo - off) / T) + 1)


def edge_values(r, T, ap):
    """(n_values, sample_edge) for the start-sync across crossing r (best of the two sample edges)"""
    lo, hi = r["d_ps"] - r["p_dn_ps"] - ap, r["d_ps"] + r["p_up_ps"] + ap
    best = None
    for edge, off in (("rise", 0.0), ("fall", T / 2)):
        n = interval_boundaries(lo, hi, T, off) + 1
        if best is None or n < best[0]:
            best = (n, edge)
    return best


def j_nominal(d, T, edge):
    # whole cycles the sync adds at the nominal phase (relative, only differences along a path matter)
    off = 0.0 if edge == "rise" else T / 2
    return -math.floor((d - off) / T)


class DSU:
    def __init__(s):
        s.p = {}

    def f(s, x):
        s.p.setdefault(x, x)
        while s.p[x] != x:
            s.p[x] = s.p[s.p[x]]
            x = s.p[x]
        return x

    def u(s, a, b):
        a, b = s.f(a), s.f(b)
        if a == b:
            return False
        s.p[a] = b
        return True


def plan(rows, T=833.0, ap=25.0, wander_frac=0.05):
    regions = sorted({r["src"] for r in rows} | {r["dst"] for r in rows})
    # candidate tree crossing per unordered region pair = fewest sync values, then smallest spread
    for r in rows:
        r["_nv"], r["_edge"] = edge_values(r, T, ap)
        r["_s"] = r["p_up_ps"] + r["p_dn_ps"]
    best = {}
    for r in rows:
        if r["src"] == r["dst"]:
            continue
        k = tuple(sorted((r["src"], r["dst"])))
        key = (r["_nv"], r["_s"], r["port"])
        if k not in best or key < best[k][0]:
            best[k] = (key, r)
    ds = DSU()
    tree = {}
    for k, (key, r) in sorted(best.items(), key=lambda kv: kv[1][0]):
        if ds.u(*k):
            tree[k] = r
    comps = {ds.f(x) for x in regions}
    # rooted tree: BFS from the region with the most tree edges
    adj = defaultdict(list)
    for (a, b), r in tree.items():
        adj[a].append((b, r))
        adj[b].append((a, r))
    root = max(regions, key=lambda x: len(adj[x])) if regions else None
    par, depth, order = {root: None}, {root: 0}, [root]
    for x in order:
        for y, r in adj[x]:
            if y not in par:
                par[y] = (x, r)
                depth[y] = depth[x] + 1
                order.append(y)
    # nominal origin (in whole cycles, PAD omitted: it is common to every tree edge and cancels in K choice through
    # n0 only as a constant the binder adds) and ambiguity counts along root paths
    a0, amb = {root: 0}, {root: 0}
    for x in order[1:]:
        p, r = par[x]
        # child origin relative to parent: PAD + j_e; j_e defined for the direction parent -> child
        d = r["d_ps"] if r["src"] == p else -r["d_ps"]
        a0[x] = a0[p] + 1 + j_nominal(d, T, r["_edge"])
        amb[x] = amb[p] + (r["_nv"] - 1)

    # per tree edge (parent -> child orientation): deviation range of j_e from its nominal over the derated phase
    dev = {}
    for x in order[1:]:
        p, r = par[x]
        if r["src"] == p:
            dn, lo, hi = r["d_ps"], r["d_ps"] - r["p_dn_ps"] - ap, r["d_ps"] + r["p_up_ps"] + ap
        else:
            dn, lo, hi = -r["d_ps"], -r["d_ps"] - r["p_up_ps"] - ap, -r["d_ps"] + r["p_dn_ps"] + ap
        jn = j_nominal(dn, T, r["_edge"])
        dev[x] = (j_nominal(hi, T, r["_edge"]) - jn, j_nominal(lo, T, r["_edge"]) - jn)

    def path_amb(u, v):
        """whole-cycle deviation range of (a_v - a_u) from nominal: sum over v's side minus sum over u's side"""
        su, sv = u, v
        ulo = uhi = vlo = vhi = 0
        while depth[su] > depth[sv]:
            ulo += dev[su][0]; uhi += dev[su][1]; su = par[su][0]
        while depth[sv] > depth[su]:
            vlo += dev[sv][0]; vhi += dev[sv][1]; sv = par[sv][0]
        while su != sv:
            ulo += dev[su][0]; uhi += dev[su][1]; su = par[su][0]
            vlo += dev[sv][0]; vhi += dev[sv][1]; sv = par[sv][0]
        return vlo - uhi, vhi - ulo

    tree_ports = {r["port"] for r in tree.values()}
    out = []
    lo_win = 0.5 * T + ap
    for r in rows:
        u, v = r["src"], r["dst"]
        w = wander_frac * max(r.get("unshared_a_ps", 0.0), r.get("unshared_b_ps", 0.0))
        if r["port"] in tree_ports:
            kind, amb_n, amb = "tree", 0, (0, 0)
            # sync window: lag of the start edge lies in [c, c + T); the binder sets K so c = lo_win (+ wander)
            width = T + 2 * w
            L_lo_rel, L_hi_rel = 0.0, width  # relative to the window start, chosen with K below
            K_rel = None
        else:
            kind = "nontree"
            amb = path_amb(u, v) if u != v else (0, 0)
            amb_n = amb[1] - amb[0]
            dlo, dhi = r["d_ps"] - r["p_dn_ps"] - ap, r["d_ps"] + r["p_up_ps"] + ap
            n0 = a0[v] - a0[u] if (u in a0 and v in a0) else 0
            # L = (K + n0 + m) T + d, m in [-amb, +amb] worst case split; conservatively both sides
            L_lo_rel, L_hi_rel = dlo + amb[0] * T, dhi + amb[1] * T
            width = L_hi_rel - L_lo_rel
        # choose the lag offset (K + n0) T so the low end sits at >= lo_win
        if kind == "tree":
            # the start sync puts the tree crossing's lag in [c, c + T) at start (c = lo_win + w), then it wanders +-w;
            # the nominal lag is the point of that window congruent to d, and the logical latency follows from it
            c = lo_win + w
            L_nom = c + ((r["d_ps"] - c) % T)
            L_lo, L_hi = lo_win, c + T + w + ap
            lat = round((L_nom - r["d_ps"]) / T)
        else:
            kt = math.ceil((lo_win - L_lo_rel) / T)
            L_lo, L_hi = kt * T + L_lo_rel, kt * T + L_hi_rel
            lat = kt
        depth_ = 4 if L_hi <= 3.5 * T - ap + 1e-9 else (8 if L_hi <= 7.5 * T - ap + 1e-9 else None)
        old_ok = r["margin_ps"] >= 0  # old ring: derated |d| inside the one-period placement window
        old_vals = interval_boundaries(r["d_ps"] - r["p_dn_ps"], r["d_ps"] + r["p_up_ps"], T, T / 2) + 1
        out.append(dict(port=r["port"], src=u, dst=v, kind=kind, d_ps=r["d_ps"], p_up_ps=r["p_up_ps"], p_dn_ps=r["p_dn_ps"],
                        wander_ps=round(w, 1), path_ambiguous_cycles=amb_n, L_lo_ps=round(L_lo, 1), L_hi_ps=round(L_hi, 1),
                        L_width_ps=round(L_hi - L_lo, 1), depth=depth_, lat_cycles=lat + 1 if depth_ else None,
                        old_ring_lat_values=old_vals, old_ring_margin_ps=r["margin_ps"], old_ring_ok=old_ok))
    summ = dict(regions=len(regions), tree_components=len(comps), tree_edges=len(tree), tree_root=root,
                tree_edges_clean=sum(1 for r in tree.values() if r["_nv"] == 1),
                tree_edges_ambiguous=[dict(port=r["port"], src=r["src"], dst=r["dst"], values=r["_nv"],
                                           spread_ps=round(r["_s"], 1)) for r in tree.values() if r["_nv"] > 1],
                crossings=len(out), depth4=sum(1 for o in out if o["depth"] == 4), depth8=sum(1 for o in out if o["depth"] == 8),
                fail=sum(1 for o in out if o["depth"] is None),
                max_path_ambiguous_cycles=max((o["path_ambiguous_cycles"] for o in out), default=0),
                max_L_width_ps=max((o["L_width_ps"] for o in out), default=0),
                lat_hist={str(k): sum(1 for o in out if o["lat_cycles"] == k) for k in sorted({o["lat_cycles"] for o in out
                                                                                               if o["lat_cycles"]})},
                lat_total_vs_old3=sum((o["lat_cycles"] or 0) - 3 for o in out),
                old_ring_not_cycle_fixed=sum(1 for o in out if o["old_ring_lat_values"] > 1),
                old_ring_fail_margin=sum(1 for o in out if not o["old_ring_ok"]))
    return summ, out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ocv_json")
    ap.add_argument("--corner", default="TT_droop-regions_corelat250,FF_droop-regions_corelat202.5",
                    help="comma list: K / DEPTH must hold on every listed corner, so each crossing's derated phase "
                         "interval is the UNION over the corners (d = the first corner's nominal)")
    ap.add_argument("--period", type=float, default=833.0)
    ap.add_argument("--aperture", type=float, default=833.0 / 8, help="ps kept from each window edge (default T/8 = "
                    "the formal proof's time resolution, which also covers the guard sampler aperture)")
    ap.add_argument("--wander-frac", type=float, default=0.05)
    ap.add_argument("--out")
    ap.add_argument("--cases", help="TSV for the Verilator bench: port K_lat DEPTH L_ps (lo / mid / hi per crossing)")
    a = ap.parse_args(argv)
    d = json.load(open(a.ocv_json))
    cs = a.corner.split(",")
    rows = [dict(r) for r in d["corners"][cs[0]]["all"]]
    for c in cs[1:]:
        other = {r["port"]: r for r in d["corners"][c]["all"]}
        for r in rows:
            o = other[r["port"]]
            lo = min(r["d_ps"] - r["p_dn_ps"], o["d_ps"] - o["p_dn_ps"])
            hi = max(r["d_ps"] + r["p_up_ps"], o["d_ps"] + o["p_up_ps"])
            r["p_dn_ps"], r["p_up_ps"] = r["d_ps"] - lo, hi - r["d_ps"]
            r["margin_ps"] = min(r["margin_ps"], o["margin_ps"])
            for k in ("unshared_a_ps", "unshared_b_ps"):
                r[k] = max(r.get(k, 0.0), o.get(k, 0.0))
    summ, out = plan(rows, a.period, a.aperture, a.wander_frac)
    summ.update(corner=a.corner, period_ps=a.period, aperture_ps=a.aperture, wander_frac=a.wander_frac, source=a.ocv_json)
    print(json.dumps(summ, indent=1))
    if a.out:
        json.dump(dict(summary=summ, crossings=out), open(a.out, "w"), indent=0)
    if a.cases:
        with open(a.cases, "w") as f:
            for o in out:
                if o["depth"] is None:
                    continue
                for L in (o["L_lo_ps"], 0.5 * (o["L_lo_ps"] + o["L_hi_ps"]), o["L_hi_ps"]):
                    f.write(f"{o['port']}\t{o['depth']}\t{int(round(L))}\n")
    return 0 if summ["fail"] == 0 and summ["tree_components"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
