#!/usr/bin/env python3
"""HC coefficient chain bench vectors (tb_s81_hcx_chain) for one layer, from hcx_real.py's released-operand dir.

Writes the layer's two HC residuals (attn x, ffn x; BF16 values) as VM H rows in the HC slab layout (hc_gate
Run.h_rows: row q = elements 8q..8q+7 of all four copies, copy k of element e at 16-bit slot 4*(e%8)+k; the layout the
layer's H landing producer / HC NORM / POST / H_STORE use), attn rows at 0..639 and ffn rows at 640..1279 (or the
canonical copy-major rows with --canonical: row q = x[32q..32q+31], the projection's component-receipt layout), and the
EXPECTED coefficient rows (independent golden: the snapshot's own pre/post/comb, hu_exp.mem, == Model.hc_mixes):
row 2c = comb (16 FP32), row 2c+1 = {pre4, post4, eps, 0 x 7}. These are compared, never written into the DUT.
"""
import argparse, json, re
from pathlib import Path


def rows16(words):
    return sum(int(w) << (32 * i) for i, w in enumerate(words))


def build(src, out, canonical):
    vm = {int(s[:8], 16): int(s[8:], 16) for s in (src / 'hu_vmi.mem').read_text().split()}
    ex = [int(s[8:], 16) for s in (src / 'hu_exp.mem').read_text().split()]
    eps = int(re.search(r"NEPS = 32'h([0-9A-Fa-f]+)", (src / 'hu_sizes.svh').read_text()).group(1), 16)
    cases = (src / 'hu_case.mem').read_text().split()
    assert len(cases) == 2 and len(ex) == 48
    h_lines, want = [], []
    for block, line in enumerate(cases):
        rec = int(line[56:], 16); a = (rec >> 128) & ((1 << 256) - 1); ab = (a >> 8) & ((1 << 40) - 1)
        x = [vm[ab + i] for i in range(20480)]
        assert all(v & 0xffff == 0 for v in x), 'HC residual must be BF16'
        bf = [v >> 16 for v in x]
        for q in range(640):
            if canonical:
                vals = bf[32 * q:32 * q + 32]
            else:
                vals = [bf[k * 5120 + 8 * q + s // 4] for s in range(32) for k in [s % 4]]
            h_lines.append(sum(v << (16 * i) for i, v in enumerate(vals)))
        w = ex[24 * block:24 * block + 24]
        want += [rows16(w[8:24]), rows16(w[:8] + [eps] + [0] * 7)]
    out.mkdir(parents=True, exist_ok=True)
    (out / 'h.mem').write_text(''.join(f'{r:0128x}\n' for r in h_lines))
    (out / 'want.mem').write_text(''.join(f'{r:0128x}\n' for r in want))
    (out / 'eps.mem').write_text(f'{eps:08x}\n')
    (out / 'meta.json').write_text(json.dumps(dict(source=str(src), layout='canonical' if canonical else 'hc_gate h_rows',
                                                   h_rows=dict(attn=[0, 639], ffn=[640, 1279]), eps=f'{eps:08x}',
                                                   golden='hu_exp.mem (snapshot pre/post/comb)'), indent=2) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--canonical', action='store_true')
    a = ap.parse_args()
    build(a.src, a.out, a.canonical)
