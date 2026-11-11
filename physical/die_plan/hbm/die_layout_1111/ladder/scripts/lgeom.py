"""DIE-LAYOUT-HBM ladder geometry + bank-run router (shared by the dry run and the builder).

Ladder spec (per side NE/NW): y-seam height of the bottom row (hb) and the u-coordinates (distance from the hub edge)
of the 3 top seams and the 3 bottom seams.  Top row = b000 b001 b002 b003 (from the hub), bottom = b010 b011 b012 b013.
"""
import heapq
import math

TOP = ['b000', 'b001', 'b002', 'b003']
BOT = ['b010', 'b011', 'b012', 'b013']
BANKS = TOP + BOT
Y0, H = 6065.28, 4320.0
WB = 4492.80
HUBX = {'NE': 23258.88, 'NW': 5140.8}
OPP = {'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}
EPS = 1e-6


def rects(side, spec):
    """{part: (x0, y0, x1, y1)} die frame.  Variant C (b000 column): b000 keeps its full-height column next to the
    hub (width spec['w0']); top row b001 b002 b003, bottom row b010 b011 b012 b013 fill [w0, WB]."""
    hb = spec['hb']
    w0 = spec.get('w0', 0.0)
    top = TOP[1:] if w0 else TOP
    e_top = [w0] + list(spec['top']) + [WB]
    e_bot = [w0] + list(spec['bot']) + [WB]
    rows = [(top, e_top, Y0 + hb, Y0 + H), (BOT, e_bot, Y0, Y0 + hb)]
    if w0:
        rows.append((['b000'], [0.0, w0], Y0, Y0 + H))
    out = {}
    for row, e, y0, y1 in rows:
        for i, b in enumerate(row):
            u0, u1 = e[i], e[i + 1]
            if side == 'NE':
                x0, x1 = HUBX[side] + u0, HUBX[side] + u1
            else:
                x0, x1 = HUBX[side] - u1, HUBX[side] - u0
            out[f'{side}_{b}'] = (round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4))
    return out


def shared_edge(a, b, tol=0.5):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    lo, hi = max(ay0, by0), min(ay1, by1)
    if hi - lo > tol:
        if abs(ax1 - bx0) < tol:
            return 'E', lo, hi, ax1
        if abs(bx1 - ax0) < tol:
            return 'W', lo, hi, ax0
    lo, hi = max(ax0, bx0), min(ax1, bx1)
    if hi - lo > tol:
        if abs(ay1 - by0) < tol:
            return 'N', lo, hi, ay1
        if abs(by1 - ay0) < tol:
            return 'S', lo, hi, ay0
    return None


def edge_point(face, c, line):
    return (line, c) if face in 'EW' else (c, line)


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def route(R, start_bank, start_pt, end_bank, end_pt, margin=20.0, start_is_bank=False, end_is_bank=False, smax=405.0,
          avoid=(), start_face=None, end_face=None, width=0, lat_w=None, seg_pen=None):
    """lat_w: cost per um of LATERAL travel (along the entry face) per bit inside a crossed bank: that travel is
    what loads the bank's cuts (check.py cuts); two crossing candidates per edge (hold the coordinate / move toward
    the target) let the router put the lateral travel where it is free (the end banks) or cheap."""
    """Dijkstra over (bank, crossing point): crossing point = clamp of the current point onto the shared edge
    (inside margin).  Returns (cost, [banks], [crossing points])."""
    names = list(R)
    adj = {a: [(b, shared_edge(R[a], R[b])) for b in names if b != a and shared_edge(R[a], R[b])] for a in names}
    # a slot never enters and leaves a bank through the same face (schema: in_face != out_face): the state carries
    # the face the current bank was entered by
    hq = [(0.0, 0, start_bank, start_pt, (start_bank,), (), start_face)]
    best = {}
    while hq:
        d, n, u, p, path, pts, inf = heapq.heappop(hq)
        if u == end_bank:
            if end_face is not None and inf is not None and end_face == inf:
                pass                     # cannot leave through the face it came in by: try further
            else:
                seg = man(p, end_pt)
                crossed = not (end_is_bank or (len(path) == 1 and start_is_bank))
                tot = d + seg + (1000.0 * max(1, math.ceil(seg / smax - 1e-9)) if crossed else 0.0)
                if lat_w is not None and crossed and inf is not None:
                    tot += (abs(p[1] - end_pt[1]) if inf in 'EW' else abs(p[0] - end_pt[0])) * lat_w * width
                if seg_pen is not None and crossed:
                    tot += seg_pen(u, p, end_pt)
                # re-queue as a finished candidate so the cheapest finished route wins
                heapq.heappush(hq, (tot, -1, '__done__', p, path, pts, None))
                continue
        if u == '__done__':
            return d, list(path), list(pts)
        key = (u, round(p[0], 1), round(p[1], 1), inf)
        if key in best and best[key] <= d + EPS:
            continue
        best[key] = d
        if n > 8:
            continue
        for v, (face, lo, hi, line) in adj[u]:
            if v in path or tuple(sorted((u, v))) in avoid or face == inf:
                continue
            pc = p[1] if face in 'EW' else p[0]
            tc = end_pt[1] if face in 'EW' else end_pt[0]
            a_, b_ = sorted((pc, tc))
            L_, H_ = lo + margin, hi - margin
            if L_ > H_:
                L_ = H_ = (lo + hi) / 2
            if max(a_, L_) <= min(b_, H_):
                c = min(max(tc, max(a_, L_)), min(b_, H_))      # move toward the target as early as possible
            else:
                c = L_ if b_ < L_ else H_
            cands = [c]
            if lat_w is not None:
                ch = min(max(pc, L_), H_)                         # hold the coordinate (travel later)
                if abs(ch - c) > 1.0:
                    cands.append(ch)
            crossed = not (len(path) == 1 and start_is_bank)
            for c in cands:
                q = edge_point(face, c, line)
                seg = man(p, q)
                # b000 is the narrow full-height column next to the hub: travel along it costs double (its cuts)
                cst = seg * (2.0 if u.endswith('b000') else 1.0) + 1.0 + \
                    (1000.0 * max(1, math.ceil(seg / smax - 1e-9)) if crossed else 0.0)
                if lat_w is not None and crossed:
                    lat = abs(p[1] - q[1]) if face in 'EW' else abs(p[0] - q[0])
                    if inf is not None and inf in 'NS' and face in 'EW':
                        lat = abs(p[0] - q[0])
                    elif inf is not None and inf in 'EW' and face in 'NS':
                        lat = abs(p[1] - q[1])
                    cst += lat * lat_w * width
                if seg_pen is not None and crossed:
                    cst += seg_pen(u, p, q)
                heapq.heappush(hq, (d + cst, n + 1, v, q, path + (v,), pts + (q,), OPP[face]))
    return None
