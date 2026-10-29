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


def sync_choice_iv(r, T, ap, start_skew=(0.0, 0.0), sync_ap=26.5, prefer=None):
    """(n_values, edge, off, dist): best sample edge for the start sync across crossing r.
    start_skew (lo, hi) ps (DIE-HEAD-4b, COORD NC-HEAD-PART): start arrival at the child's first sync flop minus the
    forwarded clock (clk->Q of the parent origin register + start wire - fclk wire; die_sta_related start row).  The
    sync samples the phase d - skew.  n (sample values over the static interval +- ap) stays the primary key, so the
    start tree and the J deviation ranges are unchanged; among the edges with the fewest values an edge is kept only if
    it also clears the skew.  Hard (the die STA start row): skewed interval [lo - hi_s, hi - lo_s] >= sync aperture
    from the boundary off + kT and static distance - sync aperture >= max|skew|.  Soft: the skewed interval >= ap
    (T/8 >= 100 ps) from the boundary.  Order: fewest values, smaller hard shortfall, smaller soft shortfall, larger
    static distance (an edge that clears both keeps the static order).  dist stays the STATIC
    distance (start_skew_limit = dist - sync aperture, as die_sta_related reads it).  Default (0, 0): unchanged.
    FLOW-ONEMODEL-1 (measured fall): when r carries 'fall_lo'/'fall_hi' (the interval on the capture pins' MEASURED
    fall arrival, die_sta_related.ca_pair_interval edge 'fall'), the fall candidate is judged on THAT interval and only
    if it is clean (one value); fall_lo None (no measured fall arrival) = rise only (fail closed, never rise + T/2).
    Without the keys (rows with no proof taps) the legacy T/2 form is kept.  Returns (n, edge, off, dist, (lo, hi, d))
    with the sampled interval and its nominal.
    prefer (FLOW-GEN-2 --start-prev, opt-in): 'rise' / 'fall' = the edge a previous pass chose; it is kept whenever it
    ties the best on (values, hard, soft), i.e. it is as valid as the best and loses only on the static distance (the
    near-tie EDGE_FALL flips between passes).  None (default): unchanged."""
    lo0, hi0 = r["lo"], r["hi"]
    measured = "fall_lo" in r
    s_lo, s_hi = float(start_skew[0]), float(start_skew[1])
    skewed = bool(s_lo or s_hi)
    smax = max(abs(s_lo), abs(s_hi))
    best = pref = None
    for edge, off in (("rise", 0.0), ("fall", T / 2)):
        lo, hi, dn = lo0, hi0, r.get("d_ps", 0.5 * (lo0 + hi0))
        if edge == "fall" and measured:
            if r["fall_lo"] is None:
                continue
            lo, hi = r["fall_lo"], r["fall_hi"]
            dn = 0.5 * (lo + hi)
        n = interval_boundaries(lo - ap, hi + ap, T, off) + 1
        if edge == "fall" and measured and n > 1:
            continue
        dist = boundary_dist(lo, hi, T, off)
        hard = soft = 0.0
        if skewed:
            sd = boundary_dist(lo - s_hi, hi - s_lo, T, off)
            hard = max(0.0, sync_ap - sd, smax - (dist - sync_ap))
            soft = max(0.0, ap - sd)
        key = (n, hard, soft, -dist)
        if best is None or key < best[0]:
            best = (key, (n, edge, off, dist, (lo, hi, dn)))
        if prefer == edge:
            pref = (key, (n, edge, off, dist, (lo, hi, dn)))
    if pref is not None and pref[0][:3] == best[0][:3]:
        return pref[1]
    return best[1]


def sync_choice(r, T, ap, start_skew=(0.0, 0.0), sync_ap=26.5):
    """(n_values, edge, off, dist): sync_choice_iv without the sampled interval"""
    return sync_choice_iv(r, T, ap, start_skew, sync_ap)[:4]


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
         skew_clean=False, _pad_pass=False, tree_parent=None, max_depth=8, start_edges=None, start_root=None,
         start_prefer=None):
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
    crossing takes the smallest of 4 / 8 / 16 whose window holds L_hi with ap (16 only when max_depth = 16).
    start_edges / start_root (START-TREE-1, METHODOLOGY 12.16b(iv)/12.16e, opt-in --start-tree clock): the start tree is
    given (clock_start_edges: the clock tree's own region/branch nodes, one dedicated start port per edge) instead of
    the min-ambiguity tree over data crossings; every data crossing is then 'nontree' and its origin difference is
    summed over the start ports on the clock-tree path between its two regions.  None (default): unchanged.
    start_prefer {start port: 'rise' | 'fall'} (FLOW-GEN-2 --start-prev, opt-in): the previous pass's EDGE_FALL pick
    of a start port is kept while it ties the best edge on validity (sync_choice_iv prefer).  None: unchanged."""
    if max_depth not in (8, 16):
        raise ValueError(f"max_depth {max_depth}: standard ring depths are 8 or 16")
    if start_edges is not None:
        if tree_parent:
            raise ValueError("tree_parent does not apply with a given start tree (--start-tree clock)")
        start_edges = [dict(e) for e in start_edges]
    smax = max(abs(float(start_skew[0])), abs(float(start_skew[1])))
    if skew_clean and not _pad_pass:
        if not smax:
            raise ValueError("skew_clean needs a nonzero start_skew (--start-skew LO,HI)")
        need = 100.0 + smax
        args = (T, ap, wander_frac, sync_ap, pad)
        kw = dict(start_edges=start_edges, start_root=start_root, start_prefer=start_prefer)
        s0, out0, regs0 = plan([dict(r) for r in rows], *args, edge_pad, start_skew, True, True, tree_parent, max_depth,
                               **kw)
        byp = {o["port"]: o for o in out0}
        ep = dict(edge_pad or {})
        add = {}
        for g in regs0:
            e = g["start_from"]
            if not e or e["sync_values"] == 1:
                continue
            o = byp.get(e["port"])
            if o is None:
                continue        # dedicated start port (--start-tree clock): no tree crossing lag to pad
            if o.get("depth") and o["margin_lo_ps"] < need:
                ep.pop(e["port"], None)
                ep[g["region"]] = add[g["region"]] = int(e["rtl"]["PAD"]) + 1
        summ, out, regs = plan(rows, *args, ep, start_skew, True, True, tree_parent, max_depth, **kw)
        sn, outn, _ = plan([dict(r) for r in rows], *args, edge_pad, start_skew, tree_parent=tree_parent,
                           max_depth=max_depth, **kw)

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
        r["_nv"], r["_edge"], r["_off"], r["_dist"], r["_s"] = sync_choice_iv(r, T, ap, start_skew, sync_ap)
        # CLK-INV-CAL-1 / COORD 10-28: wander over the crossing's OWN tap pairs (unshared_sta_ps = max
        # die_sta_related.ca_pair_unshared, the gate's function), never below the landed_phase_ocv row's own figure
        r["_w"] = wander_frac * max(r.get("unshared_a_ps", 0.0), r.get("unshared_b_ps", 0.0),
                                    r.get("unshared_sta_ps", 0.0))
    data_regions = sorted({r["src"] for r in rows} | {r["dst"] for r in rows})
    regions = data_regions
    if start_edges is not None:
        for r in start_edges:
            r["lo"], r["hi"] = r["d_ps"] - r["p_dn_ps"], r["d_ps"] + r["p_up_ps"]
            r["_nv"], r["_edge"], r["_off"], r["_dist"], r["_s"] = sync_choice_iv(
                r, T, ap, start_skew, sync_ap, (start_prefer or {}).get(r["port"]))
            r["_w"] = 0.0
        root, par = start_root, {start_root: None}
        for r in start_edges:
            par[r["dst"]] = (r["src"], r)
        regions = sorted(set(data_regions) | set(par))
        stack, seen = [start_root], {start_root}
        kids0 = defaultdict(list)
        for x, v in par.items():
            if v:
                kids0[v[0]].append(x)
        for x in stack:
            for y in kids0[x]:
                if y not in seen:
                    seen.add(y); stack.append(y)
        if seen != set(par):
            raise ValueError(f"start_edges: {len(set(par) - seen)} nodes not reached from start_root {start_root}")
    else:
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
        # the SAMPLED phase (FLOW-ONEMODEL-1: the measured fall interval for a fall sample; else d's own interval)
        s_lo_, s_hi_, s_d_ = r["_s"]
        jn[x] = J(s_d_, T, r["_off"])
        a0[x] = a0[p] + pe(x) + 2 + jn[x]
        # J deviation range over the derated interval +- ap (J decreases with d)
        dev[x] = (J(s_hi_ + ap, T, r["_off"]) - jn[x], J(s_lo_ - ap, T, r["_off"]) - jn[x])
        if skew_clean:
            # the sync samples d - skew: cover the skewed phase (+- the sync aperture) too
            s_lo, s_hi = float(start_skew[0]), float(start_skew[1])
            dev[x] = (min(dev[x][0], J(s_hi_ - s_lo + sync_ap, T, r["_off"]) - jn[x]),
                      max(dev[x][1], J(s_lo_ - s_hi - sync_ap, T, r["_off"]) - jn[x]))

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

    def hops(u, v):
        su, sv, n = u, v, 0
        while su != sv:
            if depth[su] >= depth[sv]:
                su = par[su][0]
            else:
                sv = par[sv][0]
            n += 1
        return n

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
        if r.get("src_part") is not None and r.get("dst_part") is not None and r.get("_named"):
            out_parts = dict(src_part=r["src_part"], dst_part=r["dst_part"])
        else:
            out_parts = {}
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
                        old_ring_ok=(r.get("margin_ps", 0) >= 0), **out_parts))
        if start_edges is not None:
            out[-1]["start_hops"] = hops(u, v)
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
            if "fall_lo" in r:
                # FLOW-ONEMODEL-1: the sampled interval (rise: d's own; fall: the MEASURED fall arrival interval)
                e["sample_d_ps"] = r["_s"][2]
                e["sample_interval_ps"] = [round(r["_s"][0], 1), round(r["_s"][1], 1)]
                e["fall_measured"] = r["fall_lo"] is not None
            if start_edges is not None:
                e.update({k: r[k] for k in START_EDGE_KEYS if k in r})
                e["start_interval_ps"] = [round(r["lo"], 1), round(r["hi"], 1)]
        regs.append(dict(region=x, origin_cycles=a0[x], tree_depth=depth[x], start_from=e))
        if start_edges is not None:
            regs[-1]["virtual"] = x not in data_regions
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
    if start_edges is not None:
        se = [g["start_from"] for g in regs if g["start_from"]]
        hp = sorted(o["start_hops"] for o in out if "start_hops" in o)
        wd = sorted(e["start_interval_ps"][1] - e["start_interval_ps"][0] for e in se)
        summ["start_tree"] = dict(
            form="clock", data_regions=len(data_regions), virtual_nodes=sum(1 for g in regs if g.get("virtual")),
            retime_nodes=sum(1 for e in se if e.get("retime")), start_edges=len(se),
            start_clean=sum(1 for e in se if e["sync_values"] == 1 and e.get("clean_ok", True)),
            start_fail=sum(1 for e in se if e["sync_values"] > 1 or not e.get("clean_ok", True)),
            start_fail_edges=[e["port"] for e in se if e["sync_values"] > 1 or not e.get("clean_ok", True)][:20],
            start_width_ps=dict(median=wd[len(wd) // 2] if wd else None, max=wd[-1] if wd else None),
            start_min_sync_dist_ps=min((e["sync_dist_ps"] for e in se), default=None),
            crossing_start_hops=dict(median=hp[len(hp) // 2] if hp else None, max=hp[-1] if hp else None),
            rule="12.16b(iv): every start (reset-release) port is a crossing; CLEAN iff its interval (same shared model, "
                 "clock_variation table) +- aperture holds no sampling boundary; an unclean port FAILs the plan")
    return summ, out, regs

# ---------------------------------------------------------------- START-TREE-1 (opt-in --start-tree clock)
# METHODOLOGY 12.16b(i)/(iv) + 12.16e: the start (reset-release) distribution follows the CLOCK tree.  Root cause it
# removes (results/start_tree_1028/README.md): the default start tree is a min-ambiguity spanning tree over DATA
# crossings, each start edge's interval is the region-pair union of all its tap pairs (incl. the whole unshared clock
# + OCV), so with OCV many start edges are ambiguous, and a crossing between regions that are far apart in that tree
# sums every ambiguous edge on the path (QC t6: 6-9 cycles on all 94 FAILs, 10-11 start hops).
START_EDGE_KEYS = ("launch", "capture", "launch_part", "capture_part", "retime", "unshared_a_ps", "unshared_b_ps",
                   "fork_node", "clean_ok", "hop_um", "clock_interval_ps", "data_delay_ps", "data_delay_source",
                   "data_delay_by_corner_ps")


def load_start_data_delay(path):
    """HEAD-START-4 V1 (COORD 10-29, 12.18a: a model fix inside the existing related-pair gate, not a new check): the
    START port's DATA path.  The clock-only model samples d = capture clock - launch clock; the start bit itself leaves
    the launch flop at its clock edge and reaches the capture D after dd (clk->Q + relay chain + wire), so the sync
    samples d - dd.  JSON {"ports": {"start:<src>-><dst>": [dd_lo_ps, dd_hi_ps]}, "model": {"lo_ps": [a, b],
    "hi_ps": [a, b]} (optional), "basis": "..."}: per port the MEASURED launch CLK -> capture D range (lo = min over
    corners, the FF min; hi = max, the TT max); model (optional, planner only) = a + b x hop_um for candidate ports with
    no measurement (retime / contraction search, new stages), labelled 'model'.  die_sta_related reads only 'ports'."""
    doc = json.load(open(path))
    def checked(rows):
        ports = {}
        for p, v in rows.items():
            lo, hi = float(v[0]), float(v[1])
            if not (math.isfinite(lo) and math.isfinite(hi)) or lo > hi:
                raise ValueError(f"--start-data-delay {p}: want finite [lo, hi] with lo <= hi, got {v}")
            ports[p] = (lo, hi)
        return ports
    ports = checked(doc.get("ports") or {})
    model = doc.get("model")
    if model is not None:
        model = {k: (float(model[k][0]), float(model[k][1])) for k in ("lo_ps", "hi_ps")}
    result = dict(ports=ports, model=model, basis=doc.get("basis"))
    if "corners" in doc:
        result["corners"] = {c: checked(rows) for c, rows in doc["corners"].items()}
    if "corner_models" in doc:
        result["corner_models"] = {c: {k: tuple(float(x) for x in model[k]) for k in ("lo_ps", "hi_ps")}
                                   for c, model in doc["corner_models"].items()}
        if not all(len(v) == 2 and all(math.isfinite(x) for x in v)
                   for model in result["corner_models"].values() for v in model.values()):
            raise ValueError("--start-data-delay corner_models need finite [intercept, slope] coefficients")
    return result


def start_data_delay_for_corner(doc, corner):
    """Measured DATA delay for this clock corner; absent corner/port fails closed.

    Legacy documents contain one conservative interval per port. A document with
    ``corners`` never substitutes another corner's measurement for a missing row.
    """
    return doc["corners"].get(corner, {}) if "corners" in doc else doc["ports"]


def shift_corner_data_delay(r, by_corner, delays, source="measured"):
    """Union same-corner (clock - data) intervals, without cross-corner combinations."""
    first = next(iter(by_corner))
    lo = min(iv[0] - delays[c][1] for c, iv in by_corner.items())
    hi = max(iv[1] - delays[c][0] for c, iv in by_corner.items())
    d = min(max(r["d_ps"] - sum(delays[first]) / 2, lo), hi)
    q = dict(r, d_ps=d, p_dn_ps=d-lo, p_up_ps=hi-d,
             clock_interval_ps=[round(r["d_ps"]-r["p_dn_ps"], 1), round(r["d_ps"]+r["p_up_ps"], 1)],
             data_delay_ps=[min(v[0] for v in delays.values()), max(v[1] for v in delays.values())],
             data_delay_by_corner_ps=delays, data_delay_source=source)
    if all(iv[2] is not None for iv in by_corner.values()):
        q["fall_lo"] = min(iv[2]-delays[c][1] for c, iv in by_corner.items())
        q["fall_hi"] = max(iv[3]-delays[c][0] for c, iv in by_corner.items())
    return q


def data_delay_of(dd, port, r):
    """(lo, hi, source) of a start port: measured, else the hop model, else None (the port is never clean: a candidate
    is not taken, a final port FAILs the plan; fail closed)"""
    if port in dd["ports"]:
        return dd["ports"][port] + ("measured",)
    m = dd.get("model")
    if m is None:
        return None
    h = float(r["hop_um"])
    return m["lo_ps"][0] + m["lo_ps"][1] * h, m["hi_ps"][0] + m["hi_ps"][1] * h, "model"


def shift_data_delay(r, lo, hi, source):
    """the port row on the SAMPLED phase d - dd: interval [lo_c - dd_hi, hi_c - dd_lo] (rise and measured fall), nominal
    d - (dd_lo + dd_hi) / 2; the clock-only interval and dd are kept for the record"""
    clo, chi = r["d_ps"] - r["p_dn_ps"], r["d_ps"] + r["p_up_ps"]
    nlo, nhi, nd = clo - hi, chi - lo, r["d_ps"] - 0.5 * (lo + hi)
    q = dict(r, d_ps=nd, p_dn_ps=nd - nlo, p_up_ps=nhi - nd, clock_interval_ps=[round(clo, 1), round(chi, 1)],
             data_delay_ps=[round(lo, 1), round(hi, 1)], data_delay_source=source)
    if r.get("fall_lo") is not None:
        q["fall_lo"], q["fall_hi"] = r["fall_lo"] - hi, r["fall_hi"] - lo
    return q


def width_robust(r, T, ap, skew_range=0.0):
    """FLOW-ONEMODEL-1 --start-clean width on MEASURED edges.  r: lo/hi (rise-sampled interval) and fall_lo/fall_hi (the
    measured fall-sampled interval, None = not measured).  Shift both by a common s (the port's arrivals move after
    build): rise is unclean on arcs of length A = w_r + sr + 2 ap (circle of length T), fall on arcs of length
    B = w_f + sr + 2 ap whose centres sit D = (T/2 + c_r - c_f) mod T away.  One edge is clean for EVERY s iff the
    two families of unclean arcs never overlap: min(D, T - D) >= (A + B) / 2.  With fall = rise + T/2 (c_f = c_r, w_f = w_r) this is the
    original width + skew range <= T/2 - 2 ap; with a measured duty distortion D moves off T/2.  No measured fall:
    False.  Without fall keys at all (legacy rows): the original rule."""
    w = r["hi"] - r["lo"]
    if "fall_lo" not in r:
        return w + skew_range <= T / 2 - 2 * ap + 1e-9
    if r["fall_lo"] is None:
        return False
    wf = r["fall_hi"] - r["fall_lo"]
    D = (T / 2 + 0.5 * (r["lo"] + r["hi"]) - 0.5 * (r["fall_lo"] + r["fall_hi"])) % T
    return min(D, T - D) + 1e-9 >= 0.5 * ((w + skew_range + 2 * ap) + (wf + skew_range + 2 * ap))


def _lcp(a, b):
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return a[:n]


def clock_contexts(proof, plan_path, corners, clock_cal="spice", clock_ocv="table", clock_droop=None,
                   droop_regions_file=None, core_latency_ff=None, clock_cell="auto"):
    """{corner: dict(meta, taps, ocv, rng)} with the ONE shared die model exactly as sta_d_intervals builds it (tap
    arrivals of PROOF, --clock-cal spice, CPPR at the last common tree node, clock_ocv_fn table + shared droop)."""
    import die_sta_related as DSR
    from pathlib import Path
    if clock_ocv == "none":
        raise ValueError("--start-tree clock needs a clock variation model (--sta-clock-ocv table): 12.16b(iv) checks "
                         "reset release with the same CA rule")
    plan = json.load(open(plan_path))
    lt = float(plan.get("clock", {}).get("common_latency_ps", 250.0))
    out = {}
    for c in corners:
        meta, taps = DSR.load_taps(Path(proof), c)
        if not all("tree_path" in t for t in taps.values()):
            raise ValueError("--start-tree clock needs tap tree_path in the proof (the clock tree topology)")
        cc, _ = DSR.resolve_clock_cell(clock_cell, proof, meta)   # CLK-INV-CAL-1: same clock-cell model as the gate
        meta, taps = DSR.apply_clock_cal(meta, taps, c, cc, clock_cal, proof=Path(proof))
        taps = dict(taps)
        lat = core_latency_ff if (c == "FF" and core_latency_ff is not None) else lt
        old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
        try:
            ocv = DSR.ca_ocv(Path(proof), meta, taps, c, lat, clock_ocv, clock_droop, "mesh", droop_regions_file,
                             clock_cell=cc)
        finally:
            DSR.CPPR_LCA = old
        out[c] = dict(meta=meta, taps=taps, ocv=ocv, rng=meta.get("cppr_node_range_ps"))
    return out


def partition_start_origins(rows):
    """Give each physical partition its own origin; data intervals remain unchanged.

    This removes same-region START relays only as part of a full origin/K/depth reprice.
    It does not change the measured data clock hull or invent another clock phase.
    """
    for r in rows:
        if not r.get("src_part") or not r.get("dst_part"):
            raise ValueError("partition START origins require actual src_part/dst_part on every crossing")
        r["src"], r["dst"] = r["src_part"], r["dst_part"]
    return rows


def native_start_clocks(rows, ctx):
    """Map each origin to the emitted .clk(clk) frame, never the nearest data tap.

    A multi-partition region must first be split or have an explicit physical origin;
    guessing its origin from a convenient capture tap changes counter phase.
    """
    owners = defaultdict(set)
    for r in rows:
        for side in ("src", "dst"):
            owners[r[side]].add(r.get(side + "_part", r[side]))
    out = {}
    for region, parts in owners.items():
        if len(parts) != 1:
            raise ValueError(f"native START region {region} has {len(parts)} physical partitions; split its origins first")
        part = next(iter(parts))
        tap = f"t_{part}__clk"
        if any(tap not in c["taps"] or c["taps"][tap].get("part") != part for c in ctx.values()):
            raise ValueError(f"native START origin {region} needs measured {tap} at every corner")
        out[region] = tap
    return out


def clock_start_edges(rows, ctx, T=833.0, ap=833.0 / 8, sync_ap=26.5, start_skew=(0.0, 0.0), skew_clean=False,
                      retime_max=8, clean_by="phase", retime_up=False, prev=None, max_hop_um=None, capture_taps=None, launch_taps=None, endpoint_xy=None, root_region=None, distinct_stage_clocks=False, leaf_origins=False,
                      data_delay=None):
    """START TREE = CLOCK TREE (START-TREE-1).  ctx = clock_contexts() ({corner: meta/taps/ocv/rng}, first = nominal).
    Nodes: every data region at its clock root (longest common tree_path prefix of its taps) and every branch node of
    the clock subtree spanning those roots (virtual 'st:<path>', a retime flop on that tree node).  Each node's start
    parent is its nearest clock-tree ancestor node, so the start path between two regions IS their clock-tree path.
    One DEDICATED start port per edge (not a data crossing, no region-pair union):
      launch  = virtual tap at the parent node, or the parent region's FORK tap (deepest common tree node with the
                child's sync tap; the parent's start reaches it in-region, same clock);
      capture = virtual tap at the child node, or the child region's tap with the shortest leg below its root (its
                origin / sync flop).
    The port's interval is count_align_d_intervals on that one tap pair (same CPPR + ocv as the gate) over every
    corner (union), d nominal from the first corner.  An unclean port is split by retime flops at intermediate tree
    nodes, down to the sync tap's driving node inside the child region (greedy deepest clean segment, <= retime_max
    per edge), so every start port is CLEAN where the tree allows;
    a port that stays unclean is kept (its J range enters path ambiguity as before) and FAILs the plan (12.16b(iv)).
    A branch node is contracted (no stage of its own) when all its children take a clean port straight from its parent.
    retime_up (opt-in, DIE-S81-13): when no capture-side node gives a clean segment from the launch (the launch is a
    region leaf deep below the fork: its in-region insertion alone makes every segment too wide), the start first climbs
    the LAUNCH side of the clock tree: a retime flop on the shallowest clean ancestor of the launch tap, down to the
    fork node itself (sync on the spine tap at the fork), then continues down the capture path as above.
    Virtual taps: node arrival + the proof's median tap leg (late / early / stages from the tap's driving tree node).
    prev (FLOW-GEN-2, opt-in --start-prev: a previous count_align_plan --out doc): deterministic tie-break between
    passes.  A branch node the previous plan kept as its own stage is not contracted again, and a retime node it used
    ('st:<path>' dst of a retime start edge) is taken again whenever it is a candidate of the same search and still
    CLEAN under the same rule; only otherwise the default choice (deepest clean node) applies.  So re-planning from
    the measured build of a plan keeps its stage set (fixed point) unless a kept stage is no longer clean.
    None (default): unchanged.
    max_hop_um (opt-in): a clean segment must also fit this Manhattan physical tap-to-tap reach.
    This preserves branch stages and inserts existing clock-node retime stages; a gap with no legal
    intermediate node fails clean_ok. Emitted flop siting and final pin geometry still need GEOM.
    data_delay (HEAD-START-4 V1, opt-in --start-data-delay, load_start_data_delay): every port (final and candidate) is
    judged on the sampled phase d - dd (shift_data_delay); None (default): unchanged (clock-only).
    Returns (root, edges, info)."""
    if max_hop_um is not None and (not math.isfinite(max_hop_um) or max_hop_um <= 0):
        raise ValueError("START max hop must be finite and positive")
    if data_delay is not None and (data_delay.get("model") is not None or data_delay.get("corner_models")) and max_hop_um is None:
        raise ValueError("--start-data-delay hop model needs --start-max-hop-um (port hop geometry)")
    import die_sta_related as DSR
    cs = list(ctx)
    c0 = ctx[cs[0]]
    if max_hop_um is not None:
        xy = c0["meta"].get("node_xy_um", {})
        if not all(p in xy and len(xy[p]) == 2 and all(math.isfinite(float(v)) for v in xy[p])
                   for p in c0["meta"]["node_late_ps"]):
            raise ValueError("START max-hop needs finite physical coordinates for every tap/node")
    p2r = {}
    for r in rows:
        p2r.setdefault(r.get("src_part", r["src"]), r["src"])
        p2r.setdefault(r.get("dst_part", r["dst"]), r["dst"])
    rtaps = defaultdict(list)
    for k, t in sorted(c0["taps"].items()):
        if t.get("part") in p2r:
            rtaps[p2r[t["part"]]].append(k)
    regions = sorted({r["src"] for r in rows} | {r["dst"] for r in rows})
    miss = [x for x in regions if not rtaps.get(x)]
    if miss:
        raise ValueError(f"--start-tree clock: {len(miss)} regions without proof taps (e.g. {miss[:5]})")
    for role, overrides in (("capture", capture_taps), ("launch", launch_taps)):
        for region, tap in (overrides or {}).items():
            if region not in rtaps or tap not in rtaps[region] or any(tap not in ctx[c]["taps"] for c in cs):
                raise ValueError(f"START {role} override {region}: {tap} is not that region's measured proof tap")
    for role, positions in (endpoint_xy or {}).items():
        if role not in ("launch", "capture"):
            raise ValueError("START endpoint coordinates require launch/capture roles")
        for region, xy in positions.items():
            if region not in regions or len(xy) != 2 or not all(math.isfinite(float(v)) for v in xy):
                raise ValueError("START endpoint coordinates need finite points of real START regions")
    leg = {c: DSR.tap_leg(k["meta"], k["taps"]) for c, k in ctx.items()}
    fleg = {c: DSR.tap_leg_fall(k["meta"], k["taps"]) for c, k in ctx.items()}
    # Leaves have one actual measured capture tap. Their clock path is not the
    # LCP of all taps elsewhere in the physical partition.
    capture_of_key = {x: (capture_taps or {}).get(x) or min(rtaps[x], key=lambda k: (float(c0["taps"][k]["late_ps"]), k)) for x in regions}
    rootp = {}
    for x in regions:
        ps = [c0["taps"][k]["tree_path"] for k in ([capture_of_key[x]] if leaf_origins else rtaps[x])]
        p = ps[0]
        for q in ps[1:]:
            p = _lcp(p, q)
        rootp[x] = p
    paths = sorted(set(rootp.values()))
    allp = set(paths) | {_lcp(a, b) for a, b in zip(paths, paths[1:])}
    if len(paths) > 1:
        top = paths[0]
        for q in paths[1:]:
            top = _lcp(top, q)
        allp.add(top)
    at = defaultdict(list)
    for x in regions:
        at[rootp[x]].append(x)
    node_of, path_of = {}, {}
    for p in sorted(allp, key=lambda q: (len(q), q)):
        prim = at[p][0] if at.get(p) and not leaf_origins else f"st:{p}"
        node_of[p] = prim
        path_of[prim] = p
        for x in (at.get(p, []) if leaf_origins else at.get(p, [])[1:]):
            path_of[x] = p
    root = node_of[min(allp, key=lambda q: (len(q), q))]

    def vtap(c, p):
        return DSR.virtual_tap(ctx[c]["meta"], ctx[c]["taps"], p, leg[c], fleg[c])

    def capture_of(y):
        if y.startswith("st:"):
            return vtap(cs[0], path_of[y])
        if leaf_origins:
            return capture_of_key[y]
        if capture_taps is not None and y in capture_taps:
            return capture_taps[y]
        m = c0["meta"]
        return min(rtaps[y], key=lambda k: (float(c0["taps"][k]["late_ps"]) - float(m["node_late_ps"][path_of[y]]), k))

    def launch_of(x, cap_path):
        if x.startswith("st:"):
            return vtap(cs[0], path_of[x])
        if launch_taps is not None and x in launch_taps:
            return launch_taps[x]
        m = c0["meta"]

        def key(k):
            t = c0["taps"][k]
            f = _lcp(t["tree_path"], cap_path)
            return (-len(f), float(t["late_ps"]) - float(m["node_late_ps"][f]), k)
        return min(rtaps[x], key=key)

    def interval(a, b, corner_intervals=None):
        old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
        try:
            lo = hi = flo = fhi = None
            fall_ok = True
            for c in cs:
                for k in (a, b):
                    if k.startswith("__st__"):
                        vtap(c, k[6:])
                tp = ctx[c]["taps"]
                # FLOW-ONEMODEL-1: the gate's own pair function (die_sta_related.count_align_start_ports calls it too)
                iv = DSR.ca_pair_interval(tp[a], tp[b], a, b, ctx[c]["rng"], ctx[c]["ocv"])
                lo = iv[0] if lo is None else min(lo, iv[0])
                hi = iv[1] if hi is None else max(hi, iv[1])
                try:
                    fv = DSR.ca_pair_interval(tp[a], tp[b], a, b, ctx[c]["rng"], ctx[c]["ocv"], "fall")
                    flo = fv[0] if flo is None else min(flo, fv[0])
                    fhi = fv[1] if fhi is None else max(fhi, fv[1])
                except DSR.FallArrivalMissing:
                    fall_ok = False
                    fv = (None, None)
                if corner_intervals is not None:
                    corner_intervals[c] = (iv[0], iv[1], fv[0], fv[1])
        finally:
            DSR.CPPR_LCA = old
        A, B = c0["taps"][a], c0["taps"][b]
        node = _lcp(A["tree_path"], B["tree_path"]) or "h"
        nl = c0["meta"]["node_late_ps"]
        d = 0.5 * (float(B["late_ps"]) + float(B["early_ps"])) - 0.5 * (float(A["late_ps"]) + float(A["early_ps"]))
        d = min(max(d, lo), hi)
        geometry = {}
        if max_hop_um is not None:
            def xy(t, role):
                region = p2r.get(t.get("part"))
                q = (endpoint_xy or {}).get(role, {}).get(region)
                if q is None:
                    q = t.get("xy_um", c0["meta"].get("node_xy_um", {}).get(t["tree_path"]))
                if q is None or len(q) != 2 or not all(math.isfinite(float(v)) for v in q):
                    raise ValueError("START max-hop needs finite physical coordinates for every tap/node")
                return q
            aa, bb = xy(A, "launch"), xy(B, "capture")
            geometry = dict(hop_um=sum(abs(float(x) - float(y)) for x, y in zip(aa, bb)))
        return dict(**geometry, d_ps=d, p_dn_ps=d - lo, p_up_ps=hi - d, fork_node=node,
                    fall_lo=flo if fall_ok else None, fall_hi=fhi if fall_ok else None,
                    unshared_a_ps=float(A["late_ps"]) - float(nl[node]), unshared_b_ps=float(B["late_ps"]) - float(nl[node]))

    def ival(a, b, src, dst):
        by_corner = {} if data_delay is not None and "corners" in data_delay else None
        r = interval(a, b, by_corner)
        if data_delay is None:
            return r
        port = f"start:{src}->{dst}"
        if by_corner is not None:
            delays = {c: start_data_delay_for_corner(data_delay, c).get(port) for c in cs}
            if all(v is not None for v in delays.values()):
                return shift_corner_data_delay(r, by_corner, delays)
            # An incomplete measured port cannot fall back to another corner or
            # the candidate model. Entirely new candidate edges may use the model.
            if any(v is not None for v in delays.values()) or port in data_delay["ports"]:
                return dict(r, data_delay_source="missing")
            models = data_delay.get("corner_models", {})
            if all(c in models for c in cs):
                h = r["hop_um"]
                delays = {c: tuple(models[c][key][0] + models[c][key][1]*h for key in ("lo_ps", "hi_ps")) for c in cs}
                if any(lo > hi for lo, hi in delays.values()):
                    raise ValueError(f"START data-delay corner model has inverted interval at hop {h}")
                return shift_corner_data_delay(r, by_corner, delays, "model")
        dd = data_delay_of(data_delay, port, r)
        return dict(r, data_delay_source="missing") if dd is None else shift_data_delay(r, *dd)

    smax = max(abs(float(start_skew[0])), abs(float(start_skew[1])))
    prev_mid = {e["dst"] for e in (prev or {}).get("start_edges", []) if e.get("retime")}
    prev_nodes = {e["dst"] for e in (prev or {}).get("start_edges", []) if not e.get("retime")}
    kept = 0

    def clean(r):
        q = dict(r, lo=r["d_ps"] - r["p_dn_ps"], hi=r["d_ps"] + r["p_up_ps"])
        n, _, _, dist = sync_choice(q, T, ap, start_skew, sync_ap)
        ok = n == 1 and (not skew_clean or dist - sync_ap >= smax)
        if clean_by == "width":
            # SAFE BY DESIGN: the port is narrow enough that one of rise / fall is clean wherever d lands, not only by
            # the luck of its phase.  FLOW-ONEMODEL-1: on the MEASURED edges (width_robust): a common shift of the
            # port's arrivals must always leave one edge clean; without a measured fall arrival there is one edge
            # only, so no port is width-clean (fail closed)
            ok = ok and width_robust(q, T, ap, float(start_skew[1]) - float(start_skew[0]))
        return ok and (max_hop_um is None or r["hop_um"] <= max_hop_um) and r.get("data_delay_source") != "missing"

    def part(k):
        return c0["taps"][k].get("part")

    edges = []
    pairs = []
    for p in sorted(allp, key=lambda q: (len(q), q)):
        prim = node_of[p]
        if prim != root:
            pp = max((q for q in allp if len(q) < len(p) and p.startswith(q)), key=len)
            pairs.append((node_of[pp], prim))
        pairs += [(prim, x) for x in (at.get(p, []) if leaf_origins else at.get(p, [])[1:])]
    if root_region is not None:
        if root_region not in regions:
            raise ValueError(f"START root {root_region} is not a real data region")
        # The physical clock tree is undirected for reset/START forwarding. Keep
        # the real boot source rather than inventing a root outside the host.
        neighbours = defaultdict(list)
        for a, b in pairs:
            neighbours[a].append(b)
            neighbours[b].append(a)
        seen, queue, pairs = {root_region}, [root_region], []
        for a in queue:
            for b in sorted(neighbours[a]):
                if b not in seen:
                    seen.add(b)
                    queue.append(b)
                    pairs.append((a, b))
        root = root_region
    # contract virtual branch nodes: a branch node needs its own start stage only if some child cannot take a CLEAN
    # port straight from the branch node's parent (fewer stages, fewer retime flops; every kept port stays clean)
    par_of = {y: x for x, y in pairs}
    kids_of = defaultdict(list)
    for x, y in pairs:
        kids_of[x].append(y)
    contracted = 0
    for p in sorted(allp, key=lambda q: (len(q), q)):
        v = node_of[p]
        if not v.startswith("st:") or v == root:
            continue
        x = par_of[v]

        def direct_ok(c):
            cp = capture_of(c)
            return clean(ival(launch_of(x, c0["taps"][cp]["tree_path"]), cp, x, c))
        if v in prev_nodes:
            kept += 1           # FLOW-GEN-2 --start-prev: the previous plan kept this branch stage; keep it
            continue
        if all(direct_ok(c) for c in kids_of[v]):
            for c in kids_of[v]:
                par_of[c] = x
                kids_of[x].append(c)
            kids_of[x].remove(v)
            del par_of[v], kids_of[v]
            contracted += 1
    pairs = [(x, y) for x in sorted(kids_of) for y in kids_of[x]]
    up_made = {}
    for x, y in pairs:
        cap = capture_of(y)
        cpath = c0["taps"][cap]["tree_path"]
        lau = launch_of(x, cpath)
        src, chain = x, []
        while True:
            r = ival(lau, cap, src, y)
            if clean(r) or len(chain) >= retime_max:
                break
            f = _lcp(c0["taps"][lau]["tree_path"], cpath)
            # retime candidates: tree nodes strictly below the launch fork, down to the child node (a virtual child)
            # or to the sync tap's driving node inside the child region (its own clock tree)
            stop = len(path_of[y]) - 1 if y.startswith("st:") else len(cpath) - 1
            best = None
            for n in (range(stop, len(f), -1) if prev_mid else ()):
                mp = cpath[:n]
                if f"st:{mp}" in prev_mid:
                    rm = ival(lau, vtap(cs[0], mp), src, f"st:{mp}")
                    if clean(rm):
                        best = (mp, rm)
                        kept += 1
                        break
            for n in (range(stop, len(f), -1) if best is None else ()):
                mp = cpath[:n]
                rm = ival(lau, vtap(cs[0], mp), src, f"st:{mp}")
                if clean(rm):
                    best = (mp, rm)
                    break
            up = False
            if best is None and retime_up:
                lp = c0["taps"][lau]["tree_path"] if lau in c0["taps"] else path_of.get(src, "")
                nlp = c0["meta"]["node_late_ps"]
                for n in range(len(f), len(lp)):
                    mp = lp[:n]
                    if mp not in nlp:
                        continue
                    rm = ival(lau, vtap(cs[0], mp), src, f"st:{mp}@{src if lau.startswith('__st__') else lau}")
                    if clean(rm):
                        best, up = (mp, rm), True
                        break
            if best is None:
                break
            mp, rm = best
            # DIE-S81-13 / DIE-QC-13: an up stage sits on the LAUNCH side, where a branch node st:<mp> of the start tree
            # (or another child's up stage) may already exist; it is its own flop, named by its launch tap (or by its
            # start parent when that is itself a retime node), and a second
            # child of the same region that climbs from the same launch tap to the same node REUSES it (one edge)
            mid = f"st:{mp}@{src if lau.startswith('__st__') else lau}" if up else f"st:{mp}"
            path_of[mid] = mp
            if not (up and mid in up_made):
                edges.append(dict(port=f"start:{src}->{mid}", src=src, dst=mid, launch=lau, capture=vtap(cs[0], mp),
                                  launch_part=part(lau), capture_part=None, retime=True, clean_ok=True, **rm))
                if up:
                    up_made[mid] = src
            elif up_made[mid] != src:
                raise ValueError(f"--start-retime-up: up stage {mid} reached from {up_made[mid]} and {src}")
            chain.append(mid)
            src, lau = mid, vtap(cs[0], mp)
        edges.append(dict(port=f"start:{src}->{y}", src=src, dst=y, launch=lau, capture=cap, launch_part=part(lau),
                          capture_part=part(cap), retime=False, clean_ok=clean(r), **r))
    for e in edges:
        # Climbing the same clock node from different real origins creates
        # distinct START flops. Keep each future measured clock pin distinct.
        for side, key in (("src", "launch"), ("dst", "capture")):
            if distinct_stage_clocks and e[side].startswith("st:") and "@" in e[side]:
                e[key] = vtap(cs[0], e[side][3:])
        e["lo"], e["hi"] = e["d_ps"] - e["p_dn_ps"], e["d_ps"] + e["p_up_ps"]
    start_tree_check(root, edges)
    info = dict(clean_by=clean_by, clean_by_width=sum(1 for e in edges if width_robust(e, T, ap)),
                fall_measured=sum(1 for e in edges if e.get("fall_lo") is not None),
                root=root, root_path=path_of[root], leg_ps={c: list(v) for c, v in leg.items()},
                regions=len(regions), branch_nodes=sum(1 for p in allp if not at.get(p)), branch_nodes_contracted=contracted,
                retime_nodes=sum(1 for e in edges if e["retime"]))
    if leaf_origins:
        info["leaf_origins"] = True
    if max_hop_um is not None:
        info.update(max_hop_um=max_hop_um, reach_fail=sum(e["hop_um"] > max_hop_um for e in edges))
    if data_delay is not None:
        used = {e["port"] for e in edges}
        info["data_delay"] = dict(basis=data_delay.get("basis"), model=data_delay.get("model"),
                                  measured=sum(e["data_delay_source"] == "measured" for e in edges),
                                  modelled=sum(e["data_delay_source"] == "model" for e in edges),
                                  missing=sum(e["data_delay_source"] == "missing" for e in edges),
                                  measured_unused=len(set(data_delay["ports"]) - used))
    if prev is not None:
        info["prev_kept"] = kept
        info["prev_nodes"] = len(prev_mid) + len(prev_nodes)
    return root, edges, info


def start_tree_check(root, edges):
    """fail closed unless the start edges form ONE tree from root: every node has exactly one incoming edge (the root
    none) and every node is reached from the root (DIE-QC-13: duplicate retime nodes made '753 nodes not reached')"""
    inc = defaultdict(list)
    kids = defaultdict(list)
    for e in edges:
        inc[e["dst"]].append(e["src"])
        kids[e["src"]].append(e["dst"])
    dup = {v: u for v, u in inc.items() if len(u) > 1}
    if root in inc:
        dup[root] = inc[root]
    seen, st = {root}, [root]
    while st:
        for k in kids[st.pop()]:
            if k not in seen:
                seen.add(k)
                st.append(k)
    lost = sorted((set(inc) | set(kids)) - seen)
    if dup or lost:
        raise ValueError(f"start tree is not a tree from {root}: {len(dup)} nodes with !=1 parent "
                         f"(e.g. {list(dup.items())[:3]}), {len(lost)} not reached (e.g. {lost[:3]})")


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
            r = byp[e["port"]]
            if e["edge"] == "fall" and r.get("fall_lo") is not None:
                # FLOW-ONEMODEL-1: the fall sample lands in the MEASURED fall interval
                x = rnd.uniform(r["fall_lo"], r["fall_hi"]) if mode == 0 else (r["fall_lo"], r["fall_hi"])[rnd.random() < 0.5]
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


class _Ident(dict):
    def __missing__(self, k):
        return k


def row_ports(rows):
    """FLOW-ONEMODEL-1: the plan rows as count_align_port_intervals ports + their {partition: region} map (the same
    map count_align_bind --parts ocv writes into bind parts, so the gate's --count-align-key region sees the same)"""
    ports = {r["port"]: dict(src=r["src"], dst=r["dst"], src_part=r.get("src_part"), dst_part=r.get("dst_part"))
             for r in rows}
    pr = _Ident()
    for r in rows:
        for k, x in (("src_part", "src"), ("dst_part", "dst")):
            if r.get(k) is not None:
                pr[r[k]] = r[x]
    return ports, pr


def sta_rows_hull(rows, a):
    """FLOW-ONEMODEL-1: hull every row with die_sta_related.sta_port_intervals (THE gate interval, per port, plus the
    measured-fall interval for start samples); returns the sta_hull summary"""
    import die_sta_related as DSR
    cs = sorted({c.split("_")[0] for c in a.corner.split(",")})
    ports, pr = row_ports(rows)
    sta = DSR.sta_port_intervals(a.sta_proof, a.sta_plan, cs, ports, pr, a.sta_clock_cal, a.sta_cppr_lca, fall=True,
                                 **sta_ocv_kw(a))
    return sta_hull(rows, sta)


def sta_hull(rows, sta):
    """DIE-HEAD-5 (COORD 00:22): ONE interval model.  sta = {corner: {'srcpart->dstpart': (lo, hi)}} from
    die_sta_related.sta_d_intervals (legacy), or FLOW-ONEMODEL-1 {corner: {rise: {port: (lo, hi)}, fall: {port:
    (lo, hi) | None}, unbound: [...]}} from die_sta_related.sta_port_intervals = the per-port interval die_sta_related
    --count-align gates on (count_align_port_intervals).  Each row's derated interval
    [d - p_dn, d + p_up] (landed_phase_ocv AOCV + droop, kept: 12.14a crossing margin after OCV + droop) becomes its hull
    with the STA interval of its port on every corner, so every plan margin (lag, sync edge clearance incl.
    start skew) is a lower bound of the same margin on the gate numbers.  d (nominal) is unchanged.  With the port form
    each row also gets fall_lo / fall_hi: the union over corners of its MEASURED fall interval, or None if a corner has
    none (then the planner never samples it on the fall edge).  Returns a summary."""
    widened, missing, worst = 0, [], (0.0, None)
    port_form = all(isinstance(c, dict) and "rise" in c for c in sta.values()) and bool(sta)
    nofall = 0
    for r in rows:
        if port_form:
            iv = [c["rise"][r["port"]] for c in sta.values() if c["rise"].get(r["port"]) is not None]
            fv = [c.get("fall", {}).get(r["port"]) for c in sta.values()]
            if any(x is None for x in fv):
                r["fall_lo"] = r["fall_hi"] = None
                nofall += 1
            else:
                r["fall_lo"], r["fall_hi"] = min(x[0] for x in fv), max(x[1] for x in fv)
            r["_named"] = True
            us = [c["unshared"][r["port"]] for c in sta.values() if r["port"] in (c.get("unshared") or {})]
            if us:
                r["unshared_sta_ps"] = max(us)
        else:
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
    out = dict(corners=sorted(sta), rows=len(rows), widened=widened, max_widen_ps=round(worst[0], 1),
               max_widen_port=worst[1], missing=len(missing), missing_ports=missing[:20])
    if port_form:
        unb = sorted({t for c in sta.values() for t in c.get("unbound", [])})
        out.update(interval="port (die_sta_related.count_align_port_intervals)", rows_without_measured_fall=nofall,
                   unbound=len(unb), unbound_tags=unb[:20])
    return out


def add_sta_ocv_args(ap):
    """CA-OCV-1: the --sta-proof hull takes the same clock variation term die_sta_related --count-align adds
    (--clock-ocv / --clock-droop / --droop-regions / --core-latency-ff); default none = unchanged hull."""
    ap.add_argument("--sta-clock-ocv", choices=("none", "flat", "table"), default="none",
                    help="as die_sta_related --clock-ocv (CA-OCV-1: the gate's CA interval carries it; table = gate form)")
    ap.add_argument("--sta-clock-droop", choices=("stated", "shared"), help="as die_sta_related --clock-droop")
    ap.add_argument("--sta-droop-regions", help="as die_sta_related --droop-regions")
    ap.add_argument("--sta-core-latency-ff", type=float, help="as die_sta_related --core-latency-ff")
    ap.add_argument("--sta-ca-ring", metavar="SPEC.json",
                    help="as die_sta_related --ca-ring (DIE-HEAD-18 opt-in): the hull uses the BUILT ring clocks")
    ap.add_argument("--sta-clock-cell", choices=("auto", "buf", "inv", "inv2"), default="auto",
                    help="as die_sta_related --clock-cell: auto = the proof's tap_arrivals clock_cell declaration; "
                         "missing -> FAIL closed (COORD ruling ba28d3143)")


def sta_ocv_kw(a):
    return dict(clock_ocv=a.sta_clock_ocv, clock_droop=a.sta_clock_droop, droop_regions_file=a.sta_droop_regions,
                core_latency_ff=a.sta_core_latency_ff, clock_cell=getattr(a, "sta_clock_cell", "auto"),
                **({"ca_ring": a.sta_ca_ring} if getattr(a, "sta_ca_ring", None) else {}))


def add_start_tree_args(ap):
    """START-TREE-1 (opt-in): --start-tree clock; default 'data' = the min-ambiguity tree over data crossings (unchanged)"""
    ap.add_argument("--start-tree", choices=("data", "clock"), default="data",
                    help="START-TREE-1 (12.16b(iv)/12.16e): 'clock' = the start (reset-release) tree follows the clock "
                         "tree of --sta-proof, one dedicated start port per clock-tree edge (fork tap -> child sync tap, "
                         "retime flops on tree nodes where a port would be unclean), each port checked as a crossing "
                         "with the --sta-clock-ocv model; needs --sta-proof/--sta-plan and --sta-clock-ocv table")
    ap.add_argument("--start-root-region", help="real boot source region; forward START over the same undirected clock-tree links")
    ap.add_argument("--start-native-clocks", action="store_true",
                    help="use measured t_<part>__clk for both START ends, matching emitted .clk(clk); no nearest data-tap substitution")
    ap.add_argument("--start-partition-origins", action="store_true",
                    help="full reprice with one origin per src_part/dst_part (removes long same-region START relays); requires native clocks")
    ap.add_argument("--start-launch-taps", metavar="JSON",
                    help="opt-in {region: measured proof tap port} fixed physical origin launch clocks")
    ap.add_argument("--start-endpoint-xy", metavar="JSON",
                    help="opt-in {launch|capture: {region: [die x,y]}} actual physical START pins; clock proof tap selection is separate")
    ap.add_argument("--start-capture-taps", metavar="JSON",
                    help="opt-in {region: measured proof tap port} capture selection; actual type-uniform GLUE pin mapping is supplied by plan owner")
    ap.add_argument("--start-max-hop-um", type=float,
                    help="opt-in physical START reach bound: keep/split clock-tree stages until each Manhattan tap-to-tap hop fits; requires physical proof coordinates; final emitted placement still needs GEOM")
    ap.add_argument("--start-leaf-origins", action="store_true", help="opt-in: each data START origin is a leaf of the virtual clock-node tree; needed for nested physical clock groups")
    ap.add_argument("--start-retime-max", type=int, default=8, help="max retime flops per clock-tree start edge")
    ap.add_argument("--start-retime-up", action="store_true",
                    help="--start-tree clock (opt-in): allow retime flops on ANCESTOR nodes of the launch tap (climb the "
                         "launch region tree to the fork node, sync on the spine tap) when no capture-side node is clean; "
                         "default off = byte-identical")
    ap.add_argument("--start-prev", metavar="PLAN_JSON",
                    help="--start-tree clock (opt-in, FLOW-GEN-2): deterministic tie-break between passes: keep the "
                         "retime nodes and start EDGE_FALL picks of this previous count_align_plan --out doc wherever "
                         "they are still clean / tie the best edge (default off = byte-identical)")
    ap.add_argument("--start-data-delay", metavar="JSON",
                    help="--start-tree clock (opt-in, HEAD-START-4 V1): per start port MEASURED launch CLK -> capture D "
                         "delay {ports: {port: [lo, hi]}, model: {lo_ps: [a, b], hi_ps: [a, b]} (a + b x hop_um, "
                         "candidate ports)}; each port is judged on the sampled phase d - dd (load_start_data_delay); "
                         "default off = byte-identical (clock-only)")
    ap.add_argument("--start-clean", choices=("phase", "width"), default="phase",
                    help="--start-tree clock: 'phase' (default) = the CA rule: the port's derated interval (shared model, "
                         "OCV + droop) keeps >= T/8 from every sampling boundary of the chosen edge; 'width' (stricter) = "
                         "also width (+ skew range) <= T/2 - 2 ap, clean wherever d lands (more retime stages on deep trees)")


def check_start_tree_args(a, err):
    if getattr(a, "start_partition_origins", False) and not getattr(a, "start_native_clocks", False):
        err("--start-partition-origins needs --start-native-clocks")
    if a.start_tree != "clock":
        if getattr(a, "start_root_region", None):
            err("--start-root-region needs --start-tree clock")
        if getattr(a, "start_native_clocks", False):
            err("--start-native-clocks needs --start-tree clock")
        if getattr(a, "start_prev", None):
            err("--start-prev needs --start-tree clock")
        if getattr(a, "start_launch_taps", None) or getattr(a, "start_endpoint_xy", None):
            err("--start-launch-taps / --start-endpoint-xy need --start-tree clock")
        if getattr(a, "start_capture_taps", None):
            err("--start-capture-taps needs --start-tree clock")
        if getattr(a, "start_max_hop_um", None) is not None:
            err("--start-max-hop-um needs --start-tree clock")
        if getattr(a, "start_data_delay", None):
            err("--start-data-delay needs --start-tree clock")
        return
    if not (a.sta_proof and a.sta_plan):
        err("--start-tree clock needs --sta-proof and --sta-plan (the clock tree)")
    if a.sta_clock_ocv == "none":
        err("--start-tree clock needs --sta-clock-ocv table (12.16b(iv): reset release under the same CA rule)")
    if a.tree_parent:
        err("--start-tree clock and --tree-parent exclude each other (the clock tree fixes every start edge)")


def start_tree_from_args(a, rows, err):
    """(start_edges, start_root, info) for --start-tree clock, else (None, None, None)"""
    if getattr(a, "start_retime_up", False) and a.start_tree != "clock":
        err("--start-retime-up needs --start-tree clock")
    if getattr(a, "start_leaf_origins", False) and a.start_tree != "clock":
        err("--start-leaf-origins needs --start-tree clock")
    if a.start_tree != "clock":
        return None, None, None
    check_start_tree_args(a, err)
    if getattr(a, "start_partition_origins", False):
        partition_start_origins(rows)
    cs = [c.split("_")[0] for c in a.corner.split(",")]
    cs = list(dict.fromkeys(cs))
    ctx = clock_contexts(a.sta_proof, a.sta_plan, cs, a.sta_clock_cal, a.sta_clock_ocv, a.sta_clock_droop,
                         a.sta_droop_regions, a.sta_core_latency_ff, getattr(a, "sta_clock_cell", "auto"))
    native = native_start_clocks(rows, ctx) if getattr(a, "start_native_clocks", False) else None
    captures = json.load(open(a.start_capture_taps)) if getattr(a, "start_capture_taps", None) else None
    launches = json.load(open(a.start_launch_taps)) if getattr(a, "start_launch_taps", None) else None
    if native is not None:
        if any(t != native.get(r) for m in (captures, launches) for r, t in (m or {}).items()):
            raise ValueError("explicit START override conflicts with emitted native clock frame")
        captures = launches = native
    root, edges, info = clock_start_edges(rows, ctx, a.period, a.aperture, a.sync_aperture, a.start_skew,
                                          a.start_skew_clean, a.start_retime_max, a.start_clean,
                                          getattr(a, "start_retime_up", False), start_prev_doc(a),
                                          getattr(a, "start_max_hop_um", None),
                                          captures, launches,
                                          json.load(open(a.start_endpoint_xy)) if getattr(a, "start_endpoint_xy", None) else None,
                                          getattr(a, "start_root_region", None), bool(native),
                                          getattr(a, "start_leaf_origins", False),
                                          load_start_data_delay(a.start_data_delay)
                                          if getattr(a, "start_data_delay", None) else None)
    if native is not None:
        info["native_origin_clocks"] = native
    return edges, root, info


def start_prev_doc(a):
    """--start-prev PLAN_JSON -> the previous plan doc (None without the flag)"""
    p = getattr(a, "start_prev", None)
    return json.load(open(p)) if p else None


def start_prefer_of(doc):
    """{start port: 'rise' | 'fall'} of a previous plan doc's start tree (regions[].start_from)"""
    return {g["start_from"]["port"]: g["start_from"]["edge"] for g in (doc or {}).get("regions", [])
            if g.get("start_from") and g["start_from"].get("edge")}


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
    ap.add_argument("--sta-clock-cal", choices=("none", "spice", "spice_edge", "spice_buf_edge", "spice_cell"),
                    default="spice",
                    help="as die_sta_related --clock-cal (12.15b gate: spice)")
    ap.add_argument("--sta-cppr-lca", action="store_true", help="as die_sta_related --cppr-lca")
    add_sta_ocv_args(ap)
    ap.add_argument("--max-depth", type=int, choices=(8, 16), default=8,
                    help="DIE-S81-11 / 12.16 b(iii) opt-in: largest standard ring DEPTH (16 needs its RTL proof; default 8)")
    add_start_tree_args(ap)
    ap.add_argument("--mc-chips", type=int, default=0)
    ap.add_argument("--out")
    ap.add_argument("--cases", help="TSV for the Verilator bench: port DEPTH L_ps (lo / mid / hi per crossing)")
    a = ap.parse_args(argv)
    check_start_tree_args(a, ap.error)
    rows = load_rows(a.ocv_json, a.corner, a.scale)
    sta_info = None
    if a.sta_proof:
        if not a.sta_plan:
            ap.error("--sta-proof needs --sta-plan")
        sta_info = sta_rows_hull(rows, a)
        sta_info.update(proof=a.sta_proof, plan=a.sta_plan, clock_cal=a.sta_clock_cal, cppr_lca=a.sta_cppr_lca,
                        clock_ocv=a.sta_clock_ocv,
                        model="hull(landed_phase_ocv derated, die_sta_related.count_align_port_intervals)")
        import die_sta_related as DSR
        cs = sorted({c.split("_")[0] for c in a.corner.split(",")})
        tp = DSR.Path(a.sta_proof) / f"tap_arrivals_{cs[0]}.json"
        # record only (the hull above already resolved the cell, fail closed); no proof file = stubbed hull in tests
        cc, cb = (DSR.resolve_clock_cell(getattr(a, "sta_clock_cell", "auto"), a.sta_proof,
                                         DSR.load_taps(DSR.Path(a.sta_proof), cs[0])[0]) if tp.exists()
                  else ("buf", "no tap_arrivals"))
        if cc != "buf":         # CLK-INV-CAL-1 (BUFx24 records unchanged)
            sta_info["clock_cell"] = dict(cell=cc, basis=cb, aocv_class=DSR.CLOCK_CELL_AOCV_CLASS[cc])
        if sta_info["missing"]:
            print(f"WARNING --sta-proof: {sta_info['missing']} crossings without STA tap pairs keep the OCV interval "
                  "(die_sta_related fails them closed: no taps)", file=sys.stderr)
    if a.start_skew_clean and not any(a.start_skew):
        ap.error("--start-skew-clean needs --start-skew LO,HI")
    sedges, sroot, sinfo = start_tree_from_args(a, rows, ap.error)
    skw = dict(start_edges=sedges, start_root=sroot) if sedges is not None else {}
    if sedges is not None and getattr(a, "start_prev", None):
        skw["start_prefer"] = start_prefer_of(start_prev_doc(a))
    summ, out, regs = plan(rows, a.period, a.aperture, a.wander_frac, a.sync_aperture, a.pad, parse_edge_pad(a.edge_pad),
                           a.start_skew, a.start_skew_clean, tree_parent=parse_edge_pad(a.tree_parent, str) or None,
                           max_depth=a.max_depth, **skw)
    if sinfo:
        summ["start_tree"].update(sinfo)
    if a.tree_parent:
        summ["tree_parent"] = parse_edge_pad(a.tree_parent, str)
    if any(a.start_skew):
        summ["start_skew_ps"] = list(a.start_skew)
    if sta_info:
        summ["sta_interval"] = sta_info
    summ.update(corner=a.corner, period_ps=a.period, aperture_ps=a.aperture, sync_aperture_ps=a.sync_aperture,
                wander_frac=a.wander_frac, pad=a.pad, scale=a.scale, source=a.ocv_json)
    if a.mc_chips:
        n, bad, wl, wh = mc_check(rows + (sedges or []), out, regs, a.period, a.mc_chips, a.sync_aperture,
                                  start_skew=a.start_skew if a.start_skew_clean else None)
        summ["mc"] = dict(chips=n, violations=bad, worst_lo_to_guard_ps=wl, worst_hi_to_guard_ps=wh)
    print(json.dumps({k: v for k, v in summ.items() if k != "tree_edges_ambiguous"}, indent=1))
    if a.out:
        doc = dict(summary=summ, regions=regs, crossings=out)
        if sedges is not None:
            doc["start_edges"] = [{k: v for k, v in e.items() if not k.startswith("_")} for e in sedges]
        json.dump(doc, open(a.out, "w"), indent=0)
    if a.cases:
        with open(a.cases, "w") as f:
            for o in out:
                if not o.get("depth"):
                    continue
                for L in (o["L_lo_ps"], 0.5 * (o["L_lo_ps"] + o["L_hi_ps"]), o["L_hi_ps"]):
                    f.write(f"{o['port']}\t{o['depth']}\t{int(round(L))}\n")
    sfail = summ.get("start_tree", {}).get("start_fail", 0)
    return 0 if summ["fail"] == 0 and summ["regions_reached"] == summ["regions"] and not sfail else 1


if __name__ == "__main__":
    sys.exit(main())
