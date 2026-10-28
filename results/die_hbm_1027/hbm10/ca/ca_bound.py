#!/usr/bin/env python3
"""DIE-HBM-10 ESTIMATE (plan time, no build): count-aligned bound of every HBM die region link on the PHY_N W/C/E split
re-tree (DIE-HBM-9 retree/hbm_feed_split.tsv + hbm_xings_split.tsv), with the ONE shared model only:
tools/die_plan/locality.margins (landed_phase_ocv.analyse, clk_aocv g021 table = clock_variation 'table', one-sided droop
between regions, class-B core latency) and locality.cap_reading (= count_align_plan unchanged: K, DEPTH 4/8, start tree,
path ambiguity, T/8 aperture, 5 % wander).  Spice scale x1.05 (12.15b plan tools) on every unshared clock delay.
Branch geometry = the die_retree.py model (edge delay = CHECKED tree-edge unshared where the crossing exists, else
Manhattan(feed taps) x v, + the endpoint region insertion on an unmeasured last edge); per link ua/ub = sum of edge delays LCA -> a / LCA -> b; AOCV distance from the bbox of the
taps on both paths.  Links that miss DEPTH 8 or 100 ps become 12.13c/12.16b(i) hop chains along the tree path: one
count-aligned landing per tree edge (the tree-edge crossing = shared up to the tap), re-planned with the same tool.
usage: ca_bound.py REPO FEED_TSV XINGS_TSV OUT_JSON [MAX_DIRECT_HOPS]
MAX_DIRECT_HOPS (optional): links whose tree path has more hops also become hop chains (12.16b(i): a direct crossing
is a tree edge or closes a SHORT loop), even if they pass."""
import csv, sys, json, collections, math
repo, feedp, xsp, outp = sys.argv[1:5]
MAXH = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
sys.path.insert(0, f"{repo}/tools/die_plan")
import types
_p = f"{repo}/tools/die_plan/locality.py"; _s = open(_p).read()   # CLK-LOCAL-EST-1 loc.py patch: keep FAIL rows (no L_lo)
_old = '                x["margin_lo_ps"] = round(x["L_lo_ps"] - 0.5 * period, 1)\n'
assert _old in _s
_s = _s.replace(_old, '                if "L_lo_ps" not in x:\n                    x.update(L_lo_ps=None, L_hi_ps=None, margin_lo_ps=None, margin_hi_ps=None, depth=None, lat_cycles=x.get("lat_cycles"), kind=x.get("kind", "FAIL"), path_ambiguous_cycles=x.get("path_ambiguous_cycles", -1))\n                    res[x["port"]] = x\n                    continue\n' + _old)
L = types.ModuleType("locality"); L.__file__ = _p; sys.modules["locality"] = L; exec(compile(_s, _p, "exec"), L.__dict__)
Tt = L.CA.load(L.TABLE); P = 833.0; V = 0.3659; SPICE = 1.05
feed = list(csv.DictReader(open(feedp), delimiter="\t")); xs = list(csv.DictReader(open(xsp), delimiter="\t"))
par, tap, ins = {}, {}, {}
for r in feed:
    par[r["child_region"]] = r["parent_region"]; ins[r["child_region"]] = float(r["ins_ps"])
    tap[r["child_region"]] = json.loads(r["feed_tap_xy_um"]) if r["feed_tap_xy_um"] else None
tap["ROOT"] = [14199.84, 8570.88]
meas = {}
for r in xs:
    if r["class"] == "tree-edge":
        a, b, n = r["src_region"], r["dst_region"], r["tree_node_region"]
        meas[(n, b if n == a else a)] = float(r["unshared_ps"])
def ed(p, c):
    if (p, c) in meas: return meas[(p, c)]
    pt = tap.get(p) or tap["ROOT"]; ct = tap[c] or pt
    return (abs(pt[0] - ct[0]) + abs(pt[1] - ct[1])) * V
def anc(a):
    out = [a]
    while out[-1] != "ROOT": out.append(par[out[-1]])
    return out
T = {}
def arr(r):
    if r == "ROOT": return 0.0
    if r not in T: T[r] = arr(par[r]) + ed(par[r], r)
    return T[r]
links = collections.defaultdict(int)
for r in xs: links[tuple(sorted((r["src_region"], r["dst_region"])))] += int(r["bits"])
def br(a, b):
    A, B = anc(a), anc(b); sB = set(B); l = next(x for x in A if x in sB)
    pa, pb = A[:A.index(l)], B[:B.index(l)]
    # endpoint region: an unmeasured last edge also pays the region insertion (centre -> farthest leaf, upper bound;
    # die_retree.py omitted it).  CHECKED tree-edge values already include the leaf.
    last = lambda e: 0.0 if (par[e], e) in meas else ins[e]
    ua = sum(ed(par[x], x) for x in pa) + (last(a) if pa else 0.0)
    ub = sum(ed(par[x], x) for x in pb) + (last(b) if pb else 0.0)
    pts = [tap[x] for x in pa + pb if tap.get(x)] or [tap.get(a) or tap["ROOT"]]
    if len(pts) == 1: pts = pts * 2
    return dict(lca=l, ua=ua * SPICE, ub=ub * SPICE, div=arr(l) * SPICE, pts=pts, hops=len(pa) + len(pb))
def run(pairs):
    """both directions per link (the start tree is directed); a link's row = the worse direction."""
    dp = [(a, b, n) for (a, b, n) in pairs] + [(b, a, n) for (a, b, n) in pairs]
    B = [br(a, b) for (a, b, _) in dp]
    R = L.margins(B, Tt, P)
    for i, ((a, b, n), b_, r) in enumerate(zip(dp, B, R)):
        r.update(id=f"{a}>{b}", ra=a, rb=b, width=n, lca=b_["lca"], hops=b_["hops"])
    cs = L.cap_reading(R, P)
    def key(r): return (r["depth"] is not None, min(r["m_lo"], r["m_hi"]) if r["depth"] else -1e9)
    out = []
    for i, (a, b, n) in enumerate(pairs):
        r = min(R[i], R[i + len(pairs)], key=key); r = dict(r); r.update(id=f"{a}~{b}", ra=a, rb=b); out.append(r)
    return out, cs
pairs = [(a, b, n) for (a, b), n in sorted(links.items())]
R, cs = run(pairs)
def ok(r): return r["depth"] is not None and min(r["m_lo"], r["m_hi"]) >= 100 and r["hops"] <= MAXH
direct = [dict(link=r["id"], bits=r["width"], lca=r["lca"], hops=r["hops"], unshared_ps=round(r["ua_tt"] + r["ub_tt"], 1),
               p_tt=r["p_tt"], p_ff=r["p_ff"], depth=r["depth"], m_lo=r["m_lo"], m_hi=r["m_hi"], lat=r["lat"], amb=r["amb"])
          for r in sorted(R, key=lambda r: -(r["ua_tt"] + r["ub_tt"]))]
bad = [r for r in R if not ok(r)]
# hop chains: every failing link re-timed along its tree path; tree edges carried by chains get a synthetic crossing
edge_bits = collections.defaultdict(int)
for r in R:
    if ok(r): continue
    A, Bn = anc(r["ra"]), anc(r["rb"]); sB = set(Bn); l = next(x for x in A if x in sB)
    for x in A[:A.index(l)] + Bn[:Bn.index(l)]: edge_bits[(par[x], x)] += r["width"]
keep = [(r["ra"], r["rb"], r["width"]) for r in R if ok(r)]
have = {tuple(sorted(p[:2])) for p in keep}
hop_pairs = keep + [(p, c, n) for (p, c), n in edge_bits.items() if tuple(sorted((p, c))) not in have]
# tree-edge crossings carried by an existing direct link just add bits
R2, cs2 = run(sorted(hop_pairs))
L2 = {r["id"]: r for r in R2}
def lat_of(a, b):
    k = f"{a}~{b}" if f"{a}~{b}" in L2 else f"{b}~{a}"
    return L2[k]
chains = []
for r in bad:
    A, Bn = anc(r["ra"]), anc(r["rb"]); sB = set(Bn); l = next(x for x in A if x in sB)
    path = A[:A.index(l) + 1] + Bn[:Bn.index(l)][::-1]
    hops = [lat_of(path[i], path[i + 1]) for i in range(len(path) - 1)]
    chains.append(dict(link=r["id"], bits=r["width"], direct_unshared_ps=round(r["ua_tt"] + r["ub_tt"], 1),
                       direct_depth=r["depth"], direct_m=[r["m_lo"], r["m_hi"]], path=path,
                       hop_depth=[h["depth"] for h in hops], hop_min_margin=min((min(h["m_lo"], h["m_hi"]) if h["depth"] else -1e9) for h in hops),
                       chain_lat_cycles=sum(h["lat"] or 0 for h in hops), direct_lat=r["lat"]))
def summ(R, cs):
    return dict(links=len(R), depth4=cs["depth4"], depth8=cs["depth8"], fail=cs["fail"],
                below100=sum(1 for r in R if r["depth"] is None or min(r["m_lo"], r["m_hi"]) < 100), not_direct=sum(1 for r in R if not ok(r)), worst_margin_lo_ps=cs["worst_margin_lo_ps"],
                worst_margin_hi_ps=cs["worst_margin_hi_ps"], max_unshared_ps=round(max(r["ua_tt"] + r["ub_tt"] for r in R), 1),
                max_p_tt=max(r["p_tt"] for r in R), max_p_ff=max(r["p_ff"] for r in R), max_lat=cs["max_lat"],
                max_amb=cs["max_path_ambiguous_cycles"])
out = dict(scope="ESTIMATE (plan time); shared locality.margins + cap_reading (count_align_plan), clock_variation=table g021, "
                 "droop regions, spice x1.05; branch geometry die_retree model", period_ps=P, v_ps_mm=V * 1000,
           direct=summ(R, cs), direct_rows=direct, hop_form=summ(R2, cs2), chains=chains,
           hop_rows=[dict(link=r["id"], bits=r["width"], unshared_ps=round(r["ua_tt"] + r["ub_tt"], 1), depth=r["depth"],
                          m_lo=r["m_lo"], m_hi=r["m_hi"], lat=r["lat"]) for r in sorted(R2, key=lambda r: -(r["ua_tt"] + r["ub_tt"]))])
json.dump(out, open(outp, "w"), indent=1, default=str)
print("direct", json.dumps(out["direct"])); print("hop", json.dumps(out["hop_form"]))
for x in direct[:8]: print(x)
for c in chains: print("chain", c)
