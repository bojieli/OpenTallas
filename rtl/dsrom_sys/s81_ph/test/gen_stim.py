#!/usr/bin/env python3
"""Stimulus for tb_s81ph_gather_capture (CLAUDE S81-PH): phases of root partials (golden csum-tree nodes of each
row's segments, ot_v41_ret_pkg tags) for the 128 S81 roots, per the canonical S81 root ownership
(ot_dsrom_s81_phase_capture_profile: root r owns rows 256j + 2r, 2r + 1).  File format (one record a line, hex):
  P <rows> <np> <obase> <ops> <fmt> <rsplit> <fp32lo> <fp32hi> <identity> <phase>     phase start
  C <gap> <root> <tag> <data> <e>          a partial on root's lane, <gap> cycles after the previous C (0 = same cycle)
  E                                        end of phase rows (TB waits for drained)
  R <lvl>                                  reset_request level (fault case)
"""
import random, struct, sys

def rows_of(R, r):
    out = []
    for j in range(R >> 8):
        out += [256 * j + 2 * r, 256 * j + 2 * r + 1]
    lo = R & 255
    if lo > 2 * r: out.append(256 * (R >> 8) + 2 * r)
    if lo > 2 * r + 1: out.append(256 * (R >> 8) + 2 * r + 1)
    return out

def fval(rng):
    e = rng.randint(100, 150); return (rng.getrandbits(1) << 31) | (e << 23) | rng.getrandbits(23)

def tag(pos, row, lo, k, n): return (pos << 29) | (row << 13) | (lo << 8) | (k << 5) | n

def partials(rng, pos, row, nseg, depth_bias):
    """random cut of the golden tree over [0, nseg): list of (tag, val)"""
    K = max(0, (nseg - 1).bit_length())
    out = []
    def rec(lo, k):
        if lo >= nseg: return
        if k == 0 or rng.random() < depth_bias:
            out.append((tag(pos, row, lo, k, nseg), fval(rng)))
        else:
            rec(lo, k - 1); rec(lo + (1 << (k - 1)), k - 1)
    rec(0, K)
    return out

def phase(rng, f, ph, R, np_, fmt, burst, maxseg, obase=None, extra=None, err=None, ops=None):
    ops = ops if ops is not None else R + rng.randint(0, 64)
    obase = obase if obase is not None else rng.randint(0, 4096)
    rsplit = rng.randint(0, R)
    f.write(f'P {R:x} {np_:x} {obase:x} {ops:x} {fmt:x} {rsplit:x} {rng.getrandbits(1):x} {rng.getrandbits(1):x} '
            f'{rng.getrandbits(47):x} {ph:x}\n')
    per = []
    for r in range(128):
        lst = []
        for pos in range(np_ + 1):
            for row in rows_of(R, r):
                p = partials(rng, pos, row, rng.randint(1, maxseg), 0.5)
                rng.shuffle(p); lst += p
        per.append(lst)
    if extra is not None: per[extra].append((tag(0, rows_of(R, extra)[0], 0, 0, 1), fval(rng)))
    ev = []   # (cycle, root, tag, val, e)
    for r in range(128):
        t = rng.randint(0, 8)
        for i, (tg, v) in enumerate(per[r]):
            t += 1 if burst else rng.randint(1, 4)
            e = 1 if (err is not None and err == (r, i)) else 0
            ev.append((t, r, tg, v, e))
    ev.sort(key=lambda x: (x[0], x[1]))
    prev = 0
    for t, r, tg, v, e in ev:
        f.write(f'C {t - prev:x} {r:x} {tg:x} {v:x} {e:x}\n'); prev = t
    f.write('E\n')

def main():
    case, seed, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    rng = random.Random(seed)
    with open(out, 'w') as f:
        if case == 'mix':
            ph = 0
            for fmt in (0, 1, 2):
                for np_ in (0, 3, 7):
                    phase(rng, f, ph, rng.choice([64, 256, 300, 576, 1000]), np_, fmt, burst=rng.random() < 0.5, maxseg=8); ph += 1
        elif case == 'trace':       # the retained I66 trace shape: 576 rows, every root's rows complete in a burst
            phase(rng, f, 0, 576, 0, 2, burst=True, maxseg=1)
            phase(rng, f, 1, 7168, 0, 0, burst=True, maxseg=1)
        elif case == 'err':
            phase(rng, f, 0, 256, 0, 0, burst=False, maxseg=4, err=(5, 0))
        elif case == 'over':
            phase(rng, f, 0, 256, 0, 1, burst=False, maxseg=4, extra=7)
        elif case == 'range':
            phase(rng, f, 0, 256, 1, 1, burst=False, maxseg=2, obase=(1 << 19) - 300, ops=256)
        elif case == 'rreq':
            phase(rng, f, 0, 256, 0, 0, burst=False, maxseg=2); f.write('R 1\n')
        else: raise SystemExit(case)

if __name__ == '__main__': main()
