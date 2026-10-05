#!/usr/bin/env python3
"""Static HBM weight stream of one stage program (the compiler-known read order).

For each weight-sourced ME instruction in program order this lists the INT8
code-word addresses exactly as ot_hdc_matvec's issue loop presents them
(round r, then k, then slot j: wbase + r*ts + k*ks + (j >> jsh)*js),
with consecutive repeats merged.  The first line gives the stage's BF16 row-
scale bytes (2 per output row of every weight op), which the supply model
fetches ahead of the stage's first code word.  The runtime supply checks every
engine read against this stream and fails closed on a mismatch.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import hdc_isa as I
import hdc_qwen_fullshape_isa as QI


def stream(program_hex: Path):
    words, scale_bytes = [], 0
    for line in program_hex.read_text().split():
        f = QI.decode_instruction(int(line, 16))
        if f['unit'] != I.UNIT_ME or f['me_wsrc']:
            continue
        if f['me_d_wbase'] or f['me_d_tiles'] or f['me_d_k'] or f['me_d_nout']:
            raise ValueError('weight op with DYN geometry: stream is not static')
        for r in range(f['me_tiles']):
            for k in range(f['me_k']):
                for j in range(I.INTERLEAVE):
                    a = f['me_wbase'] + r * f['me_ts'] + k * f['me_ks'] + (j >> f['me_jsh']) * f['me_js']
                    if not words or words[-1] != a:
                        words.append(a)
        scale_bytes += 2 * f['me_nout']
    return words, scale_bytes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--stages', type=Path, required=True, help='stage file: name die0dir die1dir kv_reset')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for line in args.stages.read_text().splitlines():
        if not line.strip():
            continue
        name, d0, d1, _ = line.split()
        for d, path in enumerate((d0, d1)):
            words, sb = stream(Path(path) / 'program.hex')
            (args.out / f'{name}_d{d}.wstream').write_text(f'{sb}\n' + ''.join(f'{w}\n' for w in words))
            print(name, d, len(words), sb)


if __name__ == '__main__':
    main()
