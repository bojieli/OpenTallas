#!/usr/bin/env python3
"""Re-emit a Qwen O4 stage's program for another stream-unit width (HDC_SU_WIDTH).

The program's chase thresholds count stream-unit VECTORS (hdc_program.chase_threshold),
so a program must be emitted for the width of the stream unit that runs it; nothing
else in the image depends on it (the arithmetic of a vector stream unit is the
width-independent R-ARITH order, hdc_golden.reduce_chunked).  This writes a stage
directory whose program.hex (layers: FP.profile with the image's own matrix layout and
post-TP scale bases; lm_head: FP.profile_lm_head) is emitted at HDC_SU_WIDTH, with every
other file linked from the source image, and a manifest pinning both.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import hdc_isa as I
import hdc_qwen_fullshape_program_w12 as FP


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--src', type=Path, required=True)
    ap.add_argument('--dst', type=Path, required=True)
    ap.add_argument('--head-die', type=int, choices=range(4), help='the source is an lm_head stage of this die')
    ap.add_argument('--head-geometry', type=Path, help='head_rom.json of that die (geometry)')
    a = ap.parse_args()
    a.dst.mkdir(parents=True, exist_ok=True)
    if a.head_die is None:
        man = json.loads(next(a.src.glob('layer*_rom.json')).read_text())
        prog = FP.profile(man['die'], matrix_rows=man['matrix_layout'], post_scale_bases=man['post_tp_scale_bases'])
    else:
        geo = dict(json.loads(a.head_geometry.read_text())['geometry'])
        geo['scale_base'] = 0
        prog = FP.profile_lm_head(a.head_die, geo, 0)
    old = (a.src / 'program.hex').read_text().split()
    (a.dst / 'program.hex').write_text('\n'.join(prog['program_hex']) + '\n')
    for name in ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex', 'segments.hex'):
        link = a.dst / name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to((a.src / name).resolve())
    seg = (a.src / 'segments.hex').read_text().split()
    if [s.lower() for s in prog['descriptor_hex']] != [s.lower() for s in seg]:
        raise SystemExit('segment descriptors differ at this width')
    diff = sum(x.lower() != y.lower() for x, y in zip(old, prog['program_hex'])) + abs(len(old) - len(prog['program_hex']))
    rec = {'schema': 'opentallas.qwen-rom-program-sw.v1', 'su_width': I.SU_WIDTH,
           'source_program_sha256': sha(a.src / 'program.hex'), 'program_sha256': sha(a.dst / 'program.hex'),
           'instructions_changed': diff, 'tool_sha256': sha(Path(__file__))}
    (a.dst / 'program_sw.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec))


if __name__ == '__main__':
    main()
