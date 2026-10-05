#!/usr/bin/env python3
"""Plans + expects for the full-shape DSpark speculative step on the VPRM REAL_MEM runtime, layer-parallel.

From the GPU ISA golden run (tools/qwen_rom_dspark_oracle_gpu_w12.py: oracle.json, kv_P<P>/, step1_P<P>/pos*/,
step2_P<P'>/pos*/) and verify images (tools/qwen_rom_verify_program_w12.py at p = 1 and p = 4), one job per
decoder layer n, three stages in ONE die instance (one KV service, HBM region 0 preloaded with the layer's
window before P from the golden):
  S1L<n>  verify block P .. P+3 (np 4), X of the 4 positions from the golden's layer input
  S2L<n>  host COMMIT of a+1 positions (the step-1 accept, checked equal to the RTL head's), then the step-2
          block P' .. P'+3 over the HBM state the RTL left (rejected rows still in HBM: rollback by the
          committed length)
  ARL<n>  AR (p = 1) at P (the AR baseline on the same path; reads only rows < P)
and two head jobs (H1, H2: the p = 4 verify head, ACCEPT with the pending token and drafts, the accept unit
fires).  Every stage output is checked bit-exactly (X of every position on every die, the written K/V).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

XB4 = [16384, 109424, 202464, 295504]


def e4m3(bits):
    s, e, m = bits >> 31, (bits >> 23) & 255, bits & 0x7fffff
    if e == 0 and m == 0:
        return s << 7
    if 121 <= e <= 135 and m & 0xfffff == 0:
        return (s << 7) | ((e - 120) << 3) | (m >> 20)
    if e == 120 and m & 0x1fffff == 0:
        return (s << 7) | 4 | (m >> 21)
    if e == 119 and m & 0x3fffff == 0:
        return (s << 7) | 2 | (m >> 22)
    if e == 118 and m == 0:
        return (s << 7) | 1
    raise ValueError(f'{bits:08x}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--oracle', type=Path, required=True, help='golden run dir (oracle.json)')
    ap.add_argument('--img4', type=Path, required=True)
    ap.add_argument('--img1', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--layers', type=int, default=36, help='decoder-layer jobs 0 .. N-1 (the owner rule: one layer)')
    ap.add_argument('--head-input-layer', type=int, default=35)
    a = ap.parse_args()
    o = json.loads((a.oracle / 'oracle.json').read_text())
    s1, s2 = o['step1'], o['step2']
    P, P2, acc = s1['P'], s2['P'], s1['accepted']
    assert P2 == P + acc + 1 and acc < len(s1['block_tokens']) - 1
    d1 = a.oracle / f'step1_P{P}'
    d2 = a.oracle / f'step2_P{P2}'
    a.out.mkdir(parents=True, exist_ok=True)
    dirs = lambda img, name: ' '.join(str(img / f'{name}-d{d}') for d in range(4))  # noqa: E731

    def preload(path, srcs, bases):
        path.write_text(''.join(f'@{b:x}\n' + Path(s).read_text() for s, b in zip(srcs, bases)))
        return path

    def kvblk(path, posdirs, n, d):
        lines = []
        for j, pd in enumerate(posdirs):
            g = json.loads((pd / 'kv_at_P' / f'L{n}_die{d}.json').read_text())
            lines += [f'K {j} {i // 128} {i % 128} {e4m3(int(b, 16)):02x}' for i, b in enumerate(g['k_bits'])]
            lines += [f'V {j} {i // 128} {i % 128} {e4m3(int(b, 16)):02x}' for i, b in enumerate(g['v_bits'])]
        path.write_text('\n'.join(lines) + '\n')
        return str(path)

    p1 = [d1 / f'pos{p}' for p in s1['positions']]
    p2 = [d2 / f'pos{p}' for p in s2['positions']]
    jobs = {}
    for n in range(a.layers):
        j = a.out / f'L{n}'
        j.mkdir(exist_ok=True)
        x1 = preload(j / 'x1.hex', [pd / f'L{n:02d}_die0_xin.hex' for pd in p1], XB4)
        x2 = preload(j / 'x2.hex', [pd / f'L{n:02d}_die0_xin.hex' for pd in p2], XB4)
        x0 = preload(j / 'x0.hex', [p1[0] / f'L{n:02d}_die0_xin.hex'], [4096])
        plan = [f'XBASES {",".join(map(str, XB4))}',
                f'STAGE S1L{n} {n} 0 {P} 4 0 0 {x1} {dirs(a.img4, f"L{n}")}',
                f'STAGE S2L{n} {n} 0 {P2} 4 {acc + 1} 0 {x2} {dirs(a.img4, f"L{n}")}']
        exp = {'stages': {
            f'S1L{n}': {'x': {f'p{q}_die{d}': str(p1[q] / f'L{n:02d}_die{d}_x.hex') for q in range(4) for d in range(4)},
                        'kv': {f'die{d}': kvblk(j / f's1_die{d}_kvblk.hex', p1, n, d) for d in range(4)}},
            f'S2L{n}': {'x': {f'p{q}_die{d}': str(p2[q] / f'L{n:02d}_die{d}_x.hex') for q in range(4) for d in range(4)},
                        'kv': {f'die{d}': kvblk(j / f's2_die{d}_kvblk.hex', p2, n, d) for d in range(4)}}}}
        (j / 'plan').write_text('\n'.join(plan) + '\n')
        (j / 'expect.json').write_text(json.dumps(exp, indent=1) + '\n')
        # AR baseline at P on the same path (its own job: p = 1 X base 4096)
        ja = a.out / f'AR{n}'
        ja.mkdir(exist_ok=True)
        (ja / 'plan').write_text(f'XBASES 4096\nSTAGE ARL{n} {n} 0 {P} 1 0 0 {x0} {dirs(a.img1, f"L{n}")}\n')
        (ja / 'expect.json').write_text(json.dumps({'stages': {f'ARL{n}': {
            'x': {f'p0_die{d}': str(p1[0] / f'L{n:02d}_die{d}_x.hex') for d in range(4)},
            'kv': {f'die{d}': kvblk(ja / f'ar_die{d}_kvblk.hex', p1[:1], n, d) for d in range(4)}}}}, indent=1) + '\n')
        jobs[f'L{n}'] = str(j); jobs[f'AR{n}'] = str(ja)
    L = a.head_input_layer
    for tag, st, pds in (('H1', s1, p1), ('H2', s2, p2)):
        j = a.out / tag
        j.mkdir(exist_ok=True)
        xh = preload(j / 'xh.hex', [pd / f'L{L:02d}_die0_x.hex' for pd in pds], XB4)
        toks = st['block_tokens']
        (j / 'plan').write_text(f'XBASES {",".join(map(str, XB4))}\nACCEPT {" ".join(map(str, toks))}\n'
                                f'STAGE {tag} -1 0 {st["P"]} 4 0 1 {xh} {dirs(a.img4, "head")}\n')
        ys = st['argmax']
        (j / 'expect.json').write_text(json.dumps({'stages': {}, 'tokens': ys, 'accept': {
            'a': st['accepted'], 'n_emit': st['accepted'] + 1, 'bonus': ys[st['accepted']]}}, indent=1) + '\n')
        jobs[tag] = str(j)
    # AR head at P (p = 1)
    j = a.out / 'H0'
    j.mkdir(exist_ok=True)
    xh = preload(j / 'xh.hex', [p1[0] / f'L{L:02d}_die0_x.hex'], [4096])
    (j / 'plan').write_text(f'XBASES 4096\nSTAGE H0 -1 0 {P} 1 0 0 {xh} {dirs(a.img1, "head")}\n')
    (j / 'expect.json').write_text(json.dumps({'stages': {}, 'tokens': s1['argmax'][:1]}, indent=1) + '\n')
    jobs['H0'] = str(j)
    (a.out / 'jobs.json').write_text(json.dumps({'P': P, 'P2': P2, 'a': acc, 'jobs': jobs}, indent=1) + '\n')
    print(json.dumps({'P': P, 'P2': P2, 'a': acc, 'n_jobs': len(jobs)}))


if __name__ == '__main__':
    main()
