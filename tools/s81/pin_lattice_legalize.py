"""Die-tool pin lattice legalizer for GENERATED S81 masters (S-DIE 2026-10-15, --pin-lattice).

Owner rule (top-down pin assignment): the die tools assign the pins of unclosed masters.  The die PLACE step
(snap.tcl ot_mts::rule) needs ONE site-grid origin per axis that puts every signal pin centre of the master on its
layer's track: c19b failed 'sp_su_s y has no legal origin' and, after that was corrected, 'sp_gather x has no legal
origin' -- 20 generated masters carried GEO-S repin translations that were not multiples of the track pitch, or a
whole group off the site/track lattice.  This module moves each off-lattice pin the smallest distance onto the
master's common lattice, never onto another pin (min spacing kept), never off the outline, and reports every move.

Model (identical to snap.tcl ot_mts::rule for R0/MX/MY/R180 with ASAP7 make_tracks.tcl):
  layer -> (axis constrained, pitch, offset): a pin centre c on that axis needs (O + c) % pitch == offset.
  The origin O lies on the site grid (x: 54 nm, y: 270 nm; die rows start on the grid).
  Layers with several track families (M2) or unknown layers are left alone.
Bound views / real LEF masters are never passed here (their measured pins stand).
Integer nm throughout (the LEF is written with 3 decimals).
"""
import math
from collections import defaultdict

# layer: (constrained axis 0=x/1=y, pitch nm, offset nm); ASAP7 make_tracks.tcl
TRACKS = {'M1': (0, 36, 9), 'M3': (0, 36, 9), 'M4': (1, 48, 12), 'M5': (0, 48, 12), 'M6': (1, 64, 16),
          'M7': (0, 64, 16), 'M8': (1, 80, 116 % 80), 'M9': (0, 80, 116 % 80)}
SITE = (54, 270)
SPACE = 24          # nm: same-layer min spacing used by pin_clashes


def _nm(v):
    return int(round(v * 1000))


def legal_origins(pins, axis):
    """origin residues (mod lcm) that satisfy every pin on this axis; pins = [(layer, c2)] with c2 = 2 x centre (nm)"""
    per = defaultdict(set)
    for layer, c2 in pins:
        t = TRACKS.get(layer)
        if t and t[0] == axis:
            per[layer].add(c2)
    L = SITE[axis]
    for layer in per:
        L = math.lcm(L, TRACKS[layer][1])
    legal = set(range(0, L, SITE[axis]))
    for layer, cs in per.items():
        _, P, off = TRACKS[layer]
        for c2 in cs:
            if c2 % 2:
                return []
            c = c2 // 2
            legal = {o for o in legal if (o + c - off) % P == 0}
    return sorted(legal)


def legalize(name, w, h, rects):
    """rects: [(pin, layer, (x0, y0, x1, y1)) um] -> (new rects, report).  Raises if no legal result exists."""
    W, H = _nm(w), _nm(h)
    R = [[nm, ly, [_nm(v) for v in r]] for nm, ly, r in rects]
    report = dict(master=name, moved=0, max_move_nm=0, axes={})
    for axis in (0, 1):
        lo, hi = (0, 2) if axis == 0 else (1, 3)
        idx = [i for i, (_, ly, _r) in enumerate(R) if ly in TRACKS and TRACKS[ly][0] == axis]
        if not idx:
            continue
        pins = [(R[i][1], R[i][2][lo] + R[i][2][hi]) for i in idx]
        if legal_origins(pins, axis):
            continue
        L = SITE[axis]
        for i in idx:
            L = math.lcm(L, TRACKS[R[i][1]][1])
        # choose the origin residue that leaves the most pins in place, then the least total movement
        best = None
        for o in range(0, L, SITE[axis]):
            keep, cost = 0, 0
            for i in idx:
                _, P, off = TRACKS[R[i][1]]
                c2 = R[i][2][lo] + R[i][2][hi]
                d = (off - o - c2 // 2) % P if c2 % 2 == 0 else None
                if d == 0:
                    keep += 1
                else:
                    d = P if d is None else min(d, P - d)
                    cost += d
            key = (-keep, cost, o)
            if best is None or key < best:
                best = key
        o = best[2]
        # occupancy per layer: intervals along the constrained axis of pins that stay, for spacing checks
        by_layer = defaultdict(list)
        movers = []
        for i in idx:
            _, P, off = TRACKS[R[i][1]]
            c2 = R[i][2][lo] + R[i][2][hi]
            if c2 % 2 == 0 and (o + c2 // 2 - off) % P == 0:
                by_layer[R[i][1]].append(i)
            else:
                movers.append(i)

        B = 2000                       # nm bucket for the spacing index
        grid = defaultdict(list)

        def _add(j):
            s = R[j][2]
            for bx in range((s[0] - SPACE) // B, (s[2] + SPACE) // B + 1):
                for by in range((s[1] - SPACE) // B, (s[3] + SPACE) // B + 1):
                    grid[(R[j][1], bx, by)].append(j)

        for ly_, js in by_layer.items():
            for j in js:
                _add(j)

        def clash(i, r):
            ly = R[i][1]
            for bx in range((r[0] - SPACE) // B, (r[2] + SPACE) // B + 1):
                for by in range((r[1] - SPACE) // B, (r[3] + SPACE) // B + 1):
                    for j in grid.get((ly, bx, by), ()):
                        s = R[j][2]
                        if s[0] < r[2] + SPACE and r[0] < s[2] + SPACE and s[1] < r[3] + SPACE and r[1] < s[3] + SPACE:
                            return True
            return False

        moves = []
        for i in movers:
            ly = R[i][1]
            _, P, off = TRACKS[ly]
            r = R[i][2]
            size = r[hi] - r[lo]
            touches_lo, touches_hi = r[lo] <= 0, r[hi] >= (W if axis == 0 else H)
            ext = W if axis == 0 else H
            placed = None
            if touches_lo or touches_hi:
                # a face pin whose DEPTH lies on the constrained axis: keep the outline edge, move the inner edge
                for grow in range(1, 4 * P):
                    nr = list(r)
                    if touches_lo:
                        nr[hi] = r[hi] + grow
                    else:
                        nr[lo] = r[lo] - grow
                    c2 = nr[lo] + nr[hi]
                    if c2 % 2 == 0 and (o + c2 // 2 - off) % P == 0 and not clash(i, nr) \
                            and nr[lo] >= 0 and nr[hi] <= ext:
                        placed = nr
                        break
            else:
                c2 = r[lo] + r[hi]
                base = (off - o - (c2 // 2)) % P if c2 % 2 == 0 else None
                cands = []
                if base is None:
                    # odd doubled centre: widen by 1 nm first (never happens with 24/18-nm generated pins)
                    raise ValueError(f'{name}: odd pin centre {R[i][0]} {ly}')
                for k in range(0, 40):
                    cands += [base + k * P, base - (k + 1) * P]
                cands.sort(key=abs)
                for d in cands:
                    nr = list(r)
                    nr[lo] += d
                    nr[hi] += d
                    if nr[lo] < 0 or nr[hi] > ext:
                        continue
                    if not clash(i, nr):
                        placed = nr
                        break
            if placed is None:
                raise ValueError(f'{name}: no lattice spot for pin {R[i][0]} on {ly} (axis {"xy"[axis]})')
            mv = abs((placed[lo] + placed[hi]) - (r[lo] + r[hi])) // 2
            moves.append((R[i][0], ly, mv))
            R[i][2] = placed
            by_layer[ly].append(i)
            _add(i)
        pins = [(R[i][1], R[i][2][lo] + R[i][2][hi]) for i in idx]
        legal = legal_origins(pins, axis)
        if not legal:
            raise ValueError(f'{name}: lattice legalization left no origin on axis {"xy"[axis]}')
        report['moved'] += len(moves)
        report['max_move_nm'] = max([report['max_move_nm']] + [m_[2] for m_ in moves])
        report['axes']['xy'[axis]] = dict(origin_residue_nm=o, period_nm=L, moved=len(moves),
                                          max_move_nm=max(m_[2] for m_ in moves) if moves else 0,
                                          examples=[list(m_) for m_ in moves[:6]])
    out = [(nm, ly, tuple(v / 1000.0 for v in r)) for nm, ly, r in R]
    return out, report
