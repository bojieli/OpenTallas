#!/usr/bin/env python3
"""CLKSITE-RESERVE-1115: build the STAMPED tree natively in tree.json form (nodes, kids, physical_leg chains, parity, taps).

Everything of a type that lies inside an instance's tile box (local region tree + in-tile feed legs) is replaced by the
TEMPLATE of its topology class, transformed by the instance orientation (isometry: stage lengths/delays inside the region are
preserved exactly; cell BOX mirrored via clksite_stamp.orient_rect; M7 PG slide <= --max-slide applied once in the type frame).
Classes: instances are grouped by (number of in-tile top nodes, number of exit nodes); each class with > 1 member gets its own
template (R0 preferred, most nodes), so the 2-top/2-exit and 3/1 boundary topologies are stamped too.  Tops/exits are paired
with the template's by their sorted type-frame position.  Legs crossing the tile boundary are re-priced (8.8 ps + 0.24 ps/um per
stage, stage <= --rep-um) in `stamp_leg` and carry NO physical_leg chain: the kit validates every chain point against its
legal-site map and lays a leg without a chain out itself.
usage: clksite_stamp_native.py PLAN TREE.json TYPE OUT.json [--max-slide 1.7] [--rep-um 150]
Writes OUT.json and OUT.json.report.json."""
import argparse, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_stamp as K

STAGE_PS, PS_PER_UM = 8.8, 0.24


def leg_price(a, b, rep):
    L = abs(a[0] - b[0]) + abs(a[1] - b[1])
    st = max(1, math.ceil(L / rep))
    return dict(stages=st, delay_ps=round(st * STAGE_PS + PS_PER_UM * L, 3), wire_um=round(L, 3),
                model="CLKSITE stamp leg (8.8 ps + 0.24 ps/um per stage)"), L / st


def stamp_tree(P, T, tname, max_slide=1.7, rep_um=150.0, site=None):
    N = {int(k): v for k, v in T["nodes"].items()}
    nb = {int(k): v for k, v in T["node_buf"].items()}
    sites, po = T["sites"], T["parent_of"]
    size = tuple(P.types[tname]["outline_um"])
    inst = sorted(n for n, p in P.parts.items() if p["type"] == tname)
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
    inst = [n for n in inst if inside[n]]

    def tpos(n, i): return tuple(P.to_type(n, (N[i]["x"], N[i]["y"])))
    tops, exits = {}, {}
    for n in inst:
        tops[n] = sorted((i for i in inside[n] if N[i].get("parent") not in inside[n]), key=lambda i: tpos(n, i))
        exits[n] = sorted((i for i in inside[n] if any(k not in inside[n] for k in N[i].get("kids", []))), key=lambda i: tpos(n, i))
    def side(n, i):                # which side of the tile (type frame) the node lies on: W/E/S/N
        x, y = tpos(n, i)
        dx, dy = (x - size[0] / 2) / size[0], (y - size[1] / 2) / size[1]
        return ("E" if dx > 0 else "W") if abs(dx) >= abs(dy) else ("N" if dy > 0 else "S")
    classes = {}
    for n in inst:
        key = (len(tops[n]), len(exits[n]), tuple(side(n, i) for i in tops[n]), tuple(side(n, i) for i in exits[n]))
        classes.setdefault(key, []).append(n)
    tmpl = {}                      # instance -> its template instance
    cls_of = {}
    rep = dict(type=tname, instances=len(inst), classes={}, unchanged=[], legs_over_405=0)
    for sig, mem in classes.items():
        t0 = max(mem, key=lambda n: (P.orient(n) == "R0", len(inside[n]), n))
        rep["classes"]["%dtop/%dexit top@%s exit@%s" % (sig[0], sig[1], "".join(sig[2]), "".join(sig[3]))] = dict(
            members=len(mem), template=t0, orient=P.orient(t0))
        if len(mem) < 2:
            rep["unchanged"] += mem
            continue
        mt = tuple(mem)
        for n in mem:
            tmpl[n] = t0
            cls_of[n] = mt
    slide = {}
    illegal_left = [0]

    def die_ll(n, ll):
        box = K.orient_rect(K.cell_box((ll[0] + 0.81, ll[1] + 0.135)), size, P.orient(n))
        o = P.parts[n]["origin_um"]
        return [round(o[0] + box[0] + K.HALO[0], 4), round(o[1] + box[1] + K.HALO[1], 4)]

    def legal_all(ll, mem):
        return all(site.legal(tuple(die_ll(n, ll))) for n in mem)

    def slid_ll(ll, mem):
        """type-frame lower-left after the M7 PG slide (<= max_slide, 0.054 steps, nearest first) that is ALSO a legal
        die clock site in EVERY instance of the class (die forbidden rects differ per instance)"""
        key = (round(ll[0], 3), round(ll[1], 3), id(mem))
        if key in slide:
            return slide[key]
        best = None
        for d in sorted((i * 0.054 for i in range(-int(max_slide / 0.054), int(max_slide / 0.054) + 1)), key=abs):
            c = (round(ll[0] + d, 4), ll[1])
            b = K.slide_off_pg(K.cell_box((c[0] + 0.81, c[1] + 0.135)), 0.0)[0]
            if b is None:
                continue
            if site is None or legal_all(c, mem):
                best = c; break
        if best is None:
            illegal_left[0] += 1
            best = ll
        slide[key] = best
        return best

    dev = {}

    def pt_die(n, p):              # template-instance die point (cell lower-left) -> die lower-left in instance n
        k = (n, round(p[0], 3), round(p[1], 3))
        if k not in dev:
            q = die_ll(n, slid_ll(P.to_type(tmpl[n], p), cls_of[n]))
            if site is not None and not site.legal(tuple(q)):      # no slide is legal in every instance: this instance deviates
                q = [round(v, 4) for v in site.nearest(tuple(q))]
                rep.setdefault("deviating_sites", 0); rep["deviating_sites"] += 1
            dev[k] = q
        return dev[k]
    stamped = [n for n in inst if n in tmpl]
    drop = set().union(*[inside[n] for n in stamped]) if stamped else set()
    ids, nxt = {}, max(N) + 1
    for n in stamped:
        for i in sorted(inside[tmpl[n]]):
            ids[(n, i)] = nxt; nxt += 1
    newN, newnb, newsites, newpo = {}, {}, {}, {}
    for (n, i), nid in ids.items():
        t0 = tmpl[n]
        v = dict(N[i]); v["id"] = nid
        v["parent"] = ids[(n, v["parent"])] if v.get("parent") in inside[t0] else None
        v["kids"] = [ids[(n, k)] for k in N[i].get("kids", []) if k in inside[t0]]
        v["x"], v["y"] = pt_die(n, (N[i]["x"], N[i]["y"]))
        if "req_xy" in v: v["req_xy"] = [v["x"], v["y"]]
        pl = N[i].get("physical_leg")
        if pl and N[i].get("parent") in inside[t0]:
            v["physical_leg"] = dict(pl, chain=[pt_die(n, c) for c in pl["chain"]])
            v["detour"] = v["physical_leg"]["chain"]
        else:
            v.pop("physical_leg", None); v.pop("detour", None)
        newN[nid] = v
        newnb[nid] = f"b{nid}"
        newsites[newnb[nid]] = [v["x"], v["y"]]
    exit_of = {}                   # old exit node id -> new exit node id
    for n in stamped:
        for q, oe in enumerate(exits[n]):
            exit_of[oe] = ids[(n, exits[tmpl[n]][q])]
    for n in stamped:
        for q, otop in enumerate(tops[n]):
            top = ids[(n, tops[tmpl[n]][q])]
            par = N[otop].get("parent")
            par = exit_of.get(par, par)
            pn = N.get(par) or newN[par]
            newN[top]["parent"] = par
            newN[top]["stamp_leg"], per = leg_price((pn["x"], pn["y"]), (newN[top]["x"], newN[top]["y"]), rep_um)
            rep["legs_over_405"] += int(per > 405)
        for q, oe in enumerate(exits[n]):
            ne = ids[(n, exits[tmpl[n]][q])]
            for k in N[oe].get("kids", []):
                if k in drop:
                    continue
                newN[ne]["kids"].append(k)
                N[k]["parent"] = ne
                N[k].pop("physical_leg", None); N[k].pop("detour", None)
                N[k]["stamp_leg"], per = leg_price((newN[ne]["x"], newN[ne]["y"]), (N[k]["x"], N[k]["y"]), rep_um)
                rep["legs_over_405"] += int(per > 405)
    taps_by_node = {}
    for t in T["taps"]:
        taps_by_node.setdefault(t["node"], []).append(t)
    new_taps = []
    for n in stamped:
        tmap = {t["tap"]: t for i in inside[tmpl[n]] for t in taps_by_node.get(i, [])}
        for i in inside[n]:
            for t in taps_by_node.get(i, []):
                tt = tmap.get(t["tap"])
                if tt is not None:
                    nid = ids[(n, tt["node"])]
                    new_taps.append(dict(t, node=nid, xy=[newN[nid]["x"], newN[nid]["y"]]))
    nodes = {i: v for i, v in N.items() if i not in drop}
    nodes.update(newN)
    for nid, v in newN.items():
        if v["parent"] is not None and nid not in nodes[v["parent"]].setdefault("kids", []):
            nodes[v["parent"]]["kids"].append(nid)
    for v in nodes.values():
        v["kids"] = [k for k in v.get("kids", []) if k in nodes]
    # POLARITY: a re-laid boundary leg (no chain: the kit lays it out with nrep = ceil(L / rep) - 1 repeaters) must give the
    # child the inverter parity it had in the template.  Where it does not, one parity node X is inserted on the leg at a
    # fraction that makes both half-legs add up (the "parity site"); node parity = parent ^ ((nrep + 1) & 1) per leg.
    def nrep_of(a_, b_):
        return max(0, math.ceil((abs(a_["x"] - b_["x"]) + abs(a_["y"] - b_["y"])) / rep_um) - 1)
    nx = max(list(nodes) + [nxt]) + 1
    pfix = dict(checked=0, inserted=0, unsolved=0)
    for c in [i for i, v in list(nodes.items()) if v.get("stamp_leg") and v.get("parent") in nodes]:
        v = nodes[c]; pr = nodes[v["parent"]]
        pfix["checked"] += 1
        want = (v.get("inv_parity", 0) ^ pr.get("inv_parity", 0)) & 1
        if (nrep_of(pr, v) + 1) & 1 == want:
            continue
        done = False
        for f in [0.5, 0.45, 0.55, 0.4, 0.6, 0.35, 0.65, 0.3, 0.7, 0.25, 0.75]:
            L = abs(pr["x"] - v["x"]) + abs(pr["y"] - v["y"])
            dx = abs(v["x"] - pr["x"])
            t = L * f
            xx = pr["x"] + math.copysign(min(t, dx), v["x"] - pr["x"])
            yy = pr["y"] + math.copysign(max(0.0, t - dx), v["y"] - pr["y"])
            X = dict(v); X.pop("stamp_leg", None); X.pop("physical_leg", None); X.pop("detour", None)
            X.update(id=nx, x=round(xx, 3), y=round(yy, 3), parent=v["parent"], kids=[c], taps=[], ntaps=0)
            X["req_xy"] = [X["x"], X["y"]]
            n1, n2 = nrep_of(pr, X), nrep_of(X, v)
            X["inv_parity"] = (pr.get("inv_parity", 0) ^ ((n1 + 1) & 1)) & 1
            if (X["inv_parity"] ^ ((n2 + 1) & 1)) & 1 == v.get("inv_parity", 0) & 1:
                X["stamp_leg"] = dict(leg_price((pr["x"], pr["y"]), (X["x"], X["y"]), rep_um)[0], note="parity node")
                v["stamp_leg"] = leg_price((X["x"], X["y"]), (v["x"], v["y"]), rep_um)[0]
                pr["kids"] = [nx if k == c else k for k in pr["kids"]]
                v["parent"] = nx
                nodes[nx] = X; newN[nx] = X; newnb[nx] = f"b{nx}"
                newsites[f"b{nx}"] = [X["x"], X["y"]]
                nx += 1; pfix["inserted"] += 1; done = True
                break
        if not done:
            pfix["unsolved"] += 1
    rep["parity_nodes"] = pfix
    nbo = {i: s for i, s in nb.items() if i not in drop}; nbo.update(newnb)
    so = {k: v for k, v in sites.items() if k not in {nb[i] for i in drop}}; so.update(newsites)
    for nid, v in newN.items():
        if v["parent"] in nbo:
            newpo[newnb[nid]] = nbo[v["parent"]]
    pbo = {k: v for k, v in po.items() if k in so}; pbo.update(newpo)
    taps_out = [t for t in T["taps"] if t["node"] not in drop] + new_taps

    def path_delay(nds, i):
        s = 0.0
        while i is not None:
            pl = nds[i].get("physical_leg") or nds[i].get("stamp_leg")
            s += pl["delay_ps"] if pl else 0.0
            i = nds[i].get("parent")
        return s
    before = {(t["part"], t["tap"]): path_delay(N, t["node"]) for t in T["taps"] if t["node"] in drop}
    after = {(t["part"], t["tap"]): path_delay(nodes, t["node"]) for t in new_taps}
    common = [k for k in after if k in before]
    dl = sorted(after[k] - before[k] for k in common)
    q = lambda l, f: round(l[min(len(l) - 1, int(f * len(l)))], 1) if l else None

    def spread(d):
        by = {}
        for (part, nm), v in d.items(): by.setdefault(part, []).append(v)
        return sorted(max(v) - min(v) for v in by.values() if len(v) > 1)
    sb, sa = spread({k: before[k] for k in common}), spread({k: after[k] for k in common})
    sig_of = {n: "%dtop/%dexit top@%s exit@%s" % (len(tops[n]), len(exits[n]), "".join(side(n, i) for i in tops[n]),
                                                  "".join(side(n, i) for i in exits[n])) for n in inst}
    percls = {}
    for k in common:
        percls.setdefault(sig_of.get(k[0], "?"), []).append(after[k] - before[k])
    rep["delta_per_class_ps"] = {c: dict(n=len(v), p50=q(sorted(v), .5), min=q(sorted(v), 0), max=q(sorted(v), 1.0)) for c, v in percls.items()}
    rep.update(stamped=len(stamped), insertion_delta_ps=dict(p50=q(dl, .5), p90=q(dl, .9), max=q(dl, 1.0), min=q(dl, 0.0)),
               tile_spread_before_ps=dict(p50=q(sb, .5), max=q(sb, 1.0)), tile_spread_after_ps=dict(p50=q(sa, .5), max=q(sa, 1.0)),
               nodes_before=len(N), nodes_after=len(nodes), taps_before=len(T["taps"]), taps_after=len(taps_out),
               slid_sites=sum(1 for k, v in slide.items() if tuple(v) != (k[0], k[1])), max_slide_um=max_slide,
               no_legal_slide=illegal_left[0])
    meta = dict(T["meta"], stamped=dict(type=tname, classes=rep["classes"], max_slide_um=max_slide, schema="clksite_stamp_native/2"))
    out = dict(meta=meta, nodes={str(i): v for i, v in nodes.items()}, taps=taps_out,
               node_buf={str(i): s for i, s in nbo.items()}, parent_of=pbo, sites=so)
    return out, rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("tree"); ap.add_argument("type"); ap.add_argument("out")
    ap.add_argument("--max-slide", type=float, default=1.7); ap.add_argument("--rep-um", type=float, default=150.0)
    a = ap.parse_args(argv)
    import schema as S
    P = S.Plan(S.load(a.plan), Path(a.plan))
    import die_trial as D
    out, rep = stamp_tree(P, json.load(open(a.tree)), a.type, a.max_slide, a.rep_um, site=D.clock_site(P))
    json.dump(out, open(a.out, "w"))
    json.dump(rep, open(a.out + ".report.json", "w"), indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
