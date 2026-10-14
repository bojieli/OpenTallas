#!/usr/bin/env python3
"""S81 die CUT TABLE from the PLAN (before any GRT; owner 2026-10-12: bits per cut against tracks <= 0.55-0.60 in every
die spec).  Input: plan.json.gz of tools/s81/c5diag_v15_dump.py (instances + every pin-to-pin hop with the first and the
last bit's coordinates).  Output: cuts.json + CUTS.md.

Accounting (the c5diag_cuts.py method, with a MODEL supply because no route exists yet):
  CUT       a line segment: vertical x = X over [y0, y1] (crossed by horizontal wires: M4, M6) or horizontal y = Y over
            [x0, x1] (M5, M7).  M8 / M9 are the die's power and global nets: reported apart, not in the ratio.
  SUPPLY    free length of the segment (not under any placed instance: every master is taken to block M4..M7 over its
            outline -- M5-capped tiles would leave M6 / M7, so this is the conservative side) x tracks per um:
            M4, M5 at 0.048 pitch x 0.70 (c5 GRT: 30 % layer adjustment), M6, M7 at 0.064 x 0.854.
  DEMAND    bits of the plan's hops whose two pins lie on opposite sides of the line; each bit is spread uniformly over
            the extent of its two pins along the line (an L route may cross anywhere in it); 'captive' = the bits
            whose whole extent is inside the segment.
  RATIO     demand share / supply; WATCH > 0.55, OVER > 0.60.
Cuts taken: (a) the four faces of every hub slab / service (line 4.32 um outside the face, the face span); (b) every
straight VCH lane between two slabs (mid-gap line over the lane rows); (c) JOG cuts where a 2-track hub pin group
meets a 1-track first station (--lane-pins 2 vs dsfd_hstn): horizontal lines through the pin span, between the pin
face and the station face; (d) a 480-um scan of the field frame columns' relay channels is NOT taken here (the field
is judged by the die GRT: 61.9 % of the c5 overflow was field-frame pin access, a pin problem, not a cut).

usage: c5diag_plan_cuts.py PLAN.json.gz OUT_DIR [--min-bits 64]"""
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

TPU = {'v': 0.70 / 0.048 + 0.854 / 0.064, 'h': 0.70 / 0.048 + 0.854 / 0.064}     # tracks per um of free cut length (M4+M6 | M5+M7)
TPU89 = 1 / 0.08
EX = ('clock_trunk', 'reset', 'reset_tree', 'clock', 'col_clock', 'col_reset', 'fclk', 'top_in')


def free_len(insts, vert, c, a0, a1):
    """length of the segment not under an instance outline"""
    cov = []
    for n, mst, x, y, w, h, o, kind, reg in insts:
        lo, hi, p0, p1 = (y, y + h, x, x + w) if vert else (x, x + w, y, y + h)
        if p0 < c < p1 and hi > a0 and lo < a1:
            cov.append((max(lo, a0), min(hi, a1)))
    cov.sort()
    tot, cur = 0.0, a0
    for lo, hi in cov:
        if hi > cur:
            tot += hi - max(lo, cur)
            cur = hi
    return max(0.0, (a1 - a0) - tot)


def demand(hops, vert, c, a0, a1):
    share, captive, fam = 0.0, 0, defaultdict(float)
    for bid, cls, bits, da, dp, li, lp, first, last, mn, mx in hops:
        if cls in EX or first is None:
            continue
        for k, q in ((0.5, first), (0.5, last)) if bits > 1 else ((1.0, first),):
            xa, ya, xb, yb = q
            u0, u1, v0, v1 = (xa, xb, ya, yb) if vert else (ya, yb, xa, xb)
            if (u0 - c) * (u1 - c) >= 0:
                continue
            lo, hi = min(v0, v1), max(v0, v1)
            ext = max(hi - lo, 1.0)
            ov = max(0.0, min(hi, a1) - max(lo, a0)) if hi - lo >= 1.0 else (1.0 if a0 <= lo <= a1 else 0.0)
            s = bits * k * (ov / ext)
            if s:
                share += s
                fam[f'{cls}:{da.rstrip("0123456789_")}->{li.rstrip("0123456789_")}'] += s
                if lo >= a0 and hi <= a1:
                    captive += bits * k
    return share, captive, sorted(fam.items(), key=lambda kv: -kv[1])[:4]


def main():
    plan = json.load(gzip.open(sys.argv[1]))
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    minb = int(sys.argv[sys.argv.index('--min-bits') + 1]) if '--min-bits' in sys.argv else 64
    insts, hops = plan['insts'], plan['hops']
    by = {i[0]: i for i in insts}
    cuts = []
    # (a) slab faces
    for n, mst, x, y, w, h, o, kind, reg in insts:
        if kind not in ('hub', 'svc', 'ctrl', 'band_blk', 'phy', 'host'):
            continue
        for f, vert, c, a0, a1 in (('W', True, x - 4.32, y, y + h), ('E', True, x + w + 4.32, y, y + h),
                                   ('S', False, y - 4.32, x, x + w), ('N', False, y + h + 4.32, x, x + w)):
            cuts.append((f'face {n}.{f}', 'face', vert, c, a0, a1))
    # (c) pin-group jogs: both ends of a hop spread their bits along the SAME axis (facing faces) with different spans or
    # centres (2-track hub pins against a 1-track station, or a centred group against an off-centre peer): every bit
    # shifts along that axis inside the gap between the two faces and crosses the lines normal to it there.
    BIG = ('hub', 'svc', 'ctrl', 'band_blk', 'svcj', 'host')
    seen = set()
    for bid, cls, bits, da, dp, li, lp, first, last, mn, mx in hops:
        if cls in EX or first is None or bits < minb:
            continue
        A, B = by[da], by[li]
        if A[7] not in BIG and B[7] not in BIG:
            continue
        xa, ya, xb, yb = first
        xa2, ya2, xb2, yb2 = last
        ax_a = 'y' if abs(ya2 - ya) > abs(xa2 - xa) else 'x'
        ax_b = 'y' if abs(yb2 - yb) > abs(xb2 - xb) else 'x'
        if ax_a != ax_b or (da, dp, li) in seen:
            continue
        seen.add((da, dp, li))
        if ax_a == 'y':      # pins along y on facing E / W faces: gap in x, horizontal cut lines, vertical tracks
            p0, p1, q0, q1, g0, g1 = ya, ya2, yb, yb2, min(xa, xb), max(xa, xb)
        else:                # pins along x on facing N / S faces: gap in y, vertical cut lines, horizontal tracks
            p0, p1, q0, q1, g0, g1 = xa, xa2, xb, xb2, min(ya, yb), max(ya, yb)
        if abs(abs(p1 - p0) - abs(q1 - q0)) <= 2.0 and abs((p0 + p1) - (q0 + q1)) / 2 <= 2.0:
            continue         # bit-aligned: no jog
        s0, s1 = min(p0, p1, q0, q1), max(p0, p1, q0, q1)
        worst, jmax = None, 0.0
        for j in range(64):
            t = (j + 0.5) / 64
            jmax = max(jmax, abs((p0 + (p1 - p0) * t) - (q0 + (q1 - q0) * t)))
        for k in range(1, 32):
            C = s0 + (s1 - s0) * k / 32
            cross = sum(bits / 64 for j in range(64)
                        if ((p0 + (p1 - p0) * (j + 0.5) / 64) - C) * ((q0 + (q1 - q0) * (j + 0.5) / 64) - C) < 0)
            fl = free_len(insts, ax_a != 'y', C, g0, g1) if g1 - g0 > 0.1 else 0.0
            sup = fl * TPU['h']
            r = cross / sup if sup else (float('inf') if cross else 0.0)
            if worst is None or r > worst[0]:
                worst = (r, C, cross, sup)
        cuts.append((f'jog {da}.{dp} -> {li}.{lp} ({bits} b; spans {abs(p1 - p0):.0f} / {abs(q1 - q0):.0f} um, gap {g1 - g0:.0f} um, max jog {jmax:.0f} um)',
                     'jog', ax_a != 'y', worst[1], g0, g1, worst))
    rows = []
    for cdef in cuts:
        name, typ, vert, c, a0, a1 = cdef[:6]
        if typ == 'jog':
            r, Y, cross, sup = cdef[6]
            rows.append(dict(cut=name, type=typ, line=('x' if vert else 'y') + f' = {c:.1f}', span=[round(a0, 1), round(a1, 1)],
                             demand_bits=round(cross), captive_bits=round(cross), supply_tracks_m4_m7=round(sup),
                             ratio=(None if cross else 0.0) if sup == 0 else round(r, 3), families=[]))
            continue
        sh, cap, fam = demand(hops, vert, c, a0, a1)
        if sh < minb:
            continue
        fl = free_len(insts, vert, c, a0, a1)
        sup = fl * TPU['v' if vert else 'h']
        rows.append(dict(cut=name, type=typ, line=('x' if vert else 'y') + f' = {c:.1f}', span=[round(a0, 1), round(a1, 1)],
                         free_um=round(fl, 1), demand_bits=round(sh), captive_bits=cap, supply_tracks_m4_m7=round(sup),
                         supply_m8_m9=round((a1 - a0) * TPU89), ratio=None if sup == 0 else round(sh / sup, 3),
                         families=[(k, round(v)) for k, v in fam]))
    rows.sort(key=lambda r: -(r['ratio'] if r['ratio'] is not None else 9e9))
    over = [r for r in rows if r['ratio'] is None or r['ratio'] > 0.60]
    watch = [r for r in rows if r['ratio'] is not None and 0.55 < r['ratio'] <= 0.60]
    rec = dict(tool='tools/s81/c5diag_plan_cuts.py', plan=sys.argv[1], model=__doc__.split('Accounting')[1].split('usage')[0][:1400],
               cuts=len(rows), over_0p60=len(over), watch_0p55=len(watch), worst=rows[0] if rows else None, rows=rows)
    (out / 'cuts.json').write_text(json.dumps(rec, indent=1) + '\n')
    md = ['# S81 die cut table from the plan (model supply, before GRT)', '',
          f'{len(rows)} cuts with >= {minb} bits; OVER 0.60: {len(over)}; WATCH 0.55-0.60: {len(watch)}.', '',
          '| cut | line | span um | free um | demand b | captive b | supply M4-M7 | ratio | families |', '|---|---|---|---:|---:|---:|---:|---:|---|']
    for r in rows[:60]:
        md.append(f"| {r['cut']} | {r['line']} | {r['span'][0]}..{r['span'][1]} | {r.get('free_um', '')} | {r['demand_bits']} | {r['captive_bits']} | "
                  f"{r['supply_tracks_m4_m7']} | {'BLOCKED' if r['ratio'] is None else r['ratio']} | "
                  + '; '.join(f'{k} {v}' for k, v in r['families']) + ' |')
    (out / 'CUTS.md').write_text('\n'.join(md) + '\n')
    print('PLAN_CUTS cuts=%d over0.60=%d watch=%d worst=%s' % (len(rows), len(over), len(watch),
                                                              (rows[0]['cut'], rows[0]['ratio']) if rows else None))


if __name__ == '__main__':
    main()
