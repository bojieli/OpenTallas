#!/usr/bin/env python3
"""Plans + expects for the DSpark verify-layer component at the TARGET context (Qwen3-8B, position ~8,191).

Owner measurement rule: one representative decoder layer at the longest target position, with a rejection.
Golden: two layer-0 runs of the GPU position oracle (tools/qwen_rom_position_oracle_gpu.py --layers 1):
  A  the prompt, positions P .. P+4 recorded (P = 8187): the AR golden at P, the KV window before P, and the
     step-2 block P+1 .. P+4 (the prompt's tokens);
  B  the prompt to P, then three DRAFT tokens at P+1 .. P+3 that differ from the prompt's (all rejected).
Jobs (tools/qwen_rom_rt_vprm_w12.py, one die instance, one KV service, HBM preloaded with A's window before P):
  L0   S1L0 verify block P .. P+3 = [t_P, r1, r2, r3] (np 4); host COMMIT 1 (a = 0: the three drafts rejected,
       their K/V rows P+1 .. P+3 stay in HBM); S2L0 verify block P+1 .. P+4 = the prompt over the HBM the RTL
       left (rollback by the committed length: the rejected rows are rewritten before they are read)
  AR0  ARL0 = AR (np 1) at P on the same path (p = 1 images)
Every stage output is checked bit-exactly (X of every position on every die, the K/V rows written).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from qwen_dspark_step_plans import XB4, e4m3


def body(path):
    return ''.join(line + '\n' for line in Path(path).read_text().split() if not line.startswith('@'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--gold-a', type=Path, required=True)
    ap.add_argument('--gold-b', type=Path, required=True)
    ap.add_argument('--P', type=int, default=8187)
    ap.add_argument('--img4', type=Path, required=True, help='verify images (np 4): L0-d<d>')
    ap.add_argument('--img1', type=Path, required=True, help='AR images (np 1): L0-d<d>')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    P = a.P
    A = lambda p: a.gold_a / f'P{p}'  # noqa: E731
    B = lambda p: a.gold_b / f'P{p}'  # noqa: E731
    s1 = [A(P), B(P + 1), B(P + 2), B(P + 3)]
    s2 = [A(P + 1), A(P + 2), A(P + 3), A(P + 4)]
    tok = lambda d: json.loads((d / 'embedding_row.json').read_text())['token']  # noqa: E731
    t1, t2 = [tok(d) for d in s1], [tok(d) for d in s2]
    if any(x == y for x, y in zip(t1[1:], t2)) or t1[0] != tok(A(P)):
        raise SystemExit(f'drafts must differ from the prompt at every rejected position: {t1} vs {t2}')
    out = a.out
    kvd = out / 'kv'
    kvd.mkdir(parents=True, exist_ok=True)
    for d in range(4):
        np.load(A(P) / 'kv_pre' / f'L0_die{d}.npy').astype('<u4').tofile(kvd / f'L0_die{d}.bin')
    dirs = lambda img: ' '.join(str(img / f'L0-d{d}') for d in range(4))  # noqa: E731

    def preload(path, srcs, bases):
        path.write_text(''.join(f'@{b:x}\n' + body(s / 'x_preload.hex') for s, b in zip(srcs, bases)))
        return path

    def kvblk(path, pds, d):
        lines = []
        for j, pd in enumerate(pds):
            g = json.loads((pd / 'kv_at_P' / f'L0_die{d}.json').read_text())
            lines += [f'K {j} {i // 128} {i % 128} {e4m3(int(b, 16)):02x}' for i, b in enumerate(g['k_bits'])]
            lines += [f'V {j} {i // 128} {i % 128} {e4m3(int(b, 16)):02x}' for i, b in enumerate(g['v_bits'])]
        path.write_text('\n'.join(lines) + '\n')
        return str(path)

    j = out / 'L0'
    j.mkdir(exist_ok=True)
    x1, x2 = preload(j / 'x1.hex', s1, XB4), preload(j / 'x2.hex', s2, XB4)
    (j / 'plan').write_text(f'XBASES {",".join(map(str, XB4))}\n'
                            f'STAGE S1L0 0 0 {P} 4 0 0 {x1} {dirs(a.img4)}\n'
                            f'STAGE S2L0 0 0 {P + 1} 4 1 0 {x2} {dirs(a.img4)}\n')
    exp = {'stages': {
        'S1L0': {'x': {f'p{q}_die{d}': str(s1[q] / f'L00_die{d}_x.hex') for q in range(4) for d in range(4)},
                 'kv': {f'die{d}': kvblk(j / f's1_die{d}_kvblk.hex', s1, d) for d in range(4)}},
        'S2L0': {'x': {f'p{q}_die{d}': str(s2[q] / f'L00_die{d}_x.hex') for q in range(4) for d in range(4)},
                 'kv': {f'die{d}': kvblk(j / f's2_die{d}_kvblk.hex', s2, d) for d in range(4)}}}}
    (j / 'expect.json').write_text(json.dumps(exp, indent=1) + '\n')
    ja = out / 'AR0'
    ja.mkdir(exist_ok=True)
    x0 = preload(ja / 'x0.hex', [A(P)], [4096])
    (ja / 'plan').write_text(f'XBASES 4096\nSTAGE ARL0 0 0 {P} 1 0 0 {x0} {dirs(a.img1)}\n')
    (ja / 'expect.json').write_text(json.dumps({'stages': {'ARL0': {
        'x': {f'p0_die{d}': str(A(P) / f'L00_die{d}_x.hex') for d in range(4)},
        'kv': {f'die{d}': kvblk(ja / f'ar_die{d}_kvblk.hex', [A(P)], d) for d in range(4)}}}}, indent=1) + '\n')
    rec = {'P': P, 'P2': P + 1, 'a': 0, 'commit': 1, 's1_tokens': t1, 's2_tokens': t2,
           'jobs': {'L0': str(j), 'AR0': str(ja)}, 'kv_dir': str(kvd)}
    (out / 'jobs.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec))


if __name__ == '__main__':
    main()
