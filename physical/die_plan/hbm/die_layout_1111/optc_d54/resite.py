"""DIE-LAYOUT-HBM option C / 0-cycle re-site of normal FT slot stations through dense macro fields.
Per (TYPE, SLOT): stations only on clear sites (outside every hard core + HALO, inside the outline - EDGE); wires may
cross cores (M6/M7 above the M5 core ceilings). S0 stays at the input face (regs_um[0] unchanged). Layered L1 BFS on a
GRID-um lattice gives the minimum number of stations m so that every hop (worst input-window bit -> S1, S_i -> S_i+1,
S_last -> worst output-window bit) <= LIM. If m <= k: same count, extra stations at clear sites near the midpoints of
the longest hops (0 cycles). If m > k: k := m (+ (m - k) cycles on every lane through the slot; reported).
usage: resite.py PLAN_IN PLAN_OUT REPORT.json TYPE:SLOT ...   env LIM (395) GRID (4.32) HALO (2.0)"""
import json, os, sys
import numpy as np
LIM = float(os.environ.get('LIM', 395)); G = float(os.environ.get('GRID', 4.32)); HALO = float(os.environ.get('HALO', 2.0)); EDGE = 2.16
P = json.load(open(sys.argv[1])); rep = []

def l1dt(seed):
    """exact L1 distance (in grid steps) to the nearest True cell."""
    INF = 10 ** 9
    d = np.where(seed, 0, INF).astype(np.int64)
    for i in range(1, d.shape[0]): d[i] = np.minimum(d[i], d[i - 1] + 1)
    for i in range(d.shape[0] - 2, -1, -1): d[i] = np.minimum(d[i], d[i + 1] + 1)
    for j in range(1, d.shape[1]): d[:, j] = np.minimum(d[:, j], d[:, j - 1] + 1)
    for j in range(d.shape[1] - 2, -1, -1): d[:, j] = np.minimum(d[:, j], d[:, j + 1] + 1)
    return d

def face_pts(face, win, W, H):
    a, b = win
    return {'W': [(0, a), (0, b)], 'E': [(W, a), (W, b)], 'S': [(a, 0), (b, 0)], 'N': [(a, H), (b, H)]}[face]

def man(p, q): return abs(p[0] - q[0]) + abs(p[1] - q[1])

for arg in sys.argv[4:]:
    tn, sn = arg.split(':')
    t = P['partition_types'][tn]; W, H = t['outline_um']
    s = next(x for x in t['ft_slots'] if x['name'] == sn)
    k = int(s['stations']); old = [list(r) for r in s['regs_um']]
    nx, ny = int(W // G) + 1, int(H // G) + 1
    X = np.arange(nx) * G; Y = np.arange(ny) * G
    XX, YY = np.meshgrid(X, Y, indexing='ij')
    clear = (XX >= EDGE) & (XX <= W - EDGE) & (YY >= EDGE) & (YY <= H - EDGE)
    for h in t['hard_cores']:
        x0, y0 = h['origin_um']; w, hh = h['outline_um']
        clear &= ~((XX > x0 - HALO) & (XX < x0 + w + HALO) & (YY > y0 - HALO) & (YY < y0 + hh + HALO))
    for x0, y0, x1, y1 in (t.get('clock') or {}).get('keepouts_um', []) or []:
        clear &= ~((XX > x0 - HALO) & (XX < x1 + HALO) & (YY > y0 - HALO) & (YY < y1 + HALO))
    inp = face_pts(s['in_face'], s['in_window_um'], W, H); outp = face_pts(s['out_face'], s['out_window_um'], W, H)
    # worst-bit distance from the window = max over its two ends
    din = np.maximum(*[np.abs(XX - p[0]) + np.abs(YY - p[1]) for p in inp])
    dout = np.maximum(*[np.abs(XX - p[0]) + np.abs(YY - p[1]) for p in outp])
    lim = int(LIM // G)
    layers = [clear & (din <= LIM)]
    while not (layers[-1] & (dout <= LIM)).any() and len(layers) < 40:
        layers.append(clear & (l1dt(layers[-1]) <= lim) & ~np.logical_or.reduce(layers))
        if not layers[-1].any(): break
    ok = (layers[-1] & (dout <= LIM)).any()
    if not ok:
        rep.append(dict(type=tn, slot=sn, status='blocked', k=k)); print(tn, sn, 'BLOCKED'); continue
    # backtrack: last site = in last layer within LIM of exit, nearest the exit; then predecessors, each the
    # one in the previous layer within LIM that is farthest from the input (keeps hops balanced)
    def pick(mask, score):
        idx = np.argwhere(mask); best = idx[np.argmin(score[mask])]; return (float(X[best[0]]), float(Y[best[1]]))
    m = len(layers)                      # stations besides S0
    chain = [pick(layers[-1] & (dout <= LIM), dout)]
    for L in range(m - 2, -1, -1):
        cx, cy = chain[0]
        near = layers[L] & ((np.abs(XX - cx) + np.abs(YY - cy)) <= LIM)
        chain.insert(0, pick(near, -din + 0 * XX))   # farthest-from-input admissible predecessor... balanced enough
    need = m + 1                          # S0 + chain
    kk = max(k, need)
    pts = [tuple(old[0])] + chain
    # extras: split the longest hop with a clear site near its midpoint (inside the hop's bounding box)
    def hops(ps):
        h = [max(man(p, ps[1]) for p in inp)] if len(ps) > 1 else []
        h += [man(ps[i], ps[i + 1]) for i in range(1, len(ps) - 1)]
        h.append(max(man(ps[-1], p) for p in outp)); return h
    while len(pts) < kk:
        best = None
        for i in range(1, len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            d = man(a, b)
            if best is None or d > best[0]: best = (d, i)
        if best is None:
            pts.append(pts[-1]); continue
        a, b = pts[best[1]], pts[best[1] + 1]
        box = clear & (XX >= min(a[0], b[0])) & (XX <= max(a[0], b[0])) & (YY >= min(a[1], b[1])) & (YY <= max(a[1], b[1]))
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        box &= ((np.abs(XX - a[0]) + np.abs(YY - a[1])) >= 2 * G) & ((np.abs(XX - b[0]) + np.abs(YY - b[1])) >= 2 * G)
        if box.any():
            c = pick(box, np.abs(XX - mid[0]) + np.abs(YY - mid[1]))
        else:
            # no clear site inside the hop box (both ends in one narrow channel): nearest clear site off the box,
            # minimising the larger of the two new hops, at least 2 grid steps from both ends
            da = np.abs(XX - a[0]) + np.abs(YY - a[1]); db = np.abs(XX - b[0]) + np.abs(YY - b[1])
            sc = np.maximum(da, db); cand = clear & (da >= 2 * G) & (db >= 2 * G) & (sc <= LIM)
            c = pick(cand, sc) if cand.any() else a
        pts.insert(best[1] + 1, c)
    new = [list(old[0])] + [[round(x, 3), round(y, 3)] for x, y in pts[1:]]
    h = hops(pts)
    s['regs_um'] = new
    if kk != k: s['stations'] = kk
    s['note'] = (str(s.get('note', '')) + f' | DIE-LAYOUT-HBM OPTC 11-12: stations re-sited on clear sites through the macro field '
                 f'(S0 kept at the input face), max hop {max(h):.0f} um <= {LIM:.0f}' + (f', stations {k} -> {kk} (+{kk-k} cycles)' if kk != k else ', 0 cycles')).lstrip(' |')
    r = dict(type=tn, slot=sn, status='resited', k_old=k, k_new=kk, min_needed=need, max_hop_um=round(max(h), 1), hops=[round(v, 1) for v in h], regs_um=new)
    rep.append(r); print(tn, sn, 'k', k, '->', kk, 'need', need, 'max hop', round(max(h), 1), [round(v) for v in h])
json.dump(P, open(sys.argv[2], 'w'), indent=1)
json.dump(rep, open(sys.argv[3], 'w'), indent=1)
