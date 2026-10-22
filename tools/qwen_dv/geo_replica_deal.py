#!/usr/bin/env python3
"""SQC-CTLM 10-22: geometry-coherent fan-out replicas (function-exact, no edge, no port change).

The native generator splits an overloaded driver into identical copies (same cell type, same input nets) and fills
them in sink-ID order, so one copy can serve sinks hundreds of um apart: every such copy is a single-cycle wire
round trip (safe17a CTS: u_8213 (391,591) -> AND copy u_39347 placed at (256,310) -> back to u_8503 (459,716),
~590 ps of wire buffers; reset distributor copies u_68463.. span 969 um each).  This pass re-deals the pooled sinks
of every replica group by PLACED GEOMETRY (loc.txt of a prior placement: '<inst> x y master region'): capacitated
recursive bisection along the longer axis, then each cluster goes to the nearest copy.  Every sink pin still reads a
net computed by an identical cell from identical input nets (flops: identical C/D/R nets), so the function is
unchanged; no cell or net is added, input-net loads never change, and every copy's mapped load weight stays within
the group's original maximum (cap <= 32 when the original was <= 32).  Copies that drive anything outside the
qfd_bmath cell set (ports, macros, hard children) keep exactly their current sinks.

usage: geo_replica_deal.py <in.sv> <loc.txt> <out.sv> <record.json> [--min-span UM] [--only-gain UM]
"""
import argparse, collections, hashlib, json, re, sys

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('loc'); ap.add_argument('dst'); ap.add_argument('rec')
ap.add_argument('--min-span', type=float, default=120.0, help='re-deal a group only if its worst copy HPWL exceeds this (um)')
ap.add_argument('--only-gain', type=float, default=40.0, help='keep a re-deal only if the worst copy HPWL drops by this (um)')
ap.add_argument('--mode', choices=('deal', 'split'), default='deal',
                help='deal: re-deal existing replica groups only; split: also add identical copies of the --split drivers')
ap.add_argument('--split', help='file: one netlist driver name per line (split mode targets)')
ap.add_argument('--target-weight', type=int, default=8, help='split mode: mapped load weight per copy')
ap.add_argument('--prefix', default='qkgeo', help='split mode: new cell u_<prefix>_N, net n_<prefix>_N')
a = ap.parse_args()

text = open(a.src).read(); lines = text.split('\n')
cell_re = re.compile(r'^(\(\* [^*]*\*\) )?(qfd_bmath_\w+) #\(\.ID\(0\)\) (\\\S+ |[^\s(]+)\((.*)\);$')
pin_re = re.compile(r'\.(\w+)\(([^()]*)\)')
cells = {}; other = collections.Counter()
for i, l in enumerate(lines):
    m = cell_re.match(l)
    if m:
        cells[m.group(3).strip()] = (m.group(2), dict(pin_re.findall(m.group(4))), i)
    elif not l.startswith('wire '):
        for t in re.findall(r'\bn_\w+\b', l): other[t] += 1

def outp(t): return 'Q' if t.startswith('qfd_bmath_dff') else 'Y'
sinks = collections.defaultdict(list)
for n, (t, p, i) in cells.items():
    for q, v in p.items():
        if q != outp(t): sinks[v].append((n, q))

# placed location of each netlist cell = mean of its mapped sub-instances
acc = collections.defaultdict(lambda: [0.0, 0.0, 0])
for l in open(a.loc):
    f = l.split()
    if not f or f[0] == 'REGION': continue
    top = f[0].split('/')[0]
    s = acc[top]; s[0] += float(f[1]); s[1] += float(f[2]); s[2] += 1
LOC = {k.lstrip('\\'): (v[0] / v[2], v[1] / v[2]) for k, v in acc.items()}
def key(n): return n.lstrip('\\').strip()

_nw = {}
def netw(net):
    """mapped dynamic loads of a net: NOT is transparent (absorbed by mapping), MUX S = 2, other pins 1."""
    if net in _nw: return _nw[net]
    _nw[net] = 0
    _nw[net] = sum(w(s, p) for s, p in sinks.get(net, [])) + other[net]
    return _nw[net]
def w(s, p):
    t = cells[s][0]
    if t == 'qfd_bmath_not': return max(1, netw(cells[s][1]['Y']))
    return 2 if (t == 'qfd_bmath_mux' and p == 'S') else 1
_loc = {}
def where(s, depth=0):
    if s in _loc: return _loc[s]
    r = LOC.get(key(s))
    if r is None and cells[s][0] == 'qfd_bmath_not' and depth < 8:
        pts = [where(x, depth + 1) for x, _ in sinks.get(cells[s][1]['Y'], [])]
        pts = [q for q in pts if q]
        if pts: r = (sum(x for x, y in pts) / len(pts), sum(y for x, y in pts) / len(pts))
    _loc[s] = r
    return r
def hpwl(pts):
    if not pts: return 0.0
    xs = [x for x, y in pts]; ys = [y for x, y in pts]
    return (max(xs) - min(xs)) + (max(ys) - min(ys))

grp = collections.defaultdict(list)
for n, (t, p, i) in cells.items():
    if t == 'qfd_bmath_not': continue  # NOT copies are transparent; re-dealing them moves weight upstream
    o = outp(t)
    grp[(t, tuple(sorted((q, v) for q, v in p.items() if q != o)))].append(n)

def bisect(items, copies, cap):
    """items: [(x,y,w,sp)], copies: k -> k item-lists, each weight <= cap.  Cut along the longer axis at the
    widest geometric gap that both halves can carry (copies split k1/k-k1 to match), ties to the balanced cut."""
    k = copies
    if k == 1: return [items] if sum(it[2] for it in items) <= cap else None
    if not items: return [[] for _ in range(k)]
    xs = [it[0] for it in items]; ys = [it[1] for it in items]
    ax = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
    items = sorted(items, key=lambda it: (it[ax], it[1 - ax]))
    tot = sum(it[2] for it in items)
    pre = [0]
    for it in items: pre.append(pre[-1] + it[2])
    best = None
    for j in range(1, len(items)):
        gap = items[j][ax] - items[j - 1][ax]
        for k1 in range(1, k):
            k2 = k - k1
            if pre[j] <= k1 * cap and tot - pre[j] <= k2 * cap and j >= k1 and len(items) - j >= k2:
                imb = abs(pre[j] / k1 - (tot - pre[j]) / k2)
                sc = (round(gap, 0), -imb)
                if best is None or sc > best[0]: best = (sc, j, k1)
    if best is None: return None
    _, j, k1 = best
    l = bisect(items[:j], k1, cap); r = bisect(items[j:], k - k1, cap)
    if l is None or r is None: return None
    return l + r

edits = {}; stats = collections.Counter(); changed = []; added = []; extra = collections.Counter()
targets = set(x.strip() for x in open(a.split)) - {''} if (a.mode == 'split' and a.split) else set()
drv = {}
for n, (t, p, i) in cells.items():
    if outp(t) in p: drv[p[outp(t)]] = n
def in_chain(base):
    """(net, weight) loads one more copy of base adds: every non-clock input, walking up transparent NOTs."""
    t, p, i = cells[base]; r = []
    for q, v in p.items():
        if q in (outp(t), 'C') or not v.startswith('n_'): continue
        net = v; wt = 2 if (t == 'qfd_bmath_mux' and q == 'S') else 1
        while True:
            r.append((net, wt)); d = drv.get(net)
            if d is None or cells[d][0] != 'qfd_bmath_not': break
            net = cells[d][1]['A']
    return r
def room(base):
    ch = in_chain(base)
    return min([(32 - netw(n) - extra[n]) // wt for n, wt in ch] or [0])
for gk, ms in sorted(grp.items(), key=lambda kv: kv[1][0]):
    tgt = bool(targets & {key(m) for m in ms})
    if a.mode == 'split' and not tgt: continue
    if len(ms) < 2 and not tgt: continue
    t = gk[0]; o = outp(t)
    free = [m for m in ms if not other[cells[m][1][o]]]
    if len(free) < (1 if tgt else 2): stats['skip_external'] += 1; continue
    nets = {m: cells[m][1][o] for m in free}
    pool = [(s, p, m) for m in free for (s, p) in sinks.get(nets[m], [])]
    pts = {(s, p): (where(s) or LOC.get(key(m))) for s, p, m in pool}  # absorbed NOT to a port: stays by its copy
    if any(v is None for v in pts.values()): stats['skip_unplaced_sink'] += 1; continue
    before = {m: hpwl([pts[(s, p)] for s, p in sinks.get(nets[m], [])]) for m in free}
    if not tgt and max(before.values()) < a.min_span: stats['below_min_span'] += 1; continue
    wts = {m: sum(w(s, p) for s, p in sinks.get(nets[m], [])) for m in free}
    cap = max(wts.values())
    items = [(pts[(s, p)][0], pts[(s, p)][1], w(s, p), (s, p)) for s, p, m in pool]
    k = len(free); tot = sum(it[2] for it in items)
    if tgt:
        base = sorted(free, key=lambda m: m)[0]
        need = -(-tot // a.target_weight)
        k = max(k, min(need, k + max(0, room(base)), len(items)))
        if k == len(free) and len(free) == 1: stats['skip_split_no_room'] += 1; continue
        cap = max(max(it[2] for it in items), -(-tot // k) + 2, a.target_weight) if k > len(free) else cap
        cap = min(cap, max(32, max(wts.values())))
    cl = bisect(items, k, cap)
    if cl is None: stats['skip_no_fit'] += 1; continue
    if any(not c for c in cl): stats['skip_empty_cluster'] += 1; continue  # unloaded copy would be swept
    after_h = [hpwl([(it[0], it[1]) for it in c]) for c in cl]
    if not tgt and max(before.values()) - max(after_h) < a.only_gain: stats['skip_small_gain'] += 1; continue
    # nearest copy to each cluster centroid (greedy, largest cluster first) keeps placement churn low
    cen = [(sum(it[0] for it in c) / len(c), sum(it[1] for it in c) / len(c)) for c in cl]
    mloc = {m: (LOC.get(key(m)) or cen[0]) for m in free}
    left = set(free); assign = {}
    for ci in sorted(range(len(cl)), key=lambda i: -sum(it[2] for it in cl[i])):
        if not left: break
        m = min(left, key=lambda m: abs(mloc[m][0] - cen[ci][0]) + abs(mloc[m][1] - cen[ci][1]))
        left.discard(m); assign[ci] = m
    for ci in range(len(cl)):
        if ci in assign: continue
        base = sorted(free)[0]; bt, bp, bi = cells[base]
        n_ = len(added); cn = f'u_{a.prefix}_{n_}'; nn = f'n_{a.prefix}_{n_}'
        bl = lines[bi]
        bm = cell_re.match(bl)
        nl = bl[:bm.start(3)] + cn + bl[bm.end(3):]  # escaped base '\\a.b ' -> plain 'u_<prefix>_N'
        nl = nl.replace('.' + o + '(' + bp[o] + ')', '.' + o + '(' + nn + ')')
        assert nl.count(nn) == 1 and cell_re.match(nl).group(3).strip() == cn, base
        added.append((bi, nl, nn)); cells[cn] = (bt, dict(bp, **{o: nn}), None); nets[cn] = nn; assign[ci] = cn
        for net, wt in in_chain(base): extra[net] += wt
        stats['copies_added'] += 1
    for ci, c in enumerate(cl):
        for it in c: edits[it[3]] = nets[assign[ci]]
    stats['groups_split' if k > len(free) else 'groups_dealt'] += 1
    changed.append(dict(type=t, inputs={q: v for q, v in gk[1]}, copies=[assign[i] for i in range(len(cl))], cap=cap,
                        hpwl_before=round(max(before.values()), 1), hpwl_after=round(max(after_h), 1),
                        weights_before=sorted(wts.values()), weights_after=sorted(sum(it[2] for it in c) for c in cl)))
over = {n: netw(n) + e for n, e in extra.items() if netw(n) + e > 32}
if over: sys.exit(f'refuse: input nets over 32 mapped loads: {list(over.items())[:5]}')

byline = collections.defaultdict(list)
for (s, p), net in edits.items(): byline[cells[s][2]].append((p, net))
moved = 0
for i, lst in byline.items():
    l = lines[i]
    for p, net in lst:
        l2, nsub = re.subn(r'\.' + p + r'\((n_\w+)\)', '.' + p + '(' + net + ')', l, count=1)
        if nsub != 1: sys.exit(f'refuse: pin {p} not rewritable on line {i}')
        if l2 != l: moved += 1
        l = l2
    lines[i] = l
for i, l, nn in sorted(added, reverse=True): lines.insert(i + 1, l)
if added:
    hdr = next(j for j, l in enumerate(lines) if l.startswith('wire '))
    lines.insert(hdr, 'wire ' + ', '.join(nn for _, _, nn in added) + ';')
out = '\n'.join(lines)
open(a.dst, 'w').write(out)
r = dict(schema='opentallas.sqc_ctlm.geo_replica_deal.v1', source=a.src,
         source_sha256=hashlib.sha256(text.encode()).hexdigest(), out_sha256=hashlib.sha256(out.encode()).hexdigest(),
         loc=a.loc, min_span=a.min_span, only_gain=a.only_gain, stats=dict(stats), sink_pins_moved=moved, mode=a.mode,
         target_weight=a.target_weight, split_targets=sorted(targets), new_cells=[cell_re.match(nl).group(3).strip() for _, nl, _ in added], groups=changed)
json.dump(r, open(a.rec, 'w'), indent=1)
print(json.dumps(dict(stats=dict(stats), sink_pins_moved=moved)))
