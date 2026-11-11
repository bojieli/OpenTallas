"""shelf packer for the ladder bank types: cores sorted by height (desc), shelves bottom-up, lanes on the 4.32
lattice; slack spread evenly between shelves and between cores of a shelf.  Returns {inst: (x, y)} or None."""
import math
G = 4.32


def fl(v):
    return math.floor(v / G + 1e-9) * G


def ce(v):
    return math.ceil(v / G - 1e-9) * G


def shelves_of(W, cores, lane):
    cs = sorted(cores, key=lambda c: (-ce(c['h']), -ce(c['w']), c.get('key', 0)))
    rows, cur, x = [], [], lane
    for c in cs:
        w = ce(c['w'])
        if cur and x + w + lane > W + 1e-6:
            rows.append(cur)
            cur, x = [], lane
        if w + 2 * lane > W + 1e-6:
            return None
        cur.append(c)
        x += w + lane
    if cur:
        rows.append(cur)
    return rows


def pack(W, H, cores, lanes=(34.56, 25.92, 17.28)):
    for lane in lanes:
        rows = shelves_of(W, cores, lane)
        if rows is None:
            continue
        hs = [ce(max(c['h'] for c in r)) for r in rows]
        if sum(hs) + (len(rows) + 1) * lane > H + 1e-6:
            continue
        gy = fl((H - sum(hs)) / (len(rows) + 1))
        place, streets_y, streets_x = {}, [], []
        y = gy
        streets_y.append(gy / 2)
        for r, h in zip(rows, hs):
            # keep old x order inside a shelf (locality)
            r = sorted(r, key=lambda c: c.get('ocx', 0))
            ws = [ce(c['w']) for c in r]
            gx = fl((W - sum(ws)) / (len(r) + 1))
            x = gx
            for c, w in zip(r, ws):
                place[c['inst']] = (round(x, 4), round(y, 4))
                streets_x.append(round(x - gx / 2, 4))
                x += w + gx
            y += h + gy
            streets_y.append(round(y - gy / 2, 4))
        return place, dict(lane_um=lane, shelves=len(rows), gy=gy, streets_y=streets_y,
                           streets_x=sorted(set(streets_x)))
    return None


def min_width(H, cores, lo=200.0):
    w = ce(lo)
    while w < 5000:
        if pack(w, H, cores) is not None:
            return w
        w += G
    return None
