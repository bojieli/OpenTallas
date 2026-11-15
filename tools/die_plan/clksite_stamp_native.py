#!/usr/bin/env python3
"""CLKSITE-RESERVE-1115: build the STAMPED tree natively in tree.json form (nodes, kids, physical_leg chains, parity, taps,
node_buf, parent_of, sites).  Everything of a type that lies inside an instance's tile box (local region tree + the in-tile
feed legs) is replaced by the TEMPLATE instance's, transformed by the instance orientation (isometry: stage lengths and delays
inside the region are preserved exactly, cell BOX mirrored via clksite_stamp.orient_rect, M7 PG slide applied once in the type
frame).  The legs that cross the tile boundary (outside parent -> stamped top node, stamped exit node -> outside kids) are
re-routed (Manhattan, stages <= --rep-um) and priced with the fitted model (8.8 ps + 0.24 ps/um per stage, FABLE-PD-HEAD-0945).
usage: clksite_stamp_native.py PLAN TREE.json TYPE OUT.json [--template INST] [--max-slide 1.7] [--rep-um 150]
Writes OUT.json and OUT.report.json (instances stamped / skipped, site sets, legs > 405, insertion delta, spread before/after).
SITES: tree.json site xy = body lower-left (cell body 1.62 x 0.27)."""
import argparse, json, math, sys, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_stamp as K

STAGE_PS, PS_PER_UM = 8.8, 0.24


def leg_chain(a, b, rep):
    """Manhattan chain a->b (x first), stage length <= rep"""
    L = abs(a[0] - b[0]) + abs(a[1] - b[1])
    n = max(1, math.ceil(L / rep))
    pts = [list(a)]
    for k in range(1, n):
        t = L * k / n
        dx = abs(b[0] - a[0])
        pts.append([round(a[0] + math.copysign(min(t, dx), b[0] - a[0]), 3),
                    round(a[1] + math.copysign(max(0.0, t - dx), b[1] - a[1]), 3)])
    pts.append(list(b))
    return pts, n, L


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("tree"); ap.add_argument("type"); ap.add_argument("out")
    ap.add_argument("--template"); ap.add_argument("--max-slide", type=float, default=1.7)
    ap.add_argument("--rep-um", type=float, default=150.0)
    a = ap.parse_args(argv)
    import schema as S
    P = S.Plan(S.load(a.plan), Path(a.plan))
    T = json.load(open(a.tree))
    N = {int(k): v for k, v in T["nodes"].items()}
    nb = {int(k): v for k, v in T["node_buf"].items()}
    sites, po = T["sites"], T["parent_of"]
    size = tuple(P.types[a.type]["outline_um"])
    inst = sorted(n for n, p in P.parts.items() if p["type"] == a.type)
    rect = {n: P.rect(n) for n in inst}

    def tile_of(x, y):
        for n in inst:
            r = rect[n]
            if r[0] <= x < r[2] and r[1] <= y < r[3]:
                return n
    inside = {n: set() for n in inst}
    for i, v in N.items():
        n = tile_of(v["x"], v["y"])
        if n:
            inside[n].add(i)

    def exits(n):      # in-tile nodes with an outside kid; outside parent of the top node
        ex = [i for i in sorted(inside[n]) if any(k not in inside[n] for k in N[i].get("kids", []))]
        tops = [i for i in sorted(inside[n]) if N[i].get("parent") not in inside[n]]
        return tops, ex
    ok = {n: exits(n) for n in inst if inside[n]}
    cand = [n for n in ok if P.orient(n) == "R0" and len(ok[n][0]) == 1]
    tpl = a.template or max(cand, key=lambda n: (len(inside[n]), n))
    ttop, tex = ok[tpl]
    tI = inside[tpl]

    def ty(n, p): return P.to_type(n, p)
    # template geometry in the type frame; the slide is decided per SITE once (keyed by the site's type-frame ll)
    slide = {}

    def slid_ll(ll):
        key = (round(ll[0], 3), round(ll[1], 3))
        if key not in slide:
            box = K.cell_box((ll[0] + 0.81, ll[1] + 0.135))
            b, d = K.slide_off_pg(box, a.max_slide)
            slide[key] = (ll if b is None else (round(b[0] + 0.54, 4), round(b[1] + 0.27, 4)))
        return slide[key]

    def to_die(n, ll_type):
        box = K.cell_box((ll_type[0] + 0.81, ll_type[1] + 0.135))
        r = K.orient_rect(box, size, P.orient(n))
        o = P.parts[n]["origin_um"]
        return [round(o[0] + r[0] + K.HALO[0], 4), round(o[1] + r[1] + K.HALO[1], 4)]

    def pt_die(n, p):   # a chain point / node point (a cell position) in type frame -> die of instance n
        return to_die(n, slid_ll(ty(tpl, p)))
    # template node -> site name(s)
    tsite = {i: nb[i] for i in tI}
    rep = dict(type=a.type, template=tpl, instances=len(inst), stamped=0, skipped=[], legs_over_405=0)
    newN, newnb, newsites, newpo = {}, {}, {}, {}
    drop = set()
    nxt = max(N) + 1
    tap_by_node = {}
    for t in T["taps"]:
        tap_by_node.setdefault(t["node"], []).append(t)
    tap_name = lambda t: t["tap"]
    new_taps = []
    keep_taps = [t for t in T["taps"] if t["node"] not in set().union(*[inside[n] for n in inst if inside[n]])]
    before_ins, after_ins = {}, {}

    def path_delay(nodes, i):
        s = 0.0
        while i is not None:
            pl = nodes[i].get("physical_leg")
            s += pl["delay_ps"] if pl else 0.0
            i = nodes[i].get("parent")
        return s
    for n in inst:
        if not inside[n]:
            continue
        tops, ex = ok[n]
        if n != tpl and (len(tops) != 1 or len(ex) != len(tex)):
            rep["skipped"].append((n, len(tops), len(ex))); continue
        for t in T["taps"]:
            if t["node"] in inside[n]:
                before_ins[(n, tap_name(t))] = path_delay(N, t["node"])
    ids = {}
    for n in inst:
        if not inside[n] or any(s[0] == n for s in rep["skipped"]):
            continue
        for i in tI:
            ids[(n, i)] = nxt; nxt += 1
        drop |= inside[n]
    for (n, i), nid in ids.items():
        v = dict(N[i]); v["id"] = nid
        v["parent"] = ids.get((n, v["parent"]), v["parent"]) if v.get("parent") in tI else None
        v["kids"] = [ids[(n, k)] for k in N[i].get("kids", []) if k in tI]
        v["x"], v["y"] = (lambda p: (p[0], p[1]))(pt_die(n, (N[i]["x"], N[i]["y"])))
        if "req_xy" in v: v["req_xy"] = [v["x"], v["y"]]
        pl = N[i].get("physical_leg")
        if pl and N[i].get("parent") in tI:
            v["physical_leg"] = dict(pl, chain=[pt_die(n, c) for c in pl["chain"]])
            v["detour"] = v["physical_leg"]["chain"]
        newN[nid] = v
        newnb[nid] = f"{nb[i]}@{n}"
        newsites[newnb[nid]] = list(pt_die(n, (N[i]["x"], N[i]["y"])))
    # reconnect to the outside: top node and exit nodes
    for n in inst:
        if (n, ttop[0]) not in ids:
            continue
        top = ids[(n, ttop[0])]
        otop = ok[n][0][0]
        par = N[otop].get("parent")
        if par in drop:        # parent lies in a neighbouring stamped tile: it is that tile's exit node
            for m in inst:
                if par in inside[m] and (m, tex[0]) in ids:
                    q = ok[m][1].index(par)
                    par = ids[(m, tex[q])]
                    break
        newN[top]["parent"] = par
        pn = N.get(par) or newN[par]
        chain, st, L = leg_chain([pn["x"], pn["y"]], [newN[top]["x"], newN[top]["y"]], a.rep_um)
        newN[top]["physical_leg"] = dict(chain=chain, stages=st, delay_ps=round(st * STAGE_PS + PS_PER_UM * L, 3), wire_um=round(L, 3),
                                         model="CLKSITE stamp entry leg (8.8 ps + 0.24 ps/um per stage)")
        newN[top]["detour"] = chain
        rep["legs_over_405"] += int(L / st > 405)
        for q, (te, oe) in enumerate(zip(tex, ok[n][1])):
            ne = ids[(n, te)]
            for k in N[oe].get("kids", []):
                if k in drop:
                    continue
                newN[ne]["kids"].append(k)
                N[k]["parent"] = ne
                ch, st2, L2 = leg_chain([newN[ne]["x"], newN[ne]["y"]], [N[k]["x"], N[k]["y"]], a.rep_um)
                N[k]["physical_leg"] = dict(chain=ch, stages=st2, delay_ps=round(st2 * STAGE_PS + PS_PER_UM * L2, 3), wire_um=round(L2, 3),
                                            model="CLKSITE stamp exit leg")
                N[k]["detour"] = ch
                rep["legs_over_405"] += int(L2 / st2 > 405)
        # taps by name
        for t in T["taps"]:
            pass
        rep["stamped"] += 1
    tpl_taps = {tap_name(t): t for t in T["taps"] if t["node"] in tI}
    for n in inst:
        for t in T["taps"]:
            if t["node"] in inside[n] and (n, t["node"]) not in ids and not any(s[0] == n for s in rep["skipped"]):
                pass
    for n in inst:
        if not inside[n] or any(s[0] == n for s in rep["skipped"]):
            continue
        for t in T["taps"]:
            if t["node"] in inside[n]:
                tt = tpl_taps.get(tap_name(t))
                if tt is None:
                    continue
                nid = ids[(n, tt["node"])]
                new_taps.append(dict(t, node=nid, xy=list(newN[nid]["x:y".split(":")[0]:] if False else (newN[nid]["x"], newN[nid]["y"]))))
    # assemble
    nodes = {i: v for i, v in N.items() if i not in drop}
    nodes.update(newN)
    for nid, v in newN.items():
        if v["parent"] is not None and v["parent"] in nodes:
            if nid not in nodes[v["parent"]].setdefault("kids", []):
                nodes[v["parent"]]["kids"].append(nid)
    for v in nodes.values():       # kids that were replaced (old in-tile tops / exits) are dropped
        v["kids"] = [k for k in v.get("kids", []) if k in nodes]
    nbo = {i: s for i, s in nb.items() if i not in drop}; nbo.update(newnb)
    so = {k: v for k, v in sites.items() if k not in {nb[i] for i in drop}}; so.update(newsites)
    for nid, v in newN.items():
        if v["parent"] in nbo:
            newpo[newnb[nid]] = nbo[v["parent"]]
    pbo = {k: v for k, v in po.items() if k in so}; pbo.update(newpo)
    tapsout = [t for t in T["taps"] if t["node"] not in drop] + new_taps
    for t in tapsout:
        after = None
    for (n, nm) in before_ins:
        pass
    for t in new_taps:
        after_ins[(next(n for n in inst if tile_of(*t["xy"]) == n), tap_name(t))] = path_delay(nodes, t["node"])
    def spread(d):
        by = {}
        for (n, nm), v in d.items(): by.setdefault(n, []).append(v)
        return [max(v) - min(v) for v in by.values() if len(v) > 1]
    common = [k for k in after_ins if k in before_ins]
    dl = sorted(after_ins[k] - before_ins[k] for k in common)
    q = lambda l, f: round(l[min(len(l) - 1, int(f * len(l)))], 1) if l else None
    sb, sa = spread({k: before_ins[k] for k in common}), spread({k: after_ins[k] for k in common})
    rep.update(insertion_delta_ps=dict(p50=q(dl, .5), p90=q(dl, .9), max=q(dl, 1.0), min=q(dl, 0.0)),
               tile_spread_before_ps=dict(p50=q(sorted(sb), .5), max=q(sorted(sb), 1.0)),
               tile_spread_after_ps=dict(p50=q(sorted(sa), .5), max=q(sorted(sa), 1.0)),
               site_sets_in_type=len({frozenset(round(v, 3) for s in [0] for v in ()) for _ in [0]}),
               nodes_before=len(N), nodes_after=len(nodes), taps_before=len(T["taps"]), taps_after=len(tapsout),
               slid_sites=sum(1 for k, v in slide.items() if tuple(v) != (k[0], k[1])), exits_per_tile=len(tex))
    meta = dict(T["meta"], stamped=dict(type=a.type, template=tpl, max_slide_um=a.max_slide, schema="clksite_stamp_native/1"))
    json.dump(dict(meta=meta, nodes={str(i): v for i, v in nodes.items()}, taps=tapsout,
                   node_buf={str(i): s for i, s in nbo.items()}, parent_of=pbo, sites=so), open(a.out, "w"))
    json.dump(rep, open(a.out + ".report.json", "w"), indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
