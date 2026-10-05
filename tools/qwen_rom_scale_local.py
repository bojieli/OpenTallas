#!/usr/bin/env python3
"""Port-local scale ROM image of one Qwen O4 stage (ot_hdc_matvec_part SCALE_LOCAL = 1).

The dense scale image holds, for a K-split matrix of per_round = G/S tiles a
round, word  wcs + round*per_round*IL + q*IL + slot  for result-port group q.
With SCALE_LOCAL each port group q holds only its own words, at
    LB(m) + round*IL + slot,   LB(m) = sum over the stage's earlier matrices of rounds*IL
(every port reserves every matrix's rounds; a port beyond a matrix's
per_round holds 1.0 padding it never reads).  This tool rewrites a stage:
program.hex with each dense matrix op's me_wcs set to LB(m), and
matrix_scale_port.hex, NP port images of DEPTH words back to back (header line
"@ports NP depth DEPTH" is not used: the depth is in scale_port.json).  The
other stage files are linked unchanged.  Values are the dense image's words,
so the arithmetic is unchanged; the RTL run with SCALE_LOCAL = 1 must give the
dense run's results bit for bit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import hdc_isa as I
import hdc_qwen_fullshape_isa as QI

W, IL = I.W_LANES, I.INTERLEAVE


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def convert(src: Path, dst: Path, groups: int, smin: int):
    dst.mkdir(parents=True, exist_ok=True)
    words = (src / 'program.hex').read_text().split()
    prog = [QI.decode_instruction(int(w, 16)) for w in words]
    dense = (src / 'matrix_scale_bf16.hex').read_text().split()
    ports = groups >> smin
    lb = 0
    plan = []
    for i, f in enumerate(prog):
        if f['unit'] != I.UNIT_ME or f['me_wsrc']:
            continue
        per_round = groups >> f['me_split']
        rounds = f['me_tiles']
        plan.append((i, f['me_wcs'], per_round, rounds, lb))
        lb += rounds * IL
    depth = lb
    pad = '3f80' * W
    img = [[pad] * depth for _ in range(ports)]
    for i, wcs, per_round, rounds, base in plan:
        for q in range(min(ports, per_round)):
            for r in range(rounds):
                for j in range(IL):
                    a = wcs + r * per_round * IL + q * IL + j
                    img[q][base + r * IL + j] = dense[a] if a < len(dense) else pad
        prog[i] = dict(prog[i], me_wcs=base)
    out_words = []
    for f, w in zip(prog, words):
        e = QI.encode_instruction(f)
        out_words.append(f'{e:0{len(w)}x}')
    (dst / 'program.hex').write_text('\n'.join(out_words) + '\n')
    with (dst / 'matrix_scale_port.hex').open('w') as fh:
        for q in range(ports):
            fh.write('\n'.join(img[q]) + '\n')
    for name in ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex', 'segments.hex'):
        link = dst / name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to((src / name).resolve())
    rec = {'schema': 'opentallas.qwen-rom-scale-local.v1', 'groups': groups, 'smin': smin, 'ports': ports,
           'depth_words_per_port': depth, 'matrix_ops': len(plan),
           'source': {n: sha(src / n) for n in ('program.hex', 'matrix_scale_bf16.hex')},
           'out': {n: sha(dst / n) for n in ('program.hex', 'matrix_scale_port.hex')},
           'tool_sha256': sha(Path(__file__))}
    (dst / 'scale_port.json').write_text(json.dumps(rec, indent=1) + '\n')
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--src', type=Path, required=True)
    ap.add_argument('--dst', type=Path, required=True)
    ap.add_argument('--groups', type=int, default=6144)
    ap.add_argument('--smin', type=int, default=6)
    a = ap.parse_args()
    r = convert(a.src, a.dst, a.groups, a.smin)
    print(json.dumps({k: r[k] for k in ('ports', 'depth_words_per_port', 'matrix_ops')}))


if __name__ == '__main__':
    main()
