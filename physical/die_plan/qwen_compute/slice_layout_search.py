#!/usr/bin/env python3
"""PLAN-QCv2 slice region layout search: 15 slice regions (su_c spans 2 cells) on the 4x4 grid; each candidate is scored
by negotiated routing of the slice-record region flows over the region faces (cap per face = length x pins/um).
Usage: slice_layout_search.py VCAP HCAP TOPN FWFE_ROW   (caps in bits per E/W and N/S face; TOPN candidates routed)."""
import itertools, heapq, collections, json, sys, random
FL = [('stm','ctl',1024),('ctl','st_a',1024),('tap','hc2',1567),('hc2','hc1',1567),('hc1','hc0',1567),('hc2','hc3',1567),
('fe','fw',1105),('ctl','fw',1262),('stm','fw',1088),('sc','fw',48),('fw','fe',1616),('stm','fe',1088),('sc','fe',48),('st_a','fe',258),
('st_b','fe',256),('fw','ctl',1155),('stm','ctl',29),('st_a','ctl',269),('st_b','ctl',256),('su_c','ctl',1005),('sc','ctl',119),('hc0','ctl',1),
('ctl','su_c',1655),('ctl','sc',160),('fe','sc',48),('fw','sc',48),('su_c','sc',99),('ctl','stm',35),('fw','stm',1097),('fe','stm',1088),
('su_c','stm',456),('stm','st_a',27),('ctl','st_a',116),('hc1','st_a',528),('fw','st_a',264),('st_b','st_a',8),('ctl','st_b',116),('st_a','st_b',664),
('hc1','st_b',528),('fw','st_b',264),('ctl','tap',4),('fw','tap',453),('stm','tap',1050),('hc0','tap',8),('hc1','tap',8),('hc2','tap',8),('hc3','tap',8),
('tap','hc0',24),('tap','hc1',24),('tap','hc2',24),('tap','hc3',24),('su_c','su_l0',2435),('su_c','su_l1',2408)]
VC, HC = float(sys.argv[1]), float(sys.argv[2])   # vertical-face cap (E/W faces, row height), horizontal (N/S faces, col width)
def graph(cells):
    own = {}
    for r, cs in cells.items():
        for c in (cs if isinstance(cs, list) else [cs]): own[c] = r
    caps = collections.Counter()
    for (c, r), a in own.items():
        for (dc, dr, cap) in ((1, 0, VC), (0, 1, HC)):
            b = own.get((c + dc, r + dr))
            if b and b != a: caps[tuple(sorted((a, b)))] += cap
    return own, caps
def evaluate(cells, iters=60):
    own, caps = graph(cells)
    nb = collections.defaultdict(list)
    for (a, b) in caps: nb[a].append(b); nb[b].append(a)
    base = collections.Counter()
    for c in range(4):
        col = [own[(c, r)] for r in (3, 2, 1, 0)]
        for x, y in zip(col, col[1:]):
            if x != y: base[tuple(sorted((x, y)))] += 516
    hist = collections.Counter(); pf = 0.5; best = 9
    for it in range(iters):
        load = collections.Counter(base)
        for a, b, w in sorted(FL, key=lambda f: -f[2]):
            dist = {a: 0}; prev = {}; pq = [(0, a)]
            while pq:
                d, n = heapq.heappop(pq)
                if n == b: break
                if d > dist[n]: continue
                for m in nb[n]:
                    e = tuple(sorted((n, m)))
                    ov = max(0, (load[e] + w) / caps[e] - 1)
                    nd = d + 100 * (1 + hist[e]) * (1 + pf * ov * 10)
                    if nd < dist.get(m, 1e300): dist[m] = nd; prev[m] = n; heapq.heappush(pq, (nd, m))
            p = [b]
            while p[-1] != a: p.append(prev[p[-1]])
            for x, y in zip(p, p[1:]): load[tuple(sorted((x, y)))] += w
        mx = max(load[e] / caps[e] for e in caps)
        best = min(best, mx)
        if mx <= 1: return mx
        for e in caps:
            if load[e] > caps[e]: hist[e] += load[e] / caps[e] - 1 + 0.1
        pf = min(pf * 1.3, 1e4)
    return best
def proxy(cells):
    pos = {}
    for r, cs in cells.items():
        cs = cs if isinstance(cs, list) else [cs]
        pos[r] = (sum(c for c, _ in cs) / len(cs), cs[0][1])
    return sum(w * (abs(pos[a][0] - pos[b][0]) * HC / VC + abs(pos[a][1] - pos[b][1])) for a, b, w in FL)
RF = int(sys.argv[4])
fixed = {"hc0": (0, 3), "hc1": (1, 3), "hc2": (2, 3), "hc3": (3, 3), "fw": (0, RF), "fe": (3, RF)}
free = [(c, r) for r in (2, 1, 0) for c in range(4) if (c, r) not in ((0, RF), (3, RF))]
others = ["stm", "tap", "ctl", "st_b", "st_a", "su_l0", "su_l1", "sc"]
cands = []
for su in [((c, r), (c + 1, r)) for r in (2, 1, 0) for c in range(3)] + [((c, r), (c, r - 1)) for r in (2, 1) for c in range(4)]:
    if not all(x in free for x in su): continue
    rest = [x for x in free if x not in su]
    for perm in itertools.permutations(rest, len(others)):
        cells = dict(fixed, su_c=list(su), **dict(zip(others, perm)))
        cands.append((proxy(cells), cells))
cands.sort(key=lambda t: t[0])
print(len(cands), "candidates; proxy best", cands[0][0])
cur = {"hc0": (0, 3), "hc1": (1, 3), "hc2": (2, 3), "hc3": (3, 3), "fw": (0, 2), "stm": (1, 2), "tap": (2, 2), "fe": (3, 2),
       "ctl": (0, 1), "su_c": [(1, 1), (2, 1)], "st_b": (3, 1), "st_a": (0, 0), "su_l0": (1, 0), "su_l1": (2, 0), "sc": (3, 0)}
print("current", round(proxy(cur)), round(evaluate(cur), 3))
res = []
for pr, c in cands[:int(sys.argv[3])]:
    res.append((evaluate(c), pr, c))
res.sort(key=lambda t: (t[0], t[1]))
for r in res[:5]: print(round(r[0], 3), round(r[1]), json.dumps(r[2]))
