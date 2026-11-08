#!/usr/bin/env python3
"""S81-TYPES-7-LEAFB channel-open leaf form (class B, leaf GRT congestion), one rule for every row.

RULE: a channel between two hard macros that face each other (overlap > 20 um) carries the signal pins of the
busier facing face (pins that cross straight are counted once). Track supply = width x (sum of 1/pitch of the layers running along the channel) x 0.7 (GRT derate).
Every channel must have demand/supply <= TARGET (0.6). Hot channels are opened, worst first, by pushing one side
away along the channel normal in 8.64-um steps (pushed macros push the macros they then touch, as a rigid chain).
A move is legal only when every moved macro stays inside the outline (4.32 edge), keeps the 8.64 macro gap, covers
no FT bit site, no grid clock tap (+-4.32) (internal station registers are re-placed near their point by ff_put_near; count reported), and the weighted core-to-core bus
length (pin-count weighted centre distance) rises <= 10 %. A move is kept only when it lowers the hot channel's ratio and no
other touched channel rises above max(its old ratio, TARGET). Macro positions come from the kit's macro_place.tcl (facing form already applied), sizes,
pins and keepouts from the plan. Output: per-macro delta in um for macro_place.tcl.
usage: channel_open.py PLAN TYPE MACRO_PLACE.tcl [--apply OUT.tcl] [--json OUT.json]"""
import json, os, re, sys, itertools
G = 8.64; EDGE = 4.32; MGAP = 8.64; TARGET = 0.6; CLR = 4.32; MAXSTEP = 12; BUSCAP = 0.10
TPU_V = (1 / 0.036 + 1 / 0.048 + 1 / 0.064) * 0.7   # M3 M5 M7 vertical tracks per um
TPU_H = (1 / 0.039 + 1 / 0.048 + 1 / 0.064) * 0.7   # M2 M4 M6 horizontal tracks per um
args = sys.argv[1:]
P, T, TCL = args[:3]
OUT = args[args.index('--apply') + 1] if '--apply' in args else None
JOUT = args[args.index('--json') + 1] if '--json' in args else None
pd = os.path.dirname(P); t = json.load(open(P))['partition_types'][T]; W, H = t['outline_um']
norm = lambda s: re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')
hc = {}
for h in t['hard_cores']:
    n = h['inst'].split('.', 1)[-1]
    pf = h.get('pins_file'); pins = []
    if pf and os.path.exists(os.path.join(pd, pf)):
        pins = json.load(open(os.path.join(pd, pf)))['pins']
    hc[n] = dict(s=list(h['outline_um']), pins=pins, key=norm(n))
tcl = open(TCL).read()
pos = {}; ori = {}; tname = {}
for m in re.finditer(r'place_macro -macro_name \{(\S+)\} -location \{([\d.]+) ([\d.]+)\} -orientation (\S+)', tcl):
    nm, x, y, r = m.group(1), float(m.group(2)), float(m.group(3)), m.group(4)
    k = norm(nm.replace('u_bound.', '', 1))
    k = re.sub(r'^u_(lf\d*_)?', '', k)
    hit = [n for n in hc if hc[n]['key'] == k or hc[n]['key'].endswith('_' + k) or k.endswith(hc[n]['key'])]
    hit = [n for n in hit if norm(n) == k] or hit
    assert len(hit) == 1, (nm, k, hit)
    n = hit[0]; pos[n] = [x, y]; ori[n] = r; tname[n] = nm
assert set(pos) == set(hc), set(hc) ^ set(pos)
def faces(n):
    w, h = hc[n]['s']; r = ori[n]; c = {'N': 0, 'S': 0, 'E': 0, 'W': 0}
    for p in hc[n]['pins']:
        x, y = p['x'], p['y']
        if r in ('MY', 'R180'): x = w - x
        if r in ('MX', 'R180'): y = h - y
        d = {'W': x, 'E': w - x, 'S': y, 'N': h - y}; c[min(d, key=d.get)] += 1
    return c
F = {n: faces(n) for n in hc}
NP = {n: len(hc[n]['pins']) for n in hc}
keep = []
for s in t.get('ft_slots', []):
    for st in s.get('bit_sites_um') or []:
        for p in st: keep.append((p[0], p[1], 1.0))
c = t.get('clock', {})
for tp in c.get('taps', []) + c.get('added_taps', []):
    if 'xy' in tp and tp.get('kind') != 'core': keep.append((tp['xy'][0], tp['xy'][1], CLR))
STREGS = [p for s in t.get('internal_stations', []) or [] for p in (s.get('regs_um', []) or [])]
# internal station registers are placed by ff_put_near (nearest free site), so a macro over one only moves it a little:
# not a keepout, but the count of covered registers is reported
def rect(n, p): o = p[n]; s = hc[n]['s']; return (o[0], o[1], o[0] + s[0], o[1] + s[1])
def legal_one(n, p):
    r = rect(n, p)
    if r[0] < EDGE - 0.2 or r[1] < EDGE - 0.2 or r[2] > W - EDGE + 0.2 or r[3] > H - EDGE + 0.2: return False
    for (x, y, cl) in keep:
        if r[0] - cl < x < r[2] + cl and r[1] - cl < y < r[3] + cl: return False
    return True
def touch(a, b, p):
    ra, rb = rect(a, p), rect(b, p)
    return ra[0] < rb[2] + MGAP - 0.05 and rb[0] < ra[2] + MGAP - 0.05 and ra[1] < rb[3] + MGAP - 0.05 and rb[1] < ra[3] + MGAP - 0.05
def channels(p):
    ch = []
    for a, b in itertools.permutations(p, 2):
        ra, rb = rect(a, p), rect(b, p)
        ov = min(ra[3], rb[3]) - max(ra[1], rb[1])
        if rb[0] >= ra[2] - 0.01 and ov > 20 and rb[0] - ra[2] < 150:
            w = rb[0] - ra[2]; d = F[a]['E'] + F[b]['W']
            d = max(F[a]['E'], F[b]['W'])  # crossing pairs counted once, the rest run along the channel
            if d: ch.append(('x', a, b, w, d, d / max(w * TPU_V, 1)))
        ov = min(ra[2], rb[2]) - max(ra[0], rb[0])
        if rb[1] >= ra[3] - 0.01 and ov > 20 and rb[1] - ra[3] < 150:
            w = rb[1] - ra[3]; d = F[a]['N'] + F[b]['S']
            d = max(F[a]['N'], F[b]['S'])
            if d: ch.append(('y', a, b, w, d, d / max(w * TPU_H, 1)))
    return ch
def buscost(p):
    # pin-count weighted centre distance between macros with facing pins (proxy for the core-to-core buses)
    cen = {n: (p[n][0] + hc[n]['s'][0] / 2, p[n][1] + hc[n]['s'][1] / 2) for n in p}
    return sum(min(F[a][fa], F[b][fb]) * (abs(cen[a][0] - cen[b][0]) + abs(cen[a][1] - cen[b][1]))
               for (ax, a, b, w, d, r) in channels(p) for fa, fb in [(('E', 'W') if ax == 'x' else ('N', 'S'))])
DBG = os.environ.get('CO_DEBUG')
def why(msg):
    if DBG: print('DBG', msg, file=sys.stderr)
def legal_why(n, p):
    r = rect(n, p)
    if r[0] < EDGE - 0.2 or r[1] < EDGE - 0.2 or r[2] > W - EDGE + 0.2 or r[3] > H - EDGE + 0.2: return 'edge'
    for (x, y, cl) in keep:
        if r[0] - cl < x < r[2] + cl and r[1] - cl < y < r[3] + cl: return 'keepout(%.1f,%.1f,cl%.2f)' % (x, y, cl)
    return None
def push(p, n, ax, d):
    q = {k: list(v) for k, v in p.items()}; moved = {n}; front = [n]; i = 0 if ax == 'x' else 1
    q[n][i] += d
    while front:
        m = front.pop()
        for o in q:
            if o in moved: continue
            if touch(m, o, q):
                # only push macros lying in the push direction
                if (q[o][i] - q[m][i]) * d > 0:
                    q[o][i] += d; moved.add(o); front.append(o)
                else:
                    why('%s %s%+.2f blocked by %s on the back side' % (n, ax, d, o)); return None, moved
    for m in moved:
        w_ = legal_why(m, q)
        if w_: why('%s %s%+.2f: %s %s' % (n, ax, d, m, w_)); return None, moved
    for a, b in itertools.combinations(q, 2):
        if (a in moved or b in moved) and touch(a, b, q): return None, moved
    return q, moved
base = {k: list(v) for k, v in pos.items()}; cur = {k: list(v) for k, v in pos.items()}
c0 = buscost(base); log = []
for rnd in range(40):
    hot = sorted([c for c in channels(cur) if c[5] > TARGET], key=lambda c: -c[5])
    done = False
    for (ax, a, b, w, d, r) in hot:
        need = max(G, (d / (TARGET * (TPU_V if ax == 'x' else TPU_H))) - w)
        k0 = int(-(-need // G))
        best = None
        for k in range(1, MAXSTEP + 1):
            for side, n, sg in (('b', b, 1), ('a', a, -1)):
                q, moved = push(cur, n, ax, sg * k * G)
                if q is None: continue
                old = {(c[0], c[1], c[2]): c[5] for c in channels(cur)}
                nc = [c for c in channels(q) if c[1] in moved or c[2] in moved]
                bad_ = [c for c in nc if c[5] > max(old.get((c[0], c[1], c[2]), 0), TARGET) + 1e-9]
                if bad_: why('%s %s%+.2f worsens %s|%s r=%.2f' % (n, ax, sg * k * G, bad_[0][1], bad_[0][2], bad_[0][5])); continue
                tgt = [c[5] for c in nc if (c[0], c[1], c[2]) == (ax, a, b)]
                if tgt and tgt[0] >= r - 1e-9: continue
                worst_new = max([c[5] for c in nc] + [0])
                if buscost(q) > c0 * (1 + BUSCAP): why('%s %s%+.2f bus %.1f%%' % (n, ax, sg * k * G, 100 * (buscost(q) / c0 - 1))); continue
                score = (max(worst_new, TARGET) , k * len(moved))
                if best is None or score < best[0]: best = (score, q, n, sg * k * G, moved)
            if best and k >= k0: break
        if best:
            cur = best[1]; log.append(dict(ch='%s|%s' % (a, b), axis=ax, width=round(w, 2), pins=d, ratio=round(r, 2),
                                          move=best[2], d_um=round(best[3], 2), chain=sorted(best[4])))
            done = True; break
    if not done: break
def summary(p):
    ch = channels(p); return dict(worst=round(max([c[5] for c in ch] + [0]), 2), hot=sum(1 for c in ch if c[5] > TARGET),
                                  hot_list=['%s|%s w=%.2f pins=%d r=%.2f' % (c[1], c[2], c[3], c[4], c[5]) for c in sorted(ch, key=lambda c: -c[5]) if c[5] > TARGET])
delta = {n: [round(cur[n][0] - base[n][0], 3), round(cur[n][1] - base[n][1], 3)] for n in cur if cur[n] != base[n]}
def covered(p): return sum(1 for (x, y) in STREGS if any(rect(n, p)[0] < x < rect(n, p)[2] and rect(n, p)[1] < y < rect(n, p)[3] for n in p))
res = dict(type=T, target=TARGET, station_regs_under_macros=[covered(base), covered(cur)], before=summary(base), after=summary(cur), bus_cost_rise_pct=round(100 * (buscost(cur) / c0 - 1), 2) if c0 else 0,
           moves={tname[n]: dict(inst=n, delta_um=delta[n], to=[round(cur[n][0], 4), round(cur[n][1], 4)], orient=ori[n]) for n in delta}, steps=log)
print(json.dumps(res, indent=1))
if JOUT: json.dump(res, open(JOUT, 'w'), indent=1)
if OUT:
    s = tcl
    for n in delta:
        pat = re.compile(r'(place_macro -macro_name \{' + re.escape(tname[n]) + r'\} -location \{)([\d.]+) ([\d.]+)(\})')
        s, k = pat.subn(lambda m: m.group(1) + '%.4f %.4f' % (cur[n][0], cur[n][1]) + m.group(4), s, count=1); assert k == 1, n
    open(OUT, 'w').write(s)
