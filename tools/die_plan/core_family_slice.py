#!/usr/bin/env python3
"""ONE scripted 12.3 core-latency path for a core FAMILY (S81-CORE-LAT-R13; COORD RULING S81-CORE-LAT-R12; OWNER 10-27
type reduction + automated work; METHODOLOGY 12.2a1 / 12.3 / 12.8 a-d1).

  placed sink census -> tree plan -> 12.3 plan slice (planned tree, centre entry, in-core islands) -> geometry checks
  -> render, for every member core of a family, with the FAMILY TEMPLATE's parameters (no per-core hand tuning).

Stages (all deterministic, plan model only; no measured timing input, no residual tools):
  census  : OpenROAD (docker, memory cap) dumps the placed clock sinks of the core's own trial kit (3_place.odb, current
            RTL) with the 12.8a centre entry (outline centre), and the legal-site/PG description of its floorplan ODB.
  plan    : equal-count H partition entry -> W/E -> 2 islands per side (= the 4 in-core islands, 12.2a1) -> family
            leaf levels chosen from the sink count and the family leaf target; every edge = its own SHORTEST legal maze
            path (no length padding / meander, COORD 18:5x); long leaves split into equal-count siblings on the same
            driver (same stage count); 12.8 d1 plan-computed sizing (BUFx8..x24 envelope) under the R7 NLDM chain,
            then (if the uf_phys3 fit is given) the R9 uf_phys3 coordinate descent.
  slice   : tools/die_plan/core_plan_to_infra.py (legal row sites, PG obstructions, --band info, --ndr per family).
  check   : automated geometry gates (GEOM-REVIEW-10 form): every leg <= 1.10 x Manhattan of its endpoints, leaf
            spread <= 40 um, every census sink in exactly one leaf, equal stage count on every root->sink path, driver
            displacement <= 2 um, plan TT/FF window <= 20, leaf slew <= 80; plan latency vs 250/202.5 +-20 = INFO.
  render  : PNG of sinks + legs by level + drivers at the converted legal sites.
usage:
  core_family_slice.py run --family FAMILIES.json --core MODULE --kit KITDIR --work DIR [--fit FIT --libdir DIR]
  core_family_slice.py family --family FAMILIES.json --name FAMILY --kits DIR --work DIR   (every member with a 3_place)
PLAN MODEL numbers are UNCHECKED until a build measures them."""
import argparse, collections, gzip, json, math, os, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "results" / "core_lat_r7_1026"))
sys.path.insert(0, str(REPO / "results" / "core_lat_r8_1026"))
import core_infra_htree as H          # noqa: E402
import l0r_r7_model as M7             # noqa: E402  (R7 NLDM predictor + 12.8 d1 sizing)
import l0r_r8_model as M8             # noqa: E402  (split_long_leaves, leaf_spread, leaf_mst)

IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
ENV = ['BUFx24_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx12_ASAP7_75t_R', 'BUFx10_ASAP7_75t_R',
       'BUFx8_ASAP7_75t_R']
GATES = dict(leg_detour_max=1.10, leaf_spread_um=40.0, disp_um=2.0, window_ps=20.0, slew_ps=80.0)
BAND = {"TT": (250.0, 20.0), "FF": (202.5, 20.0)}
_exact = H.exact_points


def _straight(mz, a, b, T, k):
    """every leg = its own shortest legal maze path (no padding to the level maximum; COORD 18:5x meander ruling)."""
    return _exact(mz, a, b, mz.md(a, b), k)


H.exact_points = _straight
M8.H.exact_points = _straight


# ------------------------------------------------------------------ long-leaf split (generic; replaces the R8 helper)
NAME_POOL = "pqrstuvwxyzabcdefghijklmnoPQRSTUVWXYZABCDEFGHIJKLMNO"


def farthest_clusters(pts, limit, driver_xy=None):
    """deterministic farthest-point (k-centre) clustering, k grows until every part's centroid->farthest-sink
    Manhattan spread <= limit; parts may hold unequal counts (joint_nldm_plan load balance + d1 sizing absorb it).
    Isolated face/pin/reset registers get their own small leaf instead of stretching a big one (structure, no wire)."""
    def spread(g):
        cx = sum(p[0] for p in g) / len(g); cy = sum(p[1] for p in g) / len(g)
        if driver_xy is not None:cx,cy=driver_xy((cx,cy))
        return max(abs(p[0] - cx) + abs(p[1] - cy) for p in g)
    for k in range(2, 60):
        seeds = [min(pts, key=lambda p: (p[0], p[1]))]
        while len(seeds) < k:
            seeds.append(max(pts, key=lambda p: (min(abs(p[0] - q[0]) + abs(p[1] - q[1]) for q in seeds), p[0], p[1])))
        for _ in range(12):
            grp = [[] for _ in seeds]
            for p in pts:
                grp[min(range(len(seeds)), key=lambda i: (abs(p[0] - seeds[i][0]) + abs(p[1] - seeds[i][1]), i))].append(p)
            grp = [g for g in grp if g]
            seeds = [(sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)) for g in grp]
        if max(spread(g) for g in grp) <= limit:
            return grp
    return grp


def split_long_leaves(P, limit_um, actual_legal=False):
    """every leaf whose driver->farthest-sink spread exceeds limit_um becomes k sibling leaves on the SAME parent
    driver (same level, same stage count, natural leg length); leaf driver at each part's centroid; names keep the
    level length (letters from NAME_POOL) so level bookkeeping is unchanged.  Every sink stays in exactly one leaf."""
    mz = P['mz']; out = []; sp = M8.leaf_spread(P); node = {n[0]: n for n in P['nodes']}
    taken = {n[0] for n in P['nodes']}
    for u in sorted(sp):
        if sp[u] <= limit_um:
            continue
        # the leaf's own wire edge starts at its '_br' branch buffer; a repeated leaf edge (node[u][1] = u_rK) keeps
        # its repeater count on every part, so siblings hang on the branch's driver with the same stage count
        sinks = P['leafsinks'][u]; br = u + '_br'; drv = node[br][1]; hub = node[br][2]
        nseg = len(next(w['segs'] for w in P['wires'] if w['edge'] == u))
        if nseg > 1:
            reps = {u + '_r%d' % i for i in range(nseg - 1)}
            P['nodes'] = [n for n in P['nodes'] if n[0] not in reps]
        parts = farthest_clusters(sinks, limit_um, driver_xy=(lambda p: mz.xy(mz.cell(p))) if actual_legal else None)
        cells = [mz.cell((sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g))) for g in parts]
        free = [u[:-1] + ch for ch in NAME_POOL if u[:-1] + ch not in taken]
        if len(free) < len(parts) - 1:
            raise SystemExit('split_long_leaves: name pool exhausted at %s (%d parts)' % (u, len(parts)))
        names = [u] + free[:len(parts) - 1]; taken.update(names)
        nsib = sum(1 for n in P['nodes'] if n[4] == 'branch' and n[1] == drv)
        for i, (nm, g, c) in enumerate(zip(names, parts, cells)):
            if i == 0:
                bcell = node[br][2]
            else:
                bcell = mz.cell((mz.xy(hub)[0], mz.xy(hub)[1] + (nsib + i - 1) * 1.08))
                P['nodes'].append((nm + '_br', drv, bcell, H.BIG, 'branch'))
            pts = H.exact_points(mz, bcell, c, mz.md(bcell, c), nseg) if nseg > 1 else []
            prev = nm + '_br'
            for j, q in enumerate(pts):
                P['nodes'].append((nm + '_r%d' % j, prev, q, H.REP, 'rep')); prev = nm + '_r%d' % j
            if i == 0:
                P['nodes'] = [(n[0], prev if n[0] == u else n[1], c if n[0] == u else n[2], n[3], n[4]) for n in P['nodes']]
                P['wires'] = [w for w in P['wires'] if w['edge'] != u]
            else:
                P['nodes'].append((nm, prev, c, H.BIG, 'leaf'))
            chain = [bcell] + pts + [c]
            P['wires'].append(dict(level=len(P['splits']), edge=nm, segs=[mz.md(chain[j], chain[j + 1]) for j in range(len(chain) - 1)],
                                   cells=[mz.path(chain[j], chain[j + 1]) for j in range(len(chain) - 1)]))
            P['leafsinks'][nm] = g
        out.append(dict(leaf=u, spread_um=sp[u], parts=len(parts), part_sinks=[len(g) for g in parts]))
    order, seen, rest = [], set(), list(P['nodes'])
    while rest:
        nxt = [n for n in rest if n[1] is None or n[1] in seen]
        if not nxt:
            raise SystemExit('cycle in plan nodes')
        for n in nxt:
            order.append(n); seen.add(n[0])
        rest = [n for n in rest if n[0] not in seen]
    P['nodes'] = order
    return out


def fix_keepout_strays(P, mode, limit_um, smax):
    """DIE-S81-30 opt-in (family "keepout_stray": "merge" | "reparent"; macro_leaves plans only).  split_long_leaves
    gives a split-off part its own leaf at the part centroid on the ORIGINAL parent; beside macro keep-outs that leg
    walks round the macro (VSW: 1 + 4 flops in the channel between the two SRAMs, 1.61x / 1.92x Manhattan) or runs
    far past smax with no repeater (VSW Tqqwq: 128 um, leaf slew-in 95 ps).  Every leaf-level single-segment leg
    > 1.10x Manhattan or > smax is resolved structurally (no sink moves, no stage added), trying in mode order:
      merge    -- the stray sinks join the existing leaf whose driver reaches every one of them by a <= 1.10x maze path
                  with the merged driver->sink spread <= limit_um (least spread wins); the emptied leaf is pruned.
      reparent -- the stray leaf keeps its own leaf buffer (same stage count) but hangs on the same-level driver whose
                  branch site reaches it by a single <= 1.10x, <= smax leg (shortest wins).
    "merge" tries merge then reparent; "reparent" tries reparent then merge.  A leg with no legal fix is left
    unchanged (the plan gates then fail honestly).  Returns the per-leaf record."""
    if mode not in ("merge", "reparent"):
        raise SystemExit("keepout_stray: mode must be merge or reparent, got %r" % mode)
    mz = P['mz']; G = mz.G; tol = GATES["leg_detour_max"] + 1e-9
    man = lambda a, b: (abs(a[0] - b[0]) + abs(a[1] - b[1])) * G
    lvl = max(w['level'] for w in P['wires'])
    node = {n[0]: n for n in P['nodes']}
    leafset = lambda: {w['edge'] for w in P['wires'] if w['level'] == lvl and node.get(w['edge'], (0,) * 5)[4] == 'leaf'}

    def ratio(w):
        q = [s / man(c[0], c[-1]) for s, c in zip(w['segs'], w['cells']) if man(c[0], c[-1]) > 1.0]
        return max(q) if q else 1.0
    wire = {w['edge']: w for w in P['wires']}
    bad = sorted(u for u in leafset() if ratio(wire[u]) > tol or (len(wire[u]['segs']) == 1 and wire[u]['segs'][0] > smax + 1e-9))
    ismac = lambda u: any(s[4].startswith("MACRO:") for s in P['leafsinks'][u])

    def merge(u, sinks):
        best = None
        for v in sorted(leafset() - set(bad) - {u}):
            if ismac(v):
                continue
            d = node[v][2]; xy = mz.xy(d); spread = 0.0
            for s in P['leafsinks'][v] + sinks:
                spread = max(spread, abs(s[0] - xy[0]) + abs(s[1] - xy[1]))
            if spread > limit_um or (best is not None and spread >= best[0]):
                continue
            if all(man(d, c) <= 1.0 or mz.md(d, c) <= tol * man(d, c) for c in (mz.cell(s[:2], node=False) for s in sinks)):
                best = (spread, v)
        if best is None:
            return None
        P['leafsinks'][best[1]] = P['leafsinks'][best[1]] + sinks; P['leafsinks'][u] = []
        return dict(fixed="merge", into=best[1], spread_um=round(best[0], 2), pruned=prune_empty_leaves(P))

    def reparent(u, sinks):
        c = node[u][2]; own = node[u + '_br'][1]; best = None
        for v in sorted(leafset() - {u}):
            drv = node[v + '_br'][1]
            if drv == own:
                continue
            hub = node[v + '_br'][2]
            nsib = sum(1 for n in P['nodes'] if n[4] == 'branch' and n[1] == drv)
            b = mz.cell((mz.xy(hub)[0], mz.xy(hub)[1] + nsib * 1.08))
            L = mz.md(b, c)
            if L <= smax and (man(b, c) <= 1.0 or L <= tol * man(b, c)) and (best is None or (L, drv) < best[:2]):
                best = (L, drv, b)
        if best is None:
            return None
        L, drv, b = best
        P['nodes'] = [(n[0], drv, b, n[3], n[4]) if n[0] == u + '_br' else n for n in P['nodes']]
        wire[u]['segs'] = [L]; wire[u]['cells'] = [mz.path(b, c)]
        return dict(fixed="reparent", driver=drv, leg_um=round(L, 2), branch_xy=mz.xy(b), pruned=prune_empty_leaves(P))
    out = []
    for u in bad:
        sinks = P['leafsinks'][u]
        rec = dict(leaf=u, sinks=len(sinks), ratio=round(ratio(wire[u]), 3), leg_um=round(sum(wire[u]['segs']), 2), mode=mode)
        if ismac(u) or len(wire[u]['segs']) != 1:
            out.append(dict(rec, fixed=False, why="macro leaf or repeated leaf edge")); continue
        r = None
        for f in ((merge, reparent) if mode == "merge" else (reparent, merge)):
            r = f(u, sinks)
            if r is not None:
                break
        node = {n[0]: n for n in P['nodes']}
        out.append(dict(rec, **r) if r is not None else dict(rec, fixed=False, why="no legal merge/reparent target"))
    if not any(r.get("fixed") == "reparent" for r in out):
        return out
    order, seen, rest = [], set(), list(P['nodes'])   # parents before children (a reparented branch may point back)
    while rest:
        nxt = [n for n in rest if n[1] is None or n[1] in seen]
        if not nxt:
            raise SystemExit('keepout_stray: cycle in plan nodes')
        for n in nxt:
            order.append(n); seen.add(n[0])
        rest = [n for n in rest if n[0] not in seen]
    P['nodes'] = order
    return out


def reparent_obstructed_edges(P, smax, model=None, edges=None, max_donors=4):
    """Opt-in same-depth macro-face repair; optional bounded electrical selection.

    Keep endpoints, sink membership, repeater counts and every sink path depth.
    Check BOTH the effective parent hub->branch stub and every branch->endpoint
    segment. The local fan stays in the executable H-tree model domain (<=4um
    landed, <3um ordinary). No legal donor leaves the original failure intact.
    With model=(libs,r,c,wc), score at most max_donors distinct legal donors by
    the ENTIRE composed TT/FF model, including changed upstream fanout/load.
    """
    mz = P['mz']; tol = GATES['leg_detour_max'] + 1e-9
    man = lambda a, b: sum(abs(x-y) for x, y in zip(a, b)) * mz.G
    wire = {w['edge']: w for w in P['wires']}

    def depths():
        nd = {n[0]: n for n in P['nodes']}; out = {}
        def visit(u, seen):
            if u in out: return out[u]
            if u in seen: raise ValueError('macro-face repair cycle at ' + u)
            par = nd[u][1]
            out[u] = 0 if par is None else visit(par, seen | {u}) + 1
            return out[u]
        for u in nd: visit(u, set())
        return out

    def legal(segments, paths):
        return all(0 <= length <= smax + 1e-9
                   and (man(path[0], path[-1]) <= 1.0
                        or length <= tol * man(path[0], path[-1]))
                   for length, path in zip(segments, paths))

    def objective(res):
        return (max(res[c]['window'] for c in ('TT', 'FF')),
                sum(res[c]['window'] for c in ('TT', 'FF')))

    before = {u: d for u, d in depths().items() if u in P['leafsinks']}
    result = []
    for w in sorted(P['wires'], key=lambda w: (w['level'], w['edge'])):
        u = w['edge']
        if edges is not None:
            if u not in edges: continue
        elif legal(w['segs'], w['cells']): continue
        br = u + '_br'; k = len(w['segs'])
        nodes = {n[0]: n for n in P['nodes']}; dep = depths()
        own = nodes[br][1]; endpoint = w['cells'][-1][-1]
        owned = {br} | {u + '_r%d' % i for i in range(k-1)}
        occupied = {n[2] for n in P['nodes'] if n[0] not in owned}
        baseline = M7.model_x(P, *model)[0] if model else None
        target = {}
        if model:
            # Existing exact model arrivals rank a bounded donor shortlist. Final
            # choice below always re-evaluates the whole tree, never this proxy.
            for co, L in model[0].items():
                it = P['_int'][co]; affected = []
                for leaf in P['leafsinks']:
                    n = leaf
                    while n is not None and n != br: n = nodes[n][1]
                    if n != br: continue
                    ct, el = it['drv'][leaf]; lib = L[nodes[leaf][3]]; slew = it['slew'][leaf]
                    d = .5 * (H.interp(lib['rise'], slew, ct) + H.interp(lib['fall'], slew, ct))
                    affected.append(it['arr'][leaf] + d + el[0][1])
                mid = .5 * (baseline[co]['leaf_mean_min'] + baseline[co]['leaf_mean_max'])
                target[co] = it['arr'][br] + mid - sum(affected) / len(affected)
        options = []; seen_drivers = set()
        for donor in sorted(P['wires'], key=lambda z: z['edge']):
            vb = donor['edge'] + '_br'
            if donor['level'] != w['level'] or vb == br: continue
            drv = nodes[vb][1]
            if drv == own or drv in seen_drivers or dep[drv] != dep[own]: continue
            seen_drivers.add(drv)
            landed = drv in P['land']
            hub = wire[P['land'][drv][1]]['cells'][-1][-1] if landed else nodes[drv][2]
            bound = 4.0 if landed else 3.0
            radius = math.ceil(bound / mz.G); best_site = None
            for dx in range(-radius, radius+1):
                for dy in range(-radius, radius+1):
                    b = (hub[0]+dx, hub[1]+dy)
                    direct = man(hub, b)
                    if direct > bound or (not landed and direct >= bound): continue
                    if not (0 <= b[0] <= mz.NX and 0 <= b[1] <= mz.NY) or not mz.site_ok(*b): continue
                    if b in occupied: continue
                    stub = mz.md(hub, b)
                    if stub < 0 or stub > bound or (not landed and stub >= bound): continue
                    if stub > tol * direct + 1e-9: continue
                    # Maze adjacency is undirected; use one endpoint BFS for all
                    # nearby branch slots instead of caching a BFS per slot.
                    length = mz.md(endpoint, b)
                    if length < 0 or length > k*smax + 1e-9: continue
                    if length > tol * man(b, endpoint) + 1e-9: continue
                    score = (length, stub, b)
                    if best_site is None or score < best_site[0]: best_site=(score,b,stub)
            if best_site is None: continue
            (length, _, _), b, stub = best_site
            proxy = sum(abs(P['_int'][co]['arr'][vb] - target[co]) for co in target) if model else 0
            options.append((proxy, length, drv, b, stub, bound, hub))
        options.sort(); best = None; tested = 0
        saved_nodes = P['nodes']; saved_segs = w['segs']; saved_paths = w['cells']; saved_land = dict(P['land'])
        for proxy, length, drv, b, stub, bound, hub in options:
            pts = H.exact_points(mz, b, endpoint, length, k)
            if len(set([b]+pts)) != k or any(p in occupied for p in pts): continue
            chain=[b]+pts+[endpoint]
            segs=[mz.md(a,z) for a,z in zip(chain,chain[1:])]
            paths=[mz.path(a,z) for a,z in zip(chain,chain[1:])]
            if not legal(segs,paths): continue
            tested += 1
            positions={br:b, **{u+'_r%d'%i:p for i,p in enumerate(pts)}}
            new_nodes=[(n[0],drv if n[0]==br else n[1],positions.get(n[0],n[2]),n[3],n[4]) for n in saved_nodes]
            P['nodes']=new_nodes; w['segs'],w['cells']=segs,paths
            last=u+'_r%d'%(k-2) if k>1 else br
            if last in P['land']:P['land'][last]=(segs[-1],u)
            prediction=M7.model_x(P,*model)[0] if model else None
            score=objective(prediction) if model else (sum(segs),drv,b)
            valid=not model or (all(prediction[c][key]<=GATES['slew_ps'] for c in ('TT','FF')
                                   for key in ('leaf_slew_in_max','leaf_out_slew_max'))
                                     and score < objective(baseline))
            if valid and (best is None or score<best[0]):
                best=(score,new_nodes,segs,paths,dict(P['land']),drv,b,stub,bound,hub,prediction)
            P['nodes']=saved_nodes;w['segs'],w['cells']=saved_segs,saved_paths;P['land']=dict(saved_land)
            if not model or tested>=max_donors:break
        if best is None:
            result.append(dict(edge=u,level=w['level'],fixed=False,tested=tested,
                why='no legal same-depth donor improves composed timing' if model else 'no reachable same-depth donor preserving edge stages'))
            continue
        score,P['nodes'],w['segs'],w['cells'],P['land'],drv,b,stub,bound,hub,prediction=best
        result.append(dict(edge=u,level=w['level'],fixed='reparent',old_driver=own,driver=drv,
            parent_depth=dep[drv],repeaters=k-1,branch_xy=mz.xy(b),segment_um=w['segs'],
            source_stub=dict(hub_xy=mz.xy(hub),length_um=stub,direct_um=man(hub,b),bound_um=bound),
            **(dict(model_before=baseline,model_after=prediction,tested=tested) if model else {})))
    after=depths()
    if any(after[u]!=d for u,d in before.items()):raise ValueError('macro-face repair changed sink path stage count')
    order,seen,rest=[],set(),list(P['nodes'])
    while rest:
        ready=[n for n in rest if n[1] is None or n[1] in seen]
        if not ready:raise ValueError('macro-face repair cycle')
        order.extend(ready);seen.update(n[0] for n in ready);rest=[n for n in rest if n[0] not in seen]
    P['nodes']=order
    return result


def reassign_nearest(P, cap):
    """structure, no wire: every sink goes to the NEAREST leaf driver (Manhattan, deterministic, capacity cap sinks per
    leaf, farthest-first), so isolated face/pin/reset registers join the closest leaf instead of stretching the
    equal-count partition leaf they fell into.  Leaf drivers then move to their new centroid (legal cell)."""
    mz = P['mz']; pos = {n[0]: mz.xy(n[2]) for n in P['nodes'] if n[4] == 'leaf'}
    allp = [s_ for v in P['leafsinks'].values() for s_ in v]; leaves = sorted(pos)
    d = lambda s_, u: abs(s_[0] - pos[u][0]) + abs(s_[1] - pos[u][1])
    order = sorted(allp, key=lambda s_: (-min(d(s_, u) for u in leaves), s_[2], s_[3]))
    new = {u: [] for u in leaves}
    for s_ in order:
        for u in sorted(leaves, key=lambda u: (d(s_, u), u)):
            if len(new[u]) < cap: new[u].append(s_); break
    moved = sum(1 for u in leaves for s_ in new[u] if s_ not in set(map(tuple, P['leafsinks'][u])))
    # R14: a leaf that is nobody's nearest driver is REMOVED with its exclusive chain (prune_empty_leaves); the R13
    # fallback copied one of its old sinks back into it, so that sink sat in two leaves (gunit_l2, sstn_base566).
    P['leafsinks'] = new
    pruned = prune_empty_leaves(P)
    new = P['leafsinks']
    cell = {u: mz.cell((sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g))) for u, g in new.items()}
    P['nodes'] = [(n[0], n[1], cell[n[0]] if n[0] in cell else n[2], n[3], n[4]) for n in P['nodes']]
    node = {n[0]: n for n in P['nodes']}
    for w in P['wires']:
        if w['edge'] in cell:
            k = len(w['segs']); b = node[w['edge'] + ('_br' if k == 1 else '_r%d' % (k - 2))][2]
            w['segs'][-1] = mz.md(b, cell[w['edge']]); w['cells'][-1] = mz.path(b, cell[w['edge']])
    return dict(moved=moved, cap=cap, pruned=pruned)


def _edge_of(name):
    """plan node name -> its wire edge (T0123_br / T0123_r1 / T0123 -> T0123)."""
    m = re.match(r"(.*)_(br|r\d+)$", name)
    return m.group(1) if m else name


def prune_empty_leaves(P):
    """structure, no wire: a leaf left without sinks is REMOVED together with its exclusive driver chain (branch
    buffer, repeaters, wire edge, landing); any driver left without children is removed the same way (recursive).
    No sink is ever copied (each census sink stays in exactly one leaf) and no driver drives nothing; the surviving
    root->sink paths keep their stage count.  Returns the removed node names (sorted)."""
    empty = sorted(u for u, v in P['leafsinks'].items() if not v)
    if not empty:
        return []
    for u in empty:
        del P['leafsinks'][u]
    gone = set(empty)
    while True:
        alive = [n for n in P['nodes'] if n[0] not in gone]
        haskid = {n[1] for n in alive if n[1]}
        more = {n[0] for n in alive if n[4] not in ('entry', 'leaf') and n[0] not in haskid}
        if not more:
            break
        gone |= more
    P['nodes'] = [n for n in P['nodes'] if n[0] not in gone]
    live = {_edge_of(n[0]) for n in P['nodes']}
    P['wires'] = [w for w in P['wires'] if w['edge'] in live]
    if 'land' in P:
        P['land'] = {k: v for k, v in P['land'].items() if k not in gone and v[1] in live}
    return sorted(gone)


# ------------------------------------------------------------------ census
def docker_or(kit, tcl, env, log):
    kit = Path(kit).resolve()
    e = []
    for k, v in env.items():
        e += ["-e", "%s=%s" % (k, v)]
    cmd = ["docker", "run", "--rm", "--memory=8g", "--memory-swap=8g", "-v", "%s:/work" % kit, "-v", "%s:/tcl:ro" % HERE] + e + \
          [IMAGE, "bash", "-lc", "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /tcl/%s" % tcl]
    with open(log, "w") as f:
        rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
    if rc:
        raise SystemExit("census: %s rc %d (see %s)" % (tcl, rc, log))


def clock_bterm_from_log(log, declared):
    """R14: the census tcl resolves the declared clock port to the placed ODB's BTerm (a 1-bit bus port `clk` is the
    BTerm `clk[0]`; bk_g, qbank_S) and prints DUMP_GEO_CLKPORT <bterm>; the slice names that exact BTerm."""
    got = re.findall(r"^DUMP_GEO_CLKPORT (\S+)\s*$", log, re.M)
    if len(got) != 1:
        raise SystemExit("census: clock port %s not resolved to one BTerm (%d DUMP_GEO_CLKPORT lines)" % (declared, len(got)))
    b = got[0]
    if b != declared and b != declared + "[0]":
        raise SystemExit("census: clock BTerm %s does not match declared port %s" % (b, declared))
    return b


def census(kit, work):
    kit = Path(kit).resolve(); work.mkdir(parents=True, exist_ok=True)
    base = sorted(kit.glob("run/results/asap7/*/base"))
    if not base or not (base[-1] / "3_place.odb").is_file():
        raise SystemExit("census: %s has no 3_place.odb (submit the trial census kit with GOAL=place first)" % kit)
    rel = base[-1].relative_to(kit)
    ctx = json.loads((kit / "boundary_guard_context.json").read_text())
    clk = ctx["clock_ports"][0]
    if not (work / "geo.txt").is_file():
        docker_or(kit, "core_family_geo.tcl", dict(ODB="/work/%s/3_place.odb" % rel, OUT="/work/r13_geo.txt", CLK=clk), work / "geo.log")
        (kit / "r13_geo.txt").replace(work / "geo.txt")
        (work / "clkport.txt").write_text(clock_bterm_from_log((work / "geo.log").read_text(), clk) + "\n")
    if (work / "clkport.txt").is_file():
        clk = (work / "clkport.txt").read_text().strip()
    if not (work / "sites.txt").is_file():
        docker_or(kit, "core_family_sites.tcl", dict(ODB="/work/%s/2_floorplan.odb" % rel, OUT="/work/r13_sites.txt"), work / "sites.log")
        (kit / "r13_sites.txt").replace(work / "sites.txt")
    return clk


# ------------------------------------------------------------------ 12.8c fixed entry trunk (R14)
TRUNK_MENU = ['BUFx8_ASAP7_75t_R', 'BUFx10_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R', 'BUFx24_ASAP7_75t_R']
TRUNK_NMAX = 16


def add_entry_trunk(P, master, n):
    """12.8c: ONE designed fixed trunk at the entry of a shallow core: n identical buffers in series between the entry
    root and the root's children (the W/E branch buffers), on a straight column below the entry at 1.08 um pitch; the
    LAST stage sits next to the branch buffers (stubs <= 2.2 um), the root drives the first stage.  Same cell chain
    for every instance of the type; kind 'trunk' (never resized by d1 sizing); every root->sink path gains n stages."""
    if n <= 0:
        return []
    mz = P['mz']; ex, ey = mz.xy(P['ent'])
    names = ['K_r%d' % i for i in range(n)]
    tr = [(nm, 'root' if i == 0 else names[i - 1], mz.cell((ex, ey - 1.08 * (n - i) - 0.54)), master, 'trunk')
          for i, nm in enumerate(names)]
    out = []
    for nd in P['nodes']:
        if nd[1] == 'root':
            nd = (nd[0], names[-1], nd[2], nd[3], nd[4])
        out.append(nd)
        if nd[0] == 'root':
            out += tr
    P['nodes'] = out
    return names


def remove_entry_trunk(P):
    names = {n[0] for n in P['nodes'] if n[4] == 'trunk'}
    if not names:
        return
    last = [n[0] for n in P['nodes'] if n[4] == 'trunk'][-1]
    P['nodes'] = [(n[0], 'root' if n[1] == last else n[1], n[2], n[3], n[4]) for n in P['nodes'] if n[0] not in names]


def choose_entry_trunk(P, libs, r, c, wc, cal):
    """plan-computed trunk (12.8c + d1: deterministic, before the build).  cal = the core's own BUILT CTS insertion and
    the plan-model number of that same built slice (COORD RULING S81-CORE-LAT-R13: calibrate on the built CTS, not on
    the plan number): offset[c] = built[c] - plan[c]; for every (master, n) in TRUNK_MENU x 1..TRUNK_NMAX the predicted
    built latency = model(plan + trunk) + offset; pick min |TT - 250| + |FF - 202.5| (tie: fewer cells, smaller master)."""
    off = {k: float(cal["built_" + k]) - float(cal["plan_" + k]) for k in ("TT", "FF")}
    base, _ = M7.model_x(P, libs, r, c, wc)
    best = None
    for m in TRUNK_MENU:
        for n in range(1, TRUNK_NMAX + 1):
            add_entry_trunk(P, m, n)
            res, _ = M7.model_x(P, libs, r, c, wc)
            remove_entry_trunk(P)
            pred = {k: res[k]["mean"] + off[k] for k in ("TT", "FF")}
            err = abs(pred["TT"] - BAND["TT"][0]) + abs(pred["FF"] - BAND["FF"][0])
            key = (round(err, 1), n, TRUNK_MENU.index(m))
            if best is None or key < best[0]:
                best = (key, m, n, pred, {k: res[k]["mean"] for k in ("TT", "FF")})
    _, m, n, pred, mod = best
    add_entry_trunk(P, m, n)
    return dict(rule="12.8c fixed entry trunk, plan-computed (d1) from the core's own built CTS insertion (COORD RULING S81-CORE-LAT-R13)",
                master=m, stages=n, offset_ps={k: round(v, 2) for k, v in off.items()}, calibration=cal,
                model_no_trunk={k: base[k]["mean"] for k in ("TT", "FF")}, model_with_trunk=mod,
                predicted_built={k: round(v, 2) for k, v in pred.items()},
                predicted_band={k: ("IN" if abs(pred[k] - BAND[k][0]) <= BAND[k][1] else "OUT") for k in ("TT", "FF")},
                label="PLAN MODEL + one-build calibration, UNCHECKED until the trunk build is measured")


# ------------------------------------------------------------------ family template -> splits
def family_islands(fam):
    """Explicit family crossing anchors: complete two-column, two/three-row grid.

    Coordinates name planned centres, not native body origins. Actual maze and
    row-site displacements remain subject to the existing 2um conversion gate.
    Missing islands_xy keeps the historical auto topology unchanged.
    """
    if "islands_xy" not in fam:return None
    points=fam["islands_xy"]
    if not isinstance(points,list) or len(points) not in (4,6):
        raise SystemExit("islands_xy needs four or six explicit two-column anchors")
    try:
        if any(not isinstance(p,(list,tuple)) or len(p)!=2 or
               any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p) for p in points):
            raise ValueError()
        points=[tuple(map(float,p)) for p in points]
        xs=sorted({p[0] for p in points});ys=sorted({p[1] for p in points})
        if len(xs)!=2 or len(ys)!=len(points)//2 or set(points)!={(x,y) for x in xs for y in ys}:raise ValueError()
    except (TypeError,ValueError):
        raise SystemExit("islands_xy needs finite unique anchors on a complete two-column grid")
    return points


def explicit_island_sites(mz, entry, points, splits):
    """Pin level-two hubs to declared bays; never silently move across streets."""
    xs=sorted({p[0] for p in points});ys=sorted({p[1] for p in points})
    if list(splits[:2])!=[2,len(ys)]:
        raise SystemExit("islands_xy topology requires first splits 2,%d" % len(ys))
    if not xs[0]<entry[0]<xs[1]:raise SystemExit("islands_xy columns must straddle the clock entry")
    sites={};receipt=[]
    for col,x in enumerate(xs):
        for row,y in enumerate(ys):
            if not (mz.core[0]<=x<=mz.core[2] and mz.core[1]<=y<=mz.core[3]):
                raise SystemExit("islands_xy anchor outside core bounds: %r" % ((x,y),))
            cell=mz.cell((x,y));actual=mz.xy(cell);displacement=abs(actual[0]-x)+abs(actual[1]-y)
            if displacement>GATES['disp_um']+1e-9:
                raise SystemExit("islands_xy anchor cannot fit legal maze bay within 2um: %r -> %r" % ((x,y),actual))
            if cell in sites.values():raise SystemExit("islands_xy anchors collapse to the same legal maze site")
            sites[(col,row)]=cell
            receipt.append(dict(group=[col,row],requested_xy_um=[x,y],maze_xy_um=list(actual),
                                maze_displacement_um=round(displacement,6)))
    return sites,receipt


def splits_for(n, fam):
    """W/E x islands per side x leaf levels, sized from the family menu and sink count.
    Default topology is 2x2; explicit six-anchor families use 2x3.
    A calibrated re-plan (replan_structure) passes its menu candidate as fam['splits_override']."""
    islands=family_islands(fam)
    upper=[2,len(islands)//2] if islands is not None else [2,2]
    if fam.get("splits_override"):
        override=list(fam["splits_override"])
        if islands is not None and override[:2]!=upper:
            raise SystemExit("islands_xy contradicts splits_override topology")
        return override
    tgt = fam.get("leaf_target", 48); menu = fam.get("menu", [1, 2, 4, 8])
    want = max(1.0, n / (float(math.prod(upper)) * tgt)); best = None
    for a in menu:
        for b in menu:
            if a > b: continue
            v = (abs(math.log(a * b / want)), a + b)
            if best is None or v < best[0]: best = (v, (a, b))
    a, b = best[1]
    sp = upper + [x for x in (a, b) if x > 1]
    return sp if len(sp) > 2 else upper + [1]


_PLANS = {}   # plan name -> (P, libs, r, c, wire classes) of the last plan() call (refresh_after_d1)


def refresh_after_d1(rec0, rec):
    """S81-CORE-LAT-R20: after the R9 uf_phys3 d1 descent the plan carries NEW frozen masters, but the record kept the
    R7 NLDM numbers of the PRE-d1 masters -- the window/slew gates and the converter's model_qualification then judged
    a tree that is not the one being built (gunit_l2: gate R7 window 20.28/20.36 on pre-d1 masters vs 15.49/17.13 on the
    d1 masters it ships).  Re-evaluate the SAME R7 chain on the shipped masters; the pre-d1 numbers stay as info.
    Deterministic, plan-model only (12.8 d1), no measurement input."""
    P, libs, r, c, wc = _PLANS[rec0["name"]]
    fm = rec["frozen_masters"]
    miss = sorted(n[0] for n in P["nodes"] if n[0] not in fm)
    if miss:
        raise SystemExit("refresh_after_d1: d1 record lacks frozen masters for %s" % miss[:4])
    P["nodes"] = [(n[0], n[1], n[2], fm[n[0]], n[4]) for n in P["nodes"]]
    if sorted((n[0], n[3]) for n in P["nodes"]) != sorted((n[0], n[3]) for n in rec["nodes_xy"]):
        raise SystemExit("refresh_after_d1: d1 nodes_xy masters differ from frozen_masters")
    res, _ = M7.model_x(P, libs, r, c, wc)
    rec["model_pre_d1"] = {k: rec0[k] for k in ("TT", "FF")}
    calibrated = rec.get("d1_uf3", {}).get("prediction")
    if calibrated is not None:
        for corner in ("TT", "FF"):
            q = calibrated[corner]
            needed = {"mean", "window", "sink_min", "sink_max", "leaf_out_slew_max", "leaf_slew_in_max"}
            if needed - set(q) or q.get("model") != "uf_phys3 v1" or q.get("basis") != "GRT":
                raise SystemExit("refresh_after_d1: malformed calibrated prediction at " + corner)
        rec["model_r7_info"] = res
        rec["TT"], rec["FF"] = calibrated["TT"], calibrated["FF"]
        rec["model"] = "uf_phys3 v1 GRT, TT max-rise / FF min-rise-fall; SAME frozen masters and kernel as d1 (R21); R7 retained as info"
    else:
        rec["TT"], rec["FF"] = res["TT"], res["FF"]
        rec["model"] = rec0["model"] + "; R7 re-evaluated on the d1 (uf_phys3) masters (R20)"
    return rec


def plan(geo, fam, libtt, libff, name, trunk_cal=None):
    sinks = sum(1 for l in open(geo) if l.startswith("SINK"))
    macro_mode = bool(fam.get("macro_leaves"))
    if not macro_mode and fam.get("island_assignment", "auto") != "auto":
        raise SystemExit("island_assignment requires macro_leaves topology")
    if macro_mode:
        sinks += sum(1 for line in open(geo) if line.startswith("MACRO"))
    sp = splits_for(sinks, fam)
    M7.BUFS = list(ENV)
    if macro_mode:
        P = ungated_macro_htree(str(geo), sp[:-1], fam.get("smax", 70.0),
                                [list(k) for k in fam.get("keepout_um", [])], float(fam.get("leaf_target", 48)),
                                entry_node=bool(fam.get("entry_node_legal")), x_bands=fam.get("lv0_x_bands_um"),
                                islands=family_islands(fam), island_assignment=fam.get("island_assignment", "auto"))
        rea = None
    else:
        if fam.get("lv0_x_bands_um") is not None:
            raise SystemExit("lv0_x_bands_um needs macro_leaves (ungated_macro_htree) plans")
        anchors=family_islands(fam)
        if anchors is not None and len(anchors)!=4:
            raise SystemExit("six explicit islands currently require macro_leaves topology")
        kwargs={"islands":anchors} if anchors is not None else {}
        P = H.plan(str(geo), sp, fam.get("smax", 70.0), [list(k) for k in fam.get("keepout_um", [])], **kwargs)
        if anchors is not None:
            _,P['island_snap']=explicit_island_sites(P['mz'],P['entry'],anchors,sp)
        rea = reassign_nearest(P, int(fam.get("reassign_cap", 1.5) * max(len(v) for v in P["leafsinks"].values()))) if fam.get("reassign") else None
    if type(fam.get("leaf_actual_legal", False)) is not bool:
        raise SystemExit("leaf_actual_legal must be a boolean")
    split = split_long_leaves(P, fam.get("leaf_limit", 35.0), actual_legal=fam.get("leaf_actual_legal", False))
    stray = fix_keepout_strays(P, fam["keepout_stray"], fam.get("leaf_limit", 35.0), fam.get("smax", 70.0)) \
        if macro_mode and fam.get("keepout_stray") else None
    face_repair = reparent_obstructed_edges(P, fam.get("smax", 70.0)) \
        if macro_mode and fam.get("macro_face_reparent") else None
    kr, kc = map(float, fam.get("rc", "0.8,0.9").split(","))
    r = 0.5 * (1.80365e-2 + 1.89935e-2) * kr; c = 0.5 * (1.78475e-1 + 1.64264e-1) * kc
    cells = sorted(set(ENV + [H.REP, H.BIG]))
    libs = {"TT": H.lib_cells(libtt, cells), "FF": H.lib_cells(libff, cells)}
    M7.apply_masters(P, {"rep": "BUFx24_ASAP7_75t_R"})
    wc = {l: fam.get("wire", "std") for l in range(1, len(sp) + 2)}
    sized = M7.size_d1(P, libs, r, c, wc)
    face_balance = None
    if face_repair is not None and fam.get("macro_face_balance"):
        face_balance = reparent_obstructed_edges(P, fam.get("smax", 70.0),
            model=(libs, r, c, wc), edges={x['edge'] for x in face_repair if x.get('fixed')}, max_donors=4)
        # Existing canonical sizing on the final topology, never a stale load.
        sized = M7.size_d1(P, libs, r, c, wc)
    trunk = choose_entry_trunk(P, libs, r, c, wc, trunk_cal) if trunk_cal else None
    res, st = M7.model_x(P, libs, r, c, wc)
    _PLANS[name] = (P, libs, r, c, wc)
    par = {n[0]: n[1] for n in P["nodes"]}; depths = set()
    for n in P["nodes"]:
        if n[4] == "leaf":
            d = 1; u = n[0]
            while par[u]: u = par[u]; d += 1
            depths.add(d)
    mz = P["mz"]

    def corners(cs):
        pts = [mz.xy(x) for x in cs]; kp = [pts[0]]
        for i in range(1, len(pts) - 1):
            if (pts[i][0] - kp[-1][0]) * (pts[i + 1][1] - pts[i][1]) != (pts[i][1] - kp[-1][1]) * (pts[i + 1][0] - pts[i][0]): kp.append(pts[i])
        return kp + [pts[-1]]
    spread = M8.leaf_spread(P)
    islands = sorted({mz.xy(P["site"][g]) for g in P["site"] if len(g) == 2})
    rec = dict(name=name, family=fam["name"], splits=",".join(map(str, sp)), smax=fam.get("smax", 70.0), wire=fam.get("wire", "std"),
               sinks=sinks, split_leaves=split, reassign=rea, entry_trunk=trunk, level_len_um=[round(x, 2) for x in P["T"]],
               repeaters_per_edge=[k - 1 for k in P["K"]], stages=sorted(depths), n_cells=len(P["nodes"]),
               sized_masters={"%s:%s" % k: v for k, v in sorted(sized.items())},
               frozen_masters={n[0]: n[3] for n in P["nodes"]}, TT=res["TT"], FF=res["FF"],
               entry=mz.xy(P["ent"]), islands_xy=islands, core=list(mz.core), maze_g_um=mz.G,
               nodes_xy=[(n[0], n[1], mz.xy(n[2]), n[3], n[4]) for n in P["nodes"]],
               wire_paths=[dict(level=w["level"], edge=w["edge"], segs=[round(x, 2) for x in w["segs"]],
                                paths=[corners(cs) for cs in w["cells"]]) for w in P["wires"]],
               leaf_members={u: len(v) for u, v in P["leafsinks"].items()},
               leaf_sinks={u: ["%s/%s" % (s[2], s[3]) for s in v] for u, v in P["leafsinks"].items()},
               leaf_spread_um=spread, leaf_mst_um=M8.leaf_mst(P),
               leaf_spread_max=dict(all=max(spread.values()), main=max(spread.values()), strip=0.0,
                                    n_gt_40=sum(v > 40 for v in spread.values()), top=sorted(spread.items(), key=lambda kv: -kv[1])[:8]),
               model="R7 NLDM+Elmore chain + 12.8 d1 (core_family_slice); PLAN MODEL, UNCHECKED")
    if fam.get("islands_xy") is not None:
        rec["islands_requested_xy"]=[list(p) for p in family_islands(fam)]
        rec["island_snap"]=P["island_snap"]
        if fam.get("island_assignment", "auto") != "auto":
            rec["island_assignment"]=fam["island_assignment"]
            rec["island_loads"]=P["island_loads"]
    if fam.get("leaf_actual_legal"):
        rec["leaf_actual_legal"]=True
    if fam.get("keepout_um"):
        rec["macro_keepout_um"] = [list(k) for k in fam["keepout_um"]]
    if macro_mode:
        rec["macro_clock_model"] = "separate same-stage macro leaves, physical pins and exact TT/FF liberty clock caps"
        rec["sinks"] = sum(len(v) for v in P["leafsinks"].values())
        rec["sinkcap"] = P["sinkcap"]
        rec["macro_leaves"] = sorted(u for u, v in P["leafsinks"].items() if all(q[4].startswith("MACRO:") for q in v))
        if stray is not None:
            rec["keepout_stray"] = stray
        if face_repair is not None:
            rec["macro_face_reparent"] = face_repair
        if face_balance is not None:
            rec["macro_face_balance"] = face_balance
    return rec


# ------------------------------------------------------------------ symmetric lattice + one master per level (QC-A0-KITS-8)
class _LatticeMaze:
    """identity 'maze' for lattice plans: a cell IS its (x, y) coordinate in um (legal sites come from the converter)."""
    G = 1.0

    def __init__(self, core):
        self.core = core

    def xy(self, p):
        return (round(p[0], 3), round(p[1], 3))


def lattice_levelkey(n):
    """level key of a plan node for the one-master-per-level rule: (leaf?, tree level, position in edge)."""
    if n[4] in ("entry", "trunk"):
        return ("root",)
    return (1 if n[4] == "leaf" else 0, M7.lvl_of(n[0]), 0)


def lattice_build(sinks, entry, levels, master="BUFx16f_ASAP7_75t_R", root="BUFx24_ASAP7_75t_R", pitch=1.08):
    """SYMMETRIC plan geometry (balance by geometry, not by size compensation): level l = a stack of len(levels[l])
    branch buffers at every hub (pitch um apart, centred on the hub), branch i drives ONE straight L leg of
    |dx_i|+|dy_i| to the tip hub + levels[l][i]; every leg of a level has the SAME Manhattan length (refused otherwise).
    Last level tips = leaf drivers; every sink goes to the NEAREST leaf (Manhattan, ties by name); a leaf with no sink is
    removed with its exclusive branch.  Returns P in the core_infra_htree form (land/wires) for M7.model_x."""
    for li, offs in enumerate(levels):
        ls = {round(abs(o[0]) + abs(o[1]), 6) for o in offs}
        if len(ls) != 1:
            raise SystemExit("lattice level %d: legs differ in length %s (symmetric geometry needs one length per level)" % (li, sorted(ls)))
    nodes = [("root", None, tuple(entry), root, "entry")]; land = {}; wires = []; hubs = [("", tuple(entry), "root", 0.0)]
    for li, offs in enumerate(levels):
        nh = []
        for dg, hp, drv, seg in hubs:
            k = len(offs)
            for i, o in enumerate(offs):
                nm = "T" + dg + str(i)
                nodes.append((nm + "_br", drv, (hp[0], hp[1] + (i - (k - 1) / 2.0) * pitch), master, "branch"))
                nh.append((dg + str(i), (hp[0] + o[0], hp[1] + o[1]), nm + "_br", abs(o[0]) + abs(o[1])))
            land[drv] = (seg, "H" + (dg or "R")); wires.append(dict(level=li, edge="H" + (dg or "R"), segs=[seg], hub=hp))
        hubs = nh
    pts = {}
    for dg, tp, drv, seg in hubs:
        nodes.append(("T" + dg, drv, tp, master, "leaf")); pts["T" + dg] = tp
        land[drv] = (seg, "L" + dg); wires.append(dict(level=len(levels), edge="L" + dg, segs=[seg], hub=tp))
    names = sorted(pts); leafsinks = {u: [] for u in names}
    for s in sinks:
        u = min(names, key=lambda u: (abs(s[0] - pts[u][0]) + abs(s[1] - pts[u][1]), u)); leafsinks[u].append(s)
    empty = {u for u in names if not leafsinks[u]}
    if empty:
        brs = {n[1] for n in nodes if n[0] in empty}
        nodes = [n for n in nodes if n[0] not in empty and n[0] not in brs]
        for b in brs:
            land.pop(b, None)
        wires = [w for w in wires if not (w["edge"].startswith("L") and "T" + w["edge"][1:] in empty)]
        leafsinks = {u: v for u, v in leafsinks.items() if u not in empty}
    for w in wires:
        w["cells"] = [[w["hub"]]]
    return dict(mz=None, nodes=nodes, land=land, wires=wires, leafsinks=leafsinks, empty=sorted(empty))


def lattice_masters(P, libs, r, c, slew_max=60.0, passes=3):
    """ONE master per level (12.8 d1 by intent, COORD 21:07 QC-A0-KITS-7 ruling): deterministic coordinate descent over
    the BUFx8..x24 envelope, one level key at a time, minimising TT window + FF window under TT leaf slew <= slew_max;
    plan model only (no measurement).  Returns {level key: master}."""
    keys = sorted({lattice_levelkey(n) for n in P["nodes"]}, key=str)
    cur = {k: "BUFx16f_ASAP7_75t_R" for k in keys}

    def score(m):
        P["nodes"] = [(n[0], n[1], n[2], m[lattice_levelkey(n)], n[4]) for n in P["nodes"]]
        res, _ = M7.model_x(P, libs, r, c, {})
        bad = res["TT"]["leaf_out_slew_max"] > slew_max or res["TT"]["leaf_slew_in_max"] > GATES["slew_ps"]
        return res["TT"]["window"] + res["FF"]["window"] + (1e3 if bad else 0.0)
    best = score(cur)
    for _ in range(passes):
        for k in keys:
            for m in ENV:
                t = dict(cur); t[k] = m; v = score(t)
                if v < best - 1e-6:
                    best, cur = v, t
    score(cur)
    return cur


def plan_lattice(geo, fam, libtt, libff, name):
    """family key 'lattice' (opt-in; absent = plan() unchanged): {"levels": [[[dx, dy], ...], ...]} tip offsets per level
    from the core clock entry.  Geometry from the plan lattice (equal leg length per level), ONE master per level
    (lattice_masters), no d1 per-driver sizing, no uf_phys3 descent.  PLAN MODEL, UNCHECKED until routed arrivals."""
    L = [l.split() for l in open(geo)]
    sinks = [(float(f[1]), float(f[2]), f[4], f[5]) for f in L if f[:1] == ["SINK"]]
    ent = next((float(f[2]), float(f[3])) for f in L if f[:2] == ["PIN", "ck"])
    core = next([float(v) for v in f[1:5]] for f in L if f[:1] == ["CORE"])
    levels = [[tuple(map(float, o)) for o in lv] for lv in fam["lattice"]["levels"]]
    P = lattice_build(sinks, ent, levels)
    P["mz"] = _LatticeMaze(core)
    cells = sorted(set(ENV + [H.REP, H.BIG]))
    libs = {"TT": H.lib_cells(libtt, cells), "FF": H.lib_cells(libff, cells)}
    kr, kc = map(float, fam.get("rc", "0.8,0.9").split(","))
    r = 0.5 * (1.80365e-2 + 1.89935e-2) * kr; c = 0.5 * (1.78475e-1 + 1.64264e-1) * kc
    lm = lattice_masters(P, libs, r, c)
    res, _ = M7.model_x(P, libs, r, c, {})
    _PLANS[name] = (P, libs, r, c, {})
    par = {n[0]: n[1] for n in P["nodes"]}; pos = {n[0]: n[2] for n in P["nodes"]}; depths = set()
    for n in P["nodes"]:
        if n[4] == "leaf":
            d = 1; u = n[0]
            while par[u]: u = par[u]; d += 1
            depths.add(d)
    legs = []
    for n in P["nodes"]:          # one leg per driver -> its landing hub: straight L (x first, then y)
        if n[0] in P["land"] and n[4] != "entry":
            seg, hub = P["land"][n[0]]; hp = next(w["hub"] for w in P["wires"] if w["edge"] == hub); a = pos[n[0]]
            legs.append(dict(level=M7.lvl_of(n[0]), edge=n[0], segs=[round(abs(hp[0] - a[0]) + abs(hp[1] - a[1]), 2)],
                             paths=[[list(a), [hp[0], a[1]], list(hp)]]))
    spread = {u: round(max(abs(s[0] - pos[u][0]) + abs(s[1] - pos[u][1]) for s in v), 2) for u, v in P["leafsinks"].items()}
    cnt = sorted(len(v) for v in P["leafsinks"].values())
    rec = dict(name=name, family=fam["name"], splits="lattice " + ",".join(str(len(l)) for l in levels), smax=None, wire=fam.get("wire", "std"),
               sinks=len(sinks), split_leaves=[], reassign=None, entry_trunk=None,
               level_len_um=[round(abs(l[0][0]) + abs(l[0][1]), 3) for l in levels], repeaters_per_edge=[0] * len(levels),
               stages=sorted(depths), n_cells=len(P["nodes"]),
               level_masters={"/".join(map(str, k)): v for k, v in sorted(lm.items(), key=lambda kv: str(kv[0]))},
               sized_masters={"%s:%s" % k: v for k, v in sorted(collections.Counter((n[4], n[3]) for n in P["nodes"]).items())},
               frozen_masters={n[0]: n[3] for n in P["nodes"]}, TT=res["TT"], FF=res["FF"],
               entry=list(ent), islands_xy=[], core=core, maze_g_um=None,
               nodes_xy=[(n[0], n[1], [round(n[2][0], 3), round(n[2][1], 3)], n[3], n[4]) for n in P["nodes"]],
               wire_paths=legs, empty_leaves_removed=P["empty"],
               leaf_members={u: len(v) for u, v in P["leafsinks"].items()},
               leaf_members_stats=dict(min=cnt[0], median=cnt[len(cnt) // 2], max=cnt[-1]),
               leaf_sinks={u: ["%s/%s" % (s[2], s[3]) for s in v] for u, v in P["leafsinks"].items()},
               leaf_spread_um=spread, leaf_mst_um=None,
               leaf_spread_max=dict(all=max(spread.values()), main=max(spread.values()), strip=0.0,
                                    n_gt_40=sum(v > GATES["leaf_spread_um"] for v in spread.values()),
                                    top=sorted(spread.items(), key=lambda kv: -kv[1])[:8]),
               plan_rule="symmetric lattice (equal leg length per level) + ONE master per level; no d1 per-driver sizing, "
                         "no uf_phys3 descent (QC-A0-KITS-8, COORD 21:07)",
               model="R7 NLDM+Elmore chain, lattice geometry, one master per level (core_family_slice lattice); PLAN MODEL, UNCHECKED")
    return rec


# ------------------------------------------------------------------ calibrated structural re-plan (R16)
WIRE_MENU = ("std", "ndr2w")


def _menu_splits(fam):
    menu = fam.get("menu", [1, 2, 4, 8]); out = []
    for a in menu:
        for b in menu:
            if a <= b:
                sp = [2, 2] + [x for x in (a, b) if x > 1]
                sp = sp if len(sp) > 2 else [2, 2, 1]
                if sp not in out:
                    out.append(sp)
    return out


def _replan_one(args):
    geo, fam, libtt, libff, name, off = args
    try:
        rec = plan(geo, fam, libtt, libff, name)
    except ValueError as e:                       # the H planner refuses some menu shapes (shared wire): not a candidate
        return dict(splits=fam["splits_override"], wire=fam["wire"], error=str(e)[:120]), None
    pred = {k: round(rec[k]["mean"] + off[k], 2) for k in ("TT", "FF")}
    gates = []
    for c in ("TT", "FF"):
        if rec[c]["window"] > GATES["window_ps"]: gates.append("%s window %.1f" % (c, rec[c]["window"]))
        if rec[c]["leaf_out_slew_max"] > GATES["slew_ps"]: gates.append("%s slew %.1f" % (c, rec[c]["leaf_out_slew_max"]))
    if rec["leaf_spread_max"]["n_gt_40"]: gates.append("leaf spread")
    if len(rec["stages"]) != 1: gates.append("stages %s" % rec["stages"])
    err = abs(pred["TT"] - BAND["TT"][0]) + abs(pred["FF"] - BAND["FF"][0])
    row = dict(splits=fam["splits_override"], wire=fam["wire"], stages=rec["stages"], cells=rec["n_cells"],
               plan={k: rec[k]["mean"] for k in ("TT", "FF")}, window={k: rec[k]["window"] for k in ("TT", "FF")},
               predicted_built=pred, band={k: ("IN" if abs(pred[k] - BAND[k][0]) <= BAND[k][1] else "OUT") for k in pred},
               gate_fails=gates, err=round(err, 2))
    return row, rec


def replan_structure(geo, fam, libtt, libff, name, cal, jobs=8):
    """12.3 calibrated re-plan for a core whose BUILT CTS insertion is out of band HIGH (a trunk only lengthens).
    offset[c] = built[c] - plan[c] of the core's own built slice (COORD RULING S81-CORE-LAT-R13: calibrate on the built CTS);
    every family-menu structure (leaf levels from fam menu) x wire class (std / 2W NDR) is planned with the same
    deterministic planner + d1 sizing; candidates that fail a plan gate (window 20, slew 80, spread 40, equal stages) are
    out; pick min |pred TT - 250| + |pred FF - 202.5| (tie: fewer cells, std wire).  No per-core hand tuning: the rule and
    menu are the family's; the offset is applied unchanged to NDR candidates (NDR halves wire R, so the std offset is the
    conservative high side).  PLAN MODEL + one-build calibration, UNCHECKED until the re-planned build is measured."""
    from concurrent.futures import ProcessPoolExecutor
    off = {k: float(cal["built_" + k]) - float(cal["plan_" + k]) for k in ("TT", "FF")}
    cands = [dict(fam, splits_override=sp, wire=w) for w in WIRE_MENU for sp in _menu_splits(fam)]
    args = [(str(geo), f, libtt, libff, name, off) for f in cands]
    if jobs <= 1:
        res = [_replan_one(x) for x in args]
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            res = list(ex.map(_replan_one, args))
    ok = [(r, rec, f) for (r, rec), f in zip(res, cands) if rec is not None and not r["gate_fails"]]
    if not ok:
        raise SystemExit("replan: no family-menu structure passes the plan gates")
    r, rec, f = min(ok, key=lambda t: (t[0]["err"], t[0]["cells"], WIRE_MENU.index(t[0]["wire"])))
    rec["calibrated_replan"] = dict(rule=replan_structure.__doc__.split(".")[0], offset_ps={k: round(v, 2) for k, v in off.items()},
                                    calibration=cal, chosen=r, candidates=[x for x, _ in res],
                                    label="PLAN MODEL + one-build calibration, UNCHECKED until the re-planned build is measured")
    return rec, f


# ------------------------------------------------------------------ checks
def checks(rec, slice_, geo, window_policy="gate"):
    out = {}; fails = []
    macro_mode = bool(rec.get("macro_clock_model"))
    # (1) every leg <= 1.10 x Manhattan of its own endpoints
    worst = 0.0; nover = 0; nleg = 0
    for w in rec["wire_paths"]:
        for seg, pts in zip(w["segs"], w["paths"]):
            a, b = pts[0], pts[-1]; man = abs(a[0] - b[0]) + abs(a[1] - b[1]); nleg += 1
            if man > 1.0:
                q = seg / man; worst = max(worst, q); nover += q > GATES["leg_detour_max"] + 1e-9
    out["legs"] = dict(n=nleg, over_1p10=nover, worst_ratio=round(worst, 3))
    if nover: fails.append("legs over 1.10x Manhattan: %d" % nover)
    sp = rec["leaf_spread_um"]; out["leaf_spread"] = dict(max=max(sp.values()), n_gt_40=sum(v > GATES["leaf_spread_um"] for v in sp.values()))
    if out["leaf_spread"]["n_gt_40"]: fails.append("leaves over 40 um spread: %d" % out["leaf_spread"]["n_gt_40"])
    cen = {"%s/%s" % (l.split()[4], l.split()[5]) for l in open(geo) if l.startswith("SINK")}
    if macro_mode:
        cen |= {"%s/%s" % (line.split()[1], line.split()[7]) for line in open(geo) if line.startswith("MACRO")}
    got = collections.Counter(s for v in rec["leaf_sinks"].values() for s in v)
    out["sinks"] = dict(census=len(cen), planned=len(got), missing=len(cen - set(got)), dup=sum(1 for v in got.values() if v > 1),
                        extra=len(set(got) - cen))
    if out["sinks"]["missing"] or out["sinks"]["dup"] or out["sinks"]["extra"]: fails.append("sink coverage %s" % out["sinks"])
    out["stages"] = rec["stages"]
    if len(rec["stages"]) != 1: fails.append("unequal stage count %s" % rec["stages"])
    for c in ("TT", "FF"):
        m, tol = BAND[c]; x = rec[c]
        out[c] = dict(mean=x["mean"], window=x["window"], leaf_out_slew_max=x["leaf_out_slew_max"],
                      band_info="IN" if abs(x["mean"] - m) <= tol else "OUT")
        if x["window"] > GATES["window_ps"]:
            if window_policy == "info":   # 12.3a: plan window = design target; routed related-pair gate decides (COORD 10-31)
                out[c]["window_info"] = "OVER %.1f > 20 (INFO, --window-policy info)" % x["window"]
            else:
                fails.append("%s window %.1f > 20" % (c, x["window"]))
        if x["leaf_out_slew_max"] > GATES["slew_ps"]: fails.append("%s leaf slew %.1f > 80" % (c, x["leaf_out_slew_max"]))
    if rec.get("entry_trunk"):
        tk = rec["entry_trunk"]
        out["entry_trunk"] = dict(master=tk["master"], stages=tk["stages"], predicted_built=tk["predicted_built"],
                                  band_info=tk["predicted_band"], offset_ps=tk["offset_ps"])
    if slice_ is not None:
        disp = slice_["plan_conversion"]["displacement_um"]["max"]
        out["disp_max_um"] = disp
        out["pg_clearance"] = slice_["plan_conversion"].get("trunk_pg_clearance", {}).get("verdict")
        if disp > GATES["disp_um"]: fails.append("driver displacement %.2f > 2" % disp)
        if out["pg_clearance"] not in (None, "PASS"): fails.append("trunk PG clearance %s" % out["pg_clearance"])
    nmac = sum(1 for l in open(geo) if l.startswith("MACRO"))
    out["macro_clock_pins"] = nmac
    if macro_mode:
        out["macro_leaves"] = len(rec.get("macro_leaves", []))
        fails.extend(macro_leaf_errors(rec, geo))
    elif nmac: fails.append("%d macro clock pins: family template has no macro (early-tap, v5.0) leaf yet" % nmac)
    out["verdict"] = "FAIL" if fails else "PASS"; out["fails"] = fails
    out["scope"] = "automated geometry gates on the PLAN (GEOM-REVIEW-10 form); latency numbers PLAN MODEL, UNCHECKED"
    return out


# ------------------------------------------------------------------ render
def render(geo, rec, slice_, out_png):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    S = [l.split() for l in open(geo) if l.startswith("SINK")]
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter([float(s[1]) for s in S], [float(s[2]) for s in S], s=0.3, c="0.72", label="%d placed sinks" % len(S))
    col = {1: "tab:red", 2: "tab:blue", 3: "tab:green", 4: "tab:orange", 5: "tab:purple"}
    lv = collections.defaultdict(list)
    for w in rec["wire_paths"]:
        lv[w["level"]].append(sum(w["segs"]))
        for pts in w["paths"]:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], c=col.get(w["level"], "k"), lw=1.6 if w["level"] <= 2 else 0.8)
    for l in sorted(lv):
        ax.plot([], [], c=col.get(l, "k"), lw=2, label="L%d legs %d: %.1f-%.1f um" % (l, len(lv[l]), min(lv[l]), max(lv[l])))
    pos = {n[0]: n[2] for n in rec["nodes_xy"]}
    if slice_:
        for n in slice_["core_tree"]["nodes"]:
            pos[n["name"].split("mp_ck_", 1)[-1]] = n["xy_um"]
    for kind, mk, c in (("branch", "s", "k"), ("rep", "D", "tab:brown"), ("leaf", "o", "tab:cyan")):
        ns = [n for n in rec["nodes_xy"] if n[4] == kind and n[0] in pos]
        ax.scatter([pos[n[0]][0] for n in ns], [pos[n[0]][1] for n in ns], s=8, marker=mk, c=c, label="%s drivers %d" % (kind, len(ns)), zorder=3)
    ix = rec["islands_xy"]
    ax.scatter([p[0] for p in ix], [p[1] for p in ix], s=160, facecolors="none", edgecolors="magenta", lw=2, label="in-core islands %d" % len(ix), zorder=4)
    ax.plot(*rec["entry"], "k*", ms=16, label="sink-centroid entry" if Path(geo).name == "geo_entry.txt" else "centre entry (12.8a)", zorder=5)
    cr = rec["core"]; ax.set_xlim(cr[0] - 3, cr[2] + 3); ax.set_ylim(cr[1] - 3, cr[3] + 3); ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
    t, f = rec["TT"], rec["FF"]
    ax.set_title("%s [%s] splits %s, %s stages, leaf spread max %.1f um\nPLAN MODEL TT %.1f w%.1f / FF %.1f w%.1f (UNCHECKED)"
                 % (rec["name"], rec["family"], rec["splits"], rec["stages"], rec["leaf_spread_max"]["all"], t["mean"], t["window"], f["mean"], f["window"]), fontsize=9)
    fig.savefig(out_png, dpi=110); plt.close(fig)


# ------------------------------------------------------------------ entry (12.16e by intent, COORD dfd33a253)
ENTRY_MODES = ("centre", "sink_centroid")
MACRO_KEEPOUT_HALO_UM = 2.2     # = core_infra_htree.Maze macro halo


def macro_keepouts(sites, halo=MACRO_KEEPOUT_HALO_UM):
    """hard-macro rects of the kit floorplan (sites.txt FIXED lines taller than one row = blocks, not tap/endcap cells),
    grown by the planner's macro halo.  The census (core_family_geo.tcl) writes MACRO lines only for blocks whose clock
    pin is ON the core clock net, so a block clocked through an ICG (S81 rom_elem_q _gb: 4 ot_rom_4096x274_m8, clk via
    u_cg_r*.gclk) is invisible to the maze: the plan put branch drivers inside a ROM (mp_ck_T00_br at (71.28,152.82),
    26 um from the nearest legal row site) and the converter refused."""
    L = Path(sites).read_text().splitlines(); sh = None; out = []
    for l in L:
        f = l.split()
        if f[:1] == ["ROW0"]:
            sh = float(f[6])
    if sh is None:
        raise SystemExit("macro_keepout: %s has no ROW0 line" % sites)
    for l in L:
        f = l.split()
        if f[:1] == ["FIXED"]:
            x0, y0, x1, y1 = map(float, f[3:7])
            if y1 - y0 > 1.5 * sh:
                out.append([round(x0 - halo, 4), round(y0 - halo, 4), round(x1 + halo, 4), round(y1 + halo, 4)])
    return sorted(out)


def keepout_mode(fam, core):
    """family 'macro_keepout': absent/false = no node keep-out (unchanged); true for every member, or {member: bool}.
    true = every hard macro of the member's floorplan is a NODE keep-out for the plan (no driver/repeater/branch site
    inside macro + halo); wires may still pass over it (the plan's wire layers sit above the macro OBS)."""
    k = fam.get("macro_keepout", False)
    return bool(k.get(core, False)) if isinstance(k, dict) else bool(k)



def entry_mode(fam, core):
    """family 'entry': absent = 'centre' (12.8a outline centre from the census, unchanged); a mode string for every
    member, or {member: mode}.  'sink_centroid' = the core clock entry at the mean of the placed clock sinks (COORD
    dfd33a253: bf_col sinks hug the E face, a centre entry gives 168-220 um L1 legs and a 58 ps window)."""
    e = fam.get("entry", "centre")
    m = e.get(core, "centre") if isinstance(e, dict) else e
    if m not in ENTRY_MODES:
        raise SystemExit("family %s: entry %r for %s: one of %s" % (fam.get("name"), m, core, ENTRY_MODES))
    return m


def entry_geo(geo, mode):
    """the census geo for the chosen entry: 'centre' = geo.txt itself (byte-identical); 'sink_centroid' = geo_entry.txt,
    geo.txt with its 'PIN ck' line moved to the sink centroid (H.plan snaps it to the nearest legal maze cell)."""
    if mode == "centre":
        return geo
    L = geo.read_text().splitlines()
    S = [l.split() for l in L if l.split()[:1] == ["SINK"]]
    if not S:
        raise SystemExit("entry sink_centroid: no SINK lines in %s" % geo)
    cx = sum(float(f[1]) for f in S) / len(S); cy = sum(float(f[2]) for f in S) / len(S)
    n = sum(1 for l in L if l.split()[:2] == ["PIN", "ck"])
    if n != 1:
        raise SystemExit("entry sink_centroid: %d 'PIN ck' lines in %s" % (n, geo))
    out = geo.parent / "geo_entry.txt"
    out.write_text("\n".join("PIN ck %.3f %.3f" % (cx, cy) if l.split()[:2] == ["PIN", "ck"] else l for l in L) + "\n")
    return out




MACRO_LIB = REPO / "physical" / "asap7_memory_macros_v2"


def macro_clk_cap(master, pin):
    """{TT, FF} clock pin capacitance (fF) of a hard macro from its repo liberty (fail-closed)."""
    out = {}
    for c in ("TT", "FF"):
        p = MACRO_LIB / master / ("%s_%s.lib" % (master, c.lower()))
        if not p.is_file():
            raise SystemExit("macro_clk_cap: no liberty %s" % p)
        t = p.read_text(); i = t.find("pin (%s)" % pin)
        if i < 0:
            raise SystemExit("macro_clk_cap: %s has no pin %s" % (p, pin))
        out[c] = float(re.search(r"\bcapacitance : ([\d.]+)", t[i:i + 2000]).group(1))
    return out


def read_macro_geo(geo):
    core = entry = None
    sinks, macros = [], []
    for line in open(geo):
        f = line.split()
        if f[:1] == ["GATE"] or any(q.startswith("gate=") for q in f):
            raise SystemExit("macro_leaves does not accept gated sinks; use icg_copies")
        if f[:1] == ["CORE"]: core = tuple(map(float, f[1:5]))
        if f[:2] == ["PIN", "ck"]: entry = tuple(map(float, f[2:4]))
        if f[:1] == ["SINK"]: sinks.append((float(f[1]), float(f[2]), f[4], f[5], f[3]))
        if f[:1] == ["MACRO"]:
            macros.append((f[1], tuple(map(float, f[3:7])), tuple(map(float, f[8:10]))))
            sinks.append((float(f[8]), float(f[9]), f[1], f[7], "MACRO:" + f[2]))
    if core is None or entry is None: raise SystemExit("macro_leaves requires CORE and PIN ck")
    return core, entry, sinks, macros


def lv0_x_bands(pts, k, cuts):
    """opt-in family lv0_x_bands_um (see ungated_macro_htree): geometric first-level partition, fail closed."""
    cuts = [float(v) for v in cuts]
    if not cuts or cuts != sorted(cuts) or len(set(cuts)) != len(cuts):
        raise SystemExit("lv0_x_bands_um must be a strictly increasing non-empty list, got %r" % (cuts,))
    if k != len(cuts) + 1:
        raise SystemExit("lv0_x_bands_um: %d cuts need splits[0] == %d (splits_override), got %d" % (len(cuts), len(cuts) + 1, k))
    lo = [-math.inf] + cuts; hi = cuts + [math.inf]
    parts = [[p for p in pts if a <= p[0] < b] for a, b in zip(lo, hi)]
    empty = [i for i, q in enumerate(parts) if not q]
    if empty:
        raise SystemExit("lv0_x_bands_um: empty band(s) %s for cuts %s" % (empty, cuts))
    return parts


def nearest_island_subtrees(groups, site, fixed_islands, mz):
    """Reparent whole level-three subtrees to nearest declared bay, no level/cycle added.

    Loads may differ per bay; the existing joint NLDM model sizes the resulting
    real fanout. Equal eight-per-bay reassignment retains long forced reaches.
    All sink groups and descendant geometry stay intact.
    """
    upper=sorted(g for g in groups if len(g)==3)
    if not upper:raise SystemExit("nearest_subtree requires a level-three subtree below every island")
    bybay={g:[] for g in fixed_islands}
    for g in upper:
        point=mz.xy(site[g])
        bay=min(bybay,key=lambda b:(abs(point[0]-mz.xy(fixed_islands[b])[0])+abs(point[1]-mz.xy(fixed_islands[b])[1]),b))
        bybay[bay].append(g)
    if any(not gs for gs in bybay.values()):raise SystemExit("nearest_subtree leaves a declared island empty")
    if max(map(len,bybay.values()))>len(NAME_POOL):raise SystemExit("nearest_subtree exceeds geometric name capacity")
    rename={old:bay+(i,) for bay,gs in sorted(bybay.items()) for i,old in enumerate(sorted(gs))}
    new={():groups[()]};positions={g:c for g,c in site.items() if len(g)<3}
    for bay,children in sorted(bybay.items()):
        new[bay]=[sink for g in children for sink in groups[g]]
    for col in sorted({b[0] for b in bybay}):
        new[(col,)]=[sink for bay in sorted(bybay) if bay[0]==col for sink in new[bay]]
    for g,sinks in groups.items():
        if len(g)<3:continue
        key=rename[g[:3]]+g[3:];new[key]=sinks;positions[key]=site[g]
    loads=[dict(group=list(bay),xy_um=list(mz.xy(fixed_islands[bay])),
                subtree_fanout=len(children),sinks=len(new[bay]),
                flop_sinks=sum(not s[4].startswith("MACRO:") for s in new[bay]),
                macro_sinks=sum(s[4].startswith("MACRO:") for s in new[bay]))
           for bay,children in sorted(bybay.items())]
    return new,positions,loads


def ungated_macro_htree(geo, upper, smax, keepout, leaf_target=48, entry_node=False, x_bands=None, islands=None, island_assignment="auto"):
    """Same-depth separate macro leaves on actual geometry, sized with actual clock pin loads.
    x_bands (HBM-CORES-KITS-25 opt-in family "lv0_x_bands_um": [x1, x2, ...]; absent = unchanged count-median W/E split):
    the first level splits the sinks into the GEOMETRIC x bands (-inf,x1),[x1,x2),...,[xn,inf) instead of equal counts,
    so a far, sparse strip (EP hfd_ep_static W/E strips) gets its own subtree rooted inside it rather than a branch
    fed from the dense centre; upper[0] must equal len(x_bands)+1 and every band must hold a sink (fail closed)."""
    if island_assignment not in ("auto", "nearest_subtree"):
        raise SystemExit("unknown island_assignment %r" % island_assignment)
    if island_assignment != "auto" and islands is None:
        raise SystemExit("island_assignment requires explicit islands_xy")
    core, entry, sinks, macros = read_macro_geo(geo)
    # entry_node (DIE-S81-30 opt-in family "entry_node_legal"): the root driver snaps to the nearest NODE-legal site
    # (outside the macro keep-outs) instead of the nearest wire-legal one; default unchanged
    mz = H.Maze(core, macros, keepout=keepout); ent = mz.cell(entry, node=bool(entry_node))
    fixed_islands={};island_snap=[]
    if islands is not None:
        if x_bands is not None:raise SystemExit("islands_xy cannot combine with lv0_x_bands_um")
        fixed_islands,island_snap=explicit_island_sites(mz,entry,islands,upper)
    name = lambda g: "T" + "".join(NAME_POOL[i] for i in g)
    groups = {(): sinks}
    for lv, k in enumerate(upper):
        for key in sorted(g for g in groups if len(g) == lv):
            pts = groups[key]
            if lv == 0 and x_bands is not None:
                parts = lv0_x_bands(pts, k, x_bands)
            elif lv == 0 and k == 2:
                srt = sorted(pts, key=lambda p: (p[0], p[1])); h = len(srt) // 2; parts = [srt[:h], srt[h:]]
            else:
                parts = H.split(pts, k, axis=(1 if lv == 1 else None))
            for i, g in enumerate(parts):
                groups[key + (i,)] = g
    nu = len(upper)
    if islands is not None and any(not groups.get(key) for key in fixed_islands):
        raise SystemExit("islands_xy topology has an empty level-two bay")
    key_of = lambda q: "%s/%s" % (q[2], q[3])
    for key in sorted(g for g in groups if len(g) == nu):
        pts = groups[key]
        mac = [q for q in pts if q[4].startswith("MACRO:")]
        fl = [q for q in pts if not q[4].startswith("MACRO:")]
        n = max(1, int(round(len(fl) / float(leaf_target)))) if fl else 0
        parts = [[q] for q in mac] + ((H.split(fl, n) if n > 1 else [fl]) if fl else [])
        if len(parts) > len(NAME_POOL): raise SystemExit("macro_leaves exceeds geometric leaf name capacity")
        for i, part in enumerate(parts): groups[key + (i,)] = part
    depth = nu + 1
    leaves = sorted(g for g in groups if len(g) == depth)
    site = {}
    for g in leaves:
        pts = groups[g]; site[g] = mz.cell((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    kids = collections.defaultdict(list)
    for g in groups:
        if g:
            kids[g[:-1]].append(g)
    for lv in range(depth - 1, 0, -1):
        for g in sorted(x for x in groups if len(x) == lv):
            if g in fixed_islands:
                site[g]=fixed_islands[g];continue
            ch = [site[c] for c in sorted(kids[g])]
            cx = round(sum(c[0] for c in ch) / len(ch)); cy = round(sum(c[1] for c in ch) / len(ch))
            site[g] = H.minimax_site(mz, ch, (cx, cy))
    island_loads=[]
    if island_assignment == "nearest_subtree":
        groups,site,island_loads=nearest_island_subtrees(groups,site,fixed_islands,mz)
        kids=collections.defaultdict(list)
        for g in groups:
            if g:kids[g[:-1]].append(g)
        leaves=sorted(g for g in groups if len(g)==depth)
    site[()] = ent
    T, K = [], []
    for lv in range(depth):
        L = [mz.md(site[g[:-1]], site[g]) for g in groups if len(g) == lv + 1]
        T.append(max(L)); K.append(max(1, math.ceil(max(L) / smax)))
    nodes = [("root", None, ent, H.BIG, "entry")]; wires = []; branch_of = {(): "root"}
    for lv in range(depth):
        for g in sorted(x for x in groups if len(x) == lv + 1):
            par = g[:-1]; pc = site[par]; cc = site[g]; sib = sorted(kids[par]); i = sib.index(g)
            off = mz.cell((mz.xy(pc)[0], mz.xy(pc)[1] + (i - (len(sib) - 1) / 2.0) * 1.08))
            nodes.append((name(g) + "_br", branch_of[par], off, H.BIG, "branch"))
            pts = H.exact_points(mz, off, cc, T[lv], K[lv]); prev = name(g) + "_br"; chain = [off] + pts + [cc]
            for r_, c in enumerate(pts):
                n = name(g) + "_r%d" % r_; nodes.append((n, prev, c, H.REP, "rep")); prev = n
            wires.append(dict(level=lv + 1, edge=name(g), segs=[mz.md(chain[q], chain[q + 1]) for q in range(len(chain) - 1)],
                              cells=[mz.path(chain[q], chain[q + 1]) for q in range(len(chain) - 1)]))
            nodes.append((name(g), prev, cc, H.BIG, "leaf" if lv == depth - 1 else "node"))
            branch_of[g] = name(g)
    fold = {n[0]: n[1] for n in nodes if n[4] == "node"}
    land = {}
    for w in wires:
        if w["edge"] in fold:
            land[fold[w["edge"]]] = (w["segs"][-1], w["edge"])
    final = []
    for n in nodes:
        if n[0] in fold:
            continue
        par = n[1]
        while par in fold:
            par = fold[par]
        final.append((n[0], par, n[2], n[3], n[4]))
    caps = {}
    for s in sinks:
        if s[4].startswith("MACRO:"):
            c = macro_clk_cap(s[4][6:], s[3])
            for cn in ("TT", "FF"):
                caps.setdefault(cn, {})[key_of(s)] = c[cn]
    return dict(mz=mz, entry=entry, ent=ent, groups=groups, leaves=leaves, site=site, T=T, K=K, nodes=final, wires=wires,
                land=land, leafsinks={name(g): groups[g] for g in leaves}, macros=[], splits=list(upper) + ["macro_or_flop_leaf"], nm=name, sinkcap=caps,
                island_snap=island_snap,island_loads=island_loads)


def macro_leaf_errors(rec, geo):
    """Verify opt-in macro coverage/classification and both actual liberty caps."""
    errors = []
    leaves = rec.get("leaf_sinks", {})
    macro_leaves = set(rec.get("macro_leaves", []))
    for line in open(geo):
        fields = line.split()
        if fields[:1] != ["MACRO"]:
            continue
        inst, master, pin = fields[1], fields[2], fields[7]
        sink = inst + "/" + pin
        owners = [leaf for leaf, sinks in leaves.items() if sink in sinks]
        if len(owners) != 1 or owners[0] not in macro_leaves or leaves[owners[0]] != [sink]:
            errors.append("macro leaf coverage/classification: " + sink)
        expected = macro_clk_cap(master, pin)
        for corner, cap in expected.items():
            actual = rec.get("sinkcap", {}).get(corner, {}).get(sink)
            if actual is None or abs(actual - cap) > 1e-12:
                errors.append("macro leaf cap mismatch %s %s" % (corner, sink))
    return errors


# ------------------------------------------------------------------ driver
def run_core(fams, core, kit, work, a):
    fam = next(f for f in fams["families"] if core in f["members"])
    work = Path(work) / core; work.mkdir(parents=True, exist_ok=True)
    clk = census(kit, work)
    geo = entry_geo(work / "geo.txt", entry_mode(fam, core))
    if keepout_mode(fam, core):
        # DIE-S81-30 opt-in "keepout_halo_um": the kit's own macro row-cut halo (VSW kit: rows stop 4.32 um from the
        # SRAMs, so plan nodes 2.2-4.32 um from a macro were legalised 2.0-2.6 um away); default = planner halo, unchanged
        kh = {"halo": float(fam["keepout_halo_um"])} if fam.get("keepout_halo_um") is not None else {}
        fam = dict(fam, keepout_um=macro_keepouts(work / "sites.txt", **kh))
    cal = json.loads(Path(a.trunk_cal).read_text()).get(core) if getattr(a, "trunk_cal", None) else None
    rcal = json.loads(Path(a.replan_cal).read_text()).get(core) if getattr(a, "replan_cal", None) else None
    if rcal and cal:
        raise SystemExit("run: --trunk-cal and --replan-cal both name %s (trunk = built LOW, re-plan = built HIGH)" % core)
    if fam.get("lattice"):
        if rcal or cal:
            raise SystemExit("run: family %s is a lattice plan (one master per level); --trunk-cal/--replan-cal do not apply" % fam["name"])
        rec = plan_lattice(geo, fam, a.libtt, a.libff, "%s_lat_%s" % (core, fam["name"]))
    elif rcal:
        rec, fam = replan_structure(geo, fam, a.libtt, a.libff, "%s_r16_%s_rp" % (core, fam["name"]), rcal)
    else:
        rec = plan(geo, fam, a.libtt, a.libff, "%s_r13_%s%s" % (core, fam["name"], "_tk" if cal else ""), trunk_cal=cal)
    pj = work / "plan.json"; pj.write_text(json.dumps([rec]))
    if a.fit and fam.get("macro_leaves") and not fam.get("macro_d1"):
        # DIE-S81-29 (COORD DIE-S81-28-PARK (4)): opt-in per family "macro_d1": true -> the R9 d1 descent models the macro
        # leaves as kind "macro" with the record's exact TT/FF liberty clock caps (l0r_r8_uf3.PlanFromRecord + uf_phys3 cpin)
        raise SystemExit("macro_leaves uses exact NLDM caps; calibrated d1 macro support needs family macro_d1: true")
    if a.fit and not fam.get("lattice"):   # lattice = one master per level: no per-driver d1/uf3 descent
        r = subprocess.run([sys.executable, str(REPO / "results/core_lat_r9_1026/l0r_r9_d1.py"), str(pj), str(geo), a.libdir, a.fit,
                            str(work / "plan_d1.json"), "--steps", str(a.d1_steps)], capture_output=True, text=True)
        (work / "d1.log").write_text(r.stdout + r.stderr)
        if r.returncode != 0:
            # R20 fail-closed: S81-CORES-R1 sparse worktrees lacked results/core_lat_r9_1026 + model_refit2_1026, the d1
            # step died (No such file / ModuleNotFoundError) and the slice silently shipped the pre-d1 masters
            raise SystemExit("run: --fit given but the R9 d1 step failed rc %d (see %s): %s"
                             % (r.returncode, work / "d1.log", (r.stdout + r.stderr).strip()[-200:]))
        rec2 = json.loads((work / "plan_d1.json").read_text())[0]
        # refresh the NLDM numbers with the d1 masters (same chain the checks read)
        rec2["d1_from"] = "uf_phys3 v1 coordinate descent (R9)"
        if rec["name"] not in _PLANS:   # re-plan ran in worker processes: rebuild the chosen plan here (deterministic)
            plan(geo, fam, a.libtt, a.libff, rec["name"], trunk_cal=cal)
        rec = refresh_after_d1(rec, rec2)
        pj = work / "plan_d1.json"; pj.write_text(json.dumps([rec]))
    slice_dir = work / "slice"; slice_dir.mkdir(exist_ok=True)
    cmd = [sys.executable, str(HERE / "core_plan_to_infra.py"), str(pj), "--sites", str(work / "sites.txt"), "--module", core,
           "--clock-port", clk, "--band", "info", "--ndr", "none" if fam.get("wire", "std") == "std" else "2,2",
           "--out", str(slice_dir / ("%s.json" % core))]
    wpol = getattr(a, "window_policy", "gate")
    if wpol == "info":
        cmd += ["--window-policy", "info"]
    r = subprocess.run(cmd, capture_output=True, text=True); (work / "convert.log").write_text(r.stdout + r.stderr)
    sl = json.loads((slice_dir / ("%s.json" % core)).read_text()) if r.returncode == 0 else None
    ck = checks(rec, sl, geo, window_policy=wpol)
    if sl is None: ck["verdict"] = "FAIL"; ck["fails"].append("converter rc %d: %s" % (r.returncode, (r.stdout + r.stderr).strip()[-300:]))
    (work / "checks.json").write_text(json.dumps(ck, indent=1))
    render(geo, rec, sl, work / ("%s_r13.png" % core))
    line = dict(core=core, family=fam["name"], splits=rec["splits"], sinks=rec["sinks"], cells=rec["n_cells"], stages=rec["stages"],
                TT=rec["TT"]["mean"], TTw=rec["TT"]["window"], FF=rec["FF"]["mean"], FFw=rec["FF"]["window"], verdict=ck["verdict"], fails=ck["fails"],
                **({"trunk": ck["entry_trunk"]} if ck.get("entry_trunk") else {}))
    print("CORE_FAMILY_SLICE", json.dumps(line), flush=True)
    return line


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=("run", "family"))
    ap.add_argument("--family", required=True); ap.add_argument("--core"); ap.add_argument("--kit"); ap.add_argument("--name")
    ap.add_argument("--kits", help="dir holding <module>_<suffix> trial census kits"); ap.add_argument("--suffix", default="c13")
    ap.add_argument("--work", required=True)
    ap.add_argument("--libtt", required=True); ap.add_argument("--libff", required=True)
    ap.add_argument("--trunk-cal", default=None, help="JSON {core: {built_TT, built_FF, plan_TT, plan_FF, basis, source}}: "
                    "12.8c entry trunk calibrated on the core's own built CTS insertion")
    ap.add_argument("--replan-cal", default=None, help="JSON {core: {built_TT, built_FF, plan_TT, plan_FF, basis, source}}: "
                    "calibrated family-menu structure re-plan for a core built out of band HIGH")
    ap.add_argument("--fit", default=None); ap.add_argument("--libdir", default=None); ap.add_argument("--d1-steps", type=int, default=60)
    ap.add_argument("--window-policy", choices=("gate", "info"), default="gate",
                    help="12.3a opt-in (COORD 10-31, exp0): plan TT/FF window > 20 is INFO in checks() and the converter "
                         "(core_plan_to_infra --window-policy info); default gate = unchanged; routed sign-off unchanged")
    a = ap.parse_args()
    fams = json.loads(Path(a.family).read_text())
    if a.mode == "run":
        run_core(fams, a.core, a.kit, a.work, a); return
    fam = next(f for f in fams["families"] if f["name"] == a.name); rows = []
    for m in fam["members"]:
        kit = Path(a.kits) / ("%s_%s" % (fam.get("kit_name", {}).get(m, m), a.suffix))
        try:
            rows.append(run_core(fams, m, kit, a.work, a))
        except SystemExit as e:
            rows.append(dict(core=m, family=fam["name"], verdict="NO-CENSUS", fails=[str(e)])); print("CORE_FAMILY_SLICE", json.dumps(rows[-1]))
    Path(a.work, "family_%s.json" % fam["name"]).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
