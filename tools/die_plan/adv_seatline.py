"""adv_seatline.py -- PRECHECK ADV-SEATLINE (COORD 11-24, FABLE-RC-QC 749136ed; report only).

QC sle_ctl bus:b_hw_hc1_o seats 1,574 bits at one point (regs_um[0] = 357.3, 318.0): the placer has to pack ~3,000 cells (flops + about
1x logic) into whatever is free around that point, a 128 x 17 um strip -> the GRT hotspot; cbf_q11 has the same shape.  Nothing flagged it.

Per type, for every internal_stations row (stage j seated at regs_um[j], bits per stage = row bits) and ft slot (stage seats regs_um, width
bits; exact bit_sites_um give the seat window):
  cells        = bits x (1 + LOGIC_X)   (LOGIC_X = 1.0: its logic at about 1x its flop count)
  need_side    = sqrt(cells x CELL_UM2 / UTIL)          (UTIL = 0.6 placement utilisation, CELL_UM2 = 0.25 average ASAP7 cell)
  window       = bbox side of the stage's exact bit_sites_um, else 0 (a point seat)
  FLAG NARROW  need_side > MIN_SIDE_UM (20) and window < need_side
  bin density  = cell area per 100 x 100 um bin summed over all stage seats of the type; FLAG HOT: a bin over 2x the median OCCUPIED bin AND over
                 BIN_MIN_UTIL (the bin's seat area > 3 % of the bin)
The two thresholds MIN_SIDE_UM / BIN_MIN_UTIL are mine (the order only says 2x median and the sqrt rule).
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import math
import re
import statistics
import sys
from collections import defaultdict

CHECK = "ADV-SEATLINE"
LOGIC_X = 1.0
CELL_UM2 = 0.25
UTIL = 0.6
MIN_SIDE_UM = 20.0
BIN_UM = 100.0
BIN_MIN_UTIL = 0.03
STRONG_SIDE_UM = 30.0   # strong tier: a seat needing >= this side (~1,100+ bits at one point) or a bin over STRONG_DENS of seat area
STRONG_DENS = 0.30
MAX_LINES = 25


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def need_side(bits, logic_x=LOGIC_X, cell=CELL_UM2, util=UTIL):
    return math.sqrt(bits * (1.0 + logic_x) * cell / util)


def window_side(stage):
    if not stage or not isinstance(stage[0], (list, tuple)):
        return 0.0
    xs = [p[0] for p in stage]
    ys = [p[1] for p in stage]
    return min(max(xs) - min(xs), max(ys) - min(ys)) if len(stage) > 1 else 0.0


_RS = re.compile(r"^u_ist_(.+)_(\d+)[./]q\[\d+\]$")


def bit_seats(t):
    """per-bit seats of a type: {(conn tail, stage j): [(x, y)]} from relay_sites u_ist_<conn>_<j>.q[bit] (the seat the placer is told, one per bit)"""
    out = defaultdict(list)
    for k, v in (t.get("relay_sites") or {}).items():
        m = _RS.match(k)
        if m and isinstance(v, (list, tuple)) and len(v) >= 2:
            out[(m.group(1), int(m.group(2)))].append((v[0], v[1]))
    return out


def seats(t):
    """-> [(name, stage j, (x, y), bits, window_side)] stage seats of one type.  window_side comes from the PER-BIT seats (relay_sites) when the station has them
    (COORD 11-24: the station field bit_sites_um alone gave false strong flags), else from bit_sites_um, else 0 (a point seat)."""
    out = []
    bseat = bit_seats(t)
    for s in t.get("ft_slots") or []:
        if not isinstance(s, dict):
            continue
        regs, bs, w = s.get("regs_um") or [], s.get("bit_sites_um") or [], int(s.get("width") or 0)
        off = 1 if bs and len(bs) == len(regs) - 1 else 0
        for j, p in enumerate(regs):
            st = bs[j - off] if bs and 0 <= j - off < len(bs) else None
            out.append((f"ft {s.get('name')}", j, (p[0], p[1]), w, window_side(st) if st else 0.0, [(q[0], q[1]) for q in st] if st else None))
    for e in t.get("internal_stations") or []:
        if not isinstance(e, dict):
            continue
        regs, bs, b = e.get("regs_um") or [], e.get("bit_sites_um") or e.get("face_bit_sites_um") or [], int(e.get("bits") or 1)
        off = 0 if bs and len(bs) == len(regs) else 1
        for j, p in enumerate(regs):
            st = bs[j - (1 - off if off == 1 else 0) if False else (j if off == 0 else j - 1)] if bs and 0 <= (j if off == 0 else j - 1) < len(bs) else None
            pb = bseat.get((str(e.get("conn")).split(":")[-1], j))
            pts = pb if pb and len(pb) > 1 else ([(q[0], q[1]) for q in st] if st else None)
            out.append((str(e.get("conn")), j, (p[0], p[1]), b, window_side(pts) if pts and len(pts) > 1 else 0.0, pts))
    return out


def judge(ss, logic_x=LOGIC_X, cell=CELL_UM2):
    """-> (narrow [(name, j, bits, window, need)], hot [(bin, density, x_median)], median_density)"""
    narrow, bins = [], defaultdict(float)
    for name, j, xy, bits, win, *rest in ss:
        ns = need_side(bits, logic_x, cell)
        if ns > MIN_SIDE_UM and win < ns:
            narrow.append((name, j, bits, win, ns))
        pts = rest[0] if rest and rest[0] and len(rest[0]) > 1 else None
        area = bits * (1.0 + logic_x) * cell
        if pts:   # per-bit seats: spread the stage's cell area over its seats (the single regs_um point only when there are none)
            for q in pts:
                bins[(int(q[0] // BIN_UM), int(q[1] // BIN_UM))] += area / len(pts)
        else:
            bins[(int(xy[0] // BIN_UM), int(xy[1] // BIN_UM))] += area
    if not bins:
        return narrow, [], 0.0
    med = statistics.median(bins.values())
    hot = [(b, a / (BIN_UM * BIN_UM), a / med if med else 0.0) for b, a in bins.items()
           if med and a > 2 * med and a / (BIN_UM * BIN_UM) > BIN_MIN_UTIL]
    return narrow, sorted(hot, key=lambda h: -h[1]), med / (BIN_UM * BIN_UM)


def _findings(raw, plan_path, tree=None, **kw):
    types = raw.get("partition_types") or {}
    used = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    out, nt, nn, nh, nweak = [], 0, 0, 0, 0
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used):
            continue
        ss = seats(t)
        if not ss:
            continue
        narrow, hot, med = judge(ss)
        weak_n = len(narrow) + len(hot)
        narrow = [x for x in narrow if x[4] >= STRONG_SIDE_UM]
        hot = [x for x in hot if x[1] > STRONG_DENS]
        nweak += weak_n - len(narrow) - len(hot)
        if not narrow and not hot:
            continue
        nt += 1
        nn += len(narrow)
        nh += len(hot)
        nw = max(narrow, key=lambda x: x[2], default=None)
        hb = hot[0] if hot else None
        out.append((max([x[2] for x in narrow] or [0]), _w(
            f"{tn}: {len(narrow)} seat(s) narrower than their cells need" +
            (f" (worst {nw[0]} stage {nw[1]}: {nw[2]:,} bits need a {nw[4]:.0f} um side, window {nw[3]:.0f} um)" if nw else "") +
            f"; {len(hot)} hot 100 um bin(s)" + (f" (worst bin {hb[0]} at {hb[1] * 100:.0f}% seat area = {hb[2]:.1f}x the occupied-bin median)" if hb else "") +
            "; the placer packs these cells into a strip (GRT hotspot); fix: give the station exact bit sites over a window of the needed side, or split it over stages / bins")))
    out.sort(key=lambda x: -x[0])
    lines = [m for _, m in out[:MAX_LINES]]
    lines.append(_w("summary", f"{nt} type(s) flagged strong: {nn} narrow seat(s) needing >= {STRONG_SIDE_UM:g} um, {nh} bin(s) over {STRONG_DENS * 100:.0f}% seat area (+{nweak} weaker narrow/hot items counted, not listed: most stations are point seats); model cells = bits x {1 + LOGIC_X:g}, {CELL_UM2} um2/cell, util {UTIL}, "
                               f"min side {MIN_SIDE_UM:g} um, hot = >2x median occupied bin and > {BIN_MIN_UTIL * 100:.0f}% of the bin (thresholds are mine)"))
    return lines


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import json
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1]):
        print(ln)
