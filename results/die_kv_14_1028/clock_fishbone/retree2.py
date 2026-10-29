#!/usr/bin/env python3
"""DIE-KV-14 re-tree ESTIMATE v2 (DIE-KV-11 retree.py + a HARD unshared cap ranked first, start = DIE-KV-11 retree_feed).
DIE-KV-11 re-tree ESTIMATE: low-stretch forwarding tree for the KV local form (12.13b/12.16b(i)).
Start = CLK-LOCAL-EST-1 'fish' feed (max-weight spanning tree, least-eccentricity root) on the same 128-region map.
Local search: edge swaps (add an adjacent off-tree region pair, drop one tree edge on its cycle) that cut the
off-feed crossings' tree-path delay (proxy = spine arrival a + b - 2 lca); then the SAME locality.score + cap_reading
(count_align_plan unchanged, clk_aocv g021 table, droop, spice v) on the result.  usage: retree.py REPO PLAN BIND V OUT"""
import json, sys, collections, types, time, os
from pathlib import Path
repo, planp, bindp, v, outd = sys.argv[1:6]
v = float(v); outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
TH = float(sys.argv[6]) if len(sys.argv) > 6 else 2000.0
HARD = float(sys.argv[7]) if len(sys.argv) > 7 else 4000.0
START = sys.argv[8] if len(sys.argv) > 8 else None
sys.path.insert(0, f"{repo}/tools/die_plan")
_p = f"{repo}/tools/die_plan/locality.py"; _s = open(_p).read()
_old = '                x["margin_lo_ps"] = round(x["L_lo_ps"] - 0.5 * period, 1)\n'
assert _old in _s
_s = _s.replace(_old, '                if "L_lo_ps" not in x:\n                    x.update(L_lo_ps=None, L_hi_ps=None, margin_lo_ps=None, margin_hi_ps=None, depth=None, lat_cycles=x.get("lat_cycles"), kind=x.get("kind", "FAIL"), path_ambiguous_cycles=x.get("path_ambiguous_cycles", -1))\n                    res[x["port"]] = x\n                    continue\n' + _old)
L = types.ModuleType("locality"); L.__file__ = _p; sys.modules["locality"] = L; exec(compile(_s, _p, "exec"), L.__dict__)
D = L.load_plan(planp)
bind = json.loads(Path(bindp).read_text())
reg = {p: x["region"] for p, x in bind["parts"].items() if isinstance(x, dict) and x.get("region")}
for p in D["parts"]:
    reg.setdefault(p, p)
padj = L.part_adjacency(D); M = L.traffic(D); Tt = L.CA.load(L.TABLE); P = D["period"]
G = L.region_geom(D, reg); X = L.crossings(D, reg, G, padj); E = L.region_graph(D, reg, padj, X)
taps = L.tap_points(G, X)
F0 = L.feed_tree(G, E, X, v, "fish")
nodes = sorted(G)
pairs = collections.Counter(tuple(sorted((x["ra"], x["rb"]))) for x in X)
adj_ok = set(E.keys()) | {tuple(sorted(j)) for j in F0["joined"]}
def tapf(p, c): return taps.get((p, c)) or L.xing_point(G[p]["bbox"], G[c]["bbox"])
hd = {}
for (a, b) in adj_ok:
    hd[(a, b)] = L.hop_delay(G, a, b, tapf(a, b), v, "fish"); hd[(b, a)] = L.hop_delay(G, b, a, tapf(b, a), v, "fish")
def orient(und, root):
    nb = collections.defaultdict(list)
    for a, b in und: nb[a].append(b); nb[b].append(a)
    par, order, T, dep = {root: None}, [root], {root: 0.0}, {root: 0}
    i = 0
    while i < len(order):
        p = order[i]; i += 1
        for c in sorted(nb[p]):
            if c not in par:
                par[c] = p; T[c] = T[p] + hd[(p, c)]; dep[c] = dep[p] + 1; order.append(c)
    return par, order, T, dep
def lca(par, dep, a, b):
    while dep[a] > dep[b]: a = par[a]
    while dep[b] > dep[a]: b = par[b]
    while a != b: a, b = par[a], par[b]
    return a
def cost(und, root):
    par, order, T, dep = orient(und, root)
    if len(order) != len(nodes): return None
    tot, nlong, worst, nhard, thard = 0.0, 0, 0.0, 0, 0.0
    for (a, b), n in pairs.items():
        if par.get(a) == b or par.get(b) == a: continue
        c = lca(par, dep, a, b); d = T[a] + T[b] - 2 * T[c]
        worst = max(worst, d)
        if d > TH: nlong += n; tot += n * (d - TH)
        if d > HARD: nhard += n; thard += d - HARD
    return (nlong, tot, worst, max(T.values()), nhard, thard)
und = {tuple(sorted((c, p))) for c, p in F0["parent"].items() if p is not None}
root = F0["root"]
if START:
    _st = json.loads(Path(START).read_text())
    und = {tuple(sorted((c, p))) for c, p in _st["parent"].items() if p is not None}; root = _st["root"]
    OVR = json.loads(Path(sys.argv[9]).read_text()) if len(sys.argv) > 9 else {}
    if OVR.get("root"): root = OVR["root"]
    for _c, _np in OVR.get("parent", {}).items():
        _pp, _, _, _ = orient(und, root)
        if _pp.get(_c) == _np: continue
        assert tuple(sorted((_c, _np))) in adj_ok, ("not adjacent", _c, _np)
        # make _c's subtree hang from _np: drop the edge from _c toward the root ... unless _np is inside _c's subtree, then drop _np's parent edge
        _x = _np; _inside = False
        while _x is not None:
            if _x == _c: _inside = True; break
            _x = _pp[_x]
        assert not _inside, ("override parent inside child subtree", _c, _np)
        und = (und - {tuple(sorted((_c, _pp[_c])))}) | {tuple(sorted((_c, _np)))}
    print("overrides", len(OVR.get("parent", {})), "root", root, flush=True)
    _p1, _o1, _, _ = orient(und, root)
    F1 = dict(root=root, parent=_p1, order=_o1, tap={(p, c): tapf(p, c) for c, p in _p1.items() if p is not None}, joined=F0["joined"], kind="fish")
if START: _pk, _, _, _ = orient(und, root); assert len(_pk) == len(nodes), "override broke the tree"
NOSEARCH = os.environ.get("NOSEARCH") == "1"
c0 = cost(und, root); print("start", "feed" if START else "fish", root, c0, flush=True)
key = lambda c: (c[4], c[5], c[0] + c[1] / 2000.0, c[3])
best = c0; t0 = time.time(); it = 0
improved = True
while improved and not NOSEARCH and time.time() - t0 < 1800:
    improved = False; it += 1
    par, order, T, dep = orient(und, root)
    for e in sorted(adj_ok - und, key=lambda e: -pairs.get(e, 0)):
        a, b = e
        # cycle edges = tree path a..b
        c = lca(par, dep, a, b); path = []
        x = a
        while x != c: path.append(tuple(sorted((x, par[x])))); x = par[x]
        x = b
        while x != c: path.append(tuple(sorted((x, par[x])))); x = par[x]
        cand = None
        for f in path:
            u2 = (und - {f}) | {e}
            cc = cost(u2, root)
            if cc and key(cc) < key(best) and (cand is None or key(cc) < key(cand[0])): cand = (cc, u2)
        if cand:
            best, und = cand; improved = True
            par, order, T, dep = orient(und, root)
    # re-root
    for r in nodes:
        cc = cost(und, r)
        if cc and key(cc) < key(best): best, root = cc, r; improved = True
    print("pass", it, root, best, round(time.time() - t0), flush=True)
par, order, T, dep = orient(und, root)
F = dict(root=root, parent=par, order=order, tap={(p, c): tapf(p, c) for c, p in par.items() if p is not None},
         joined=F0["joined"], kind="fish")
orig = L.feed_tree
L.feed_tree = lambda G_, E_, X_, v_, kind="fwd": F
res = {}
for name, FF in (((("kv11", F1),) if START else (("fish", F0),)) + (("retree", F),)):
    L.feed_tree = lambda G_, E_, X_, v_, kind="fwd", FF=FF: FF
    S = L.score(D, reg, v, "fish", padj, M, Tt)
    R = S["crossings"]; cs = L.cap_reading(R, P)
    on = sum(1 for r in R if r["on_feed"])
    longl = [r for r in R if not r["on_feed"] and r["ua_tt"] + r["ub_tt"] > 2500]
    short = [r for r in R if not r["on_feed"] and r["ua_tt"] + r["ub_tt"] <= 2500]
    d8_long_lt100 = sum(1 for r in longl if r["depth"] is None or min(r["m_lo"], r["m_hi"]) < 100)
    Tr, _ = L.arrivals(S["G"], S["F"], v)
    far = max(Tr, key=lambda r: Tr[r] + L.ins(S["G"][r], v))
    hops = {r: len(L.lineage(S["F"], r)) - 1 for r in S["F"]["parent"]}
    out = dict(root=S["F"]["root"], tree_edge_ports=on, short_loop_ports=len(short), long_loop_ports=len(longl),
               long_loop_bits=sum(r["width"] for r in longl), long_loop_pairs=len({(r["ra"], r["rb"]) for r in longl}),
               long_loop_below100_d8=d8_long_lt100, long_loop_min_margin=min((min(r["m_lo"], r["m_hi"]) for r in longl if r["depth"]), default=None),
               worst_unshared_tt=S["summary"]["worst_unshared_tt"], worst_unshared_on=S["summary"]["worst_unshared_on_feed_tt"],
               max_p_tt=max(r["p_tt"] for r in R), max_p_ff=max(r["p_ff"] for r in R),
               chain_max_hops=max(hops.values()), chain_max_arrival_ps=round(Tr[far] + L.ins(S["G"][far], v), 1), chain_far=far,
               below100=sum(1 for r in R if r["depth"] is None or min(r["m_lo"], r["m_hi"]) < 100),
               cap={k: cs[k] for k in ("depth4", "depth8", "fail", "tree_edges", "tree_edges_clean", "max_path_ambiguous_cycles",
                                       "worst_margin_lo_ps", "worst_margin_hi_ps", "lat_hist", "bit_cycles", "d8_bits")},
               tracks_over_1=S["summary"]["tracks_over_1"], tracks_worst_ratio=S["summary"]["tracks_worst_ratio"])
    res[name] = out
    print(name, json.dumps(out), flush=True)
    rows = [dict(id=r["id"], ra=r["ra"], rb=r["rb"], width=r["width"], on_feed=r["on_feed"], tree_hops=r["tree_hops"], lca=r["lca"],
                 ua=r["ua_tt"], ub=r["ub_tt"], p_tt=r["p_tt"], p_ff=r["p_ff"], depth=r["depth"], kind=r["K_kind"], amb=r["amb"],
                 L_lo=r["L_lo"], L_hi=r["L_hi"], m_lo=r["m_lo"], m_hi=r["m_hi"], lat=r["lat"]) for r in R]
    (outd / f"rt_{name}.json").write_text(json.dumps(dict(summary=out, feed=S["feed"], regions=S["regions"], rows=rows), default=str))
(outd / "retree_summary.json").write_text(json.dumps(res, indent=1, default=str))
