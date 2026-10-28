#!/usr/bin/env python3
"""DIE-S81 (12.13 LOCALITY FIRST) minimal locality estimate, hand-over to LOCALITY-SCORE-1 (tools/die_plan/locality.py).

  s81_locality.py PLAN.json REGIONS.json OUT.json [--span-mm 4.4] [--ps-mm 321] [--core-lat 250] [--derate 0.095]

1) traffic matrix: per plan port, bits = width, bit-mm = width x Manhattan(part centres); part x part matrix.
2) locality score of a region map {part: region}: bits / bit-mm inside vs across, crossings, cut ports.
3) estimate (no build): region roots at the region bbox centre; region clock fed ALONG THE LINK GRAPH (maximum
   spanning tree of the region graph by crossing bits, rooted at the die-centre region; clock follows data).
   Unshared clock per crossing U = max(side) of [tree hops LCA-root -> region root] + [root -> part centre] (ps/mm x
   Manhattan) + core latency (both sides equal, still unshared).  Derated margin = P/2 - derate x U (d nominal = 0,
   balanced); derate 0.095 = calibrated from KV (5.66 ns -> -136 ps) and HEAD guidance (3.4 ns -> +100 ps).
   Also the current form (all regions under one die H-tree root at the die centre) for comparison.
4) proposer: greedy agglomerative regrouping of parts by traffic, a merge allowed only if the merged bbox span
   (max side) <= --span-mm and fill >= 0.5 (contiguity proxy); hard/PHY merges from REGIONS kept.
"""
import argparse, json, math, sys
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("regions"); ap.add_argument("out")
ap.add_argument("--span-mm", type=float, default=4.4)
ap.add_argument("--ps-mm", type=float, default=321.0)
ap.add_argument("--core-lat", type=float, default=250.0)
ap.add_argument("--derate", type=float, default=0.095)
ap.add_argument("--tree", default="maxbits", choices=["maxbits", "spt"])
ap.add_argument("--hop-ps", type=float, default=60.0, help="fixed per forwarding hop (re-buffer at region root)")
a = ap.parse_args()
P = json.load(open(a.plan)); R0 = json.load(open(a.regions))["part_region"]
half = P["die"]["period_ps"] / 2.0
T = P["partition_types"]
box, cen = {}, {}
for p in P["partitions"]:
    w, h = T[p["type"]]["outline_um"]
    if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    x, y = p["origin_um"]
    box[p["name"]] = (x, y, x + w, y + h); cen[p["name"]] = (x + w / 2, y + h / 2)
man = lambda u, v: abs(u[0] - v[0]) + abs(u[1] - v[1])
M = defaultdict(int)
for pr in P["ports"]:
    s, d = pr["src"]["part"], pr["dst"]["part"]
    if s in cen and d in cen and s != d:
        M[tuple(sorted((s, d)))] += pr["width"]
tot_bits = sum(M.values()); tot_bmm = sum(b * man(cen[s], cen[d]) / 1000 for (s, d), b in M.items())


def score(reg):
    inb = inbmm = 0; xb = defaultdict(int); xcut = 0
    for (s, d), b in M.items():
        bmm = b * man(cen[s], cen[d]) / 1000
        if reg[s] == reg[d]:
            inb += b; inbmm += bmm
        else:
            xb[tuple(sorted((reg[s], reg[d])))] += b; xcut += 1
    return dict(regions=len(set(reg.values())), bits_inside_pct=round(100 * inb / tot_bits, 2),
                bitmm_inside_pct=round(100 * inbmm / tot_bmm, 2), crossing_part_pairs=xcut,
                crossing_bits=sum(xb.values()), region_links=len(xb)), xb


def rbox(reg):
    B = {}
    for p, r in reg.items():
        x0, y0, x1, y1 = box[p]
        b = B.get(r)
        B[r] = (x0, y0, x1, y1) if b is None else (min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1))
    return B


def estimate(reg, mode):
    _, xb = score(reg); B = rbox(reg)
    root = {r: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for r, b in B.items()}
    W, H = P["die"]["outline_um"]; dc = (W / 2, H / 2)
    k = a.ps_mm / 1000.0
    if mode == "dietree":   # every region root hangs off one die-centre source (H-tree ~ Manhattan from centre)
        dep = {r: k * man(dc, root[r]) for r in root}
        par = {r: None for r in root}
    else:                   # link-following: maximum spanning tree by crossing bits, rooted nearest die centre
        rr = min(root, key=lambda r: man(root[r], dc))
        adj = defaultdict(list)
        for (u, v), b in xb.items():
            adj[u].append((b, v)); adj[v].append((b, u))
        import heapq
        par = {rr: None}; dep = {rr: 0.0}; hq = [(-b, rr, v) for b, v in adj[rr]]; heapq.heapify(hq)
        if a.tree == "spt":
            hq = [(k * man(root[rr], root[v]) + a.hop_ps, rr, v) for b, v in adj[rr]]; heapq.heapify(hq)
        while hq:
            nb, u, v = heapq.heappop(hq)
            if v in par:
                continue
            par[v] = u; dep[v] = dep[u] + k * man(root[u], root[v]) + a.hop_ps
            for b, w in adj[v]:
                if w not in par:
                    heapq.heappush(hq, ((dep[v] + k * man(root[v], root[w]) + a.hop_ps) if a.tree == "spt" else -b, v, w))
        for r in root:  # isolated regions (no crossings): fed from the nearest fed region
            if r not in par:
                q = min(par, key=lambda x: man(root[x], root[r])); par[r] = q
                dep[r] = dep[q] + k * man(root[q], root[r]) + a.hop_ps

    def anc(r):
        out = [r]
        while par.get(r) is not None:
            r = par[r]; out.append(r)
        return out
    rows = []
    for (s, d), b in M.items():
        ra, rb = reg[s], reg[d]
        if ra == rb:
            continue
        if mode == "dietree":
            ua, ub = dep[ra], dep[rb]
        else:
            A, Bc = anc(ra), anc(rb); sb = set(Bc); l = next(x for x in A if x in sb)
            ua, ub = dep[ra] - dep[l], dep[rb] - dep[l]
        ua += k * man(root[ra], cen[s]) + a.core_lat; ub += k * man(root[rb], cen[d]) + a.core_lat
        U = max(ua, ub)
        row = dict(src=s, dst=d, ra=ra, rb=rb, bits=b, U_ps=round(U, 1), margin_ps=round(half - a.derate * U, 1),
                   tree_edge=(mode != "dietree" and (par.get(ra) == rb or par.get(rb) == ra)))
        if mode != "dietree" and not row["tree_edge"]:
            pa = A[:A.index(l) + 1]; pb = Bc[:Bc.index(l)][::-1]; path = pa + pb
            row["chain_hops"] = len(path) - 1
            row["chain_mm"] = round(sum(man(root[path[i]], root[path[i + 1]]) for i in range(len(path) - 1)) / 1000, 2)
            row["direct_mm"] = round(man(cen[s], cen[d]) / 1000, 2)
        rows.append(row)
    us = sorted(r["U_ps"] for r in rows)
    ins = {r: k * max(man(root[r], (B[r][0], B[r][1])), man(root[r], (B[r][2], B[r][3]))) + a.core_lat for r in B}
    return dict(mode=mode, crossings=len(rows), U_max=us[-1] if us else 0, U_p50=us[len(us) // 2] if us else 0,
                over_3400=sum(u > 3400 for u in us), margin_lt_100=sum(r["margin_ps"] < 100 for r in rows),
                bits_margin_lt_100=sum(r["bits"] for r in rows if r["margin_ps"] < 100),
                worst_margin=min((r["margin_ps"] for r in rows), default=None),
                region_insertion_max_ps=round(max(ins.values()), 1), feed_depth_max_ps=round(max(dep.values()), 1),
                chain_fix=dict(n=sum(1 for r in rows if r["margin_ps"] < 100 and not r["tree_edge"]),
                               extra_crossings=sum(r.get("chain_hops", 1) - 1 for r in rows if r["margin_ps"] < 100 and not r["tree_edge"]),
                               extra_bit_mm=round(sum(r["bits"] * (r.get("chain_mm", 0) - r.get("direct_mm", 0)) for r in rows if r["margin_ps"] < 100 and not r["tree_edge"]), 1),
                               max_hops=max([r.get("chain_hops", 0) for r in rows if r["margin_ps"] < 100 and not r["tree_edge"]], default=0)),
                worst5=sorted(rows, key=lambda r: r["margin_ps"])[:5]), rows


def propose(seed):
    reg = dict(seed); hard = {p for p, r in seed.items() if r.startswith("hard")}
    lim = a.span_mm * 1000
    while True:
        _, xb = score(reg); B = rbox(reg); area = defaultdict(float)
        for p, r in reg.items():
            x0, y0, x1, y1 = box[p]; area[r] += (x1 - x0) * (y1 - y0)
        done = False
        for (u, v), b in sorted(xb.items(), key=lambda kv: -kv[1]):
            if u.startswith("hard") or v.startswith("hard"):
                continue
            bu, bv = B[u], B[v]; mb = (min(bu[0], bv[0]), min(bu[1], bv[1]), max(bu[2], bv[2]), max(bu[3], bv[3]))
            if max(mb[2] - mb[0], mb[3] - mb[1]) > lim:
                continue
            if (area[u] + area[v]) / ((mb[2] - mb[0]) * (mb[3] - mb[1])) < 0.5:
                continue
            for p in reg:
                if reg[p] == v:
                    reg[p] = u
            done = True; break
        if not done:
            return reg


cur = {p: R0.get(p, "solo_" + p) for p in cen}
out = dict(input=dict(plan=a.plan, regions=a.regions, ps_mm=a.ps_mm, core_lat=a.core_lat, derate=a.derate,
                      hop_ps=a.hop_ps, span_mm=a.span_mm, half_period=half),
           traffic=dict(part_pairs=len(M), bits=tot_bits, bit_mm=round(tot_bmm, 1),
                        top_pairs=[dict(a=s, b=d, bits=b, mm=round(man(cen[s], cen[d]) / 1000, 2))
                                   for (s, d), b in sorted(M.items(), key=lambda kv: -kv[1])[:15]]))
out["current_179"] = score(cur)[0]
out["current_179_dietree"] = estimate(cur, "dietree")[0]
out["current_179_linkfeed"] = estimate(cur, "link")[0]
new = propose(cur)
out["proposed"] = score(new)[0]
e, rows = estimate(new, "link"); out["proposed_linkfeed"] = e
out["proposed_dietree"] = estimate(new, "dietree")[0]
out["proposed_map"] = new
out["proposed_rows"] = rows
json.dump(out, open(a.out, "w"), indent=1)
for k in ("traffic", "current_179", "current_179_dietree", "current_179_linkfeed", "proposed", "proposed_linkfeed", "proposed_dietree"):
    v = out[k]; print(k, json.dumps({kk: vv for kk, vv in v.items() if kk not in ("worst5", "top_pairs")}))
