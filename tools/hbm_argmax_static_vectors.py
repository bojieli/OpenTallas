#!/usr/bin/env python3
"""Compiler schedule + vectors for the static ARGMAX.LOCAL (ot_hbm_argmax_static) on the actual SW VM slice.

The schedule is the compiler's, written from the timeline documented in rtl/hbm_accel/generic/ot_hbm_argmax_static.sv
(never read back from the RTL). Golden: numpy.argmax on FP32 (lowest index of the maximum, -0 == +0, the first NaN
wins and is flagged), global id = local + RANK * imm_a, value = the winner's FP32 bits (STREAM with bias: the FP32
RNE sum, zeros canonical +0).

  hbm_argmax_static_vectors.py OUTDIR [seed]
"""
import sys
from pathlib import Path

import numpy as np

ACK, ELAT, RANK = 12, 14, 3
HUB_TO_BANK, RESP = 2, 9
SPECIAL = np.array([0x00000000, 0x80000000, 0x7f800000, 0xff800000, 0x00000001, 0x3f800000, 0xbf800000,
                    0x7f7fffff, 0xff7fffff], np.uint32)


def golden(v):
    f = v.view(np.float32)
    nan = np.isnan(f)
    if nan.any():
        i = int(np.argmax(nan))
        return i, int(v[i]), True
    return int(np.argmax(f)), None, False


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    rng = np.random.default_rng(20261016 + seed)
    recs = []
    # production-like MTP rows: VM logits slice (REPL), and the SU STREAM with / without the Markov bias
    recs.append(dict(mode=0, n=2048, am=1, a=4096, imm=2048, o=60000, ois=1, kind=2, prod=True))
    recs.append(dict(mode=1, n=1024, am=0, a=0, imm=1024, o=60016, ois=1, kind=2, bias=0, gap=0, prod=True))
    recs.append(dict(mode=1, n=1024, am=0, a=0, imm=1024, o=60032, ois=3, kind=2, bias=1, gap=0, prod=True))
    for i in range(24):
        mode = int(rng.integers(0, 2))
        n = int(rng.choice([1, 2, 7, 8, 9, 17, 64, 100, 257, 513]))
        recs.append(dict(mode=mode, n=n, am=int(rng.integers(0, 2)), a=8192 + 1100 * i + int(rng.integers(0, 16)),
                         imm=int(rng.integers(0, 4096)), o=40000 + 32 * i + int(rng.integers(0, 16)),
                         ois=int(rng.integers(1, 9)), kind=int(rng.integers(0, 3)), bias=int(rng.integers(0, 2)),
                         gap=int(rng.integers(0, 3)), prod=False, nan=(i % 8 == 7)))
        if recs[-1]['mode'] == 1 and recs[-1]['bias']:
            recs[-1].update(kind=2, nan=False)   # biased rows: finite logits (adder overflow/invalid is a separate fault)
    recs.append(dict(mode=0, n=0, am=0, a=8, imm=0, o=40, ois=1, kind=1, prod=False))          # illegal: n = 0
    recs.append(dict(mode=0, n=8, am=0, a=(1 << 16) + 8, imm=0, o=40, ois=1, kind=1, prod=False))  # illegal: sid 1
    main_mem, mirror_mem, expect = {}, {}, {}
    out_words = set()
    G = 0; cal = {}; beats = {}; lines = []
    for rec in recs:
        n = rec['n']
        if rec['kind'] == 0:
            v = rng.choice(SPECIAL, size=max(n, 1))
        elif rec['kind'] == 1:
            v = rng.integers(-3, 4, size=max(n, 1)).astype(np.float32).view(np.uint32)
        else:
            v = rng.standard_normal(max(n, 1)).astype(np.float32).view(np.uint32)
        v = np.ascontiguousarray(v[:n], np.uint32)
        if rec.get('nan') and n:
            v[int(rng.integers(0, n))] = 0x7fc00001
        legal = n > 0 and (rec['mode'] == 1 or (rec['a'] >> 16 == 0)) and rec['o'] >> 16 == 0
        bias = None
        if rec['mode'] == 1 and rec.get('bias'):
            bias = (rng.standard_normal(n) * 0.5).astype(np.float32).view(np.uint32)
        G += 2
        ev = []
        res = None
        if legal:
            if rec['mode'] == 0:
                mem = mirror_mem if rec['am'] else main_mem
                for j, x in enumerate(v):
                    mem[rec['a'] + j] = int(x)
                S = G + 3
                sec0, secl = rec['a'] >> 3, (rec['a'] + n - 1) >> 3
                ns = secl - sec0 + 1
                for j in range(ns):
                    ev.append(('R', S + j + 1, (sec0 + j) % 8))
                L = S + ns + 9
                cand = v
            else:
                X = G + 2
                words = n
                nb = (words + 7) // 8
                for b in range(nb):
                    lanes = list(range(8 * b, min(8 * b + 8, n)))
                    vals = [int(v[j]) for j in lanes] + [0] * (8 - len(lanes))
                    bb = [int(bias[j]) for j in lanes] + [0] * (8 - len(lanes)) if bias is not None else [0] * 8
                    beats[X] = (len(lanes), b == nb - 1, vals, bb, 1 if bias is not None else 0)
                    last_x = X
                    X += 1 + (rec['gap'] if b % 3 == 1 else 0)
                L = last_x + 2
                if bias is not None:
                    s = (v.view(np.float32) + bias.view(np.float32)).astype(np.float32)
                    s[s == 0] = 0.0
                    cand = s.view(np.uint32)
                else:
                    cand = v
            idx, nb_bits, isnan = golden(cand)
            gid = idx + RANK * rec['imm']
            val = int(cand[idx]) if nb_bits is None else nb_bits
            rng_bad = gid >= 1 << 18
            res = (val, gid, isnan, rng_bad)
            W0 = L + ELAT + 1
            for i, wa in enumerate((rec['o'], rec['o'] + rec['ois'])):
                W = W0 + i
                ev += [('H', W + 1, (wa >> 3) % 8), ('P', W + 1 + HUB_TO_BANK, (wa >> 3) % 8), ('A', W + 1 + RESP, i)]
                for w in range((wa >> 3) * 8, (wa >> 3) * 8 + 8):
                    out_words.add(w)
                if not rng_bad:
                    expect[wa] = val if i == 0 else gid
            end = W0 + 1 + ACK + 1
            fault = rng_bad
        else:
            end, fault = G + 1, True
        for kind, e, val in ev:
            cal.setdefault(e, []).append((kind, val))
        lines.append(f"{G:05x} {end:05x} {int(fault)} {int(bool(res and res[2]))} {rec['mode']} {rec['imm']:05x} "
                     f"{rec['am']} {rec['a']:05x} {rec['n']:05x} {rec['o']:05x} {rec['ois']:04x}")
        G = end
    last = G + 4
    for w in out_words:
        main_mem.setdefault(w, int(rng.integers(0, 1 << 32)))
    final = dict(main_mem); final.update(expect)
    img = []
    for e in range(last + 1):
        rsel = hub = pws = 0; rv = rs = 0
        for kind, val in cal.get(e, []):
            if kind == 'R':
                assert not rsel >> val & 1; rsel |= 1 << val
            elif kind == 'H':
                assert not hub >> val & 1, ('hub double', e); hub |= 1 << val
            elif kind == 'P':
                assert not pws >> val & 1, ('bank write double', e); pws |= 1 << val
            else:
                assert not rv; rv, rs = 1, val
        img.append(rv << 26 | rs << 24 | pws << 16 | hub << 8 | rsel)
    (out / 'cal.mem').write_text(''.join(f'{x:07x}\n' for x in img))
    # stream image per edge: {bias_en, bias256, vals256, mask8, last, v} as 523 bits
    st = []
    for e in range(last + 1):
        if e in beats:
            cnt, lastb, vals, bb, be = beats[e]
            x = be << 522
            for j in range(8):
                x |= bb[j] << (266 + 32 * j) | vals[j] << (10 + 32 * j)
            x |= ((1 << cnt) - 1) << 2 | int(lastb) << 1 | 1
        else:
            x = 0
        st.append(x)
    (out / 'stream.mem').write_text(''.join(f'{x:0131x}\n' for x in st))
    (out / 'rec.txt').write_text(f'{len(recs)} {last}\n' + '\n'.join(lines) + '\n')

    def sectors(mem, mirror):
        secs = {}
        for w, x in mem.items():
            secs.setdefault(w >> 3, [0] * 8)[w & 7] = x
        return [(mirror << 15 | s, d) for s, d in sorted(secs.items())]
    pre = sectors(main_mem, 0) + sectors(mirror_mem, 1)
    (out / 'pre.mem').write_text(''.join(f"{s:04x}{''.join(f'{x:08x}' for x in reversed(d))}\n" for s, d in pre))
    chk = [(s, d) for s, d in sectors(final, 0) if any((s << 3) + j in out_words for j in range(8))]
    (out / 'chk.mem').write_text(''.join(f"{s:04x}{''.join(f'{x:08x}' for x in reversed(d))}\n" for s, d in chk))
    (out / 'counts.txt').write_text(f'{len(pre)} {len(chk)}\n')
    print(f"records {len(recs)} faults {sum(int(l.split()[2]) for l in lines)} preload {len(pre)} check {len(chk)} "
          f"edges {last}; production edges/record (G..done) " +
          ', '.join(str(int(l.split()[1], 16) - int(l.split()[0], 16) + 1) for l, r in zip(lines, recs) if r['prod']))


if __name__ == '__main__':
    main()
