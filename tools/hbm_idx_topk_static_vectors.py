#!/usr/bin/env python3
"""Compiler schedule + vectors for the static IDX.TOPK engine on the actual SW VM slice (H-IDX 2026-10-15).

The schedule below is the compiler's: it is written from the timeline documented in
rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv, never read back from the RTL. The bench replays it as the slice
calendar (read-group select, hub bank select, bank packet-write select, hub response edge) and checks every
done / fault edge, every VM write and every untouched neighbour word against the golden hgi_sim.machine.topk_ids.

  hbm_idx_topk_static_vectors.py OUTDIR [random_count <= 24] [seed]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hgi_sim.machine import topk_ids, Fault  # noqa: E402

ACK = 12          # cq registered at W -> hub samples W+1 -> cr sampled by the engine pin at W+12 (measured hub+bank)
HUB_TO_BANK = 2   # hub samples cq at W+1, its pq register drives the bank which samples at W+3
RESP = 9          # response_enable sampled by the hub at W+1+RESP (bank echo at W+3+6 = W+9, hub br at W+10)
IDX_GROUP = 4     # SW read groups: SU/SFU/HC, DMA back, SM xload, COLL, IDX
IDX_CLIENT = 4    # SW records: argmax, coll, dma, hc, idx, sfu, su
SID = 0
SPECIAL = np.array([0x00000000, 0x80000000, 0x7f800000, 0xff800000, 0x00000001, 0x80000001, 0x3f800000, 0xbf800000,
                    0x7f7fffff, 0xff7fffff], np.uint32)


def schedule(rec, G):
    """Edges for one record whose go is sampled at edge G. Returns (events, end_edge, legal)."""
    k, n, m = rec['k'], rec['n'], rec['m']
    legal = (1 <= k <= 8 and n >= k and m >= 1
             and ((rec['am'] and rec['a'] >> 16 == 0) or (not rec['am'] and rec['a'] >> 16 == SID))
             and rec['o'] >> 16 == SID and (not rec['has_r'] or rec['r'] >> 16 == SID))
    ev = []
    if not legal:
        return ev, G + 1, False
    S = G + 3
    for row in range(m):
        rb = rec['a'] + row * rec['a_str']
        sec0, secl = rb >> 3, (rb + n - 1) >> 3
        ns = secl - sec0 + 1
        for j in range(ns):
            sec = sec0 + j
            ev.append(('R', S + 2 * j + 1, sec % 8))
        F = S + 2 * (ns - 1) + 9
        P = F + 7 + 4 * k
        secs = []
        orb = rec['o'] + row * rec['o_str']
        secs += [orb >> 3] + ([(orb >> 3) + 1] if (orb % 8) + k > 8 else [])
        if rec['has_r']:
            rrb = rec['r'] + row * rec['r_str']
            secs += [rrb >> 3] + ([(rrb >> 3) + 1] if (rrb % 8) + k > 8 else [])
        for i, sec in enumerate(secs):
            W = P + 1 + i
            ev.append(('H', W + 1, sec % 8))
            ev.append(('P', W + 1 + HUB_TO_BANK, sec % 8))
            ev.append(('A', W + 1 + RESP, i))
        W_last = P + len(secs)
        S = W_last + 3
    return ev, W_last + ACK + 1, True


def make_records(rng, count):
    recs = []
    # production route.top6 shape: n 384, k 6, ascending ids, REPL (mirror) scores; with and without R
    for has_r, a_off in ((1, 0), (0, 0), (1, 3)):
        recs.append(dict(k=6, n=384, m=1, order=1, has_r=has_r, am=1, a=4096 + a_off, a_str=384,
                         o=60000 + 2 * a_off, o_str=8, r=62000 + 5 * a_off, r_str=8, mode=2, nan=False, prod=True))
    for i in range(count):
        n = int(rng.choice([1, 2, 3, 5, 7, 8, 9, 15, 16, 17, 33, 64, 100, 257, 384]))
        k = int(rng.integers(1, min(8, n) + 1)); m = int(rng.integers(1, 4))
        am = int(rng.integers(0, 2))
        recs.append(dict(k=k, n=n, m=m, order=int(rng.integers(0, 2)), has_r=int(rng.integers(0, 2)), am=am,
                         a=8192 + 1200 * i + int(rng.integers(0, 16)), a_str=n + int(rng.integers(0, 10)),
                         o=40000 + 64 * i + int(rng.integers(0, 16)), o_str=k + int(rng.integers(0, 10)),
                         r=52000 + 64 * i + int(rng.integers(0, 16)), r_str=k + int(rng.integers(0, 10)),
                         mode=int(rng.integers(0, 3)), nan=(i % 16 == 15), prod=False))
    # illegal descriptors (fault at G+1, no VM traffic)
    recs.append(dict(k=0, n=8, m=1, order=0, has_r=0, am=0, a=8, a_str=8, o=40, o_str=8, r=0, r_str=0, mode=1,
                     nan=False, prod=False))
    recs.append(dict(k=3, n=8, m=1, order=0, has_r=0, am=0, a=(1 << 16) + 8, a_str=8, o=40, o_str=8, r=0, r_str=0,
                     mode=1, nan=False, prod=False))
    return recs


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    assert cnt <= 24, 'address plan fits 24 random records in one 64K-word slice'
    rng = np.random.default_rng(20261015 + (int(sys.argv[3]) if len(sys.argv) > 3 else 0))
    recs = make_records(rng, cnt)
    main_mem, mirror_mem = {}, {}          # word address (sid-major 18 b) -> value
    for rec in recs:
        mem = mirror_mem if rec['am'] else main_mem
        rows = []
        for row in range(rec['m']):
            if rec['mode'] == 0:
                v = rng.choice(SPECIAL, size=rec['n'])
            elif rec['mode'] == 1:
                v = rng.integers(-3, 4, size=rec['n']).astype(np.float32).view(np.uint32)
            else:
                v = rng.standard_normal(rec['n']).astype(np.float32).view(np.uint32)
            rows.append(np.ascontiguousarray(v, np.uint32))
        if rec['nan']:
            rows[-1][int(rng.integers(0, rec['n']))] = 0x7fc00001
        for row, v in enumerate(rows):          # later rows overwrite shared words, as the VM would
            if rec['a'] + row * rec['a_str'] + rec['n'] > 1 << 16:
                break                           # outside this slice: the illegal-descriptor case, never preloaded
            for j, x in enumerate(v):
                mem[rec['a'] + row * rec['a_str'] + j] = int(x)
        rec['rows'] = rows
    # output regions start as random garbage so byte masks are checked
    out_words = set()
    for rec in recs:
        for row in range(rec['m']):
            for base, st in (('o', 'o_str'), ('r', 'r_str')):
                b0 = rec[base] + row * rec[st]
                for w in range((b0 >> 3) * 8, ((b0 + 8) >> 3) * 8 + 8):
                    out_words.add(w)
    for w in out_words:
        main_mem.setdefault(w, int(rng.integers(0, 1 << 32)))
    expect = dict(main_mem)
    G = 0
    cal = {}
    lines = []
    for idx, rec in enumerate(recs):
        G = G + 2
        ev, end, legal = schedule(rec, G)
        # golden (hgi_sim.machine.u_idx_topk semantics): rows in order against the CURRENT VM (earlier records'
        # writes included); a NaN row faults the record and it and later rows write nothing, earlier rows stand.
        mem = mirror_mem if rec['am'] else expect
        fault = not legal
        if legal:
            for row in range(rec['m']):
                v = np.array([mem[rec['a'] + row * rec['a_str'] + j] for j in range(rec['n'])], np.uint32)
                try:
                    ids = topk_ids(v.view(np.float32), rec['k'], bool(rec['order']))
                except Fault:
                    fault = True
                    break
                for j, x in enumerate(ids):
                    expect[rec['o'] + row * rec['o_str'] + j] = int(x)
                    if rec['has_r']:
                        expect[rec['r'] + row * rec['r_str'] + j] = int(v[x])
        for kind, e, val in ev:
            cal.setdefault(e, []).append((kind, val))
        lines.append(f"{G:05x} {end:05x} {int(fault)} {rec['k']:x} {rec['order']} {rec['n']:05x} {rec['m']:05x} "
                     f"{rec['am']} {rec['a']:05x} {rec['a_str']:05x} {rec['o']:05x} {rec['o_str']:05x} "
                     f"{rec['has_r']} {rec['r']:05x} {rec['r_str']:05x}")
        rec.update(G=G, end=end, fault=fault)
        G = end
    last = G + 4
    # calendar image, one word per edge: {resp_v, resp_seq2, pws8, hub8, rsel8}
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
    chk = [(s, d) for s, d in sectors(expect, 0) if any((s << 3) + j in out_words for j in range(8))]
    (out / 'chk.mem').write_text(''.join(f"{s:04x}{''.join(f'{x:08x}' for x in reversed(d))}\n" for s, d in chk))
    (out / 'counts.txt').write_text(f'{len(pre)} {len(chk)}\n')
    prod = [r for r in recs if r['prod']]
    print(f'records {len(recs)} (prod {len(prod)}, faults {sum(r["fault"] for r in recs)}) preload {len(pre)} '
          f'check {len(chk)} edges {last}; production edges/record ' +
          ', '.join(str(r['end'] - r['G'] + 1) for r in prod))


if __name__ == '__main__':
    main()
