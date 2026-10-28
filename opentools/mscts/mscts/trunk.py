"""opentools.mscts: a FIXED trunk on allocated tracks + mscts local trees below its leaves (region mode).

The trunk is the part of the region clock that the metal plan has already allocated (opentools.metal, or a row
reservation such as a spine column with bisection node rows and strip legs).  It is DATA:
    trunk = {entry: [x, y], nodes: [{id, xy, parent (null = from entry), len_um? (routed length on the allocated
             tracks; default Manhattan), rect? (the leaf's sink area)}]}
A trunk node with no children is a LEAF.  Each sink goes to the leaf named by sink.leaf, else to the leaf whose rect
contains it, else to the nearest leaf.  Below each leaf mscts.region.build makes a late-split local tree (legal buffer
sites if a Legality is given).  The leaves are then balanced to the latest leaf with a ledgered snake on the leaf's
own entry leg (METHODOLOGY v5.1: meander allowed sparsely, after the structural fix), never inside the shared trunk.
The result is ONE RegionTree, so arrivals / LCA / crossing report / netlist emitters work unchanged.
"""
import math

from . import region as RG


def _assign(spec, leaves, nodes):
    out = {lf: [] for lf in leaves}
    for s in spec["sinks"]:
        lf = s.get("leaf")
        if lf is None:
            for c in leaves:
                r = nodes[c].get("rect")
                if r and r[0] <= s["xy"][0] <= r[2] and r[1] <= s["xy"][1] <= r[3]:
                    lf = c
                    break
        if lf is None:
            lf = min(leaves, key=lambda c: RG._man(nodes[c]["xy"], s["xy"]))
        out[lf].append(s)
    return out


def compose(spec, model, objective="late_split", legal=None, corner="TT", balance=True):
    tr = spec["trunk"]
    nodes = {n["id"]: n for n in tr["nodes"]}
    kids = {i: [] for i in nodes}
    for n in tr["nodes"]:
        if n.get("parent") is not None:
            kids[n["parent"]].append(n["id"])
    tops = [i for i, n in nodes.items() if n.get("parent") is None]
    if len(tops) != 1:
        raise ValueError("trunk needs exactly one node fed from the entry")
    leaves = [i for i in nodes if not kids[i]]
    bysink = _assign(spec, leaves, nodes)
    xs = [tuple(x[:2]) for x in spec.get("crossings", [])]
    leaf_of = {s["name"]: lf for lf, ss in bysink.items() for s in ss}
    G = RG.RegionTree(model, corner, legal)
    gid = {}
    info = dict(leaves={}, snakes=[])

    def copy_sub(R):
        off = len(G.nodes)
        for nd in R.nodes:
            q = dict(nd)
            q["id"] = nd["id"] + off
            q["kids"] = [(k + off, L, sn) for k, L, sn in nd["kids"]]
            G.nodes.append(q)
        G.snakes += R.snakes
        G.moved += R.moved
        return R.root + off
    for lf in leaves:
        ss = bysink[lf]
        if not ss:
            gid[lf] = G.add(xy=tuple(nodes[lf]["xy"]), kind="merge", kids=[], t_ps=0.0, trunk=lf)
            continue
        lx = [(a, b) for a, b in xs if leaf_of.get(a) == lf and leaf_of.get(b) == lf]
        R = RG.build(ss, model, tuple(nodes[lf]["xy"]), lx, objective=objective, corner=corner, legal=legal)
        gid[lf] = copy_sub(R)
        G.nodes[gid[lf]]["kind"] = "merge"
        G.nodes[gid[lf]]["trunk"] = lf
        info["leaves"][lf] = dict(sinks=len(ss), local_t_ps=round(R.nodes[R.root]["t_ps"], 1))

    def mk(i):
        if not kids[i]:
            return gid[i]
        ks = [mk(c) for c in kids[i]]
        if len(ks) > 2:
            raise ValueError(f"trunk node {i}: more than 2 children (split it into binary nodes on the tracks)")
        kl = []
        for c, g in zip(kids[i], ks):
            L = float(nodes[c].get("len_um") or RG._man(nodes[i]["xy"], nodes[c]["xy"]))
            kl.append((g, L, 0.0))
        t = 0.0
        return G.add(xy=tuple(nodes[i]["xy"]), kind="merge", kids=kl, t_ps=t, trunk=i)
    top = mk(tops[0])
    Le = float(nodes[tops[0]].get("len_um") or RG._man(tr["entry"], nodes[tops[0]]["xy"]))
    G.root = G.add(xy=tuple(tr["entry"]), kind="root", kids=[(top, Le, 0.0)], t_ps=0.0)
    if balance:
        _balance(G, [gid[lf] for lf in leaves if bysink[lf]], info, corner)
    return G, info


def _latency(G, corner):
    arr, par = RG.arrivals(G, corner)
    lat = {}
    for nd in G.nodes:
        if nd["kind"] == "sink":
            lat[nd["id"]] = arr[nd["id"]] + nd.get("ins", {}).get(corner, 0.0)
    return arr, par, lat


def _balance(G, leaf_ids, info, corner):
    """snake on each leaf's local entry leg (leaf node -> its tree top) so every leaf's latest sink meets the latest."""
    def leaf_max(lid, lat, par):
        m = -1e18
        for s, v in lat.items():
            x = s
            while x is not None and x != lid:
                x = par[x]
            if x == lid:
                m = max(m, v)
        return m
    arr, par, lat = _latency(G, corner)
    lm = {lid: leaf_max(lid, lat, par) for lid in leaf_ids}
    tgt = max(lm.values())
    for lid in leaf_ids:
        dlt = tgt - lm[lid]
        if dlt < 0.5:
            continue
        nd = G.nodes[lid]
        if len(nd["kids"]) != 1:
            continue
        k, L, sn = nd["kids"][0]
        base = G.M.wire_ps(L, corner)
        lo, hi = 0.0, 20000.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if G.M.wire_ps(L + mid, corner) - base < dlt:
                lo = mid
            else:
                hi = mid
        e = (lo + hi) / 2
        nd["kids"][0] = (k, L + e, sn + e)
        G.snakes.append(dict(at=list(nd["xy"]), side=nd.get("trunk"), um=round(e, 1), kind="leaf_balance"))
        info["snakes"].append(dict(leaf=nd.get("trunk"), um=round(e, 1), ps=round(dlt, 1)))
