"""DIE-RECHECK-1 (DO_NOT_COUNT): BALANCED die-clock feed for the S81 local form on the current plan.

The DS85 feed (sb6 tree kept where its edges still abut, 38 parts re-parented) is 26 feed levels deep, so tap
arrivals spread 442..10,097 ps TT and adjacent partitions in different sb6 branches share almost no clock
(unshared clock on a landing = the feed path between the two parts via their lowest common ancestor).

This feed is a MINIMUM-DEPTH spanning tree of the plan's abutment graph (BFS), rooted at the partition that holds
the plan's clock.spine.root_um, with the parent of each part chosen among its minimum-depth abutting neighbours by
(1) most plan landings (landing_network edges, any kind) between the two parts -> the crossing becomes a feed edge
    (METHODOLOGY 12.16b(i): a data link is a clock-tree edge),
(2) shortest centre-to-centre distance.
Taps on the middle of the shared edge (feed_a3 / DS85 convention).
Hard-PHY partitions (type family serdes / phy, --leaf-re) are LEAVES: a feed leg through a PHY partition has no legal
repeater site (ck_bal fail 1: lk_ES0 -> fE0_p2_b2 leg 994 um through the SerDes).  They are transit only when a part
cannot be reached otherwise.  --avoid a->b,... drops feed edges (auto retry after a kit reach failure).
--phy-parents FEED (conservative form after 2 reach failures, ck_bal fail 2: a north-edge tap into lk_ES1 left a 994-um
leg to the SerDes clock pin): every PHY partition keeps its parent + tap from a proven feed (DS85 sb6, whose side-edge
PHY->PHY chains routed), PHYs feed only those PHY children; the BFS balances all other parts.
Usage: feed_bal.py PLAN TOOLS OUT [--leaf-re REGEX] [--avoid a->b,...] [--phy-parents FEED.json]"""
import collections
import json
import re
import sys

sys.path.insert(0, sys.argv[2])
import schema as S

plan_raw = S.load(sys.argv[1])
P = S.Plan(plan_raw, sys.argv[1])


def shared(a, b, tol=1e-3):
    ax0, ay0, ax1, ay1 = P.rect(a); bx0, by0, bx1, by1 = P.rect(b)
    for g, y in ((by0 - ay1, (ay1 + by0) / 2), (ay0 - by1, (ay0 + by1) / 2)):
        if -1e-3 < g < tol:
            lo, hi = max(ax0, bx0), min(ax1, bx1)
            if hi - lo > 0: return [round((lo + hi) / 2, 1), round(y, 1)], hi - lo
    for g, x in ((bx0 - ax1, (ax1 + bx0) / 2), (ax0 - bx1, (ax0 + bx1) / 2)):
        if -1e-3 < g < tol:
            lo, hi = max(ay0, by0), min(ay1, by1)
            if hi - lo > 0: return [round(x, 1), round((lo + hi) / 2, 1)], hi - lo
    return None, 0


def ctr(n):
    x0, y0, x1, y1 = P.rect(n); return (x0 + x1) / 2, (y0 + y1) / 2


parts = sorted(P.parts)
rx, ry = plan_raw['clock']['spine']['root_um']
inside = [n for n in parts if P.rect(n)[0] <= rx <= P.rect(n)[2] and P.rect(n)[1] <= ry <= P.rect(n)[3]]
root = inside[0] if inside else min(parts, key=lambda n: abs(ctr(n)[0] - rx) + abs(ctr(n)[1] - ry))
MIN_OV = 20.0   # um: a corner touch (overlap ~0) is not a neighbour; the tap needs a real shared edge
nb = {n: [m for m in parts if m != n and shared(m, n)[1] >= MIN_OV] for n in parts}
links = collections.Counter()
for e in plan_raw['clock']['landing_network']['edges']:
    a, b = e['src']['part'], e['dst']['part']
    if a != b: links[frozenset((a, b))] += 1
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
LEAF_RE = re.compile(arg('--leaf-re', r'^(serdes|phy)(__|$)'))
avoid = set(tuple(x.split('->')) for x in arg('--avoid', '').split(',') if '->' in x)
for a_, b_ in avoid:
    nb[a_] = [m for m in nb[a_] if m != b_]; nb[b_] = [m for m in nb[b_] if m != a_]
ptype = {p['name']: p['type'] for p in plan_raw['partitions']}
leaf = {n for n in parts if LEAF_RE.search(ptype[n]) and n != root}


def bfs(blocked):
    d = {root: 0}; q = collections.deque([root])
    while q:
        u = q.popleft()
        if u in blocked and u != root: continue        # reached, but feeds nothing
        for v in nb[u]:
            if v not in d: d[v] = d[u] + 1; q.append(v)
    return d


dep = bfs(leaf)
transit_leaf = set()
while set(parts) - set(dep):        # a part reachable only through a PHY: let the nearest PHY carry it
    miss = set(parts) - set(dep)
    opener = min((n for n in leaf - transit_leaf if n in dep and any(m in miss for m in nb[n])), key=lambda n: dep[n],
                 default=None)
    if opener is None: raise SystemExit('abutment graph disconnected: %s' % sorted(miss)[:10])
    transit_leaf.add(opener); dep = bfs(leaf - transit_leaf)
PP = json.load(open(arg('--phy-parents', ''))) if arg('--phy-parents', '') else None
fixed = {}
if PP:
    fixed = {n: (PP['parent'][n], PP['tap']['%s->%s' % (PP['parent'][n], n)]) for n in leaf if PP['parent'].get(n)}
    changed = True
    while changed:              # PHY depth from its fixed parent (chains resolve in order)
        changed = False
        for n, (pp, _) in fixed.items():
            if pp in dep and dep.get(n) != dep[pp] + 1 and (pp not in leaf or pp in fixed):
                dep[n] = dep[pp] + 1; changed = True
par = {root: None}
for c in parts:
    if c == root: continue
    if c in fixed:
        par[c] = fixed[c][0]; continue
    cand = [m for m in nb[c] if dep[m] == dep[c] - 1 and (m not in leaf or m in transit_leaf)]
    cx, cy = ctr(c)
    par[c] = max(cand, key=lambda m: (links[frozenset((m, c))], -(abs(ctr(m)[0] - cx) + abs(ctr(m)[1] - cy)), m))
tap, short = {}, []
for c, p in par.items():
    if p is None: continue
    if c in fixed:
        tap[f'{p}->{c}'] = fixed[c][1]; continue
    t, ov = shared(p, c)
    if ov <= 100: short.append((p, c, round(ov, 1)))
    tap[f'{p}->{c}'] = t
hist = sorted(collections.Counter(dep.values()).items())
on_edge = sum(n for k, n in links.items() if any(par.get(x) in k and x in k for x in k))
print('root', root, 'max depth', max(dep.values()), 'hist', hist, 'leaf-only PHY parts', len(leaf), 'PHY transit', sorted(transit_leaf), 'PHY fixed parents', len(fixed), 'avoid', sorted(avoid))
print('landings on a feed edge', on_edge, 'of', sum(links.values()), '; short overlap <=100um', short)
json.dump(dict(root=root, parent=par, tap=tap, depth_hist=hist, leaf_only=sorted(leaf - transit_leaf), avoid=sorted(map(list, avoid)),
               note='DIE-RECHECK-1 balanced (min-depth BFS) abutment feed on the current plan; parent by landing count'),
          open(sys.argv[3], 'w'), indent=0)
