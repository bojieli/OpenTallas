#!/usr/bin/env python3
"""HBM-NEXT-UNITS-IDX 2026-10-19: IDX.UNION (HGI-1R op 5) compiler schedule + vectors for ot_hnx_idx_union_static on the
ACTUAL SW VM slice (bench rtl/hbm_next/idx/tb/tb_hnx_idx_union.sv).

The schedule is the compiler's, written from the timeline in the RTL header (never read back from the RTL); the bench
replays it as the slice calendar (read-group select, hub bank select, packet-write select, hub response edge) and checks
every done / fault edge and every output sector (untouched neighbour words included) against the golden
tools/hbm_next/isa_rows.idx_union / entry_word (the CMTP single source).

  hnx_idx_union_vectors.py OUTDIR [seed=0] [random_count=8]

Records: the production verify shape (E 384, K 6, k 6 route top-6, ascending) at N = 1, 2, 3, 4, 6 (two of each N:
DS-like overlapping ids and disjoint ids), random coverage (N 1..16, k 1..8, K k..15, E 1..384, unaligned A), and
three fault records (row not strictly ascending, id >= E, illegal descriptor).
Files: rec.txt / cal.mem / pre.mem / chk.mem / counts.txt (as tools/hbm_idx_topk_static_vectors.py) + rows.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/hbm_next'))
import hbm_idx_topk_static_vectors as V  # noqa: E402  (ACK / HUB_TO_BANK / RESP / SID of the same slice client)
import isa_rows as IR  # noqa: E402

FULL = 12


def ts_of(n):
    return (1 + n + 7) // 8


def schedule(rec, G):
    k, N, E, K = rec['k'], rec['N'], rec['E'], rec['K']
    legal = (1 <= k <= 8 and 1 <= N <= 16 and 1 <= E <= 384 and K >= k
             and ((rec['am'] and rec['a'] >> 16 == 0) or (not rec['am'] and rec['a'] >> 16 == V.SID))
             and rec['o'] >> 16 == V.SID and rec['o'] % 8 == 0 and rec['d'] >> 16 == V.SID
             and rec['r'] >> 16 == V.SID and rec['r'] % 32 == 0)
    if not legal:
        return [], G + 1, False, {}
    ev = []
    e = G + 2
    for row in range(N):
        a = rec['a'] + row * rec['a_str']
        for sec in range(a >> 3, ((a + k - 1) >> 3) + 1):
            ev.append(('R', e + 1, sec % 8))
            e += 1
    eL = e - 1
    W0 = eL + 18
    T, TS = N * k, ts_of(N)
    writes = []
    for i in range(T):
        for s in range(TS):
            writes.append((rec['r'] >> 3) + 4 * i + s)
        if i % 8 == 7 or i == T - 1:
            writes.append((rec['o'] >> 3) + i // 8)
    writes.append(rec['d'] >> 3)
    for x, sec in enumerate(writes):
        W = W0 + 10 * (x // 4) + x % 4              # 4 packet sequence numbers, ack frees one at W + 10
        ev.append(('H', W + 1, sec % 8))
        ev.append(('P', W + 1 + V.HUB_TO_BANK, sec % 8))
        ev.append(('A', W + 1 + V.RESP, x % 4))
    nxt = W0 + 10 * ((len(writes) - 1) // 4) + (len(writes) - 1) % 4 + 1
    return ev, nxt + V.ACK, True, dict(read_edges=eL - G - 1, writes=len(writes), T=T, TS=TS)


def asc_ids(rng, k, E, pool=None):
    src = pool if pool is not None else np.arange(E)
    return sorted(int(x) for x in rng.choice(src, size=k, replace=False))


def make_records(rng, count):
    """address plan (one 64K-word slice): production a 1024 + 128 j, O 2560 + 64 j, D 3328 + 8 j, R 4096 + 2048 j (j < 10);
    random a 24576 + 512 i, O 28672 + 64 i, D 29184 + 8 i, R 30720 + 2048 i (i < 8, N k <= 48); faults from 47104."""
    recs = []
    j = 0
    hot = rng.choice(384, size=40, replace=False)      # DS-like: verify positions share most experts
    for N in (1, 2, 3, 4, 6):
        for mode in ('hot', 'disjoint'):
            if mode == 'hot':
                rows = [asc_ids(rng, 6, 384, hot) for _ in range(N)]
            else:
                perm = rng.permutation(384)
                rows = [sorted(int(x) for x in perm[6 * r:6 * r + 6]) for r in range(N)]
            recs.append(dict(k=6, N=N, E=384, K=6, am=0, a=1024 + 128 * j + (3 if N % 2 else 0), a_str=8 + (j % 3),
                             o=2560 + 64 * j, d=3328 + 8 * j + (j % 8), r=4096 + 2048 * j, rows=rows, prod=True,
                             kind=f'N{N}_{mode}'))
            j += 1
    assert count <= 8
    for i in range(count):
        N = int(rng.integers(1, 17)); k = int(rng.integers(1, min(8, 48 // N) + 1)); K = int(rng.integers(k, 16))
        E = int(rng.choice([384, 384, 200, 64, max(k, 9)]))
        rows = [asc_ids(rng, k, E) for _ in range(N)]
        recs.append(dict(k=k, N=N, E=E, K=K, am=int(rng.integers(0, 2)), a=24576 + 512 * i + int(rng.integers(0, 8)),
                         a_str=k + int(rng.integers(0, 9)), o=28672 + 64 * i, d=29184 + 8 * i + int(rng.integers(0, 8)),
                         r=30720 + 2048 * i, rows=rows, prod=False, kind='random'))
    # data faults: row not strictly ascending; id >= E; then an illegal descriptor (O not 8-aligned)
    recs.append(dict(k=6, N=3, E=384, K=6, am=0, a=47104, a_str=8, o=47360, d=47424, r=47616,
                     rows=[[1, 5, 9, 12, 40, 41], [3, 7, 7, 20, 30, 31], [2, 4, 6, 8, 10, 12]], prod=False, kind='fault_order'))
    recs.append(dict(k=6, N=2, E=100, K=6, am=0, a=48256, a_str=6, o=48384, d=48448, r=48640,
                     rows=[[1, 5, 9, 12, 40, 41], [3, 7, 17, 20, 99, 100]], prod=False, kind='fault_range'))
    recs.append(dict(k=6, N=2, E=384, K=6, am=0, a=49152, a_str=6, o=49411, d=49472, r=49664,
                     rows=[[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]], prod=False, kind='fault_illegal'))
    return recs


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    cnt = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    rng = np.random.default_rng(20261019 + seed)
    recs = make_records(rng, cnt)
    main_mem, mirror_mem = {}, {}
    for rec in recs:
        mem = mirror_mem if rec['am'] else main_mem
        for r, row in enumerate(rec['rows']):
            for q, x in enumerate(row):
                mem[rec['a'] + r * rec['a_str'] + q] = int(x)
    out_words = set()
    for rec in recs:
        T, TS = rec['N'] * rec['k'], ts_of(rec['N'])
        for i in range(T):
            out_words.update(range(rec['r'] + 32 * i, rec['r'] + 32 * i + 8 * TS))
        out_words.update(range(rec['o'], rec['o'] + 8 * ((T + 7) // 8)))
        out_words.update(range(rec['d'] & ~7, (rec['d'] & ~7) + 8))
    for w in out_words:
        assert w not in main_mem, ('output overlaps an input', w)
        main_mem[w] = int(rng.integers(0, 1 << 32))
    expect = dict(main_mem)
    G, cal, lines, rows_meta = 0, {}, [], []
    for rec in recs:
        G = G + 2
        ev, end, legal, meta = schedule(rec, G)
        fault = not legal
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
        for kind, e, val in ev:
            cal.setdefault(e, []).append((kind, val))
        lines.append(f"{G:05x} {end:05x} {int(fault)} {rec['k']:x} {rec['N']:02x} {rec['E']:03x} {rec['K']:x} {rec['am']} "
                     f"{rec['a']:05x} {rec['a_str']:05x} {rec['o']:05x} {rec['d']:05x} {rec['r']:05x}")
        rows_meta.append(dict(kind=rec['kind'], N=rec['N'], k=rec['k'], U=rec.get('U'), G=G, end=end, fault=fault,
                              edges=end - G + 1, **meta))
        G = end
    last = G + 4
    img = []
    for e in range(last + 1):
        rsel = hub = pws = 0; rv = rs = 0
        for kind, val in cal.get(e, []):
            if kind == 'R':
                assert not rsel >> val & 1, ('read bank double-booked', e); rsel |= 1 << val
            elif kind == 'H':
                assert not hub >> val & 1; hub |= 1 << val
            elif kind == 'P':
                assert not pws >> val & 1; pws |= 1 << val
            else:
                assert not rv, ('two responses on one edge', e); rv, rs = 1, val
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
    chk = [(s, d) for s, d in sectors(expect, 0) if any((s << 3) + q in out_words for q in range(8))]
    (out / 'chk.mem').write_text(''.join(f"{s:04x}{''.join(f'{x:08x}' for x in reversed(d))}\n" for s, d in chk))
    (out / 'counts.txt').write_text(f'{len(pre)} {len(chk)}\n')
    (out / 'rows.json').write_text(json.dumps(rows_meta, indent=1) + '\n')
    print(f'records {len(recs)} faults {sum(m["fault"] for m in rows_meta)} preload {len(pre)} check {len(chk)} edges {last}')
    for m in rows_meta:
        if m['kind'] != 'random':
            print(f"  {m['kind']}: N {m['N']} U {m['U']} compiled edges {m['edges']} (reads {m.get('read_edges')}, writes {m.get('writes')})")


if __name__ == '__main__':
    main()
