"""CORES-EARLY-5 ONE-PAGE ESTIMATE: ICG-aware core tree for S81 bf_col / rom_elem_q _gb (estimate only, no build).
Input: sinks_<core>.txt (ce5_sinks.tcl on the data-only 3_place.odb). Model: PLAN-ICG-MODEL OPEN_SUBTREE_CAL (main
core_infra_plan.py) for every CTS-open subtree (gated domain or ungated tile leaf), ICG stage from the ASAP7 liberty.
A: as-is RTL gates, one ICG per RTL gate at its domain centroid.  B: gate copies (clone_of, same enable nets) per
locality tile T x T um, one copy per (gate, tile) cluster; ungated flops get one cts_open BUF leaf per tile."""
import sys, math, json, collections
CAL = {"TT": dict(stage_ps=24.93, region_ps_per_um=0.636, lo_ps_per_um=0.092, hi_ps_per_um=0.270),
       "FF": dict(stage_ps=19.06, region_ps_per_um=0.518, lo_ps_per_um=0.086, hi_ps_per_um=0.239)}
ENV = dict(max_sinks=1472, max_levels=3, max_reach_um=224.5)
def levels(n, f=24):
    k = 1
    while f ** k < n: k += 1
    return k
def reach(pts):
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts); y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
    return max(abs(cx - a) + abs(cy - b) for a in (x0, x1) for b in (y0, y1)), (cx, cy), (x0, y0, x1, y1)
def sub(n, d, c):
    k = levels(n); m = CAL[c]["stage_ps"] * k + CAL[c]["region_ps_per_um"] * d
    return k, m, m - CAL[c]["lo_ps_per_um"] * d, m + CAL[c]["hi_ps_per_um"] * d
def summarize(clusters, label):
    out = {"label": label, "clusters": len(clusters)}
    ks = collections.Counter(levels(len(p)) for _, p in clusters)
    out["levels_hist"] = dict(sorted(ks.items()))
    ds = sorted(reach(p)[0] for _, p in clusters); out["reach_um_min_med_max"] = [round(ds[0], 1), round(ds[len(ds)//2], 1), round(ds[-1], 1)]
    ns = sorted(len(p) for _, p in clusters); out["sinks_min_med_max"] = [ns[0], ns[len(ns)//2], ns[-1]]
    out["calib_out"] = sum(1 for _, p in clusters if len(p) > ENV["max_sinks"] or levels(len(p)) > 3 or reach(p)[0] > ENV["max_reach_um"])
    for c in ("TT", "FF"):
        rows = [sub(len(p), reach(p)[0], c) for _, p in clusters]
        lo = min(r[2] for r in rows); hi = max(r[3] for r in rows)
        means = [r[1] for r in rows]; intra = max(r[3] - r[2] for r in rows)
        out[c] = dict(subtree_mean_range=[round(min(means), 1), round(max(means), 1)], flop_window=round(hi - lo, 1),
                      worst_intra_cluster=round(intra, 1), subtree_mean_wtd=round(sum(r[1]*len(p) for r, (_, p) in zip(rows, clusters)) / sum(len(p) for _, p in clusters), 1))
    return out
def tile_clusters(groups, T, nmin=25, nmax=576):
    cl = []
    for g, pts in groups.items():
        cells = collections.defaultdict(list)
        for p in pts: cells[(int(p[0] // T), int(p[1] // T))].append(p)
        big = {k: v for k, v in cells.items() if len(v) >= nmin}
        if not big: big = {next(iter(cells)): []}
        cen = {k: (sum(q[0] for q in v)/len(v), sum(q[1] for q in v)/len(v)) if v else ((k[0]+.5)*T, (k[1]+.5)*T) for k, v in big.items()}
        for k, v in cells.items():
            if k in big and v: continue
            for p in v:  # small leftovers join the nearest kept cluster of the SAME gate (same enable)
                kk = min(big, key=lambda b: abs(cen[b][0]-p[0]) + abs(cen[b][1]-p[1])); big[kk].append(p)
        for k, v in big.items():
            if not v: continue
            # keep k=2 everywhere (<=576): split an over-full tile along its long axis
            parts = [v]
            while any(len(q) > nmax for q in parts):
                q = max(parts, key=len); parts.remove(q)
                ax = 0 if (max(p[0] for p in q) - min(p[0] for p in q)) >= (max(p[1] for p in q) - min(p[1] for p in q)) else 1
                q = sorted(q, key=lambda p: p[ax]); h = len(q) // 2; parts += [q[:h], q[h:]]
            cl += [(g, q) for q in parts]
    return cl
def main(path):
    groups = collections.defaultdict(list); gates = {}; macros = []
    for ln in open(path):
        t = ln.split()
        if t[0] == "GATE": gates[t[1]] = (float(t[2]), float(t[3]))
        elif t[0] == "SINK":
            if t[5] == "1": macros.append((t[1], t[2])); continue
            groups[t[1]].append((float(t[3]), float(t[4])))
        elif t[0] == "DIE": die = (float(t[1]), float(t[2]))
    gated = {g: p for g, p in groups.items() if g != "ROOT"}; root = groups.get("ROOT", [])
    res = dict(core=path, die_um=die, gates=len(gates), gated_flops=sum(map(len, gated.values())), direct_flops=len(root),
               macro_clock_pins=[m[1] for m in macros])
    # ICG placed (by the placer, no plan) vs its domain centroid
    off = sorted(abs(gates[g][0]-reach(p)[1][0]) + abs(gates[g][1]-reach(p)[1][1]) for g, p in gated.items())
    res["placed_icg_to_domain_centroid_um_med_max"] = [round(off[len(off)//2], 1), round(off[-1], 1)]
    res["A_asis_gates"] = summarize(list(gated.items()), "A: one ICG per RTL gate at its domain centroid, CTS-open domain")
    for T in (40, 50, 60, 80):
        cl = tile_clusters(gated, T); ung = tile_clusters({"ROOT": root}, T) if root else []
        s = summarize(cl + ung, f"B{T}: ICG copies per {T} um tile + ungated cts_open tile leaves")
        s["icg_copies"] = len(cl); s["ungated_tile_leaves"] = len(ung); s["tiles_used"] = len({(int(sum(q[0] for q in p)/len(p)//T), int(sum(q[1] for q in p)/len(p)//T)) for _, p in cl + ung})
        res[f"B{T}"] = s
    print(json.dumps(res, indent=1))
for p in sys.argv[1:]: main(p)
