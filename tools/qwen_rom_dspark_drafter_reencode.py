#!/usr/bin/env python3
"""Re-encode packed DSpark drafter layer programs at another frozen start position (default-off helper).

The drafter layer program (qwen_rom_dspark_draft_isa.encode_layer, Codex commit 3fdf7430c) freezes every dynamic
field at a start position: S slots at start .. start+S-1, attention over start+S positions.  Measuring a drafter
layer at the TARGET context (owner rule: Qwen3-8B position ~8,191) needs the same layer program frozen at a start
near 8,188.  Only program.hex / segments.hex / context_program.hex / context_segments.hex depend on the start; the
matrices, scales and constant ROM are copied unchanged.

Before writing anything, the retained images are re-encoded at THEIR start (drafter_layer.json
context_program_position + 1) and must reproduce every program file byte for byte.

  python3 tools/qwen_rom_dspark_drafter_reencode.py --source-tools <checkout of 3fdf7430c>/tools \
      --images <retained images> --start 8188 --layers 0 --out <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

PROGRAM_FILES = ('program.hex', 'segments.hex', 'context_program.hex', 'context_segments.hex')
COPIED_FILES = ('crom.hex', 'matrix_int8.hex', 'matrix_scale_bf16.hex')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--source-tools', type=Path, required=True, help='tools/ of the image emitter (3fdf7430c)')
    ap.add_argument('--images', type=Path, required=True, help='retained drafter images (D<n>-d<rank>/)')
    ap.add_argument('--start', type=int, required=True)
    ap.add_argument('--slots', type=int, default=3)
    ap.add_argument('--layers', default='0')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    os.environ['QWEN_O4_TP'] = '4'
    os.environ['HDC_SU_WIDTH'] = '64'
    sys.path.insert(0, str(a.source_tools.resolve()))
    import hdc_qwen_fullshape_program_w12 as FP
    from qwen_rom_dspark_images import context_kv_program, encode_layer, encode_program

    def encode(manifest, rank, start):
        lay = FP.LayerZero(None, rank, manifest['matrix_layout'])
        lay.norm_fold = False
        prog, desc = encode_layer(lay, a.slots, start, manifest['post_tp_scale_bases'], enabled=True)
        cw, cd = encode_program(context_kv_program(lay, start - 1, enabled=True))
        return (''.join(f'{w:0256x}\n' for w in prog), ''.join(f'{w:016x}\n' for w in desc),
                ''.join(f'{w:0256x}\n' for w in cw), ''.join(f'{w:016x}\n' for w in cd))

    rec = {'schema': 'opentallas.qwen-dspark-drafter-reencode.v1', 'start': a.start, 'slots': a.slots,
           'source_tools_sha256': {f: hashlib.sha256((a.source_tools / f).read_bytes()).hexdigest()
                                   for f in ('qwen_rom_dspark_images.py', 'qwen_rom_dspark_draft_isa.py')},
           'stages': {}}
    for layer in (int(x) for x in a.layers.split(',')):
        for rank in range(4):
            src = a.images / f'D{layer}-d{rank}'
            m = json.loads((src / 'drafter_layer.json').read_text())
            retained_start = m['context_program_position'] + 1
            for text, f in zip(encode(m, rank, retained_start), PROGRAM_FILES):
                if text != (src / f).read_text():
                    raise SystemExit(f'{src / f}: re-encoding at the retained start {retained_start} does not reproduce it')
            dst = a.out / f'D{layer}-d{rank}'
            dst.mkdir(parents=True, exist_ok=True)
            text = encode(m, rank, a.start)
            for t, f in zip(text, PROGRAM_FILES):
                (dst / f).write_text(t)
            for f in COPIED_FILES:
                (dst / f).write_bytes((src / f).read_bytes())
            m.update(context_program_position=a.start - 1, program_words=len(text[0].split()), segments=len(text[1].split()))
            (dst / 'drafter_layer.json').write_text(json.dumps(m, indent=1) + '\n')
            rec['stages'][dst.name] = {'retained_start_reproduced': retained_start,
                                       **{f: hashlib.sha256((dst / f).read_bytes()).hexdigest() for f in PROGRAM_FILES}}
    (a.out / 'reencode.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('start', 'slots')} | {'stages': len(rec['stages'])}))


if __name__ == '__main__':
    main()
