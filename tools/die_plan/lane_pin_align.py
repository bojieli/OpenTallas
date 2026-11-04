#!/usr/bin/env python3
"""DIE-HBM-59/CORES 11-02: MACRO-ARRAY ONE-FACE PINS class fix -- lane-grouped face pins under each lane's macro.

Why: macro-array hard cores whose pins sit on one face can still close when each lane's pins sit next to the macro the
lane serves.  ot_hbm_su_static_sfustore_hw (16 x 1r1w_128x256 banks in 3 columns) had its 1829 pins grouped BY SIGNAL
KIND (all 16 lanes' we/re at x 9-15, every waddr/addr at x 16-160, every wdata/q at x 160-335, lanes 14/15 + fault
spilled onto E/M4 because the pins file predates the 362.88 outline): bank k's address and data pins were up to 300 um
apart and far from bank k's column -> AUTO-GEOM r2r 563 (34 captures > 405) + relay_collapse 8 (COORD GEOM 11-02).

What: per lane (pin base name matching --lane-re, group 1 = lane index) the macro whose instance name matches
--macro-re with the same index gives the lane's column (macro x-range for an S/N face, y-range for W/E).  Lanes of a
column are packed contiguously around the column centre (on --pitch-tracks x the layer track pitch, track-aligned);
inside a column the lanes whose macro is FARTHEST from the face go to the segment centre.  Segments overlapping a
neighbour are pushed apart, then clamped into the face.  Pins that belong to no lane keep their position when it is
on the face and free, else they are placed in the nearest free track slot to --misc-at.  One face, one layer: the
slot side of the core does not change, so the parent sees the same face; only coordinates along it move.  The bit
order inside every bus is kept.  Output is a new pins file (same record schema: name/layer/x/y/w/h).

    python3 tools/die_plan/lane_pin_align.py PINS_IN.json CORE_MACROS.json MODULE OUTLINE_W OUTLINE_H PINS_OUT.json \
        [--face S] [--layer M5] [--pitch-tracks 4] [--lane-re '^l(\\d+)_'] [--macro-re 'g_bank\\[(\\d+)\\]'] [--misc-at 0.5]
"""
import argparse, collections, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402

FACE_AXIS = {'S': 'x', 'N': 'x', 'W': 'y', 'E': 'y'}


def track(layer):
    for t in S.TRACKS if hasattr(S, 'TRACKS') else []:
        if t['name'] == layer:
            return t['pitch_um'], t['offset_um']
    return {'M4': (0.048, 0.024), 'M5': (0.048, 0.024), 'M6': (0.064, 0.032), 'M7': (0.064, 0.032)}[layer]


def base(name):
    return re.sub(r'\[\d+\]$', '', name)


def bit(name):
    m = re.search(r'\[(\d+)\]$', name)
    return int(m.group(1)) if m else -1


def plan(pins, macros, W, H, face='S', layer='M5', pitch_tracks=4, lane_re=r'^l(\d+)_', macro_re=r'g_bank\[(\d+)\]',
         misc_at=0.5, keep=('clk',)):
    ax = FACE_AXIS[face]
    L = W if ax == 'x' else H
    tp, to = track(layer)
    pitch = tp * pitch_tracks
    lre, mre = re.compile(lane_re), re.compile(macro_re)
    mac = {}
    for m in macros:
        g = mre.search(m['name'])
        if g:
            mac[int(g.group(1))] = m['rect_um']
    groups = collections.OrderedDict()
    misc = []
    for q in pins:
        g = lre.match(base(q['name']))
        if g and int(g.group(1)) in mac:
            groups.setdefault(int(g.group(1)), []).append(q)
        else:
            misc.append(q)
    # columns: macros sharing the along-face range
    def span(r):
        return (r[0], r[2]) if ax == 'x' else (r[1], r[3])

    def depth(r):  # distance of the macro's far edge from the face
        return {'S': r[3], 'N': H - r[1], 'W': r[2], 'E': W - r[0]}[face]
    cols = collections.OrderedDict()
    for k in sorted(groups):
        a, b = span(mac[k])
        key = round((a + b) / 2, 1)
        cols.setdefault(key, []).append(k)
    # per column: lane order, farthest macro at the centre
    segs = []
    for c in sorted(cols):
        lanes = sorted(cols[c], key=lambda k: -depth(mac[k]))  # farthest first
        order = []
        for i, k in enumerate(lanes):  # farthest in the middle, nearer lanes alternate outwards
            if i % 2:
                order.insert(0, k)
            else:
                order.append(k)
        n = sum(len(groups[k]) for k in order) + 1  # +1: room to step over one fixed pin
        segs.append([c - n * pitch / 2, n, order])
    # push overlapping segments apart (left to right), then clamp into [pitch, L - pitch]
    lo_lim, hi_lim = 2 * pitch, L - 2 * pitch
    for i in range(len(segs)):  # forward: no overlap, not below the face start
        lo = lo_lim if i == 0 else segs[i - 1][0] + segs[i - 1][1] * pitch + pitch
        segs[i][0] = max(segs[i][0], lo)
    for i in range(len(segs) - 1, -1, -1):  # backward: not beyond the face end, no overlap
        hi = hi_lim if i == len(segs) - 1 else segs[i + 1][0] - pitch
        segs[i][0] = min(segs[i][0], hi - segs[i][1] * pitch)
    if segs and segs[0][0] < lo_lim - 1e-6:
        raise SystemExit('lane pins do not fit the %s face (%.2f um, pitch %.3f): first segment at %.2f'
                         % (face, L, pitch, segs[0][0]))

    ti = lambda v: int(round((v - to) / tp))  # noqa: E731  track index along the face
    tv = lambda i: round(to + i * tp, 4)  # noqa: E731
    fp = [q for q in pins if q['layer'] == layer and
          {'S': q['y'], 'N': H - q['y'], 'W': q['x'], 'E': W - q['x']}[face] < 1.0]
    off = collections.Counter(round({'S': q['y'], 'N': H - q['y'], 'W': q['x'], 'E': W - q['x']}[face], 4)
                              for q in fp).most_common(1)[0][0] if fp else 0.096
    used = set()
    out = []
    fixed = [q for q in misc if q['name'] in keep]
    misc = [q for q in misc if q['name'] not in keep]
    for q in fixed:
        out.append(dict(q))
        used.add(ti(q['x'] if ax == 'x' else q['y']))
    free = lambda i: all(abs(i - u) >= pitch_tracks for u in used)  # noqa: E731

    def put(q, i):
        used.add(i)
        a = tv(i)
        x, y = {'S': (a, off), 'N': (a, H - off), 'W': (off, a), 'E': (W - off, a)}[face]
        r = dict(q)  # the record keeps its own fields (w/h only where the source pin had them)
        r.update(layer=layer, x=round(x, 4), y=round(y, 4))
        out.append(r)
    ledger = []
    i_lo, i_hi = ti(lo_lim), ti(hi_lim)
    nxt = i_lo
    for start, n, order in segs:
        i = max(ti(start), nxt)
        for k in order:
            g = sorted(groups[k], key=lambda q: (base(q['name']), bit(q['name'])))
            i0 = i
            for q in g:
                while not free(i):
                    i += 1
                put(q, i)
                i += pitch_tracks
            ledger.append(dict(lane=k, macro_span=span(mac[k]), macro_depth=round(depth(mac[k]), 2),
                               pins=len(g), along=[tv(i0), tv(i - pitch_tracks)]))
        nxt = i
    if nxt - pitch_tracks > i_hi:
        raise SystemExit('lane pins overrun the %s face end (%.3f > %.3f)' % (face, tv(nxt - pitch_tracks), hi_lim))
    # misc pins: keep if on this face/layer and free, else nearest free slot to misc_at * L
    for q in misc:
        on_face = q['layer'] == layer and {'S': q['y'], 'N': H - q['y'], 'W': q['x'], 'E': W - q['x']}[face] < 1.0
        i = ti(q['x'] if ax == 'x' else q['y'])
        if on_face and free(i):
            out.append(dict(q))
            used.add(i)
            continue
        t = ti(misc_at * L)
        for d in range(0, i_hi - i_lo):
            c = next((c for c in (t + d, t - d) if i_lo <= c <= i_hi and free(c)), None)
            if c is not None:
                put(q, c)
                break
        else:
            raise SystemExit('no free slot for %s' % q['name'])
    assert len(out) == len(pins) and len({p['name'] for p in out}) == len(pins)
    return out, ledger


def spread(pins, W, H, face='W', layer='M4', lo=None, hi=None, keep=('clk',)):
    """--mode spread: the face's pins keep their order along the face but are spread evenly over [lo, hi] (default
    the whole face minus 2 um), each on its own track of LAYER; pins not on FACE (and KEEP pins) are unchanged."""
    ax = FACE_AXIS[face]
    L = W if ax == 'x' else H
    tp, to = track(layer)
    dist = lambda q: {'S': q['y'], 'N': H - q['y'], 'W': q['x'], 'E': W - q['x']}[face]  # noqa: E731
    on = sorted([q for q in pins if dist(q) < 1.0 and q['name'] not in keep], key=lambda q: q[ax])
    lo = 2.0 if lo is None else lo
    hi = L - 2.0 if hi is None else hi
    i0, i1 = int(round((lo - to) / tp)), int(round((hi - to) / tp))
    if len(on) > i1 - i0 + 1:
        raise SystemExit('%d pins do not fit %d tracks' % (len(on), i1 - i0 + 1))
    step = (i1 - i0) / max(1, len(on) - 1)
    off = collections.Counter(round(dist(q), 4) for q in on).most_common(1)[0][0]
    moved, out = {}, []
    for n, q in enumerate(on):
        a = round(to + (i0 + int(round(n * step))) * tp, 4)
        x, y = {'S': (a, off), 'N': (a, H - off), 'W': (off, a), 'E': (W - off, a)}[face]
        moved[q['name']] = dict(q, layer=layer, x=round(x, 4), y=round(y, 4))
    for q in pins:
        out.append(moved.get(q['name'], dict(q)))
    got = sorted(r[ax] for r in moved.values())
    assert all(b - a >= tp - 1e-6 for a, b in zip(got, got[1:]))
    return out, dict(face=face, layer=layer, pins=len(on), lo=lo, hi=hi, pitch_um=round(step * tp, 4),
                     pins_per_um=round(len(on) / (hi - lo), 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pins_in'); ap.add_argument('core_macros'); ap.add_argument('module')
    ap.add_argument('W', type=float); ap.add_argument('H', type=float); ap.add_argument('pins_out')
    ap.add_argument('--face', default='S'); ap.add_argument('--layer', default='M5')
    ap.add_argument('--pitch-tracks', type=int, default=4)
    ap.add_argument('--lane-re', default=r'^l(\d+)_'); ap.add_argument('--macro-re', default=r'g_bank\[(\d+)\]')
    ap.add_argument('--misc-at', type=float, default=0.5)
    ap.add_argument('--mode', default='lane', choices=['lane', 'spread'])
    ap.add_argument('--keep', default='clk', help='comma list of pins kept exactly where they are (clock entry, '
                    'pins whose partner lies on another face, e.g. fault)')
    ap.add_argument('--lo', type=float); ap.add_argument('--hi', type=float)
    a = ap.parse_args()
    pins = json.load(open(a.pins_in))
    if a.mode == 'spread':
        out, rep = spread(pins, a.W, a.H, a.face, a.layer, a.lo, a.hi, tuple(a.keep.split(',')))
        Path(a.pins_out).write_text(json.dumps(out, indent=0) + '\n')
        rep.update(schema='opentallas.lane_pin_align.v1', mode='spread', module=a.module, outline_um=[a.W, a.H])
        Path(a.pins_out).with_suffix('.ledger.json').write_text(json.dumps(rep, indent=1) + '\n')
        print(json.dumps(rep))
        return
    cm = json.load(open(a.core_macros))
    macros = (cm.get('cores', cm)[a.module])['macros']
    out, ledger = plan(pins, macros, a.W, a.H, a.face, a.layer, a.pitch_tracks, a.lane_re, a.macro_re, a.misc_at,
                       tuple(a.keep.split(',')))
    Path(a.pins_out).write_text(json.dumps(out, indent=0) + '\n')
    rep = dict(schema='opentallas.lane_pin_align.v1', module=a.module, outline_um=[a.W, a.H], face=a.face,
               layer=a.layer, pitch_um=round(track(a.layer)[0] * a.pitch_tracks, 4), pins=len(out), lanes=ledger)
    Path(a.pins_out).with_suffix('.ledger.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: v for k, v in rep.items() if k != 'lanes'}), len(ledger), 'lanes')


if __name__ == '__main__':
    main()
