"""HEAD-97 rp21 die event step 1 (COORD 11-13 rulings): hd_tile form 17.28 / 43.2 / 17.28 (outline 708.48 -> 717.12)
+ the die stretched by 22 x 8.64 = 190.08 um in x so the 264-tile array keeps abutting; every partition east of a tile
column shifts with it.  W half columns k=0..10 shift 8.64k, the spine column (wshim / spn / eshim) +95.04, E half
columns 95.04 + 8.64j, the E-end turns +190.08, the W-end turns 0.  Shore rows (above / below the array) move as rigid
rows by +95.04 so every shore abutment, io rect and PG domain is kept; the 95.04 strips this opens at the W / E die
edges of the shore rows become die channels.  Die-level: outline, channels, io, pg domains, port windows (N/S faces),
clock spine root / trunk.  hd_tile internals: elemA x 17.28 / 380.16 (B unchanged, it is now centred), pin relays +
core clock taps move with their core; E-face objects (x >= 691.2 not on a core) +8.64; the two reset local taps that sat
in the W / E outline strips move into the A|A E-W street (column rule: nothing but per-pin relays in a sparse strip).
Asserts the array still abuts (turn | tiles | shims | tiles | turn) on every row."""
import json, sys, copy
src, out, rep_path = sys.argv[1:4]
P = json.load(open(src)); T = P['partition_types']; R = lambda v: round(v, 4)
import os
ES = float(os.environ.get('ES', '21.6'))    # E outline strip
WS = float(os.environ.get('WS', '21.6'))    # W outline strip
OLDW = 708.48; NEWW = round(WS + 319.68 + 43.2 + 319.68 + ES, 4); D = round(NEWW - OLDW, 4); DM = round(WS - 17.28, 4)
XA1 = round(WS + 319.68 + 43.2, 4)
assert abs(NEWW / 8.64 - round(NEWW / 8.64)) < 1e-6, NEWW
X0W, X0E, NCOL = 276.48, 9452.16, 11
YLO, YHI = 2557.44, 14999.04
HALF = NCOL * D                     # 95.04
rep = {}
# ---------------- hd_tile internals
t = T['hd_tile']; assert t['outline_um'] == [OLDW, 1036.8], t['outline_um']
NEW = {'u_core.u_b.g_cv.u_eA0': (WS, 8.64), 'u_core.u_b.g_cv.u_eA2': (WS, 380.16),
       'u_core.u_b.g_cv.u_eA1': (XA1, 8.64), 'u_core.u_b.g_cv.u_eA3': (XA1, 380.16)}
HALO = 4.32; moves = []
for h in t['hard_cores']:
    if h['inst'] in NEW:
        x0, y0 = h['origin_um']; w, hh = h['outline_um']
        assert y0 == NEW[h['inst']][1]
        moves.append((h['inst'], (x0 - HALO, y0 - HALO, x0 + w + HALO, y0 + hh + HALO), R(NEW[h['inst']][0] - x0)))
        h['origin_um'] = list(NEW[h['inst']])
    elif h['inst'].endswith('u_eB'):
        x0, y0 = h['origin_um']; w, hh = h['outline_um']
        moves.append((h['inst'], (x0 - HALO, y0 - HALO, x0 + w + HALO, y0 + hh + HALO), DM))
        h['origin_um'] = [R(x0 + DM), y0]
assert len(moves) == 5, [m[0] for m in moves]
def core_of(x, y):
    m = [mv for mv in moves if mv[1][0] <= x <= mv[1][2] and mv[1][1] <= y <= mv[1][3]]
    assert len(m) <= 1, (x, y)
    return m[0] if m else None
def gx(x, y):
    """local x map for a non-core object"""
    if x >= 691.2 - 1e-6: return R(x + D)          # E-face objects follow the E edge
    if x <= 17.28 + 1e-6: return x                 # W-face objects stay on the W edge
    return R(x + DM)                               # interior (streets, elemB lobes) keep their place round elemB
def mvpt(x, y):
    m = core_of(x, y)
    return [R(x + m[2]), y] if m else [gx(x, y), y]
cnt = {'relay_core': 0, 'relay_e': 0}
for k, (x, y) in list(t['relay_sites'].items()):
    nx = mvpt(x, y)
    if nx[0] != x: cnt['relay_core' if core_of(x, y) else 'relay_e'] += 1
    t['relay_sites'][k] = nx
for tp in t['clock'].get('taps', []):
    if tp.get('kind') == 'core':
        for inst, r, dx in moves:
            if tp['name'].startswith(inst + '.'): tp['xy'] = [R(tp['xy'][0] + dx), tp['xy'][1]]
for pn in t['clock']['landing_contract']['pins']:
    pn['xy_um'] = [gx(*pn['xy_um']), pn['xy_um'][1]]
for e in t.get('reset_start_raw_exports', []):
    e['xy_um'] = [gx(*e['xy_um']), e['xy_um'][1]]
for key in ('count_straps', 'id_straps'):
    for s in t.get(key, []):
        if 'sites_um' in s: s['sites_um'] = [[gx(x, y), y] for x, y in s['sites_um']]
lt = t['reset']['local_taps_um']; newlt = []
for x, y in lt:
    if x < 17.28 and 8.64 < y < 328.32:  newlt.append([30.24, 354.24]); rep.setdefault('reset_tap_moved', []).append([[x, y], [30.24, 354.24]])
    elif x >= 691.2 and 8.64 < y < 328.32: e = R(NEWW - 25.92); newlt.append([e, 354.24]); rep.setdefault('reset_tap_moved', []).append([[x, y], [e, 354.24]])
    else: newlt.append([gx(x, y), y])
t['reset']['local_taps_um'] = newlt
isl = t['clock'].get('die_islands_um', [])
def _isl(r):
    cx = (r[0] + r[2]) / 2; d = gx(cx, r[1]) - cx            # the island moves as a whole with its centre
    x0, x1 = R(r[0] + d), R(r[2] + d)
    if x0 < 0: x0, x1 = 0.0, R(x1 - x0)
    if x1 > NEWW: x0, x1 = R(x0 - (x1 - NEWW)), NEWW
    return [x0, r[1], x1, r[3]]
t['clock']['die_islands_um'] = [_isl(r) for r in isl]
t['outline_um'] = [NEWW, 1036.8]; rep['tile_width'] = NEWW; rep['die_dx'] = round(2 * HALF, 4)
t['note'] = t.get('note', '') + ' | HEAD-97 rp21 (COORD 11-13 F1b ruling): outline %s x 1036.8, elemA x %s / %s, elemB +%s (centred) = streets %s / 43.2 / %s (per-pin face relays = pin registers; 21.6 = 17.28 + one 4.32 site so a density clock tap is legal in the strip, 8.64 die grid); reset local taps out of the outline strips' % (NEWW, WS, XA1, DM, WS, ES)
# report any non-moved object inside a new core rect
newrects = [(NEW[i][0], NEW[i][1], NEW[i][0] + 319.68, NEW[i][1] + 319.68) for i in NEW]
bad = []
def walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if path == '' and k == 'hard_cores': continue
            walk(v, path + '/' + str(k))
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(v, (int, float)) for v in o):
            if any(r[0] + 0.01 < o[0] < r[2] - 0.01 and r[1] + 0.01 < o[1] < r[3] - 0.01 for r in newrects) and '/clock/taps' not in path: bad.append((path, o))
        else:
            for i, v in enumerate(o): walk(v, path + '/' + str(i))
walk(t, '')
rep['tile'] = dict(cnt, inside_new_cores=bad[:20], inside_n=len(bad))
# ---------------- die stretch
def col_dx(x):
    for base, off in ((X0W, 0.0), (X0E, HALF)):
        k = round((x - base) / OLDW)
        if 0 <= k < NCOL and abs(base + k * OLDW - x) < 0.01: return off + k * D
    return None
def part_dx(p):
    x, y = p['origin_um']
    if p['type'] == 'hd_tile':
        d = col_dx(x); assert d is not None, p; return d
    if YLO - 0.01 <= y < YHI - 0.01:            # array rows
        if x < X0W: return 0.0
        if x >= X0E + NCOL * OLDW - 0.01: return 2 * HALF
        if X0W + NCOL * OLDW - 0.01 <= x < X0E: return HALF
        raise ValueError(('array-row partition inside a half', p['name'], x))
    return HALF                                   # shore rows
dx = {}
for p in P['partitions']:
    d = part_dx(p); dx[p['name']] = d
    p['origin_um'] = [R(p['origin_um'][0] + d), p['origin_um'][1]]
def fx(x, y):
    """die x map for die-level rects / points"""
    if x <= 103.68 + 1e-6: return x
    if x >= 17418.24 - 1e-6: return R(x + 2 * HALF)
    if YLO - 0.01 <= y <= YHI + 0.01:
        if x <= X0W: return x
        if x <= X0W + NCOL * OLDW: k = min(int((x - X0W) // OLDW), NCOL - 1); return R(X0W + k * NEWW + (x - X0W - k * OLDW) * NEWW / OLDW)
        if x <= X0E: return R(x + HALF)
        if x <= X0E + NCOL * OLDW: k = min(int((x - X0E) // OLDW), NCOL - 1); return R(X0E + HALF + k * NEWW + (x - X0E - k * OLDW) * NEWW / OLDW)
        return R(x + 2 * HALF)
    return R(x + HALF)
die = P['die']; die['outline_um'] = [R(die['outline_um'][0] + 2 * HALF), die['outline_um'][1]]
for c in die['channels']:
    r = c['rect_um']; ym = (r[1] + r[3]) / 2
    c['rect_um'] = [fx(r[0], ym), r[1], fx(r[2], ym) if r[2] < 17521.9 else R(r[2] + 2 * HALF), r[3]]
for (y0, y1) in (((103.68, 1330.56), (16225.92, 17452.8)) if HALF > 0 else ()):  # serdes rows (no channel there before)
    die['channels'].append(dict(name='rp21_shore_w_%d' % int(y0), rect_um=[103.68, y0, R(103.68 + HALF), y1], reason='HEAD-97 rp21 die stretch: W edge strip of the rigidly shifted shore row (+95.04); die channel: no signal std cells (12.1d), PG + filler/decap'))
    die['channels'].append(dict(name='rp21_shore_e_%d' % int(y0), rect_um=[R(17418.24 + HALF), y0, R(17418.24 + 2 * HALF), y1], reason='HEAD-97 rp21 die stretch: E edge strip of the rigidly shifted shore row (+95.04); die channel'))
for io in die['io']:
    r = io['rect_um']; d = dx[io['part']]; io['rect_um'] = [R(r[0] + d), r[1], R(r[2] + d), r[3]]
iod = {io['name']: dx[io['part']] for io in die['io']}
for dm in die['pg']['domains']:
    d = {iod[i] for i in dm.get('io', [])}; assert len(d) == 1, dm['name']; d = d.pop()
    for key in ('rect_um',):
        r = dm[key]; dm[key] = [R(r[0] + d), r[1], R(r[2] + d), r[3]]
    b = dm.get('bumps', {})
    if b.get('rect_um'): r = b['rect_um']; b['rect_um'] = [R(r[0] + d), r[1], R(r[2] + d), r[3]]
# ports: N/S-face windows are x ranges -> shift by the (common) partition dx
nwin = 0; mixed = []
for pt in P['ports']:
    if not pt.get('window_um'): continue
    a, b = pt['src']['part'], pt['dst']['part']
    face = pt.get('face')
    if face in ('N', 'S'):
        if dx.get(a) != dx.get(b): mixed.append(pt['id'])
        d = dx.get(a, dx.get(b)); pt['window_um'] = [R(v + d) for v in pt['window_um']]; nwin += 1
rep['ports_ns_shifted'] = nwin; rep['ports_mixed_dx'] = mixed[:20]; rep['ports_mixed_n'] = len(mixed)
rep['port_faces'] = sorted({str(pt.get('face')) for pt in P['ports'] if pt.get('window_um')})
sp = P['clock']['spine']; sp['root_um'] = [R(sp['root_um'][0] + HALF), sp['root_um'][1]]
sp['trunk']['node_x_um'] = R(sp['trunk']['node_x_um'] + HALF); sp['trunk']['lane_x_um'] = R(sp['trunk']['lane_x_um'] + HALF)
# abutment assert per array row
rows = {}
for p in P['partitions']:
    x, y = p['origin_um']
    if YLO - 0.01 <= y < YHI - 0.01: rows.setdefault(round(y, 2), []).append((x, x + T[p['type']]['outline_um'][0], p['name']))
gaps = []
for y, v in rows.items():
    v.sort()
    for (a0, a1, an), (b0, b1, bn) in zip(v, v[1:]):
        if abs(a1 - b0) > 0.01: gaps.append((y, an, a1, bn, b0))
rep['array_row_gaps'] = gaps[:20]; rep['array_row_gaps_n'] = len(gaps)
P['note'] = P.get('note', '') + ' | HEAD-97 rp21 die event (11-13): hd_tile %s wide (F1b ruling), die +%s um in x' % (NEWW, round(2 * HALF, 2))
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n')
json.dump(rep, open(rep_path, 'w'), indent=1, default=str)
print(json.dumps(rep, default=str)[:3000])
