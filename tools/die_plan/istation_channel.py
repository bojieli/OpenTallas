"""KIT-CHAN-1 (DIE-QC-97 11-11): plan internal_stations[].leg_order "channel" -- the per-bit Z route of a core pin-face
chain through a declared channel, shared by the kit (kit_istations TCL_CHAN is_chan_bits), taps.per_bit_station_sites
and the plan gates (kit_istations.chain_macro_hits).

Why: along_first runs every bit's first leg along the face at the pin column, so 500-1300 bits stack in one gcell
column (su_l route_supply face/ring V p99 ~2.6 with per-bit legs); a channel spreads them over a band of columns.

Geometry (E/W bus face; N/S is the transpose), bit b of a bus with nbits = bound width + 1 (payload + epoch):
  col_b = lo + (hi - lo) * (b + 0.5) / nbits          channel_um = [lo, hi] along x (E/W face) / y (N/S face)
  in  bus: pin (px, py) -> (col_b, py) -> (col_b, ly) -> leaf (lx, ly)
  out bus: the same polyline from the leaf: leaf -> (col_b, ly) -> (col_b, py) -> pin
Stations: edge e of edges = n + 1 sits at arclength L_b * e / edges from the path start (per bit, no shared split),
so every planned hop of bit b is L_b / edges; the kit fails closed when L_b / edges > KIT_LIMIT_UM."""

KIT_LIMIT_UM = 403.0
ORDERS = ("normal_first", "along_first", "channel")


def column(lo, hi, bit, nbits):
    return lo + (hi - lo) * (bit + 0.5) / max(1, nbits)


def path(px, py, lx, ly, face, direction, col):
    """the bit's polyline from the chain start (pin for in, leaf for out)"""
    if face in ("E", "W"):
        pts = [(px, py), (col, py), (col, ly), (lx, ly)]
    else:
        pts = [(px, py), (px, col), (lx, col), (lx, ly)]
    return pts if direction == "in" else pts[::-1]


def length(pts):
    return sum(abs(a[0] - c[0]) + abs(a[1] - c[1]) for a, c in zip(pts, pts[1:]))


def point_at(pts, t):
    for (ax, ay), (cx, cy) in zip(pts, pts[1:]):
        d = abs(ax - cx) + abs(ay - cy)
        if t <= d:
            f = 0.0 if d == 0 else t / d
            return (ax + f * (cx - ax), ay + f * (cy - ay))
        t -= d
    return pts[-1]


def sites(px, py, lx, ly, face, direction, lo, hi, bit, nbits, n):
    """[(x, y)] of the n stations of bit b, in chain order from the path start"""
    pts = path(px, py, lx, ly, face, direction, column(lo, hi, bit, nbits))
    L = length(pts)
    return [point_at(pts, L * (k + 1) / (n + 1)) for k in range(n)]


def worst_hop(px, py, lx, ly, face, direction, lo, hi, bit, nbits, n):
    return length(path(px, py, lx, ly, face, direction, column(lo, hi, bit, nbits))) / (n + 1)


def legs(px, py, lx, ly, face, lo, hi, bit, nbits):
    """the bit's three route segments (direction-free, for macro checks)"""
    pts = path(px, py, lx, ly, face, "in", column(lo, hi, bit, nbits))
    return list(zip(pts, pts[1:]))


def entry_channel(e):
    """(lo, hi) of a channel chain; SystemExit when channel_um is missing / malformed"""
    c = e.get("channel_um")
    if not (isinstance(c, (list, tuple)) and len(c) == 2 and all(isinstance(v, (int, float)) for v in c) and c[0] <= c[1]):
        raise SystemExit(f"internal station {e.get('conn')} {e.get('core')}: leg_order channel needs channel_um [lo, hi] "
                         f"(lo <= hi), got {c!r}")
    return float(c[0]), float(c[1])
