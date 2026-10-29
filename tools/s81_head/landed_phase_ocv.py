#!/usr/bin/env python3
"""LAND-HEAD-2: landed (mesochronous) crossing phase margin INCLUDING clock OCV on the unshared tree portion.

    landed_phase_ocv.py PLAN RUN_DIR [--budget-ps 416.5] [--core-lat TT=250,FF=202.5] [--out JSON]

Shared die timing model (METHODOLOGY 12.4a b1, main tools/die_plan/clk_aocv.py + the APPROVED 0.21 %/mm table that
die_sta_related.py uses): per crossing (src entry a, dst entry b, nominal d = arr_b - arr_a on the GRT-RC routed die
clock, out_<C>/arr_<C>.txt late arrivals), the branches below the LAST COMMON tree cell (LCA of the two entries'
buffer/repeater chains in clk/tree.json) are derated with clk_aocv.branch_pessimism exactly as die_sta_related.clock_ocv_fn
builds them: branch delay = entry arrival - LCA cell output arrival (+ declared partition-internal latency as class-B
stages), cell share from the table (class A), A stages = cells below the LCA on the path, distance = bounding-box
diagonal of the two entries + the LCA cell.  Droop (shared rule): the two entries are in DIFFERENT clock regions, so the
full one-sided +5.1 % late is charged on the late branch ('regions', GATE); 'same' (0) is reported as info.
Derated |d| = max(|d + p(b late, a early)|, |d - p(a late, b early)|); margin = budget - derated |d|.
"""
import argparse
import json
import math
import sys
from pathlib import Path


def arrivals(f):
    T, N = {}, {}
    for ln in Path(f).read_text().splitlines():
        x = ln.split()
        if not x:
            continue
        if x[0] == "T":
            T[x[1]] = float(x[2])
        elif x[0] == "N":
            N[x[1]] = float(x[2])
    return T, N


def chain(tree, cell):
    out = [cell]
    while cell in tree["parent_of"]:
        cell = tree["parent_of"][cell]
        out.append(cell)
    return out  # leaf ... root


def lca(ca, cb):
    sb = set(cb)
    for i, c in enumerate(ca):
        if c in sb:
            return c, i, cb.index(c)
    raise ValueError("no common cell")


def endpoint_taps(P, pr, side, candidates):
    """Every tap nearest to an actual declared endpoint pin; ties stay in the set."""
    import schema as S
    endpoint = pr[side]
    part, bus = endpoint['part'], endpoint['bus']
    if len(candidates) == 1:
        return candidates
    geom = P._type_geom(part,bus)
    if geom is None:
        # Legacy FT slots declare their face/window in the type while route
        # layers live on the concrete die link. Use those actual link layers.
        for slot in P.ptype(part).get('ft_slots',[]):
            for suffix,stem in (('_i','in'),('_o','out')):
                if bus == slot['name']+suffix and stem+'_window_um' in slot:
                    layers=slot.get(stem+'_layers',slot.get('layers',pr.get('layers') or P.ports[pr['id']].get('layers')))
                    if layers:
                        geom=(slot[stem+'_face'],slot[stem+'_window_um'],layers,slot.get(stem+'_order',slot.get('order','lsb_low')))
    if geom is None:
        raise ValueError(f"{pr['id']} {side} {part}.{bus}: no declared endpoint geometry for tap selection")
    face,window,layers,order = geom
    pinport = dict(pr,face=face,window_um=window,layers=layers,order=order)
    pinport.pop('segments',None)
    w,h = P.ptype(part)['outline_um']
    selected = set()
    for bit,layer,c in S.pin_positions(pinport,P.layers):
        xy = {'W':(0,c),'E':(w,c),'S':(c,0),'N':(c,h)}[face]
        x,y = P.to_die(part,xy)
        distances = [(abs(t['xy'][0]-x)+abs(t['xy'][1]-y),t['port']) for t in candidates]
        best = min(d for d,_ in distances)
        selected.update(n for d,n in distances if d <= best+1e-6)
    if not selected:
        raise ValueError(f"{pr['id']} {side}: endpoint has no physical pins")
    return sorted((t for t in candidates if t['port'] in selected),key=lambda t:t['port'])


def analyse(plan, tree, arr, CA, T, corner, core_lat, budget, droop, port_taps=False, cls="A"):
    tap_of = {}
    for tap in tree['taps']:
        tap_of.setdefault(tap['part'],[]).append(tap)
    if port_taps:
        import schema as S
        P = S.Plan(plan)
    cache = {}
    Tarr, Narr = arr
    B = T["classes"]["B"][corner]
    fc = T["classes"][cls][corner]["cell_share"]
    nB = max(1, round(core_lat / B["mu_stage_ps"])) if core_lat > 0 else 0
    rows = []
    for pr in plan["ports"]:
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if s not in tap_of or d not in tap_of:
            continue
        selected = []
        for side,part in (('src',s),('dst',d)):
            if port_taps:
                key = (part,pr[side]['bus'],pr['width'],pr.get('epoch'),pr.get('kind'))
                if key not in cache:
                    cache[key] = endpoint_taps(P,pr,side,tap_of[part])
                selected.append(cache[key])
            else:
                selected.append(tap_of[part][-1:])
        pair_rows = []
        for ta in selected[0]:
            for tb in selected[1]:
                la, lb = ta.get("driver", tree["node_buf"][str(ta["node"])]), tb.get("driver", tree["node_buf"][str(tb["node"])])
                ca, cb = chain(tree, la), chain(tree, lb)
                node, ia, ib = lca(ca, cb)
                nxy = tree["sites"][node]
                pts = [ta["xy"], tb["xy"], nxy]
                dist = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
                cells = [tree["sites"][c] for c in ca[:ia] + cb[:ib]] + pts
                dist_all = math.hypot(max(p[0] for p in cells) - min(p[0] for p in cells), max(p[1] for p in cells) - min(p[1] for p in cells))
                aa, ab = Tarr[ta["port"]], Tarr[tb["port"]]
                nd = Narr[node]

                def br(arrv, nst):
                    u = arrv - nd
                    stg = {cls: nst}
                    if nB:
                        stg["B"] = nB
                    return dict(cell_ps=fc * u + B["cell_share"] * core_lat, net_ps=(1 - fc) * u + (1 - B["cell_share"]) * core_lat,
                                stages=stg, unshared_ps=u)
                bra, brb = br(aa, ia), br(ab, ib)
                same = droop == "same"
                p_up = CA.branch_pessimism(T, corner, brb, bra, dist, same, "setup")   # b late, a early: d grows
                p_dn = CA.branch_pessimism(T, corner, bra, brb, dist, same, "setup")   # a late, b early: d shrinks
                dn = ab - aa
                der = max(abs(dn + p_up), abs(dn - p_dn))
                pair_rows.append(dict(port=pr["id"], src=s, dst=d, lca=node, d_ps=round(dn, 2), unshared_a_ps=round(bra["unshared_ps"], 1),
                                 unshared_b_ps=round(brb["unshared_ps"], 1), stages_a=ia, stages_b=ib, dist_um=round(dist, 1),
                                 dist_allcells_um=round(dist_all, 1), p_up_ps=round(p_up, 2), p_dn_ps=round(p_dn, 2),
                                 derated_abs_ps=round(der, 2), margin_ps=round(budget - der, 2)))
        anchor = pair_rows[0]
        lo = min(r['d_ps']-r['p_dn_ps'] for r in pair_rows)
        hi = max(r['d_ps']+r['p_up_ps'] for r in pair_rows)
        anchor['p_dn_ps'] = math.ceil((anchor['d_ps']-lo)*100-1e-8)/100
        anchor['p_up_ps'] = math.ceil((hi-anchor['d_ps'])*100-1e-8)/100
        anchor['derated_abs_ps'] = max(abs(lo),abs(hi))
        anchor['margin_ps'] = round(budget-anchor['derated_abs_ps'],2)
        anchor['unshared_a_ps'] = max(r['unshared_a_ps'] for r in pair_rows)
        anchor['unshared_b_ps'] = max(r['unshared_b_ps'] for r in pair_rows)
        anchor['tap_src'] = [t['port'] for t in selected[0]]
        anchor['tap_dst'] = [t['port'] for t in selected[1]]
        anchor['tap_pairs'] = len(pair_rows)
        anchor['lcas'] = sorted({r['lca'] for r in pair_rows})
        rows.append(anchor)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("run")
    ap.add_argument("--tools", required=True, help="dir holding main clk_aocv.py + clk_aocv_table_g021.json")
    ap.add_argument("--budget-ps", type=float, default=833.0 / 2)
    ap.add_argument("--core-lat", default="TT=250,FF=202.5", help="partition-internal latency per corner (12.3), class B")
    ap.add_argument("--out")
    ap.add_argument("--clock-cell", choices=("auto", "buf", "inv", "inv2"), default="auto",
                    help="CLK-INV-CAL-1: die clock cell (AOCV die class A for buf, Ainv for CKINVDCx16 inv/inv2); auto = "
                         "the declaration in RUN/clk/tree.json meta clock_cell (die_trial); missing -> FAIL closed "
                         "(COORD ruling ba28d3143)")
    ap.add_argument("--port-taps",action="store_true",help="use declared endpoint pins and union all nearest-tap pairs; legacy last tap otherwise")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.tools)
    import clk_aocv as CA
    T = CA.load(Path(a.tools) / "clk_aocv_table_g021.json")
    import die_sta_related as DSR
    tj = Path(a.run) / "clk" / "tree.json"
    decl = (json.loads(tj.read_text()).get("meta") or {}).get("clock_cell") if tj.is_file() else None
    cc, cbasis = DSR.resolve_clock_cell(a.clock_cell, Path(a.run),
                                        {"source": str(Path(a.run) / "out_TT" / "arr_TT.txt"),
                                         **({"clock_cell": decl} if decl is not None else {})})
    cls = DSR.CLOCK_CELL_AOCV_CLASS[cc]
    assert abs(T["systematic"]["g_per_mm"] - 0.21) < 1e-9 or abs(T["systematic"]["g_per_mm"] - 0.0021) < 1e-9, T["systematic"]
    plan = json.loads(Path(a.plan).read_text())
    run = Path(a.run)
    tree = json.loads((run / "clk" / "tree.json").read_text())
    cl = dict(kv.split("=") for kv in a.core_lat.split(","))
    out = dict(method=__doc__.split("\n\n")[2].strip(), budget_ps=a.budget_ps, g_per_mm=T["systematic"]["g_per_mm"],
               droop_one_sided=T["droop"]["one_sided_late_frac"], core_lat=cl, corners={})
    if cc != "buf":                 # CLK-INV-CAL-1 record (BUFx24 output unchanged)
        out["clock_cell"] = dict(cell=cc, basis=cbasis, aocv_class=cls)
    for c in ("TT", "FF"):
        f = run / f"out_{c}" / f"arr_{c}.txt"
        if not f.is_file():
            continue
        arr = arrivals(f)
        for droop in ("regions", "same"):
            for clat in (float(cl[c]), 0.0):
                rows = analyse(plan, tree, arr, CA, T, c, clat, a.budget_ps, droop, port_taps=a.port_taps, cls=cls)
                rows.sort(key=lambda r: r["margin_ps"])
                key = f"{c}_droop-{droop}_corelat{clat:g}"
                out["corners"][key] = dict(crossings=len(rows), worst_margin_ps=rows[0]["margin_ps"],
                                           nominal_worst_abs_d_ps=max(abs(r["d_ps"]) for r in rows),
                                           under_100=sum(1 for r in rows if r["margin_ps"] < 100),
                                           under_0=sum(1 for r in rows if r["margin_ps"] < 0),
                                           max_unshared_ps=max(max(r["unshared_a_ps"], r["unshared_b_ps"]) for r in rows),
                                           lca_root_crossings=sum(1 for r in rows if r["lca"] == "b0"),
                                           worst=rows[:8], all=rows if (droop == "regions" and clat) else None)
                print(key, json.dumps({k: v for k, v in out["corners"][key].items() if k not in ("worst", "all")}))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
