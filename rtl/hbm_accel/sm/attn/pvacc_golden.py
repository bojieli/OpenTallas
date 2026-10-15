#!/usr/bin/env python3
"""Stimulus + golden for ot_hbm_accel_smh_pvacc (H-ELEM-A 2026-10-15): golden = tools/hgi_sim/lib.py att_pv order
(csum8 over positions: chunk = sequential from +0, chunks pairwise, +0 padded) restricted to aligned 4-chunk groups;
binary32 RNE with +0 zero results (tools/hdc_golden.py add / mul).
usage: pvacc_golden.py gen <dir> [seed]   -> stim.hex, expect.txt
       pvacc_golden.py check <dir>        -> PVACC EXACT PASS / FAIL (compares <dir>/out.txt)"""
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden as G  # noqa: E402
F = np.float32
NE, NK = 8, 4


def e4m3(code):
    s, ex, m = code >> 7, (code >> 3) & 15, code & 7
    v = (2.0 ** (ex - 7)) * (1 + m / 8) if ex else (2.0 ** -6) * (m / 8)
    return -v if s else v


def gen(d, seed):
    rng = np.random.default_rng(seed)
    rows = []                                      # per row: p, codes [NK][NE], e [NK]
    groups = [(4, 8)] * 5 + [(4, 3)] + [(3, 8)]    # (chunks, rows in the last chunk); short last chunk / group
    groups = [(4, 8)] * 5 + [(4, 5), (3, 8), (2, 8), (1, 6)]
    stim, expect = [], []
    for gi, (nch, lastrows) in enumerate(groups):
        csums = []
        for ci in range(nch):
            nr = lastrows if ci == nch - 1 else 8
            acc = np.zeros((NK, NE), dtype=F)
            for r in range(nr):
                p = F(G.to_bf16(F(rng.uniform(0, 1))))
                for k in range(NK):
                    codes = rng.integers(0, 256, NE)
                    codes[codes == 0x7f] = 0x7e; codes[codes == 0xff] = 0xfe
                    e = int(rng.integers(-12, 12))
                    w = np.array([e4m3(int(c)) * 2.0 ** e for c in codes], dtype=F)
                    y = G.mul(p, w)
                    acc[k] = G.add(F(0) if r == 0 else acc[k], y)
                    gap = int(rng.integers(0, 3)) if rng.uniform() < 0.3 else 0
                    for _ in range(gap):
                        stim.append('0 0 0 0 0 0 %016x %03x %08x' % (0, 0, 0))
                    cv = ''.join('%02x' % int(c) for c in codes[::-1])
                    stim.append('1 %d %d %d %d %d %s %03x %08x' % (k, r == 0, r == nr - 1, ci, ci == nch - 1, cv,
                                                                   e & 0x3ff, np.asarray(p, dtype=F).view(np.uint32)))
            csums.append(acc)
        while len(csums) < 4:
            csums.append(np.zeros((NK, NE), dtype=F))
        g = G.add(G.add(csums[0], csums[1]), G.add(csums[2], csums[3]))
        for k in range(NK):
            expect.append('%d %s' % (k, ''.join('%08x' % v for v in np.asarray(g[k], dtype=F).view(np.uint32)[::-1])))
    for _ in range(40):
        stim.append('0 0 0 0 0 0 %016x %03x %08x' % (0, 0, 0))
    Path(d).mkdir(parents=True, exist_ok=True)
    Path(d, 'stim.txt').write_text('\n'.join(stim) + '\n')
    Path(d, 'expect.txt').write_text('\n'.join(expect) + '\n')
    print(f'stim {len(stim)} edges, {len(expect)} group outputs')


def check(d):
    exp = Path(d, 'expect.txt').read_text().split('\n')
    out = Path(d, 'out.txt').read_text().split('\n')
    exp = [x for x in exp if x]; got = [x.replace('OUT ', '') for x in out if x.startswith('OUT')]
    fault = any(x.startswith('FAULT') for x in out)
    bad = sum(1 for a, b in zip(exp, got) if a != b) + abs(len(exp) - len(got))
    print(f'PVACC EXACT {"PASS" if bad == 0 and not fault else "FAIL"} outputs {len(got)}/{len(exp)} mismatches {bad} fault {int(fault)}')
    sys.exit(0 if bad == 0 and not fault else 1)


if __name__ == '__main__':
    if sys.argv[1] == 'gen':
        gen(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        check(sys.argv[2])
