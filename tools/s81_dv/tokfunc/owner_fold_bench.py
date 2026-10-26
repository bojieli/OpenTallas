#!/usr/bin/env python3
"""Prepare a minimum VP+VS owner-fold replay; run this on the fleet."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    root, out = Path(a.root).resolve(), Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'layer_prog'))
    from owner_fold import program
    plan = program(0, 2, 512, 600)
    ranks = np.array([[1e20, 1, -3, 1.0000001], [-1e20, 2, 1e-10, -1],
                      [3, 1e20, 4, 2], [1e-10, -1e20, -2, 1e-7]], dtype=np.float32)
    # Independent canonical TP4 reference, preserving each FP32 rounding point.
    expected = np.add(np.add(ranks[0], ranks[1], dtype=np.float32),
                      np.add(ranks[2], ranks[3], dtype=np.float32), dtype=np.float32)
    pack = lambda row: sum(int(w) << (32 * i) for i, w in enumerate(row))
    image = [0] * 1024
    for i, row in enumerate(ranks.view(np.uint32)):
        image[i] = pack(row)
    (out / 'img.mem').write_text(''.join(f'{x:032x}\n' for x in image))
    (out / 'imgv.mem').write_text(''.join(f'{int(i < 4):x}\n' for i in range(1024)))
    prog = [(1 << 188) | (11 << 184) | int(c['word'], 16) for c in plan['commands']]
    prog += [(2 << 188) | (11 << 184) | (1 << 160) | 600, 0]
    prog += [0] * (64 - len(prog))
    (out / 'prog.mem').write_text(''.join(f'{x:048x}\n' for x in prog))
    (out / 'exp.mem').write_text(f'{pack(expected.view(np.uint32)):064x}\n' + '0\n' * 255)
    (out / 'expm.mem').write_text('0f\n' + '00\n' * 255)
    (out / 'xq.mem').write_text('0\n' * 8)
    (out / 'xqi.mem').write_text('0\n' * 8)
    tb = root / 'rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_vs.sv'
    text = tb.read_text()
    old = ('nxq == 3 && !fp && !fs && !fq &&\n'
           '                           nck[8] > 0 && nck[10] > 0 && nck[11] > 0 && nck[12] > 0 && nck[13] > 0')
    if text.count(old) != 1:
        raise ValueError('Existing VP+VS bench verdict changed; inspect before adapting')
    (out / 'tb_owner_fold.sv').write_text(text.replace(old, 'nxq == 0 && !fp && !fs && !fq && nck[11] == 1'))
    script = (root / 'tools/s81_slice/vs_bench.sh').read_text()
    # vs_bench.sh (11ed229e0b+) prepends ${S81_VS_EXTRA_SOURCES:-}; expand it exactly as the shell would.
    script = script.replace('${S81_VS_EXTRA_SOURCES:-}', os.environ.get('S81_VS_EXTRA_SOURCES', ''))
    src = re.search(r'srcs="(.*?)"\n', script, re.S).group(1).split()
    src = [str(root / x) for x in src if not x.endswith('/tb_s81sl_vs.sv')]
    src.append(str(out / 'tb_owner_fold.sv'))
    (out / 'sources.f').write_text('\n'.join(src) + '\n')
    sources = {str(Path(s).relative_to(root)) if Path(s).is_relative_to(root) else s:
               hashlib.sha256(Path(s).read_bytes()).hexdigest() for s in src}
    (out / 'inputs.json').write_text(json.dumps(dict(plan=plan, sources=sources,
        inputs_fp32_bits=ranks.view(np.uint32).tolist(), expected_fp32_bits=expected.view(np.uint32).tolist(),
        scope='Synthetic finite FP32 rank partials; mechanism only. No checkpoint producer or collective transport qualification.'), indent=2) + '\n')


if __name__ == '__main__':
    main()
