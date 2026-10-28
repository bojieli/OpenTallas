#!/usr/bin/env python3
"""MESO-COUNT-1/-2: count-aligned landed-crossing plan (RTL K, DEPTH, directed start tree, start offsets).

    count_align_plan.py OCV_JSON [--corner TT_droop-regions_corelat250,FF_droop-regions_corelat202.5] [--period 833]
                        [--aperture 104.125 (T/8)] [--sync-aperture 26.5] [--wander-frac 0.05] [--pad 0]
                        [--mc-chips 2000] [--out JSON] [--cases TSV]
                        [--sta-proof PROOF_DIR --sta-plan die_plan.json [--sta-clock-cal spice] [--sta-cppr-lca]]

--sta-proof (DIE-HEAD-5, ONE interval model): every row's derated interval becomes its hull with the d interval
die_sta_related --count-align gates on (die_sta_related.count_align_d_intervals via sta_d_intervals, same proof / clock
cal / CPPR node), so plan margins and sample-edge clearances are lower bounds of the gate numbers.

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


def sync_choice(r, T, ap, start_skew=(0.0, 0.0), sync_ap=26.5):
    """(n_values, edge, off, dist): best sample edge for the start sync across crossing r.
    start_skew (lo, hi) ps (DIE-HEAD-4b, COORD NC-HEAD-PART): start arrival at the child's first sync flop minus the
    forwarded clock (clk->Q of the parent origin register + start wire - fclk wire; die_sta_related start row).  The
    sync samples the phase d - skew.  n (sample values over the static interval +- ap) stays the primary key, so the
    start tree and the J deviation ranges are unchanged; among the edges with the fewest values an edge is kept only if
    it also clears the skew.  Hard (the die STA start row): skewed interval [lo - hi_s, hi - lo_s] >= sync aperture
    from the boundary off + kT and static distance - sync aperture >= max|skew|.  Soft: the skewed interval >= ap
    (T/8 >= 100 ps) from the boundary.  Order: fewest values, smaller hard shortfall, smaller soft shortfall, larger
    static distance (an edge that clears both keeps the static order).  dist stays the STATIC
    distance (start_skew_limit = dist - sync aperture, as die_sta_related reads it).  Default (0, 0): unchanged."""
    lo, hi = r["lo"], r["hi"]
    s_lo, s_hi = float(start_skew[0]), float(start_skew[1])
    skewed = bool(s_lo or s_hi)
    smax = max(abs(s_lo), abs(s_hi))
    best = None
    for edge, off in (("rise", 0.0), ("fall", T / 2)):
        n = interval_boundaries(lo - ap, hi + ap, T, off) + 1
        dist = boundary_dist(lo, hi, T, off)
        hard = soft = 0.0
        if skewed:
            sd = boundary_dist(lo - s_hi, hi - s_lo, T, off)
            hard = max(0.0, sync_ap - sd, smax - (dist - sync_ap))
            soft = max(0.0, ap - sd)
        key = (n, hard, soft, -dist)
        if best is None or key < best[0]:
            best = (key, (n, edge, off, dist))
    return best[1]


# union-find kept for tools/die_plan/locality.py (connected components before planning)


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


def plan(rows, T=833.0, ap=833.0 / 8, wander_frac=0.05, sync_ap=26.5, pad=0, edge_pad=None, start_skew=(0.0, 0.0),
         skew_clean=False, _pad_pass=False, tree_parent=None, max_depth=8):
    """edge_pad {tree port or child region: PAD}: per-start-tree-edge PAD overriding the default `pad` (MESO-RECONCILE-1,
    COORD 10-27).  An edge PAD p_e >= pad delays the child's origin by p_e - pad counts and HOLDS the tree crossing's RTL K
    at its default-PAD value, so that crossing's lag (and latency) grow by (p_e - pad) T; every other crossing's K is
    re-chosen against the new origins (its latency is unchanged).
    skew_clean (MESO-START-2, COORD 03:0x, opt-in, needs start_skew): on the unchanged start tree, a tree edge is CLEAN
    only if its static sync distance >= sync_ap + max|skew| (QC 26.5 + 87.5 = 114 ps: die_sta_related's clean start
    row); every other tree edge is AMBIGUOUS: its J deviation range covers the
    skewed sampled phase [lo - s_hi - sap, hi - s_lo + sap], its tree crossing keeps the plan sync window and needs both
    ring margins >= 100 + max|skew| (die_sta_related ambiguous start row: margin - 100 >= |skew|).  The high side is
    met by the DEPTH choice; the low side, where short, by PAD + 1 on that edge (OWNER 12.15b; +1 cycle on the tree
    crossing, a parameter of the proven ot_dp_landing_origin, no new RTL form).  Default False: unchanged.
    tree_parent {child region: port} (MESO-START-2, COORD 03:4x, opt-in): re-parent the child (with its subtree) onto
    the given crossing (src -> child) after the min-ambiguity tree is built, so a region pair that has no bound crossing
    gets its crossing as the start edge itself (no path ambiguity); refused if the src lies in the child's subtree.
    max_depth (DIE-S81-11, METHODOLOGY 12.16 b(iii), opt-in): largest standard ring DEPTH, 8 (default, unchanged) or 16
    (RTL proof: results/die_s81_11_1028/D16.md, ot_dp_clk_landing_ca lag sweep [0.5, 15.5] T, mutants caught); a
    crossing takes the smallest of 4 / 8 / 16 whose window holds L_hi with ap (16 only when max_depth = 16)."""
    if max_depth not in (8, 16):
        raise ValueError(f"max_depth {max_depth}: standard ring depths are 8 or 16")
    smax = max(abs(float(start_skew[0])), abs(float(start_skew[1])))
    if skew_clean and not _pad_pass:
        if not smax:
            raise ValueError("skew_clean needs a nonzero start_skew (--start-skew LO,HI)")
        need = 100.0 + smax
        args = (T, ap, wander_frac, sync_ap, pad)
        s0, out0, regs0 = plan([dict(r) for r in rows], *args, edge_pad, start_skew, True, True, tree_parent, max_depth)
        byp = {o["port"]: o for o in out0}
        ep = dict(edge_pad or {})
        add = {}
        for g in regs0:
            e = g["start_from"]
            if not e or e["sync_values"] == 1:
                continue
            o = byp[e["port"]]
            if o.get("depth") and o["margin_lo_ps"] < need:
                ep.pop(e["port"], None)
                ep[g["region"]] = add[g["region"]] = int(e["rtl"]["PAD"]) + 1
        summ, out, regs = plan(rows, *args, ep, start_skew, True, True, tree_parent, max_depth)
        sn, outn, _ = plan([dict(r) for r in rows], *args, edge_pad, start_skew, tree_parent=tree_parent,
                           max_depth=max_depth)

        def lat(xs):
            return sum(o["lat_cycles"] for o in xs if o.get("lat_cycles") is not None)
        both = {o["port"] for o in outn if o.get("lat_cycles") is not None} & \
            {o["port"] for o in out if o.get("lat_cycles") is not None}
        amb = [g for g in regs if g["start_from"] and g["start_from"]["sync_values"] > 1]
        summ["start_skew_clean"] = dict(
            need_clean_dist_ps=round(sync_ap + smax, 1), need_amb_margin_ps=round(need, 1),
            tree_edges_amb_by_skew=sum(1 for g in amb if g["start_from"]["sync_dist_ps"] > ap),
            tree_edges_amb_by_skew_J_free=sum(1 for g in amb if g["start_from"]["sync_dist_ps"] > ap
                                              and g["start_from"]["J_dev"] != [0, 0]),
            padded_edges=len(add), pad_plus1={x: add[x] for x in sorted(add)},
            added_latency_cycles_pad=lat(out) - lat(out0),
            added_latency_cycles_vs_noflag=lat(o for o in out if o["port"] in both)
            - lat(o for o in outn if o["port"] in both),
            crossings_lat_changed_vs_noflag=sum(1 for a, b in zip(outn, out) if a.get("lat_cycles") != b.get("lat_cycles")),
            fail_noflag=sn["fail"],
            note="added latency (12.15c cost, record only): _pad = sum lat_cycles vs the same tree at the input PAD; "
                 "_vs_noflag = vs the plan without --start-skew-clean, over crossings that pass in both")
        return summ, out, regs
    for r in rows:
        r["lo"], r["hi"] = r["d_ps"] - r["p_dn_ps"], r["d_ps"] + r["p_up_ps"]
        r["_nv"], r["_edge"], r["_off"], r["_dist"] = sync_choice(r, T, ap, start_skew, sync_ap)
        r["_w"] = wander_frac * max(r.get("unshared_a_ps", 0.0), r.get("unshared_b_ps", 0.0))
    regions = sorted({r["src"] for r in rows} | {r["dst"] for r in rows})
    root, par = directed_tree(rows, regions)
    for x, port in (tree_parent or {}).items():
        r = next((q for q in rows if q["port"] == port), None)
        if r is None or r["dst"] != x or r["src"] == x or x not in par or r["src"] not in par:
            raise ValueError(f"tree_parent {x}={port}: not a crossing into region {x} from another reached region")
        y = r["src"]
        while y is not None:
            if y == x:
                raise ValueError(f"tree_parent {x}={port}: src {r['src']} is in {x}'s subtree (would close a loop)")
            y = par[y][0] if par[y] else None
        par[x] = (r["src"], r)
    if skew_clean:
        # the tree is the unchanged min-ambiguity tree; a CLEAN tree edge whose static sync distance misses
        # sync aperture + max|skew| is re-read as AMBIGUOUS (window, J deviation, start row, PAD)
        for x, v in par.items():
            if v and v[1]["_nv"] == 1 and v[1]["_dist"] - sync_ap < smax:
                v[1]["_nv"] = 2
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
    epad = {}
    for k, v in (edge_pad or {}).items():
        hits = [x for x in order[1:] if x == k or par[x][1]["port"] == k]
        if not hits:
            raise ValueError(f"edge_pad {k!r}: not a start-tree edge (tree port or child region) of this plan")
        if int(v) < pad:
            raise ValueError(f"edge_pad {k!r}={v} below the default PAD {pad} (would cut the tree crossing's lag)")
        for x in hits:
            epad[x] = int(v)

    def pe(x):
        return epad.get(x, pad)

    a0, dev, jn = {root: 0}, {}, {}
    for x in order[1:]:
        p, r = par[x]
        jn[x] = J(r["d_ps"], T, r["_off"])
        a0[x] = a0[p] + pe(x) + 2 + jn[x]
        # J deviation range over the derated interval +- ap (J decreases with d)
        dev[x] = (J(r["hi"] + ap, T, r["_off"]) - jn[x], J(r["lo"] - ap, T, r["_off"]) - jn[x])
        if skew_clean:
            # the sync samples d - skew: cover the skewed phase (+- the sync aperture) too
            s_lo, s_hi = float(start_skew[0]), float(start_skew[1])
            dev[x] = (min(dev[x][0], J(r["hi"] - s_lo + sync_ap, T, r["_off"]) - jn[x]),
                      max(dev[x][1], J(r["lo"] - s_hi - sync_ap, T, r["_off"]) - jn[x]))

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
        k_eff = math.ceil((lo_win - rel_lo) / T - 1e-12) + (pe(child) - pad if child is not None else 0)
        L_lo, L_hi = k_eff * T + rel_lo, k_eff * T + rel_hi
        nh = max(ap, 100.0 + smax) if (skew_clean and kind == "tree_ambiguous") else ap
        dep = next((dd for dd in (4, 8, 16) if dd <= max_depth and L_hi <= (dd - 0.5) * T - nh + 1e-9), None)
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
    byp = {o["port"]: o for o in out}
    for x in order:
        e = None
        if par[x]:
            p, r = par[x]
            # MESO-RECONCILE-1 start-skew budget for die STA (COORD 21:55 (3)): the start rides beside the tree port's
            # bus; its arrival at the first sync flop minus the forwarded-clock (word) timing shifts the sampled phase.
            # CLEAN edge: J stays chip-invariant while |skew| <= sync_dist - sync aperture.  AMBIGUOUS edge: J is already
            # free; the skew shifts the tree crossing's own lag, so the budget is its smaller ring margin above the
            # 100 ps gate.
            o = byp.get(r["port"], {})
            if r["_nv"] == 1:
                lim, basis = r["_dist"] - sync_ap, "clean: sync_dist - sync_aperture"
            elif o.get("depth"):
                lim, basis = min(o["margin_lo_ps"], o["margin_hi_ps"]) - 100.0, "ambiguous: tree crossing margin - 100"
            else:
                lim, basis = None, "ambiguous: tree crossing FAIL"
            e = dict(parent=p, port=r["port"], edge=r["_edge"], sync_values=r["_nv"],
                     sync_dist_ps=round(r["_dist"], 1), J_nominal=jn[x], J_dev=list(dev[x]),
                     offset_from_parent=pe(x) + 2 + jn[x], pad_override=x in epad,
                     start_skew_limit_ps=None if lim is None else round(lim, 1), start_skew_basis=basis,
                     rtl=dict(module="ot_dp_landing_origin", PAD=pe(x), EDGE_FALL=int(r["_edge"] == "fall")))
        regs.append(dict(region=x, origin_cycles=a0[x], tree_depth=depth[x], start_from=e))
    ok = [o for o in out if o.get("depth")]
    amb_edges = [g for g in regs if g["start_from"] and g["start_from"]["sync_values"] > 1]
    summ = dict(regions=len(regions), regions_reached=len(a0), tree_root=root, tree_edges=len(order) - 1,
                tree_edges_clean=len(order) - 1 - len(amb_edges),
                tree_edges_ambiguous=[dict(region=g["region"], **{k: g["start_from"][k] for k in
                                      ("parent", "port", "edge", "sync_values", "sync_dist_ps")}) for g in amb_edges],
                edge_pad={x: epad[x] for x in sorted(epad)},
                tree_edges_fall=sum(1 for g in regs if g["start_from"] and g["start_from"]["edge"] == "fall"),
                start_skew_limit_clean_min_ps=min((g["start_from"]["start_skew_limit_ps"] for g in regs if g["start_from"]
                                                   and g["start_from"]["sync_values"] == 1), default=None),
                start_skew_limit_min_ps=min((g["start_from"]["start_skew_limit_ps"] for g in regs if g["start_from"]
                                             and g["start_from"]["start_skew_limit_ps"] is not None), default=None),
                max_tree_depth=max(depth.values()), min_sync_dist_clean_ps=min(
                    (g["start_from"]["sync_dist_ps"] for g in regs if g["start_from"] and g["start_from"]["sync_values"] == 1),
                    default=None),
                crossings=len(out), depth4=sum(1 for o in ok if o["depth"] == 4),
                depth8=sum(1 for o in ok if o["depth"] == 8), depth16=sum(1 for o in ok if o["depth"] == 16),
                max_depth=max_depth, fail=len(out) - len(ok),
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


def mc_check(rows, out, regs, T=833.0, chips=2000, sync_ap=26.5, seed=1, start_skew=None):
    """Monte-Carlo chips against the EMITTED RTL K / DEPTH / PAD / EDGE_FALL: returns (#chips, #violations, worst lo,
    worst hi) with margins measured to the guard edges 0.5 T / (DEPTH - 0.5) T (no ap).  start_skew (lo, hi), opt-in
    (MESO-START-2 --start-skew-clean): each tree edge's sync samples d - skew, skew uniform / an endpoint per chip."""
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
            if start_skew is not None:
                x -= rnd.uniform(*start_skew) if mode == 0 else start_skew[rnd.random() < 0.5]
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


def load_rows(ocv_json, corners, scale=1.0):
    """scale: plan-time arrival scale (OSS-CLOCK-2 ruling 21:10: x1.05) on d, p_dn, p_up and unshared (as DIE-HEAD-3 ca3)"""
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
    if scale != 1.0:
        for r in rows:
            for k in ("d_ps", "p_dn_ps", "p_up_ps", "unshared_a_ps", "unshared_b_ps"):
                if k in r:
                    r[k] *= scale
    return rows


def sta_hull(rows, sta):
    """DIE-HEAD-5 (COORD 00:22): ONE interval model.  sta = {corner: {'srcpart->dstpart': (lo, hi)}} from
    die_sta_related.sta_d_intervals (the interval die_sta_related --count-align gates on).  Each row's derated interval
    [d - p_dn, d + p_up] (landed_phase_ocv AOCV + droop, kept: 12.14a crossing margin after OCV + droop) becomes its hull
    with the STA interval of its partition pair on every corner, so every plan margin (lag, sync edge clearance incl.
    start skew) is a lower bound of the same margin on the gate numbers.  d (nominal) is unchanged.  Returns a summary."""
    widened, missing, worst = 0, [], (0.0, None)
    for r in rows:
        tag = f"{r.get('src_part', r['src'])}->{r.get('dst_part', r['dst'])}"
        iv = [c[tag] for c in sta.values() if tag in c]
        if not iv:
            missing.append(r["port"])
            continue
        lo0, hi0 = r["d_ps"] - r["p_dn_ps"], r["d_ps"] + r["p_up_ps"]
        lo, hi = min([lo0] + [x[0] for x in iv]), max([hi0] + [x[1] for x in iv])
        r["sta_d_ps"] = [round(min(x[0] for x in iv), 1), round(max(x[1] for x in iv), 1)]
        if lo < lo0 or hi > hi0:
            widened += 1
            w = (lo0 - lo) + (hi - hi0)
            if w > worst[0]:
                worst = (w, r["port"])
        r["p_dn_ps"], r["p_up_ps"] = r["d_ps"] - lo, hi - r["d_ps"]
    return dict(corners=sorted(sta), rows=len(rows), widened=widened, max_widen_ps=round(worst[0], 1),
                max_widen_port=worst[1], missing=len(missing), missing_ports=missing[:20])


def add_sta_ocv_args(ap):
    """CA-OCV-1: the --sta-proof hull takes the same clock variation term die_sta_related --count-align adds
    (--clock-ocv / --clock-droop / --droop-regions / --core-latency-ff); default none = unchanged hull."""
    ap.add_argument("--sta-clock-ocv", choices=("none", "flat", "table"), default="none",
                    help="as die_sta_related --clock-ocv (CA-OCV-1: the gate's CA interval carries it; table = gate form)")
    ap.add_argument("--sta-clock-droop", choices=("stated", "shared"), help="as die_sta_related --clock-droop")
    ap.add_argument("--sta-droop-regions", help="as die_sta_related --droop-regions")
    ap.add_argument("--sta-core-latency-ff", type=float, help="as die_sta_related --core-latency-ff")


def sta_ocv_kw(a):
    return dict(clock_ocv=a.sta_clock_ocv, clock_droop=a.sta_clock_droop, droop_regions_file=a.sta_droop_regions,
                core_latency_ff=a.sta_core_latency_ff)


def parse_skew(text):
    """'LO,HI' ps -> (lo, hi) with lo <= hi"""
    lo, hi = (float(x) for x in text.split(","))
    if lo > hi:
        raise argparse.ArgumentTypeError(f"--start-skew {text}: LO > HI")
    return lo, hi


def parse_edge_pad(items, typ=int):
    """['PORT_OR_REGION=N', ...] -> {key: N}  (typ=str: ['REGION=PORT', ...] for --tree-parent)"""
    out = {}
    for it in items or []:
        k, _, v = it.rpartition("=")
        if not k:
            raise ValueError(f"--edge-pad {it!r}: want PORT=N or REGION=N")
        out[k] = typ(v)
    return out


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
    ap.add_argument("--edge-pad", action="append", metavar="PORT=N", help="per-start-tree-edge PAD override (tree port "
                    "or child region); the tree crossing keeps its RTL K, so its latency grows by N - PAD")
    ap.add_argument("--scale", type=float, default=1.0, help="plan-time arrival scale (OSS-CLOCK-2 21:10: 1.05)")
    ap.add_argument("--start-skew", type=parse_skew, default=(0.0, 0.0), metavar="LO,HI",
                    help="start skew ps at the child's first sync flop (parent origin clk->Q + start wire - fclk wire; "
                         "die_sta_related start row clkq_ps); the sample edge keeps ap from either boundary with it")
    ap.add_argument("--start-skew-clean", action="store_true",
                    help="MESO-START-2 (opt-in, needs --start-skew): a start edge is CLEAN only if it clears sync "
                         "aperture + max|skew|, else AMBIGUOUS with PAD + 1 where its tree-crossing low margin < 100 + "
                         "max|skew|; the MC samples the skewed phase")
    ap.add_argument("--tree-parent", action="append", metavar="REGION=PORT",
                    help="MESO-START-2 (opt-in): start-tree edge override, the region (and its subtree) takes PORT "
                         "(a crossing into it) as its start edge")
    ap.add_argument("--sta-proof", metavar="DIR", help="DIE-HEAD-5 one interval model: die clock proof (tap_arrivals_<C>"
                    ".json) of die_sta_related; each crossing's interval becomes its hull with the STA d interval "
                    "(die_sta_related.count_align_d_intervals) on the --corner corners; needs --sta-plan")
    ap.add_argument("--sta-plan", help="die plan JSON die_sta_related --plan reads (partition pairs of the ports)")
    ap.add_argument("--sta-clock-cal", choices=("none", "spice"), default="spice",
                    help="as die_sta_related --clock-cal (12.15b gate: spice)")
    ap.add_argument("--sta-cppr-lca", action="store_true", help="as die_sta_related --cppr-lca")
    add_sta_ocv_args(ap)
    ap.add_argument("--max-depth", type=int, choices=(8, 16), default=8,
                    help="DIE-S81-11 / 12.16 b(iii) opt-in: largest standard ring DEPTH (16 needs its RTL proof; default 8)")
    ap.add_argument("--mc-chips", type=int, default=0)
    ap.add_argument("--out")
    ap.add_argument("--cases", help="TSV for the Verilator bench: port DEPTH L_ps (lo / mid / hi per crossing)")
    a = ap.parse_args(argv)
    rows = load_rows(a.ocv_json, a.corner, a.scale)
    sta_info = None
    if a.sta_proof:
        if not a.sta_plan:
            ap.error("--sta-proof needs --sta-plan")
        import die_sta_related as DSR
        cs = sorted({c.split("_")[0] for c in a.corner.split(",")})
        sta_info = sta_hull(rows, DSR.sta_d_intervals(a.sta_proof, a.sta_plan, cs, a.sta_clock_cal, a.sta_cppr_lca,
                                                      **sta_ocv_kw(a)))
        sta_info.update(proof=a.sta_proof, plan=a.sta_plan, clock_cal=a.sta_clock_cal, cppr_lca=a.sta_cppr_lca,
                        clock_ocv=a.sta_clock_ocv,
                        model="hull(landed_phase_ocv derated, die_sta_related.count_align_d_intervals)")
        if sta_info["missing"]:
            print(f"WARNING --sta-proof: {sta_info['missing']} crossings without STA tap pairs keep the OCV interval "
                  "(die_sta_related fails them closed: no taps)", file=sys.stderr)
    if a.start_skew_clean and not any(a.start_skew):
        ap.error("--start-skew-clean needs --start-skew LO,HI")
    summ, out, regs = plan(rows, a.period, a.aperture, a.wander_frac, a.sync_aperture, a.pad, parse_edge_pad(a.edge_pad),
                           a.start_skew, a.start_skew_clean, tree_parent=parse_edge_pad(a.tree_parent, str) or None,
                           max_depth=a.max_depth)
    if a.tree_parent:
        summ["tree_parent"] = parse_edge_pad(a.tree_parent, str)
    if any(a.start_skew):
        summ["start_skew_ps"] = list(a.start_skew)
    if sta_info:
        summ["sta_interval"] = sta_info
    summ.update(corner=a.corner, period_ps=a.period, aperture_ps=a.aperture, sync_aperture_ps=a.sync_aperture,
                wander_frac=a.wander_frac, pad=a.pad, scale=a.scale, source=a.ocv_json)
    if a.mc_chips:
        n, bad, wl, wh = mc_check(rows, out, regs, a.period, a.mc_chips, a.sync_aperture,
                                  start_skew=a.start_skew if a.start_skew_clean else None)
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
