#!/usr/bin/env python3
"""DIE-S81-6 12.14b ESTIMATE (COORD ASK-1 02:23): low-insertion trunk to spine-segment roots.

Input = the MEASURED kit (tree.json + GRT-RC arr_TT/arr_FF of the spine feed).  Form T:
  * cut the 43-hop spine feed into segments, bottom-up, so every segment's height (deepest tap arrival - segment-root
    arrival, measured) <= H;
  * a balanced (zero-skew, Manhattan, snake-padded) trunk on M8/M9 from the die clock root feeds every segment root;
    delay v_t ps/mm (linear, repeaters every 450 um -> one class-A stage per 450 um);
  * inside a segment every measured arrival is kept and only shifted: A' = I_T + (A - A_segroot).
Writes a synthetic run dir (clk/tree.json + out_TT/out_FF arr files) so the UNCHANGED shared tools
(landed_phase_ocv.py -> count_align_plan.py) price every crossing exactly as on a built kit.
usage: est_trunk.py KITRUN_TREE ARR_TT ARR_FF OUTDIR --H ps --vt ps/mm [--vt-ff ps/mm]
"""
import argparse, json, math, sys
from collections import defaultdict
from pathlib import Path


def arrivals(f):
    T, N = {}, {}
    for ln in Path(f).read_text().splitlines():
        x = ln.split()
        if x and x[0] in ("T", "N"):
            (T if x[0] == "T" else N)[x[1]] = x[2:]
    return T, N


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree"); ap.add_argument("arr_tt"); ap.add_argument("arr_ff"); ap.add_argument("out")
    ap.add_argument("--H", type=float, required=True, help="max segment height (TT ps, measured)")
    ap.add_argument("--vt", type=float, required=True, help="trunk TT ps/mm")
    ap.add_argument("--vt-ff", type=float, default=None)
    ap.add_argument("--rep-um", type=float, default=450.0)
    ap.add_argument("--root", default=None, help="trunk root x,y (default plan clock spine root 15975.36,12372.48)")
    ap.add_argument("--cell-ps", type=float, default=0.0, help="extra fixed delay per trunk merge node (ps)")
    a = ap.parse_args()
    t = json.loads(Path(a.tree).read_text())
    N = t["nodes"]; nb = t["node_buf"]
    Att, Ntt = arrivals(a.arr_tt); Aff, Nff = arrivals(a.arr_ff)
    ff_ratio = None
    # region roots and feed tree
    rr = {n["region_root"]: n for n in N.values() if "region_root" in n}
    root_reg = t["meta"]["link_feed"]["root"]
    # feed parent: walk node parents up to the next region_root node
    def up_region(n):
        p = n["parent"]
        while p is not None:
            q = N[str(p)]
            if "region_root" in q:
                return q["region_root"]
            p = q["parent"]
        return None
    fpar = {r: (None if r == root_reg else up_region(n)) for r, n in rr.items()}
    kids = defaultdict(list)
    for r, p in fpar.items():
        if p:
            kids[p].append(r)
    arr = lambda r, c="TT": float((Ntt if c == "TT" else Nff)[nb[str(rr[r]["id"])]][0])
    # measured local height of each region = deepest tap of that region - its root arrival
    tap_reg = {}
    taps_by_part = defaultdict(list)
    for tp in t["taps"]:
        taps_by_part[tp["part"]].append(float(Att[tp["port"]][0]))
    # map part -> region (region = partition here)
    loc_h = {r: max([x - arr(r) for x in taps_by_part.get(r, [])] + [0.0]) for r in rr}
    # feed calibration (measured ps/mm per feed hop)
    cal = []
    for r, p in fpar.items():
        if p:
            L = abs(rr[r]["x"] - rr[p]["x"]) + abs(rr[r]["y"] - rr[p]["y"])
            if L > 500:
                cal.append(((arr(r) - arr(p)) / (L / 1000.0), (arr(r, "FF") - arr(p, "FF")) / (arr(r) - arr(p))))
    cal.sort()
    vfeed = cal[len(cal) // 2][0]
    ffr = sorted(c[1] for c in cal)[len(cal) // 2]
    vt_ff = a.vt_ff if a.vt_ff else a.vt * ffr
    # bottom-up segment cut (height in measured TT ps)
    seg_roots = {root_reg}
    order = [root_reg]
    for r in order:
        order.extend(kids[r])
    h = {}
    for r in reversed(order):
        while True:
            cand = [(arr(c) - arr(r) + h[c], c) for c in kids[r] if c not in seg_roots]
            hh = max([loc_h[r]] + [x for x, _ in cand])
            if hh <= a.H or not cand:
                break
            seg_roots.add(max(cand)[1])
        h[r] = hh
    # trunk: recursive bisection over segment roots, zero-skew Manhattan merge with snake padding
    pts = {s: (rr[s]["x"], rr[s]["y"]) for s in seg_roots}
    if a.root:
        R = tuple(float(v) for v in a.root.split(","))
    else:
        R = (15975.36, 12372.48)
    nodes = {}  # name -> dict(xy, kids, delay_to_leaf_um)
    cnt = [0]

    def build(ss, axis):
        if len(ss) == 1:
            s = ss[0]
            return dict(name="seg:" + s, xy=pts[s], kids=[], d=0.0, seg=s)
        ss = sorted(ss, key=lambda s: pts[s][axis])
        m = len(ss) // 2
        A, B = build(ss[:m], 1 - axis), build(ss[m:], 1 - axis)
        L = abs(A["xy"][0] - B["xy"][0]) + abs(A["xy"][1] - B["xy"][1])
        # zero-skew tapping point: x from A along the Manhattan path with dA + x = dB + (L - x)
        x = (B["d"] - A["d"] + L) / 2.0
        if x < 0:
            ea, eb, d = 0.0, A["d"] - B["d"], A["d"]   # B snaked
            ea, eb = 0.0, max(L, A["d"] - B["d"])
            d = A["d"]
            xy = A["xy"]
        elif x > L:
            ea, eb = max(L, B["d"] - A["d"]), 0.0
            d = B["d"]
            xy = B["xy"]
        else:
            ea, eb = x, L - x
            d = A["d"] + x
            f = x / L if L else 0.0
            # point on the L-route (x first then y) at fraction f of the Manhattan length
            dx = B["xy"][0] - A["xy"][0]; dy = B["xy"][1] - A["xy"][1]
            if x <= abs(dx):
                xy = (A["xy"][0] + math.copysign(x, dx), A["xy"][1])
            else:
                xy = (B["xy"][0], A["xy"][1] + math.copysign(x - abs(dx), dy))
        cnt[0] += 1
        return dict(name=f"tk{cnt[0]}", xy=xy, kids=[(A, ea), (B, eb)], d=d)
    top = build(sorted(seg_roots), 0)
    Lr = abs(top["xy"][0] - R[0]) + abs(top["xy"][1] - R[1])
    I_um = top["d"] + Lr
    # wire total
    def wire(n):
        return sum(e + wire(k) for k, e in n["kids"])
    W_um = wire(top) + Lr
    # emit synthetic tree: trunk cells (merge + repeaters) into parent_of/sites, re-parent segment-root entry cells
    po = dict(t["parent_of"]); sites = dict(t["sites"])
    newN_tt, newN_ff = {}, {}
    reps = [0]

    def chain(par_cell, par_xy, child_xy, e_um, par_d_um):
        """repeaters every rep_um along an edge of e_um from par_cell; returns the last cell (feeding the child)"""
        nrep = int(e_um // a.rep_um)
        last = par_cell
        for i in range(1, nrep + 1):
            reps[0] += 1
            c = f"tkr{reps[0]}"
            f = i * a.rep_um / e_um if e_um else 0
            sites[c] = [par_xy[0] + f * (child_xy[0] - par_xy[0]), par_xy[1] + f * (child_xy[1] - par_xy[1])]
            po[c] = last
            dum = par_d_um + i * a.rep_um
            newN_tt[c] = dum / 1000 * a.vt; newN_ff[c] = dum / 1000 * vt_ff
            last = c
        return last
    # root cell
    sites["tkroot"] = list(R); newN_tt["tkroot"] = 0.0; newN_ff["tkroot"] = 0.0
    seg_entry = {}

    def emit(n, par_cell, par_xy, e_um, par_d_um):
        last = chain(par_cell, par_xy, n["xy"], e_um, par_d_um)
        d_um = par_d_um + e_um
        if n.get("seg"):
            seg_entry[n["seg"]] = (last, d_um)
            return
        c = n["name"]; sites[c] = list(n["xy"]); po[c] = last
        newN_tt[c] = d_um / 1000 * a.vt + a.cell_ps; newN_ff[c] = d_um / 1000 * vt_ff + a.cell_ps
        for k, e in n["kids"]:
            emit(k, c, n["xy"], e, d_um)
    emit(top, "tkroot", R, Lr, 0.0)
    I_tt = I_um / 1000 * a.vt; I_ff = I_um / 1000 * vt_ff
    # every segment-root entry cell: parent := last trunk cell; all cells below it shifted
    seg_of_cell = {}
    for s in seg_roots:
        po[nb[str(rr[s]["id"])]] = seg_entry[s][0]
    # shift: each N/T arrival of a cell whose nearest segment root ancestor is s
    def seg_anc(cell):
        c = cell
        segcells = {nb[str(rr[s]["id"])]: s for s in seg_roots}
        while c is not None:
            if c in segcells:
                return segcells[c]
            c = po.get(c)
        return None
    segcells = {nb[str(rr[s]["id"])]: s for s in seg_roots}
    memo = {}
    def sa(c):
        path = []
        while c is not None and c not in memo:
            if c in segcells:
                memo[c] = segcells[c]; break
            path.append(c); c = po.get(c)
        v = memo.get(c) if c is not None else None
        for p in path:
            memo[p] = v
        return v
    out = Path(a.out); (out / "clk").mkdir(parents=True, exist_ok=True)
    for C, (Tm, Nm, newN, I) in (("TT", (Att, Ntt, newN_tt, I_tt)), ("FF", (Aff, Nff, newN_ff, I_ff))):
        (out / f"out_{C}").mkdir(exist_ok=True)
        lines = []
        tapcell = {tp["port"]: nb[str(tp["node"])] for tp in t["taps"]}
        for port, v in Tm.items():
            s = sa(tapcell[port]) if port in tapcell else None
            if s is None:
                continue
            base = float((Nm)[nb[str(rr[s]["id"])]][0])
            lines.append(f"T {port} {float(v[0]) - base + I:.3f}")
        for cell, v in Nm.items():
            s = sa(cell)
            if s is None:
                continue  # old feed cells above every segment root are gone
            base = float(Nm[nb[str(rr[s]["id"])]][0])
            lines.append(f"N {cell} {float(v[0]) - base + I:.3f}")
        for cell, v in newN.items():
            lines.append(f"N {cell} {v:.3f}")
        (out / f"out_{C}" / f"arr_{C}.txt").write_text("\n".join(lines) + "\n")
    # tree.json: parent_of / sites updated; drop cells no longer reachable from tkroot (old upper feed)
    t2 = dict(t); t2["parent_of"] = po; t2["sites"] = sites
    t2["meta"] = dict(t["meta"], est_trunk=dict(H_ps=a.H, vt=a.vt, vt_ff=vt_ff, segments=len(seg_roots)))
    (out / "clk" / "tree.json").write_text(json.dumps(t2))
    # old feed wire above segment roots that the trunk replaces (the cut feed hops)
    cut_um = sum(abs(rr[s]["x"] - rr[fpar[s]]["x"]) + abs(rr[s]["y"] - rr[fpar[s]]["y"]) for s in seg_roots if fpar[s])
    segh = sorted(h[s] for s in seg_roots)
    summ = dict(H_ps=a.H, vt_tt=a.vt, vt_ff=round(vt_ff, 1), measured_feed_ps_per_mm_p50=round(vfeed, 1),
                measured_feed_ff_over_tt=round(ffr, 4), segments=len(seg_roots),
                seg_height_p50_ps=round(segh[len(segh) // 2], 1), seg_height_max_ps=round(segh[-1], 1),
                trunk_insertion_um=round(I_um, 1), trunk_I_tt_ps=round(I_tt, 1), trunk_I_ff_ps=round(I_ff, 1),
                trunk_wire_um=round(W_um, 1), trunk_repeaters=reps[0], trunk_merge_cells=cnt[0],
                feed_hops_cut_um=round(cut_um, 1),
                old_max_root_arrival_tt=round(max(arr(r) for r in rr), 1),
                new_max_root_tt=round(I_tt + max(h[s] for s in seg_roots), 1),
                seg_roots=sorted(seg_roots))
    (out / "est_trunk.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps({k: v for k, v in summ.items() if k != "seg_roots"}))


if __name__ == "__main__":
    main()
