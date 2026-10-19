#!/usr/bin/env python3
"""LH-P3UNITS/UNIONVAR 10-19: vectors + golden for the factored ordered-cardinality union dispatcher
(rtl/hbm_next/control/ot_hnx_union_prefix.sv) behind the ACTUAL IDX.UNION engine on the ACTUAL SW VM slice
(bench rtl/hbm_next/control/tb_hnx_union_factored.sv).

The IDX schedule is tools/hbm_next/hnx_idx_union_vectors.schedule (the compiler's IDX timeline) and the union/row tables
come from the CMTP golden isa_rows.idx_union.  The launch golden below is written from the dispatcher spec in the RTL
header (never read back from the RTL):
  S = union done edge + 1;  loop 1 slot i at S + B1 + P1[i];  loop 2 slot i at S + B1 + T1 + G + P2[i];
  tail at S + B1 + T1 + G + T2;  P1/P2 exclusive prefix sums of D1[c]/D2[c] over the ascending union order,
  c_i = number of route rows containing union expert i;  kref = KB[loop] + c_i - 1 (tail: KBT).
Records are spaced so the next IDX go comes after the previous dispatch ends (layer order: the next layer's routing
cannot start before this layer's experts finish).  Records: the production N=1..6 shapes, random N<=16/k<=8 coverage,
the two U24 equal-U/different-cardinality counterexamples and the three IDX fault records (no launch allowed).

  union_factored_vectors.py OUTDIR [seed=0] [random_count=8]
Extra files beside the IDX ones: cfg.txt (dispatcher configuration writes), launch.txt (expected launches), factored.json.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/hbm_next'))
import hnx_idx_union_vectors as V  # noqa: E402
import isa_rows as IR  # noqa: E402
from union_variants import counterexample  # noqa: E402

P = 3                      # next-release die lanes (owner 10-19 P = 3): c rows take ceil(c / P) SM passes
B1, GMID = 4, 11
KB1, KB2, KBT = 0x100, 0x200, 0x3ff


def d1(c):                 # bench kernel spans (compiler configuration; production spans are hundreds of edges)
    return 6 + 9 * math.ceil(c / P)


def d2(c):
    return 5 + 7 * math.ceil(c / P)


def records(rng, count):
    recs = V.make_records(rng, count)
    for i, (name, rows) in enumerate(counterexample()['rows'].items()):
        r = dict(recs[8])
        r.update(a=52000 + 128 * i, a_str=8, o=52480 + 64 * i, d=52608 + 8 * i, r=53248 + 2048 * i, rows=rows,
                 kind='U24_' + name)
        recs.append(r)
    return recs


def launches(rows, E, K):
    uni, tabs = IR.idx_union(rows, experts=E, pitch=K)
    cs = [c for c, _ in tabs]
    assert cs == [sum(u in row for row in rows) for u in uni]
    p1 = [sum(d1(c) for c in cs[:i]) for i in range(len(cs) + 1)]
    p2 = [sum(d2(c) for c in cs[:i]) for i in range(len(cs) + 1)]
    ev = [(B1 + p1[i], 1, i, c, KB1 + c - 1) for i, c in enumerate(cs)]
    b2 = B1 + p1[-1] + GMID
    ev += [(b2 + p2[i], 2, i, c, KB2 + c - 1) for i, c in enumerate(cs)]
    ev.append((b2 + p2[-1], 3, len(cs), 0, KBT))
    return uni, cs, ev


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    cnt = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    rng = np.random.default_rng(20261019 + seed)
    recs = records(rng, cnt)
    main_mem, mirror_mem = {}, {}
    for rec in recs:
        mem = mirror_mem if rec['am'] else main_mem
        for r, row in enumerate(rec['rows']):
            for q, x in enumerate(row):
                mem[rec['a'] + r * rec['a_str'] + q] = int(x)
    out_words = set()
    for rec in recs:
        T, TS = rec['N'] * rec['k'], V.ts_of(rec['N'])
        for i in range(T):
            out_words.update(range(rec['r'] + 32 * i, rec['r'] + 32 * i + 8 * TS))
        out_words.update(range(rec['o'], rec['o'] + 8 * ((T + 7) // 8)))
        out_words.update(range(rec['d'] & ~7, (rec['d'] & ~7) + 8))
    for w in out_words:
        assert w not in main_mem, ('output overlaps an input', w)
        main_mem[w] = int(rng.integers(0, 1 << 32))
    expect = dict(main_mem)
    G, gap, cal, lines, meta_rows, lau = 0, 2, {}, [], [], []
    for rec in recs:
        G = G + gap
        ev, end, legal, meta = V.schedule(rec, G)
        fault = not legal
        gap = 2
        if legal:
            try:
                uni, tabs = IR.idx_union(rec['rows'], experts=rec['E'], pitch=rec['K'])
            except IR.RangeFault:
                fault = True
            if not fault:
                for x, u in enumerate(uni):
                    expect[rec['o'] + x] = u
                expect[rec['d']] = len(uni)
                for i, (c, ent) in enumerate(tabs):
                    expect[rec['r'] + 32 * i] = c
                    for q, (rho, e) in enumerate(ent):
                        expect[rec['r'] + 32 * i + 1 + q] = IR.entry_word(rho, e)
                rec['U'] = len(uni)
                _, cs, lev = launches(rec['rows'], rec['E'], rec['K'])
                S = end + 1
                for t, loop, slot, c, kref in lev:
                    lau.append((S + t, loop, slot, c, kref))
                gap = 1 + lev[-1][0] + 6            # next go after the dispatch tail
                rec['c'] = cs; rec['tail'] = lev[-1][0]
        for kind, e, val in ev:
            cal.setdefault(e, []).append((kind, val))
        lines.append(f"{G:05x} {end:05x} {int(fault)} {rec['k']:x} {rec['N']:02x} {rec['E']:03x} {rec['K']:x} {rec['am']} "
                     f"{rec['a']:05x} {rec['a_str']:05x} {rec['o']:05x} {rec['d']:05x} {rec['r']:05x}")
        meta_rows.append(dict(kind=rec['kind'], N=rec['N'], k=rec['k'], U=rec.get('U'), G=G, end=end, fault=fault,
                              c=rec.get('c'), tail_edges_after_S=rec.get('tail'), **meta))
        G = end
    last = G + 8
    img = []
    for e in range(last + 1):
        rsel = hub = pws = 0; rv = rs = 0
        for kind, val in cal.get(e, []):
            if kind == 'R':
                assert not rsel >> val & 1; rsel |= 1 << val
            elif kind == 'H':
                assert not hub >> val & 1; hub |= 1 << val
            elif kind == 'P':
                assert not pws >> val & 1; pws |= 1 << val
            else:
                assert not rv; rv, rs = 1, val
        img.append(rv << 26 | rs << 24 | pws << 16 | hub << 8 | rsel)
    assert last < (1 << 17)
    (out / 'cal.mem').write_text(''.join(f'{x:07x}\n' for x in img))
    (out / 'rec.txt').write_text(f'{len(recs)} {last}\n' + '\n'.join(lines) + '\n')

    def sectors(mem, mirror):
        secs = {}
        for w, x in mem.items():
            secs.setdefault(w >> 3, [0] * 8)[w & 7] = x
        return [(mirror << 15 | s, d) for s, d in sorted(secs.items())]
    pre = sectors(main_mem, 0) + sectors(mirror_mem, 1)
    (out / 'pre.mem').write_text(''.join(f"{s:04x}{''.join(f'{x:08x}' for x in reversed(d))}\n" for s, d in pre))
    chk = [(s, d) for s, d in sectors(expect, 0) if any((s << 3) + q in out_words for q in range(8))]
    (out / 'chk.mem').write_text(''.join(f"{s:04x}{''.join(f'{x:08x}' for x in reversed(d))}\n" for s, d in chk))
    (out / 'counts.txt').write_text(f'{len(pre)} {len(chk)} {len(lau)}\n')
    cfg = [(c - 1, d1(c)) for c in range(1, 17)] + [(15 + c, d2(c)) for c in range(1, 17)]
    cfg += [(32, B1), (33, GMID), (34, KB1), (35, KB2), (36, KBT)]
    (out / 'cfg.txt').write_text(f'{len(cfg)}\n' + ''.join(f'{a:02x} {v:08x}\n' for a, v in cfg))
    (out / 'launch.txt').write_text(''.join(f'{e:05x} {lp:x} {s:02x} {c:02x} {k:03x}\n' for e, lp, s, c, k in lau))
    (out / 'factored.json').write_text(json.dumps(dict(P=P, B1=B1, G=GMID, KB=[KB1, KB2, KBT],
        d1={c: d1(c) for c in range(1, 17)}, d2={c: d2(c) for c in range(1, 17)}, launches=len(lau),
        records=meta_rows), indent=1) + '\n')
    print(f'records {len(recs)} faults {sum(m["fault"] for m in meta_rows)} launches {len(lau)} preload {len(pre)} '
          f'check {len(chk)} edges {last}')
    for m in meta_rows:
        if m['kind'] != 'random':
            print(f"  {m['kind']}: N {m['N']} U {m['U']} c {m['c']}")


if __name__ == '__main__':
    main()
