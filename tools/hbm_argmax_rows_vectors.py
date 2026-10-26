#!/usr/bin/env python3
"""Compiler schedule + vectors for the P-row static ARGMAX.LOCAL (ot_hbm_argmax_static_rows, VM mode) on the actual
SW VM slice (H-MTP2/sudma 2026-10-16).  Successor of tools/hbm_argmax_static_vectors.py (unchanged).

The schedule is the compiler's, from the timeline in rtl/hbm_accel/generic/ot_hbm_argmax_static_rows.sv (never read
back from the RTL): G = go edge, S_0 = G+3, S_{r+1} = S_r + ns_r, L_r = S_r + ns_r + 9, W0_r = L_r + ELAT + 1,
W1_r = W0_r + 1, end = W1_{R-1} + ACK + 1; row r's writes use client tag slots 2 (r % 2) + {0, 1}.  Golden per row: numpy.argmax on FP32 (lowest index of the maximum, the
first NaN wins and is flagged), global id = local + RANK * imm_a, value = the winner's FP32 bits.

  hbm_argmax_rows_vectors.py OUTDIR [seed]
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
    # DS rank-0 ARGMAX.LOCAL shard (n 1,347 FP32 logits, O {value, id}): P = 1 (c1) and P = 6 rows (verify)
    recs.append(dict(rows=1, n=1347, am=0, a=4096, ars=0, imm=1347, o=60000, ois=1, ors=0, kind=2, prod='P1_aligned'))
    recs.append(dict(rows=6, n=1347, am=0, a=6144, ars=1352, imm=1347, o=60016, ois=1, ors=2, kind=2, prod='P6_aligned'))
    recs.append(dict(rows=1, n=1347, am=1, a=12291, ars=0, imm=1347, o=60032, ois=1, ors=0, kind=2, prod='P1_unaligned'))
    recs.append(dict(rows=6, n=1347, am=1, a=14339, ars=1347, imm=1347, o=60048, ois=1, ors=2, kind=2, prod='P6_packed'))
    a_ptr = {0: 24576, 1: 24576}
    for i in range(24):
        rows = int(rng.integers(1, 9))
        n = int(rng.choice([33, 34, 40, 41, 64, 100, 257] if rows > 1 else [1, 2, 7, 8, 9, 17, 64, 100]))
        am = int(rng.integers(0, 2))
        ars = n + int(rng.integers(0, 12))
        a = a_ptr[am] + int(rng.integers(0, 16))
        a_ptr[am] = a + rows * ars + 16
        ois = int(rng.integers(1, 9))
        recs.append(dict(rows=rows, n=n, am=am, a=a, ars=ars, imm=int(rng.integers(0, 4096)),
                         o=40000 + 256 * i + int(rng.integers(0, 16)), ois=ois, ors=ois + 1 + int(rng.integers(0, 8)),
                         kind=int(rng.integers(0, 3)), prod=None, nan=(i % 8 == 7)))
    recs.append(dict(rows=1, n=0, am=0, a=8, ars=0, imm=0, o=40, ois=1, ors=0, kind=1, prod=None))       # n = 0
    recs.append(dict(rows=0, n=8, am=0, a=8, ars=8, imm=0, o=40, ois=1, ors=2, kind=1, prod=None))       # rows = 0
    recs.append(dict(rows=2, n=32, am=0, a=8, ars=32, imm=0, o=40, ois=1, ors=2, kind=1, prod=None))     # rows>1, n<33
    recs.append(dict(rows=3, n=16, am=0, a=65530 - 40, ars=16, imm=0, o=40, ois=1, ors=2, kind=1, prod=None))  # crosses SID
    assert max(a_ptr.values()) < 65536 - 64
    main_mem, mirror_mem, expect = {}, {}, {}
    a_seen = {0: set(), 1: set()}
    out_words = set()
    G = 0; cal = {}; lines = []; prod = {}
    for rec in recs:
        n, R = rec['n'], rec['rows']
        a_last = rec['a'] + max(R - 1, 0) * rec['ars'] + n - 1
        o_last = rec['o'] + max(R - 1, 0) * rec['ors']
        legal = (n > 0 and 1 <= R <= 8 and (R == 1 or n >= 33) and rec['a'] >> 16 == 0 and
                 (R == 1 or a_last >> 16 == 0) and rec['o'] >> 16 == 0 and o_last >> 16 == 0 and
                 (o_last + rec['ois']) >> 16 == 0)
        G += 2
        ev = []
        anynan = False
        if legal:
            S = G + 3
            for r in range(R):
                if rec['kind'] == 0:
                    v = rng.choice(SPECIAL, size=n)
                elif rec['kind'] == 1:
                    v = rng.integers(-3, 4, size=n).astype(np.float32).view(np.uint32)
                else:
                    v = rng.standard_normal(n).astype(np.float32).view(np.uint32)
                v = np.ascontiguousarray(v, np.uint32)
                if rec.get('nan') and r % 2 == 0:
                    v[int(rng.integers(0, n))] = 0x7fc00001
                ab = rec['a'] + r * rec['ars']
                mem = mirror_mem if rec['am'] else main_mem
                for j, x in enumerate(v):
                    assert ab + j not in a_seen[rec['am']], ('A overlap', ab + j)
                    a_seen[rec['am']].add(ab + j)
                    mem[ab + j] = int(x)
                sec0, secl = ab >> 3, (ab + n - 1) >> 3
                ns = secl - sec0 + 1
                for j in range(ns):
                    ev.append(('R', S + j + 1, (sec0 + j) % 8))
                L = S + ns + 9
                S += ns
                idx, nb_bits, isnan = golden(v)
                anynan |= isnan
                gid = idx + RANK * rec['imm']
                val = int(v[idx]) if nb_bits is None else nb_bits
                assert gid < 1 << 18
                W0 = L + ELAT + 1
                ob = rec['o'] + r * rec['ors']
                for i, wa in enumerate((ob, ob + rec['ois'])):
                    W = W0 + i
                    ev += [('H', W + 1, (wa >> 3) % 8), ('P', W + 1 + HUB_TO_BANK, (wa >> 3) % 8), ('A', W + 1 + RESP, 2 * (r % 2) + i)]
                    for w in range((wa >> 3) * 8, (wa >> 3) * 8 + 8):
                        out_words.add(w)
                    assert wa not in expect
                    expect[wa] = val if i == 0 else gid
            end = W0 + 1 + ACK + 1
            fault = False
        else:
            end, fault = G + 1, True
        if rec['prod']:
            prod[rec['prod']] = end - G + 1
        for kind, e, val in ev:
            cal.setdefault(e, []).append((kind, val))
        lines.append(f"{G:05x} {end:05x} {int(fault)} {int(anynan)} {rec['rows']:x} {rec['imm']:05x} "
                     f"{rec['am']} {rec['a']:05x} {rec['ars']:05x} {rec['n']:05x} {rec['o']:05x} {rec['ois']:04x} "
                     f"{rec['ors']:05x}")
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
          f"edges {last}; production edges/record (G..done) " + ', '.join(f"{k} {v}" for k, v in prod.items()))


if __name__ == '__main__':
    main()
