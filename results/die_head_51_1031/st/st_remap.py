#!/usr/bin/env python3
"""DIE-HEAD-51 helper st: re-anchor the HEAD START stages (bind start ports, count_align_bind.v2 --start-tree clock) from the
retired hk5 (08-28) clock tree onto the CURRENT die clock proof, without RTL change.

Each START stage (start_stages json: one ot_dp_landing_origin per old tree node, clock port t_st_<cell>__clk, physical
rect fixed) keeps its RTL, place, parent/children and sample edge; only the clock-tree node its clock pin hangs off
changes.  Modes:
  --leaf [--radius R --any-node --want W]  (USED for bind_l48w: R 700, any node, W 25): start at the nearest
      tap-driving node (the node a real tap leg hangs off) to the stage clock pin; then local search: every stage on an
      edge whose sync distance is < aperture + W is re-hung on the node within R um (any tree node with --any-node)
      that minimises its failing edges, then its edges below aperture + W, then maximises its worst distance, then hop.
  --pure: nearest node by xy.   default: topology-preserving (strict common ancestor of the child stage nodes): gives
      mm-long hops because the hk5 start tree does not follow the l48c clock topology (diagnostic only).
Timing test = die_sta_related.count_align_start_ports (virtual_tap = node + median leg, ca_pair_interval with
CPPR_LCA, regchar clk->Q per corner, sync aperture of the bind).  The proof needs node FALL arrivals
(die_trial clock_edge_readout, see edge.sh).
usage: st_remap.py BIND STAGES PROOF_DIR OUT_BIND [--leaf --radius R --any-node --want W | --pure] --ring REGCHAR_DIR --sta DIE_STA_DIR"""
import argparse, json, math, sys, collections
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("bind"); ap.add_argument("stages"); ap.add_argument("proof"); ap.add_argument("out")
ap.add_argument("--pure", action="store_true"); ap.add_argument("--leaf", action="store_true"); ap.add_argument("--radius", type=float, default=0.0); ap.add_argument("--any-node", action="store_true"); ap.add_argument("--want", type=float, default=0.0); ap.add_argument("--debug", action="store_true"); ap.add_argument("--ring"); ap.add_argument("--sta")
a = ap.parse_args()
sys.path.insert(0, a.sta)
import die_sta_related as R
R.CPPR_LCA = True   # run_single.sh / the gate run with --cppr-lca

b = json.loads(Path(a.bind).read_text())
st = json.loads(Path(a.stages).read_text())
T = float(b["period_ps"]); sap = float(b.get("sync_aperture_ps", 26.5))
cq = {"TT": (0.0, 0.0), "FF": (0.0, 0.0)}
if a.ring:   # --ring = die_sta_related regchar dir (regchar/<C>.json: the same clk->Q range the gate uses)
    for c in cq:
        rg = json.loads((Path(a.ring) / f"{c}.json").read_text())
        cq[c] = (float(rg["clkq_min_nowire_ps"]), float(rg["clkq_max_wire_ps"]))
P = {c: json.loads((Path(a.proof) / f"tap_arrivals_{c}.json").read_text()) for c in ("TT", "FF")}
M = P["TT"]; nodes = M["node_late_ps"]; nxy = M["node_xy_um"]
taps = {c: {t["port"]: t for t in P[c]["taps"]} for c in P}
for c in P:
    assert P[c].get("node_fall_late_ps"), f"{c}: proof has no node fall arrivals"
legs = {c: (R.tap_leg(P[c], taps[c]), R.tap_leg_fall(P[c], taps[c])) for c in P}
S = {s["region"][3:]: s for s in st["stages"]}
assert len(S) == len(st["stages"])
sp = b["start_ports"]
kids = collections.defaultdict(list)          # old path -> [(port id, child old path | None, real tap | None, edge)]
for pid, c in sp.items():
    l = c["launch"][6:]; cap = c["capture"]
    edge = "fall" if b["regions"].get(c["dst"], {}).get("edge_fall") else "rise"
    if cap.startswith("__st__"):
        kids[l].append((pid, cap[6:], None, edge))
    else:
        kids[l].append((pid, None, cap, edge))
depth = lambda p: len(p)

def lca(paths):
    p = paths[0]
    for q in paths[1:]:
        n = 0
        while n < min(len(p), len(q)) and p[n] == q[n]:
            n += 1
        p = p[:n]
    return p

def vt(c, path):
    leg, fleg = legs[c]
    tp = {}
    k = R.virtual_tap(P[c], tp, path, leg, fleg)
    return tp[k]

def clean(c, lpath, cap_tap, edge):
    """sync distance of launch virtual tap at lpath -> capture tap (dict) on corner c (die_sta_related form)"""
    A = vt(c, lpath)
    try:
        iv = R.ca_pair_interval(A, cap_tap, "__st__" + lpath, cap_tap["port"], P[c]["cppr_node_range_ps"], None, edge)[:2]
    except R.FallArrivalMissing:
        return -1e9
    off = T / 2 if edge == "fall" else 0.0
    elo, ehi = iv[0] - cq[c][1], iv[1] - cq[c][0]
    k = math.floor((elo - off) / T)
    return min(elo - (off + k * T), off + (k + 1) * T - ehi) if math.floor((ehi - off) / T) == k else -1.0

drv = sorted({t["tree_path"][:-1] for t in taps["TT"].values() if len(t["tree_path"]) > 1 and t["tree_path"][:-1] in nodes})

def evaluate(newmap):
    res = collections.Counter(); worst = {}
    for pid, c in sp.items():
        l = newmap[c["launch"][6:]]; cap = c["capture"]
        edge = "fall" if b["regions"].get(c["dst"], {}).get("edge_fall") else "rise"
        for cc in ("TT", "FF"):
            capt = vt(cc, newmap[cap[6:]]) if cap.startswith("__st__") else taps[cc][cap]
            d = clean(cc, l, capt, edge)
            if a.debug and d < sap and res[("dbg", cc, edge)] < 4:
                res[("dbg", cc, edge)] += 1
                A = vt(cc, l); iv = R.ca_pair_interval(A, capt, "x", capt["port"], P[cc]["cppr_node_range_ps"], None, edge)[:2]
                print("DBG", cc, edge, pid[:40], "L", l, A["late_ps"], A["early_ps"], A.get("fall_late_ps"), "C", capt.get("tree_path"), capt["late_ps"], capt["early_ps"], capt.get("fall_late_ps"), capt.get("fall_early_ps"), "iv", [round(x, 1) for x in iv], "d", round(d, 1))
            res[(cc, edge, d >= sap)] += 1
            worst[(cc, edge)] = min(worst.get((cc, edge), 1e9), d)
    return res, worst

if a.leaf:
    import bisect
    new = {}; hop = []; stats = collections.Counter()
    for old, s in S.items():
        xy = s.get("clock_pin_xy_um") or s["node_xy_um"]
        if old == "h":
            new[old] = "h"; hop.append(0.0); continue
        p = min(drv, key=lambda q: abs(nxy[q][0] - xy[0]) + abs(nxy[q][1] - xy[1]))
        new[old] = p; hop.append(abs(nxy[p][0] - xy[0]) + abs(nxy[p][1] - xy[1])); stats["leaf_nearest"] += 1
    order = []
    if a.radius > 0:   # local search: re-hang a stage on another tap-driving node within --radius of its clock pin
        inc = collections.defaultdict(list)      # old stage path -> [(launch old, capture key, edge)]
        E = []
        for pid, c in sp.items():
            l = c["launch"][6:]; cap = c["capture"]
            edge = "fall" if b["regions"].get(c["dst"], {}).get("edge_fall") else "rise"
            e = (l, cap[6:] if cap.startswith("__st__") else None, None if cap.startswith("__st__") else cap, edge)
            E.append(e); inc[l].append(e)
            if e[1] is not None:
                inc[e[1]].append(e)
        def score(e, m):
            l, cs, ct, edge = e; w = 1e9
            for cc in ("TT", "FF"):
                capt = vt(cc, m[cs]) if cs is not None else taps[cc][ct]
                w = min(w, clean(cc, m[l], capt, edge))
            return w
        grid = collections.defaultdict(list); G = 100.0
        for q in (nodes if a.any_node else drv):
            grid[(int(nxy[q][0] // G), int(nxy[q][1] // G))].append(q)
        def near(xy):
            r = int(a.radius // G) + 1; gx, gy = int(xy[0] // G), int(xy[1] // G)
            return [q for i in range(gx - r, gx + r + 1) for j in range(gy - r, gy + r + 1) for q in grid.get((i, j), ())
                    if abs(nxy[q][0] - xy[0]) + abs(nxy[q][1] - xy[1]) <= a.radius]
        for it in range(10):
            bad = sorted({x for e in E if score(e, new) < sap + a.want for x in (e[0], e[1]) if x and x != "h"})
            print("iter", it, "failing edges", sum(score(e, new) < sap for e in E), "below want", sum(score(e, new) < sap + a.want for e in E), "stages touched", len(bad), flush=True)
            moved = 0
            for st_ in bad:
                xy = S[st_].get("clock_pin_xy_um") or S[st_]["node_xy_um"]
                cur = new[st_]
                def key(q):
                    new[st_] = q
                    v = [score(e, new) for e in inc[st_]]
                    return (sum(x < sap for x in v), sum(x < sap + a.want for x in v), -min(v), abs(nxy[q][0] - xy[0]) + abs(nxy[q][1] - xy[1]))
                best = min([cur] + near(xy), key=key)
                new[st_] = best; moved += best != cur
            if not moved:
                break
        hop = sorted(abs(nxy[new[o]][0] - (S[o].get("clock_pin_xy_um") or S[o]["node_xy_um"])[0]) +
                     abs(nxy[new[o]][1] - (S[o].get("clock_pin_xy_um") or S[o]["node_xy_um"])[1]) for o in new)
        stats["radius_um"] = a.radius; stats["any_node"] = int(a.any_node)
else:
    new = {"h": "h"}
order = [] if a.leaf else sorted(S, key=depth, reverse=True)
if not a.leaf:
    stats = collections.Counter(); hop = []
for old in order:
    if old == "h":
        continue
    s = S[old]; anchors = []; checks = []
    for pid, ch, rt, edge in kids.get(old, []):
        if ch is not None:
            anchors.append(new[ch]); checks.append(("st", new[ch], edge))
        else:
            anchors.append(taps["TT"][rt]["tree_path"]); checks.append(("tap", rt, edge))
    if not anchors:
        raise SystemExit(f"stage {old!r} has no children")
    L = lca(anchors)
    strict = L if all(len(x) > len(L) for x in anchors) else L[:-1]
    cand = [strict[:i] for i in range(1, len(strict) + 1) if strict[:i] in nodes]
    if not cand:   # an anchor already sits on the LCA (start tree deeper than the clock tree there): share its node
        cand = [L[:i] for i in range(1, len(L) + 1) if L[:i] in nodes] or ["h"]; stats["shared_node"] += 1
    xy = s.get("clock_pin_xy_um") or s["node_xy_um"]
    dist = lambda p: abs(nxy[p][0] - xy[0]) + abs(nxy[p][1] - xy[1])
    cand.sort(key=lambda p: (dist(p), -len(p)))
    pick = None
    if not a.pure:
        for p in cand:
            ok = True
            for kind, x, edge in checks:
                for c in ("TT", "FF"):
                    cap = vt(c, x) if kind == "st" else taps[c][x]
                    if clean(c, p, cap, edge) < sap:
                        ok = False; break
                if not ok:
                    break
            if ok:
                pick = p; stats["clean"] += 1; break
    if pick is None:
        pick = cand[0]; stats["nearest"] += 1
    new[old] = pick; hop.append(dist(pick))
hop.sort()
r, w = evaluate(new)
if a.debug:
    for pid, c in sp.items():
        l = new[c["launch"][6:]]; cap = c["capture"]; edge = "fall" if b["regions"].get(c["dst"], {}).get("edge_fall") else "rise"
        capt = vt("TT", new[cap[6:]]) if cap.startswith("__st__") else taps["TT"][cap]
        d = clean("TT", l, capt, edge)
        if d < sap:
            A = vt("TT", l); iv = R.ca_pair_interval(A, capt, "x", capt["port"], P["TT"]["cppr_node_range_ps"], None, edge)[:2]
            n = R.pair_node(A, capt)
            hx = S[c["launch"][6:]]; hxy = hx.get("clock_pin_xy_um")
            cxy = capt["xy_um"]
            print("FAIL TT", edge, "lca_len", len(n), "L", len(l), "C", len(capt["tree_path"]), "iv", [round(x) for x in iv], "w", round(iv[1]-iv[0]),
                  "stagehop", round(abs(hxy[0]-cxy[0])+abs(hxy[1]-cxy[1])), "real" if not cap.startswith("__st__") else "st")
print("eval", sorted(r.items()), {k: round(v, 1) for k, v in w.items()})
for pid, c in sp.items():
    for f in ("launch", "capture"):
        if c[f].startswith("__st__"):
            o = c[f][6:]
            c[f] = f"__st__{new[o]}@{S[o]['id']}"
    c["fork_node_hk5"] = c.get("fork_node"); c["fork_node"] = new.get(c.get("fork_node"), c.get("fork_node"))
b["start_tree_remap"] = dict(tool="DIE-HEAD-51 helper st st_remap.py", from_tree="hk5 (codex-head-start-0828) unicode paths",
                             to_proof=str(a.proof), stages=len(new), mode="leaf-nearest" if a.leaf else "pure-nearest" if a.pure else "nearest-clean",
                             picked=dict(stats), hop_um=dict(p50=hop[len(hop) // 2], p90=hop[int(len(hop) * .9)], max=hop[-1]),
                             map={S[o]["id"]: v for o, v in new.items()}, rtl_change=False)
Path(a.out).write_text(json.dumps(b, indent=1) + "\n")
print("stages", len(new), dict(stats), "hop um p50/p90/max", round(hop[len(hop) // 2], 1), round(hop[int(len(hop) * .9)], 1), round(hop[-1], 1))
