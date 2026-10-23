#!/usr/bin/env python3
"""RTLGAP-G9 G-KV-LEAF check: decode the RD beats u_s_3N sent on its E line (trace ports 1444..1447 =
o__w_xrE_3N_l0..l3_src) and compare rows 672..771 bit-exactly with expected.mem (25 x 512 b, row 8 = 8 exponent words).
Beat (ot_s81sl_xrt snd): [0] v, [3:1] kind, [8:4] hops, [12:9] src sid, [21+16] mask, [37+3] leaf, [40+10] row,
[50+2] pairs-1, [52+1024] pairs (pair p = 256 b at 256 p: low 128 = row a0 + 2p, high = a0 + 2p + 1)."""
import json, sys
from collections import defaultdict
from pathlib import Path

run, prog, expf = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
P = json.loads((prog / 'plan.json').read_text())
lanes = defaultdict(dict)
OP = [str(x) for x in P.get('out_ports', [1444, 1445, 1446, 1447])]
for l in (run / 'trace.txt').read_text().splitlines():
    c, p, v = l.split()
    if p in OP:
        lanes[int(c)][OP.index(p)] = int(v, 16)
cur = [0, 0, 0, 0]; beats = []
for c in sorted(lanes):
    for k, v in lanes[c].items():
        cur[k] = v
    b = sum(cur[k] << (276 * k) for k in range(4))
    if b & 1 and (b >> 1) & 7 == 4 and (b >> 9) & 0xF == P['sid']:
        beats.append((c, b))
rows = {}
for (c, b), rd in zip(beats, P['rdout']):
    pk = b >> 52
    for p in range(4):
        pr = (pk >> (256 * p)) & ((1 << 256) - 1)
        rows[rd['a0'] + 2 * p] = pr & ((1 << 128) - 1)
        rows[rd['a0'] + 2 * p + 1] = pr >> 128
E = [int(l, 16) for l in expf.read_text().split()]
bad = chk = 0; first = []
for i in range(25):
    for j in range(16):
        if i == 8 and j >= 8:
            continue
        r = 672 + 4 * i + j // 4
        got = (rows.get(r, -1) >> (32 * (j % 4))) & 0xFFFFFFFF if r in rows else None
        want = (E[i] >> (32 * j)) & 0xFFFFFFFF
        chk += 1
        if got != want:
            bad += 1
            if len(first) < 6:
                first.append(dict(row=r, word=j % 4, got=None if got is None else f'{got:08x}', want=f'{want:08x}'))
res = dict(rd_beats=len(beats), rdouts=len(P['rdout']), beat_cycles=[c for c, _ in beats], words_checked=chk,
           mismatches=bad, first_mismatches=first, mut_row=P['mut_row'],
           verdict='PASS' if bad == 0 and len(beats) == len(P['rdout']) else 'FAIL')
(run / 'kvleaf_check.json').write_text(json.dumps(res, indent=1) + '\n')
print('KVLEAF_CHECK', res['verdict'], 'beats', len(beats), 'words', chk, 'bad', bad, first[:2])
