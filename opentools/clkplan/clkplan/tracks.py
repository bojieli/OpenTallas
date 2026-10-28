"""Top-metal track demand vs supply for the clock, per layer and per channel bin.

SUPPLY (per layer, from the PG stripe pattern, the clock NDR and the pin windows):
  the PG pattern repeats every pitch_um; between two stripes is a gap.  A clock wire of width w with spacing s fits:
    shield 'none'      k = floor((gap - s) / (w + s)) wires per gap
    shield 'drawn'     each wire carries two drawn shields of width ws: footprint F = w + 2 (s + ws),
                       k = floor((gap - s) / (F + s))
    shield 'pg_flank'  the neighbouring PG stripes are the shields: at most ONE wire per gap, centred in it,
                       if gap >= w + 2 s
  a slot is WINDOW-BLOCKED when its conductor (grown by s) overlaps a pin window (cell pin-access band of an
  island / slot row, e.g. +-2.5 um around each row).  Window slots serve only the trunk of the cell on that row;
  every other clock wire (an escape, a second trunk, a jog around a cell) needs an OFF-WINDOW slot.
DEMAND (per channel bin of the planned tree, layer by leg direction: H legs on clock.layers.H, V on .V):
  trunks  = max number of distinct clock legs overlapping along the bin (interval depth);
  escapes = repeaters / nodes on a straight run whose in and out pins share one track (non flow-oriented cells):
            one extra off-window slot each (0 when flow_oriented_repeaters is set).
CHECK per bin: trunks + escapes <= fill * slots (fill = 0.6, METHODOLOGY 12.4c), escapes <= off-window slots.
"""
import math
from fractions import Fraction


def _frac(x):
    return Fraction(x).limit_denominator(1000)


def gaps(pg_layer, span):
    """[(lo, hi)] free intervals between stripes over [0, span) for a periodic stripe pattern."""
    P = pg_layer["pitch_um"]
    st = sorted((s["offset_um"], s["width_um"]) for s in pg_layer.get("stripes", []))
    if not st:
        return [(0.0, span)]
    out = []
    k0 = -1
    k1 = int(math.ceil(span / P)) + 1
    edges = []
    for k in range(k0, k1 + 1):
        for o, w in st:
            c = k * P + o
            edges.append((c - w / 2, c + w / 2))
    edges.sort()
    for (a0, a1), (b0, b1) in zip(edges, edges[1:]):
        lo, hi = a1, b0
        if hi > lo and hi > 0 and lo < span:
            out.append((lo, hi))
    return out


def slots_in_gap(lo, hi, ndr):
    w, s = ndr["width_um"], ndr["space_um"]
    mode = ndr.get("shield", "none")
    g = hi - lo
    if mode == "pg_flank":
        return [((lo + hi) / 2 - w / 2, (lo + hi) / 2 + w / 2)] if g >= w + 2 * s - 1e-9 else []
    F = w + 2 * (s + (ndr.get("shield_width_um") or w)) if mode == "drawn" else w
    k = int(math.floor((g - s) / (F + s) + 1e-9))
    out = []
    x = lo + s
    for _ in range(max(0, k)):
        c = x + F / 2
        out.append((c - w / 2, c + w / 2))
        x += F + s
    return out


def window_intervals(win, span):
    """pin windows on one layer over [0, span): rows{pitch_um, offset_um, half_um} or positions_um + half_um."""
    h = win.get("half_um", win.get("rows", {}).get("half_um", 0.0))
    if "rows" in win:
        P, o = win["rows"]["pitch_um"], win["rows"]["offset_um"]
        k0, k1 = -1, int(math.ceil(span / P)) + 1
        return [(k * P + o - h, k * P + o + h) for k in range(k0, k1 + 1)]
    return [(p - h, p + h) for p in win.get("positions_um", [])]


def layer_supply(pg_layer, ndr, windows=(), span=None):
    """slot census of one layer over one common period of the PG and window patterns.
    -> dict(period_um, slots, off_window, in_window, per_um, off_window_per_um, gap_um[min,max])"""
    P = pg_layer["pitch_um"]
    per = _frac(P)
    for w in windows:
        if "rows" in w:
            q = _frac(w["rows"]["pitch_um"])
            per = _lcm(per, q)
    span = span or float(per)
    if span > 200 * P:
        span = 200 * P
    # one full period of gaps: take the gaps whose centre lies in [span, 2 span) of a 3-period window, shifted back
    G = [(lo - span, hi - span) for lo, hi in gaps(pg_layer, 3 * span) if span - 1e-9 <= (lo + hi) / 2 < 2 * span - 1e-9]
    W = [(a - span, b - span) for w in windows for a, b in window_intervals(w, 3 * span)]
    s = ndr["space_um"]
    slots = [sl for lo, hi in G for sl in slots_in_gap(lo, hi, ndr)]
    blocked = [sl for sl in slots if any(sl[0] - s < b and sl[1] + s > a for a, b in W)]
    off = len(slots) - len(blocked)
    gw = [hi - lo for lo, hi in G]
    return dict(period_um=round(span, 4), slots=len(slots), in_window=len(blocked), off_window=off,
                per_um=len(slots) / span, off_window_per_um=off / span,
                gap_um=[round(min(gw), 3), round(max(gw), 3)] if gw else None)


def _lcm(a, b):
    """lcm of two positive Fractions."""
    n = a.numerator * b.numerator // math.gcd(a.numerator, b.numerator)
    return Fraction(n, math.gcd(a.denominator, b.denominator))


def _depth(ivs):
    ev = sorted([(lo, 1) for lo, hi in ivs] + [(hi, -1) for lo, hi in ivs], key=lambda e: (e[0], e[1]))
    d = m = 0
    for _, e in ev:
        d += e
        m = max(m, d)
    return m


def demand_bins(T, layer_dir, bin_um, W, H, flow_oriented=False, esc_um=10.0):
    """per bin of width bin_um across the run direction: max trunk depth and max (trunk + escape) depth, where every
    repeater on a run adds a local escape interval of +-esc_um (its in and out pins share the run's track)."""
    nb = int(math.ceil((H if layer_dir == "H" else W) / bin_um)) + 1
    ivs = [[] for _ in range(nb)]
    esc = [[] for _ in range(nb)]
    for lg in T.legs:
        a, b = T.cells[lg["parent"]]["xy"], T.cells[lg["child"]]["xy"]
        corner = (b[0], a[1]) if lg["route"] == "x_first" else (a[0], b[1])
        for p, q in ((a, corner), (corner, b)):
            horiz = abs(p[1] - q[1]) < 1e-9 and abs(p[0] - q[0]) > 1e-9
            vert = abs(p[0] - q[0]) < 1e-9 and abs(p[1] - q[1]) > 1e-9
            if not ((layer_dir == "H" and horiz) or (layer_dir == "V" and vert)):
                continue
            c = p[1] if horiz else p[0]
            lo, hi = sorted((p[0], q[0]) if horiz else (p[1], q[1]))
            j = min(nb - 1, max(0, int(c // bin_um)))
            ivs[j].append((lo, hi))
            if flow_oriented:
                continue
            for r in lg.get("reps", []):
                along, perp = (r[0], r[1]) if horiz else (r[1], r[0])
                if lo - 1e-6 <= along <= hi + 1e-6 and abs(perp - c) <= 3 * T.cfg["step_um"]:
                    esc[j].append((along - esc_um, along + esc_um))
    out = []
    for j in range(nb):
        if not ivs[j]:
            continue
        out.append(dict(bin=j, at_um=round(j * bin_um, 2), trunks=_depth(ivs[j]), escapes=len(esc[j]),
                        escape_depth=_depth(esc[j]) if esc[j] else 0, total_depth=_depth(ivs[j] + esc[j])))
    return out


def check(P, T, fill=0.6, bin_um=None):
    """per clock layer: supply census + worst bins.  -> dict(layers{...}, fails[...])"""
    ck = P["clock"]
    ndr = ck["ndr"]
    res, fails = {}, []
    if ndr.get("width_um") is None:
        return dict(layers={}, fails=[], note="clock.ndr.width_um not given: track check skipped")
    W, H = P["die"]["w"], P["die"]["h"]
    for d in ("H", "V"):
        lname = ck["layers"].get(d)
        if not lname:
            continue
        pg = next((g for g in P["pg"] if g["layer"] == lname), None)
        if pg is None:
            pg = dict(layer=lname, dir=d, pitch_um=1.0, stripes=[])
        wins = [w for w in P["pin_windows"] if w["layer"] == lname]
        sup = layer_supply(pg, ndr, wins)
        bu = max(bin_um or 0.0, T.cfg["step_um"], pg["pitch_um"])
        bins = demand_bins(T, d, bu, W, H, flow_oriented=bool(ck.get("flow_oriented_repeaters")))
        slots_bin = sup["per_um"] * bu
        off_bin = sup["off_window_per_um"] * bu
        bad = []
        for b in bins:
            if b["total_depth"] > max(1.0, fill * slots_bin) + 1e-9 or (b["escape_depth"] > off_bin + 1e-9):
                bad.append(dict(b, slots=round(slots_bin, 2), off_window_slots=round(off_bin, 2)))
        res[lname] = dict(dir=d, supply=sup, bin_um=bu, bins=len(bins), bins_over=len(bad),
                          max_trunks=max((b["trunks"] for b in bins), default=0),
                          escapes=sum(b["escapes"] for b in bins), worst=sorted(bad, key=lambda b: -b["total_depth"])[:10])
        if bad:
            fails.append(f"{lname}: {len(bad)}/{len(bins)} clock channel bins over capacity (bin {bu:g} um: slots "
                         f"{slots_bin:.2f}, off-window {off_bin:.2f}, fill {fill})")
        if sup["off_window"] == 0 and wins:
            fails.append(f"{lname}: 0 off-window clock slots per {sup['period_um']} um period (PG gaps "
                         f"{sup['gap_um']} um, NDR w {ndr['width_um']} s {ndr['space_um']} shield {ndr.get('shield')}): "
                         "no escape / second trunk can route outside the pin windows")
    return dict(layers=res, fails=fails)
