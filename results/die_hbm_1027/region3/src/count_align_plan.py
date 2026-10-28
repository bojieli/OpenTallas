#!/usr/bin/env python3
"""MESO-COUNT-1/-2: count-aligned landed-crossing plan (RTL K, DEPTH, directed start tree, start offsets).

    count_align_plan.py OCV_JSON [--corner TT_droop-regions_corelat250,FF_droop-regions_corelat202.5] [--period 833]
                        [--aperture 104.125 (T/8)] [--sync-aperture 26.5] [--wander-frac 0.05] [--pad 0]
                        [--mc-chips 2000] [--out JSON] [--cases TSV]

Input: the per-crossing rows of tools/s81_head/landed_phase_ocv.py: d = arr_dst - arr_src (nominal), p_up / p_dn =
derated growth / shrink of d (shared AOCV + droop model, no double count).  K / DEPTH hold on the UNION of the corners.

Model (results/meso_count_1027/README.md; RTL rtl/common/ot_dp_clk_landing_ca.sv):
  * region v has a count ORIGIN a_v (the first edge whose readers see their start high).  A count-aligned ring with RTL
    parameter K delivers sender word n at receiver count n + K; the word's lag is  L = (K + a_dst - a_src) T + d.
    Correct iff 0.5 T <= L <= (DEPTH - 0.5) T (guards 0 / DEPTH fail closed outside); the plan keeps ap from each edge.
  * START WAVEFRONT over a DIRECTED spanning tree of crossings (the parent's start is forwarded beside a crossing
    whose src is the parent, ot_dp_landing_origin in the child; one-way crossings cannot carry it backwards):
        a_child - a_parent = PAD + 2 + J(d),  J(d) = -floor((d - off) / T),  off = 0 (rise) or T/2 (EDGE_FALL)
    i.e. 3 sync flops + PAD counted from the parent's start LAUNCH edge (a_parent - 1).  Proven for every phase at T/32
    by rtl/test/meso/formal_origin (a_c - a_p in one value when d is > the sync aperture away from off, else the
    lag phase  phi = d + J T  lies in [off - sap, off + T + sap]).
  * per tree edge the sample edge (rise / fall) is the one whose boundary off + kT the derated interval +-ap avoids
    (CLEAN: J chip-invariant), ties -> larger distance; else AMBIGUOUS (J takes n values across chips).
  * K_eff = K + n0, n0 = a_dst - a_src nominal (compile-time, sum of PAD + 2 + J_nominal along the tree path):
        L = K_eff T + rel,  rel in [rel_lo, rel_hi]:
      - clean tree crossing / any crossing whose tree path is clean: rel = derated d interval  [d - p_dn, d + p_up];
      - other crossings: + [amb_lo, amb_hi] T from the ambiguous tree edges on the path (conservative, uncorrelated);
      - the ambiguous tree crossing itself: rel = phi window - J_nom T = [off - sap, off + T + sap] - J_nom T;
      - every crossing: +-wander (wander_frac x unshared, post-start drift).
    K_eff = smallest integer with K_eff T + rel_lo >= 0.5 T + ap;  DEPTH 4 if K_eff T + rel_hi <= 3.5 T - ap, else 8 if
    <= 7.5 T - ap, else FAIL.  RTL K = K_eff - n0.  Logical latency K_eff + 1 (in the root's count frame), receiver-count
    latency K + 1.  Margins: L_lo - 0.5 T and (DEPTH - 0.5) T - L_hi (ap included, gate >= 100 ps).
  * --mc-chips: Monte-Carlo chip check of the EMITTED RTL parameters: per chip every crossing's d uniform in its derated
    interval (+ endpoints), wander +-w, every tree edge's J from its own d (either value inside the sync aperture),
    origins summed down the tree, L = (K + a_dst - a_src) T + d must lie in [0.5 T, (DEPTH - 0.5) T].
"""
import argparse
import heapq
import json
import math
import random
import sys
from collections import defaultdict


def interval_boundaries(lo, hi, T, off):
    """number of points off + k*T inside [lo, hi]"""
    return max(0, math.floor((hi - off) / T) - math.ceil((lo - off) / T) + 1)


def boundary_dist(lo, hi, T, off):
    """distance from [lo, hi] to the nearest point off + k*T (negative if one lies inside)"""
    if interval_boundaries(lo, hi, T, off):
        return -1.0
    k = math.floor((lo - off) / T)
    return min(lo - (off + k * T), off + (k + 1) * T - hi)


def J(d, T, off):
    """whole cycles the start sync adds beyond PAD + 2 at static phase d (receiver minus sender)"""
    return -math.floor((d - off) / T)


def sync_choice(r, T, ap):
    """(n_values, edge, off, dist): best sample edge for the start sync across crossing r"""
    lo, hi = r["lo"], r["hi"]
    best = None
    for edge, off in (("rise", 0.0), ("fall", T / 2)):
        n = interval_boundaries(lo - ap, hi + ap, T, off) + 1
        key = (n, -boundary_dist(lo, hi, T, off))
        if best is None or key < best[0]:
            best = (key, (n, edge, off, boundary_dist(lo, hi, T, off)))
    return best[1]


def directed_tree(rows, regions):
    """directed spanning tree (start flows src -> dst) with the fewest ambiguous edges: per root, levels of equal
    ambiguity A(v) (0-1 BFS); inside a level attach by CLEAN edges first, open a level-k node by one ambiguous edge from
    level k-1 only when no clean edge reaches it (greedy: the entry that then reaches most nodes); best root over all"""
    cand = {}
    for r in rows:
        if r["src"] == r["dst"]:
            continue
        k = (r["src"], r["dst"])
        key = (r["_nv"] - 1, -r["_dist"], r["port"])
        if k not in cand or key < cand[k][0]:
            cand[k] = (key, r)
    out = defaultdict(list)
    for (a, b), (key, r) in sorted(cand.items()):
        out[a].append((b, r))
    best = None
    for root in regions:
        A = {root: 0}
        dq = [(0, root)]
        while dq:
            am, x = heapq.heappop(dq)
            if am > A[x]:
                continue
            for y, r in out[x]:
                na = am + r["_nv"] - 1
                if y not in A or na < A[y]:
                    A[y] = na
                    heapq.heappush(dq, (na, y))
        par, hops = {root: None}, {root: 0}

        def grow(front):
            q = list(front)
            for x in q:
                for y, r in out[x]:
                    if r["_nv"] == 1 and y not in par and A.get(y) == A[x]:
                        par[y], hops[y] = (x, r), hops[x] + 1
                        q.append(y)
        grow([root])
        for lev in range(1, max(A.values()) + 1):
            todo = {v for v, a in A.items() if a == lev and v not in par}
            while todo:
                opts = []
                for x in [v for v in par if A[v] < lev]:
                    for y, r in out[x]:
                        if y in todo and A[x] + r["_nv"] - 1 == lev:
                            seen, q = {y}, [y]
                            for z in q:
                                for z2, r2 in out[z]:
                                    if r2["_nv"] == 1 and z2 in todo and z2 not in seen:
                                        seen.add(z2); q.append(z2)
                            opts.append((-len(seen), hops[x], -r["_dist"], r["port"], x, y, r))
                if not opts:
                    break
                _, _, _, _, x, y, r = min(opts)
                par[y], hops[y] = (x, r), hops[x] + 1
                grow([y])
                todo = {v for v in todo if v not in par}
        n_amb = sum(1 for v in par.values() if v and v[1]["_nv"] > 1)
        key = (len(regions) - len(par), n_amb, max(A[v] for v in par), max(hops.values()), root)
        if best is None or key < best[0]:
            best = (key, root, par)
    return best[1], best[2]


def plan(rows, T=833.0, ap=833.0 / 8, wander_frac=0.05, sync_ap=26.5, pad=0):
    for r in rows:
        r["lo"], r["hi"] = r["d_ps"] - r["p_dn_ps"], r["d_ps"] + r["p_up_ps"]
        r["_nv"], r["_edge"], r["_off"], r["_dist"] = sync_choice(r, T, ap)
        r["_w"] = wander_frac * max(r.get("unshared_a_ps", 0.0), r.get("unshared_b_ps", 0.0))
    regions = sorted({r["src"] for r in rows} | {r["dst"] for r in rows})
    root, par = directed_tree(rows, regions)
    # BFS order down the tree
    kids = defaultdict(list)
    for x, v in par.items():
        if v:
            kids[v[0]].append(x)
    order, depth = [root], {root: 0}
    for x in order:
        for y in sorted(kids[x]):
            depth[y] = depth[x] + 1
            order.append(y)
    a0, dev, jn = {root: 0}, {}, {}
    for x in order[1:]:
        p, r = par[x]
        jn[x] = J(r["d_ps"], T, r["_off"])
        a0[x] = a0[p] + pad + 2 + jn[x]
        # J deviation range over the derated interval +- ap (J decreases with d)
        dev[x] = (J(r["hi"] + ap, T, r["_off"]) - jn[x], J(r["lo"] - ap, T, r["_off"]) - jn[x])

    def path_amb(u, v):
        """whole-cycle deviation range of (a_v - a_u) from nominal"""
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

    tree_port = {par[x][1]["port"]: x for x in order[1:]}
    out = []
    lo_win = 0.5 * T + ap
    for r in rows:
        u, v = r["src"], r["dst"]
        if u not in a0 or v not in a0:
            out.append(dict(port=r["port"], src=u, dst=v, kind="unreached", depth=None, lat_cycles=None, K=None))
            continue
        w = r["_w"]
        n0 = a0[v] - a0[u]
        child = tree_port.get(r["port"])
        if child is not None and r["_nv"] > 1:
            kind, amb = "tree_ambiguous", (0, 0)
            rel_lo = r["_off"] - sync_ap - jn[child] * T
            rel_hi = r["_off"] + T + sync_ap - jn[child] * T
        else:
            kind = "tree" if child is not None else "nontree"
            amb = path_amb(u, v) if (u != v and child is None) else (0, 0)
            rel_lo, rel_hi = r["lo"] + amb[0] * T, r["hi"] + amb[1] * T
        rel_lo, rel_hi = rel_lo - w, rel_hi + w
        k_eff = math.ceil((lo_win - rel_lo) / T - 1e-12)
        L_lo, L_hi = k_eff * T + rel_lo, k_eff * T + rel_hi
        dep = 4 if L_hi <= 3.5 * T - ap + 1e-9 else (8 if L_hi <= 7.5 * T - ap + 1e-9 else None)
        old_vals = interval_boundaries(r["lo"], r["hi"], T, T / 2) + 1
        out.append(dict(port=r["port"], src=u, dst=v, kind=kind, d_ps=r["d_ps"], p_up_ps=r["p_up_ps"],
                        p_dn_ps=r["p_dn_ps"], wander_ps=round(w, 1), path_ambiguous_cycles=amb[1] - amb[0],
                        n0=n0, K_eff=k_eff, K=k_eff - n0, L_lo_ps=round(L_lo, 1), L_hi_ps=round(L_hi, 1),
                        L_width_ps=round(L_hi - L_lo, 1), depth=dep,
                        margin_lo_ps=round(L_lo - 0.5 * T, 1) if dep else None,
                        margin_hi_ps=round((dep - 0.5) * T - L_hi, 1) if dep else None,
                        lat_cycles=k_eff + 1 if dep else None, rx_lat_counts=k_eff - n0 + 1 if dep else None,
                        rtl=dict(module="ot_dp_clk_landing_ca", DEPTH=dep, K=k_eff - n0, GUARD_LO=0, GUARD_HI=dep)
                        if dep else None,
                        old_ring_lat_values=old_vals, old_ring_margin_ps=r.get("margin_ps"),
                        old_ring_ok=(r.get("margin_ps", 0) >= 0)))
    regs = []
    for x in order:
        e = None
        if par[x]:
            p, r = par[x]
            e = dict(parent=p, port=r["port"], edge=r["_edge"], sync_values=r["_nv"],
                     sync_dist_ps=round(r["_dist"], 1), J_nominal=jn[x], J_dev=list(dev[x]),
                     offset_from_parent=pad + 2 + jn[x],
                     rtl=dict(module="ot_dp_landing_origin", PAD=pad, EDGE_FALL=int(r["_edge"] == "fall")))
        regs.append(dict(region=x, origin_cycles=a0[x], tree_depth=depth[x], start_from=e))
    ok = [o for o in out if o.get("depth")]
    amb_edges = [g for g in regs if g["start_from"] and g["start_from"]["sync_values"] > 1]
    summ = dict(regions=len(regions), regions_reached=len(a0), tree_root=root, tree_edges=len(order) - 1,
                tree_edges_clean=len(order) - 1 - len(amb_edges),
                tree_edges_ambiguous=[dict(region=g["region"], **{k: g["start_from"][k] for k in
                                      ("parent", "port", "edge", "sync_values", "sync_dist_ps")}) for g in amb_edges],
                tree_edges_fall=sum(1 for g in regs if g["start_from"] and g["start_from"]["edge"] == "fall"),
                max_tree_depth=max(depth.values()), min_sync_dist_clean_ps=min(
                    (g["start_from"]["sync_dist_ps"] for g in regs if g["start_from"] and g["start_from"]["sync_values"] == 1),
                    default=None),
                crossings=len(out), depth4=sum(1 for o in ok if o["depth"] == 4),
                depth8=sum(1 for o in ok if o["depth"] == 8), fail=len(out) - len(ok),
                max_path_ambiguous_cycles=max((o.get("path_ambiguous_cycles", 0) for o in out), default=0),
                worst_margin_lo_ps=min((o["margin_lo_ps"] for o in ok), default=None),
                worst_margin_lo_port=min(ok, key=lambda o: o["margin_lo_ps"])["port"] if ok else None,
                worst_margin_hi_ps=min((o["margin_hi_ps"] for o in ok), default=None),
                worst_margin_hi_port=min(ok, key=lambda o: o["margin_hi_ps"])["port"] if ok else None,
                below_100ps=sum(1 for o in ok if min(o["margin_lo_ps"], o["margin_hi_ps"]) < 100),
                lat_hist={str(k): sum(1 for o in ok if o["lat_cycles"] == k) for k in sorted({o["lat_cycles"] for o in ok})},
                K_hist={str(k): sum(1 for o in ok if o["K"] == k) for k in sorted({o["K"] for o in ok})},
                lat_total_vs_old3=sum(o["lat_cycles"] - 3 for o in ok),
                old_ring_not_cycle_fixed=sum(1 for o in out if o.get("old_ring_lat_values", 1) > 1),
                old_ring_fail_margin=sum(1 for o in out if o.get("old_ring_ok") is False))
    return summ, out, regs


def mc_check(rows, out, regs, T=833.0, chips=2000, sync_ap=26.5, seed=1):
    """Monte-Carlo chips against the EMITTED RTL K / DEPTH / PAD / EDGE_FALL: returns (#chips, #violations, worst lo,
    worst hi) with margins measured to the guard edges 0.5 T / (DEPTH - 0.5) T (no ap)."""
    rnd = random.Random(seed)
    byp = {r["port"]: r for r in rows}
    pl = {o["port"]: o for o in out if o.get("depth")}
    bad, wl, wh = 0, 1e9, 1e9
    for c in range(chips):
        mode = c % 3  # 0: uniform, 1: low endpoints, 2: high endpoints
        d = {}
        for p, r in byp.items():
            x = rnd.uniform(r["lo"], r["hi"]) if mode == 0 else (r["lo"] if mode == 1 else r["hi"])
            if mode and rnd.random() < 0.5:
                x = r["hi"] if mode == 1 else r["lo"]
            d[p] = x
        a = {}
        for g in regs:
            e = g["start_from"]
            if e is None:
                a[g["region"]] = 0
                continue
            off = 0.0 if e["edge"] == "rise" else T / 2
            x = d[e["port"]]
            j = J(x, T, off)
            ph = (x - off) % T
            if ph < sync_ap and rnd.random() < 0.5:
                j += 1           # sampled late (just after the boundary, metastable -> next edge)
            elif ph > T - sync_ap and rnd.random() < 0.5:
                j -= 1           # sampled early
            a[g["region"]] = a[e["parent"]] + e["rtl"]["PAD"] + 2 + j
        for p, o in pl.items():
            w = o["wander_ps"] * rnd.uniform(-1, 1)
            L = (o["K"] + a[o["dst"]] - a[o["src"]]) * T + d[p] + w
            lo, hi = L - 0.5 * T, (o["depth"] - 0.5) * T - L
            wl, wh = min(wl, lo), min(wh, hi)
            bad += (lo < 0 or hi < 0)
    return chips, bad, round(wl, 1), round(wh, 1)


def load_rows(ocv_json, corners):
    d = json.load(open(ocv_json))
    cs = corners.split(",")
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
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ocv_json")
    ap.add_argument("--corner", default="TT_droop-regions_corelat250,FF_droop-regions_corelat202.5",
                    help="comma list: K / DEPTH must hold on every listed corner (union of the derated intervals; "
                         "d = the first corner's nominal)")
    ap.add_argument("--period", type=float, default=833.0)
    ap.add_argument("--aperture", type=float, default=833.0 / 8, help="ps kept from each window edge and from each "
                    "sync boundary for a CLEAN tree edge (default T/8)")
    ap.add_argument("--sync-aperture", type=float, default=26.5, help="metastability aperture of the first sync stage "
                    "(ps): an ambiguous tree crossing's lag phase lies in [off - sap, off + T + sap]")
    ap.add_argument("--wander-frac", type=float, default=0.05, help="post-start drift +- frac x unshared, all crossings")
    ap.add_argument("--pad", type=int, default=0, help="PAD flops of every ot_dp_landing_origin")
    ap.add_argument("--mc-chips", type=int, default=0)
    ap.add_argument("--out")
    ap.add_argument("--cases", help="TSV for the Verilator bench: port DEPTH L_ps (lo / mid / hi per crossing)")
    a = ap.parse_args(argv)
    rows = load_rows(a.ocv_json, a.corner)
    summ, out, regs = plan(rows, a.period, a.aperture, a.wander_frac, a.sync_aperture, a.pad)
    summ.update(corner=a.corner, period_ps=a.period, aperture_ps=a.aperture, sync_aperture_ps=a.sync_aperture,
                wander_frac=a.wander_frac, pad=a.pad, source=a.ocv_json)
    if a.mc_chips:
        n, bad, wl, wh = mc_check(rows, out, regs, a.period, a.mc_chips, a.sync_aperture)
        summ["mc"] = dict(chips=n, violations=bad, worst_lo_to_guard_ps=wl, worst_hi_to_guard_ps=wh)
    print(json.dumps({k: v for k, v in summ.items() if k != "tree_edges_ambiguous"}, indent=1))
    if a.out:
        json.dump(dict(summary=summ, regions=regs, crossings=out), open(a.out, "w"), indent=0)
    if a.cases:
        with open(a.cases, "w") as f:
            for o in out:
                if not o.get("depth"):
                    continue
                for L in (o["L_lo_ps"], 0.5 * (o["L_lo_ps"] + o["L_hi_ps"]), o["L_hi_ps"]):
                    f.write(f"{o['port']}\t{o['depth']}\t{int(round(L))}\n")
    return 0 if summ["fail"] == 0 and summ["regions_reached"] == summ["regions"] else 1


if __name__ == "__main__":
    sys.exit(main())

# --- DSU shim (from main count_align_plan.py, used by locality.cap_plan_corners; DIE-HBM-3 region3 estimate only)
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

