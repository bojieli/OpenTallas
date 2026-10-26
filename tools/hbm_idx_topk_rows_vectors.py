#!/usr/bin/env python3
"""H-MTP2/idx: P-row (R = P = 6) IDX.TOPK route.top6 vectors for the die-bound static engine ot_hbm_idx_topk_static.

Reuses the compiler schedule + golden of tools/hbm_idx_topk_static_vectors.py unchanged (schedule(), the
hgi_sim.machine.topk_ids golden, the calendar image); only the record list differs: the production route top-6 shape
(n 384, k 6, ascending ids, REPL mirror scores, O + R) as P1 records and as P-row records (m = P rows, row r reads the
position-r router copy a + r a_str, writes rid / weights at o + r o_str / r + r r_str), plus the random coverage set.

  hbm_idx_topk_rows_vectors.py OUTDIR [P=6] [seed=0] [random_count=12] [engine=static|rows]
writes the files of the base generator and rows.json (per record: kind, m, G, end edge).
engine 'rows': the compiler timeline of the pipelined successor ot_hbm_idx_topk_rows_static (schedule_rows below,
an edge-by-edge replay of its documented reader / selector timeline, written from the RTL header, not read back from
the RTL); 'static': the existing engine's schedule (base generator) unchanged.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_idx_topk_static_vectors as V  # noqa: E402

P = int(sys.argv[2]) if len(sys.argv) > 2 else 6
NRAND = int(sys.argv[4]) if len(sys.argv) > 4 else 12
ENGINE = sys.argv[5] if len(sys.argv) > 5 else "static"
FULL = 12          # a row's bank is FULL 12 edges after its last read edge
ROUND = 5          # 16 > 8 > 4 > 2 > 1 tournament: 5 edges a select round


def schedule_rows(rec, G):
    """ot_hbm_idx_topk_rows_static timeline for one record whose go is sampled at edge G -> (events, end, legal)."""
    k, n, m = rec['k'], rec['n'], rec['m']
    legal = (1 <= k <= 8 and n >= k and m >= 1
             and ((rec['am'] and rec['a'] >> 16 == 0) or (not rec['am'] and rec['a'] >> 16 == V.SID))
             and rec['o'] >> 16 == V.SID and (not rec['has_r'] or rec['r'] >> 16 == V.SID))
    if not legal:
        return [], G + 1, False
    ev = []
    rows = []
    for row in range(m):
        rb = rec['a'] + row * rec['a_str']
        orb = rec['o'] + row * rec['o_str']
        secs = [orb >> 3] + ([(orb >> 3) + 1] if (orb % 8) + k > 8 else [])
        if rec['has_r']:
            rrb = rec['r'] + row * rec['r_str']
            secs += [rrb >> 3] + ([(rrb >> 3) + 1] if (rrb % 8) + k > 8 else [])
        rows.append(dict(sec0=rb >> 3, ns=((rb + n - 1) >> 3) - (rb >> 3) + 1, wsecs=secs))
    # state after G+1 (CHK): reader at ROW row 0, selector WAIT row 0; every quantity below is the value BEFORE edge e
    rs, rrow, j = 'ROW', 0, 0
    busy = [0, 0]
    full_at = {}                 # bank -> edge after which FULL is visible
    st, srow, ph, cnt, wi = 'WAIT', 0, 0, 0, 0
    e = G + 2
    end = None
    while end is None:
        nbusy = list(busy)
        # reader
        nrs, nrrow, nj = rs, rrow, j
        if rs == 'ROW':
            b = rrow & 1
            if not busy[b]:
                nbusy[b] = 1
                nrs, nj = 'RD', 0
        elif rs == 'RD':
            r = rows[rrow]
            sec = r['sec0'] + j
            ev.append(('R', e + 1, sec % 8))
            nj = j + 1
            if j == r['ns'] - 1:
                full_at[rrow & 1] = e + FULL
                if rrow + 1 == m:
                    nrs = 'DONE'
                else:
                    nrs, nrrow = 'ROW', rrow + 1
        # selector
        nst, nsrow, nph, ncnt, nwi = st, srow, ph, cnt, wi
        sb = srow & 1
        if st == 'WAIT':
            if sb in full_at and full_at[sb] < e:
                del full_at[sb]
                nst, nph, ncnt = 'SEL', 0, 0
        elif st == 'SEL':
            nph = (ph + 1) % ROUND
            if ph == ROUND - 1:
                ncnt = cnt + 1
                if cnt + 1 == k:
                    nst = 'RK1'
        elif st == 'RK1':
            nbusy[sb] = 0
            nst = 'RK2'
        elif st == 'RK2':
            nst = 'PK1'
        elif st == 'PK1':
            nst = 'PKO'
        elif st == 'PKO':
            nst, nwi = 'WR', 0
        elif st == 'WR':
            secs = rows[srow]['wsecs']
            W = e
            ev.append(('H', W + 1, secs[wi] % 8))
            ev.append(('P', W + 1 + V.HUB_TO_BANK, secs[wi] % 8))
            ev.append(('A', W + 1 + V.RESP, wi))
            nwi = wi + 1
            if wi + 1 == len(secs):
                nst = 'NEXT'
        elif st == 'NEXT':
            if srow + 1 == m:
                end = e + V.ACK          # done registered ACK edges after NEXT = W_last + ACK + 1
            else:
                nst, nsrow = 'WAIT', srow + 1
        rs, rrow, j, busy = nrs, nrrow, nj, nbusy
        st, srow, ph, cnt, wi = nst, nsrow, nph, ncnt, nwi
        e += 1
    return ev, end, True
_base_make = V.make_records


def make_records(rng, count):
    recs = []
    prod = dict(k=6, n=384, order=1, am=1, nan=False, prod=True)
    j = 0
    # P1 production (the AR record) and the P-row record of the same shape, aligned and unaligned row bases,
    # with and without R, normal and tie-heavy scores
    for m, a_str, a_off, has_r, mode in ((1, 384, 0, 1, 2), (P, 384, 0, 1, 2), (1, 384, 3, 0, 2), (P, 387, 3, 0, 2),
                                         (P, 384, 0, 1, 1), (P, 392, 5, 1, 0)):
        recs.append(dict(prod, m=m, a=40960 + 4096 * j + a_off, a_str=a_str, has_r=has_r, mode=mode,
                         o=56000 + 64 * j + a_off, o_str=8, r=57600 + 64 * j + 2 * a_off, r_str=8 + (j % 2) * 3,
                         kind=f"P{m}"))
        j += 1
    rest = _base_make(rng, count)
    return recs + [r for r in rest if not r['prod']]


V.make_records = make_records
if ENGINE == "rows":
    V.schedule = schedule_rows
out = Path(sys.argv[1])
seed = sys.argv[3] if len(sys.argv) > 3 else "0"
sys.argv = [sys.argv[0], str(out), str(NRAND), seed]
print(f"engine {ENGINE}")
V.main()
lines = (out / 'rec.txt').read_text().split('\n')[1:]
rows = []
for ln in lines:
    if not ln.strip():
        continue
    f = ln.split()
    rows.append(dict(G=int(f[0], 16), end=int(f[1], 16), fault=int(f[2]), k=int(f[3], 16), n=int(f[5], 16),
                     m=int(f[6], 16), am=int(f[7]), a_str=int(f[9], 16), has_r=int(f[12])))
(out / 'rows.json').write_text(json.dumps(rows, indent=1))
for r in rows[:6]:
    print(f"prod m{r['m']} has_r{r['has_r']} a_str{r['a_str']}: G {r['G']} done edge {r['end']} -> {r['end'] - r['G'] + 1} edges")
